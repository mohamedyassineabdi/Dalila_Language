"""Isolated eSpeak NG synthesis from the pinned espeakng-loader wheel."""
import ctypes as C
import os
from pathlib import Path
import sys
import wave
import espeakng_loader as loader

def synthesize(voice, text, output):
    if voice not in {'ar','fr','en','de','tr'}:
        raise ValueError('Unsupported speech voice')
    libpath=Path(loader.get_library_path())
    dll_dir=os.add_dll_directory(str(libpath.parent)) if os.name=='nt' else None
    lib=C.CDLL(str(libpath))
    def bind(name, args, result):
        fn=getattr(lib,name); fn.argtypes=args; fn.restype=result
        return fn
    initialize=bind('espeak_Initialize',[C.c_int,C.c_int,C.c_char_p,C.c_int],C.c_int)
    set_voice=bind('espeak_SetVoiceByName',[C.c_char_p],C.c_int)
    callback_type=C.CFUNCTYPE(C.c_int,C.POINTER(C.c_short),C.c_int,C.c_void_p)
    set_callback=bind('espeak_SetSynthCallback',[callback_type],None)
    synth=bind('espeak_Synth',[C.c_void_p,C.c_size_t,C.c_uint,C.c_int,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p],C.c_int)
    sync=bind('espeak_Synchronize',[],C.c_int)
    terminate=bind('espeak_Terminate',[],C.c_int)
    data=Path(loader.get_data_path())
    if not (data/'phontab').is_file():
        raise RuntimeError('Incomplete voice data')
    rate=initialize(2,0,os.fsencode(str(data.parent)),0x8000)
    if rate<=0: raise RuntimeError('Speech initialization failed')
    samples=bytearray()
    @callback_type
    def callback(ptr,n,events):
        if ptr and n>0:
            samples.extend(C.string_at(ptr,n*2))
        return 0
    try:
        set_callback(callback)
        if set_voice(voice.encode('ascii'))!=0:
            raise RuntimeError('Voice unavailable')
        raw=C.create_string_buffer(text.encode('utf-8'))
        if synth(C.cast(raw,C.c_void_p),len(raw),0,1,0,1,None,None)!=0 or sync()!=0:
            raise RuntimeError('Speech synthesis failed')
        if not samples or not any(samples):
            raise RuntimeError('Empty or silent speech')
        with wave.open(str(output),'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
            wav.writeframes(samples)
    finally:
        terminate()
        if dll_dir is not None: dll_dir.close()

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit(2)
    synthesize(sys.argv[1],sys.stdin.buffer.read().decode('utf-8'),sys.argv[2])
