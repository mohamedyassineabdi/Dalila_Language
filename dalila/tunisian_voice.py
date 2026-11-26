"""Opt-in noncommercial Tunisian voice worker with bounded wait and offline fallback."""
import atexit
import json
import logging
import os
from pathlib import Path
import queue
import re
import subprocess
import threading

ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.RLock()
STATE="not_enabled"
PROCESS=None
MESSAGES=None
LOG=logging.getLogger(__name__)

def enabled():
    return os.getenv("DALILA_TUNISIAN_RESEARCH","0")=="1"

def worker_python():
    return ROOT/".venv-tunisian"/("Scripts/python.exe" if os.name=="nt" else "bin/python")

def readiness():
    if not enabled(): return "not_enabled"
    if STATE=="ready" and (PROCESS is None or PROCESS.poll() is not None): return "unavailable"
    return STATE

def _read_lines(process,messages):
    try:
        for line in process.stdout:
            try:
                item=json.loads(line)
                if isinstance(item,dict):messages.put(item)
            except ValueError:
                continue
    finally:
        messages.put({"error":"Worker exited"})

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
    global PROCESS,MESSAGES,STATE
    if not enabled():return False
    if not worker_python().is_file():
        STATE="not_installed"
        return False
    with LOCK:
        if readiness()=="ready":return True
        STATE="preparing"
        try:
            _stop()
            env=dict(os.environ,PYTHONIOENCODING="utf-8",HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                     HF_HUB_DISABLE_TELEMETRY="1")
            # The child has only local text input; no cloud credentials needed.
            for key in list(env):
                if key.endswith(("_API_KEY","_TOKEN")) or key in ("HF_TOKEN","HUGGING_FACE_HUB_TOKEN"):
                    env.pop(key,None)
            PROCESS=subprocess.Popen([str(worker_python()),"-u","-m","dalila.tunisian_worker"],
                                     cwd=str(ROOT),env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                     text=True,encoding="utf-8",bufsize=1)
            MESSAGES=queue.Queue()
            threading.Thread(target=_read_lines,args=(PROCESS,MESSAGES),daemon=True).start()
            response=MESSAGES.get(timeout=900)
            if response.get("ready") is not True:raise RuntimeError("Worker unavailable")
            STATE="ready"
            return True
        except Exception as exc:
            STATE="unavailable"
            _stop()
            LOG.warning("Tunisian voice preparation failed: %s",type(exc).__name__)
            return False

def speech_text(text):
    # Preserve words, numbers and code switching. Remove only display markup and repeated whitespace.
    text=re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    text=re.sub(r"[ \t]+"," ",text).strip()
    return text

def speak_tunisian(text,output):
    global STATE
    if readiness()!="ready":raise RuntimeError("Tunisian research voice not ready")
    with LOCK:
        if readiness()!="ready":raise RuntimeError("Worker unavailable")
        try:
            payload={"text":speech_text(text),"output":str(Path(output).resolve())}
            PROCESS.stdin.write(json.dumps(payload,ensure_ascii=True)+"\n")
            PROCESS.stdin.flush()
            response=MESSAGES.get(timeout=25)
            if not response.get("ok"):raise RuntimeError("Tunisian synthesis failed")
            return {"engine":"omnivoice","voice":"aeb-synthetic","dialect_target":"aeb",
                    "dialect_authentic":False,"dialect_quality_validated":False,
                    "generation_s":response["seconds"],"audio_seconds":response["audio_seconds"]}
        except Exception:
            STATE="unavailable"
            _stop()
            raise

atexit.register(_stop)
