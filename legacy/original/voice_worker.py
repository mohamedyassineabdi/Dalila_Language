"""Separate voice process: isolates heavy speech dependencies from the UI."""
import os, sys
from pathlib import Path


def silma(reference, transcript, text, output, device):
    from huggingface_hub import hf_hub_download
    from omegaconf import OmegaConf
    from f5_tts.model import DiT
    from f5_tts.infer.utils_infer import load_model, load_vocoder, preprocess_ref_audio_text, infer_process
    import soundfile as sf
    repo = 'Ghazouaniwala/silma-tts-derja'
    cfg = OmegaConf.load(hf_hub_download(repo,'config.yaml'))
    arch = OmegaConf.to_container(cfg.model.arch,resolve=True)
    # Repository checkpoint is raw (non-EMA), not F5's default EMA weights.
    model = load_model(DiT,arch,hf_hub_download(repo,'model.pt'),mel_spec_type='vocos',vocab_file=hf_hub_download(repo,'vocab.txt'),use_ema=False,device=device)
    vocoder = load_vocoder(vocoder_name='vocos',device=device)
    ref, transcript = preprocess_ref_audio_text(reference,transcript)
    audio, sr, _ = infer_process(ref,transcript,text,model,vocoder,mel_spec_type='vocos',device=device)
    sf.write(output,audio,sr)


def xtts(reference, text, output, device):
    import soundfile as sf
    from huggingface_hub import hf_hub_download
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    repo = 'Nouira-Oussema/Tunisian-TTS'
    config = XttsConfig(); config.load_json(hf_hub_download(repo,'config.json'))
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config,checkpoint_path=hf_hub_download(repo,'best_model.pth'),vocab_path=hf_hub_download(repo,'vocab.json'),eval=True)
    model.to(device)
    result = model.synthesize(text,config,speaker_wav=reference,language='ar')
    sf.write(output,result['wav'],config.audio.output_sample_rate)


if __name__ == '__main__':
    engine, ref, transcript, text, out = sys.argv[1:]
    device = os.getenv('TTS_DEVICE','cpu')
    if engine == 'silma': silma(ref,transcript,text,out,device)
    elif engine == 'xtts': xtts(ref,text,out,device)
    else: raise ValueError('Unknown voice engine')
