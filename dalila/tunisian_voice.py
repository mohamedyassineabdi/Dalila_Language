"""Opt-in local research voice with bounded CPU work and ephemeral repeat cache."""
import atexit
from collections import OrderedDict
import hashlib
import json
import logging
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import wave

ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.RLock()
CACHE_LOCK=threading.Lock()
CACHE=OrderedDict()
STATE="not_enabled"
LAST_ERROR=None
PROCESS=None
MESSAGES=None
STEPS=4
LOG=logging.getLogger(__name__)
MAX_CACHE_BYTES=2_000_000
MAX_CACHE_ENTRIES=12

def enabled():
    return os.getenv("DALILA_TUNISIAN_RESEARCH","0")=="1"

def worker_python():
    return ROOT/".venv-tunisian"/("Scripts/python.exe" if os.name=="nt" else "bin/python")

def readiness():
    if not enabled(): return "not_enabled"
    if STATE=="ready" and (PROCESS is None or PROCESS.poll() is not None):return "unavailable"
    return STATE

def diagnostics():
    return {"state":readiness(),"reason":LAST_ERROR,"steps":STEPS,
            "timeout_s":timeout_seconds(),"cached_replies":len(CACHE)}

def timeout_seconds():
    try:return max(15,min(120,int(os.getenv("DALILA_TUNISIAN_TIMEOUT","45"))))
    except ValueError:return 45

def _read_lines(process,messages):
    try:
        for line in process.stdout:
            try:
                item=json.loads(line)
                if isinstance(item,dict):messages.put(item)
            except ValueError:continue
    finally:
        messages.put({"error":"WorkerExited"})

def _stop():
    global PROCESS
    p=PROCESS
    PROCESS=None
    if p is not None:
        try:
            p.terminate()
            p.wait(timeout=3)
        except (OSError,subprocess.TimeoutExpired):
            try:p.kill()
            except OSError:pass

def prepare():
    global PROCESS,MESSAGES,STATE,LAST_ERROR,STEPS
    if not enabled():return False
    if not worker_python().is_file():
        STATE="not_installed"
        LAST_ERROR="ResearchEnvironmentMissing"
        return False
    with LOCK:
        if readiness()=="ready":return True
        STATE="preparing"
        LAST_ERROR=None
        try:
            _stop()
            env=dict(os.environ,PYTHONIOENCODING="utf-8",HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                     HF_HUB_DISABLE_TELEMETRY="1")
            for key in list(env):
                if key.endswith(("_API_KEY","_TOKEN")) or key in ("HF_TOKEN","HUGGING_FACE_HUB_TOKEN"):
                    env.pop(key,None)
            options={"creationflags":subprocess.BELOW_NORMAL_PRIORITY_CLASS} if os.name=="nt" else {}
            PROCESS=subprocess.Popen([str(worker_python()),"-u","-m","dalila.tunisian_worker"],
                                     cwd=str(ROOT),env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                     text=True,encoding="utf-8",bufsize=1,**options)
            MESSAGES=queue.Queue()
            threading.Thread(target=_read_lines,args=(PROCESS,MESSAGES),daemon=True).start()
            response=MESSAGES.get(timeout=900)
            if response.get("ready") is not True:
                LAST_ERROR=str(response.get("error","WorkerNotReady"))[:80]
                raise RuntimeError("Worker unavailable")
            STEPS=int(response.get("steps",4))
            STATE="ready"
            return True
        except Exception as exc:
            STATE="unavailable"
            LAST_ERROR=LAST_ERROR or ("StartupTimeout" if isinstance(exc,queue.Empty) else type(exc).__name__)
            _stop()
            LOG.warning("Tunisian voice preparation failed: %s",LAST_ERROR)
            return False

def speech_text(text):
    # Preserve words, numbers and code switching.
    text=re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    return re.sub(r"[ \t]+"," ",text).strip()

def _cache_key(text):
    return hashlib.sha256((str(STEPS)+"\0"+text).encode("utf-8")).digest()

def _cached(key,output):
    with CACHE_LOCK:
        item=CACHE.get(key)
        if item is None:return None
        CACHE.move_to_end(key)
    data,meta=item
    Path(output).write_bytes(data)
    return dict(meta,cache_hit=True,generation_s=0.0)

def _remember(key,output,meta):
    path=Path(output)
    if not path.is_file() or path.stat().st_size>MAX_CACHE_BYTES:return
    try:
        with wave.open(str(path),"rb") as wav:
            if not wav.getnframes() or not any(wav.readframes(wav.getnframes())):return
        data=path.read_bytes()
    except (OSError,EOFError,wave.Error):return
    with CACHE_LOCK:
        CACHE[key]=(data,meta)
        CACHE.move_to_end(key)
        while len(CACHE)>MAX_CACHE_ENTRIES:CACHE.popitem(last=False)

def speak_tunisian(text,output):
    global STATE,LAST_ERROR
    if not enabled():raise RuntimeError("Tunisian research voice not enabled")
    text=speech_text(text)
    key=_cache_key(text)
    cached=_cached(key,output)
    if cached is not None:return cached
    if readiness()!="ready":raise RuntimeError("Tunisian research voice not ready")
    # Do not queue additional long CPU requests behind an existing synthesis.
    if not LOCK.acquire(blocking=False):raise RuntimeError("Tunisian voice busy")
    try:
        if readiness()!="ready":raise RuntimeError("Worker unavailable")
        payload={"text":text,"output":str(Path(output).resolve())}
        PROCESS.stdin.write(json.dumps(payload,ensure_ascii=True)+"\n")
        PROCESS.stdin.flush()
        try:
            response=MESSAGES.get(timeout=timeout_seconds())
        except queue.Empty:
            STATE="timed_out"
            LAST_ERROR="SynthesisTimeout"
            _stop()
            raise RuntimeError("Tunisian synthesis timeout")
        if not response.get("ok"):
            LAST_ERROR=str(response.get("error","SynthesisFailed"))[:80]
            if PROCESS.poll() is not None or LAST_ERROR=="WorkerExited":
                STATE="unavailable"
                _stop()
            raise RuntimeError("Tunisian synthesis failed")
        LAST_ERROR=None
        result={"engine":"omnivoice","voice":"aeb-synthetic","dialect_target":"aeb",
                "dialect_authentic":False,"dialect_quality_validated":False,"cache_hit":False,
                "generation_s":response["seconds"],"audio_seconds":response["audio_seconds"],
                "steps":response.get("steps",STEPS)}
        _remember(key,output,result)
        return result
    except (OSError,ValueError) as exc:
        LAST_ERROR=type(exc).__name__
        STATE="unavailable"
        _stop()
        raise
    finally:
        LOCK.release()

atexit.register(_stop)
