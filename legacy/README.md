# Derja AI Lab — Tunisian voice & text chatbot

A standalone local prototype, not a production assistant. Windows 10/11 instructions below. No Docker, database, paid API, or RAG is necessary. The model weights are downloaded separately, not bundled. First use requires internet; cached local engines can subsequently run without a cloud inference service. All audio inference is local. Groq, if explicitly selected, sends the text and recent dialogue to Groq. Do not send confidential institutional data to it.

## 1. Fastest start: no API keys

1. Extract the ZIP to a folder such as `C:\Projects\Derja_AI_Lab`.
2. Install 64-bit Python **3.11** from https://www.python.org/downloads/ (enable Add Python to PATH). Install Ollama from https://ollama.com/download/windows. Install Visual C++ redistributable if required: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist.
3. Open PowerShell inside the extracted folder. Run these commands in order:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
ollama pull hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

If `ollama` is not recognized, reopen PowerShell after installation. Ollama normally starts automatically; if connection is refused, start the Ollama app or run `ollama serve` in a separate terminal. If Python launcher is missing, reinstall Python 3.11 with launcher enabled. Scripts use their virtual environment directly; no activation needed. Alternatively use `py -3.11 -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, `Copy-Item .env.example .env`, `.\.venv\Scripts\python.exe app.py`.

Open http://127.0.0.1:7860. Select Labess 7B (local), Tunisian (Derja), Arabic script. Type `3aslema, chnowa a7welek?` and click Send. Record audio, click Transcribe audio, check or edit the transcript, then Send. The default Tunisian Whisper model (~250 MB) downloads automatically on first transcription. No HF token is normally required for the public models.

Recommended starting hardware: 16 GB RAM, 10–15 GB free disk for text + STT, preferably 6–8 GB VRAM for Labess. CPU-only is supported by Ollama but slower; actual memory/latency varies. If RAM is limited, pull `ollama pull qwen3:4b` and choose Qwen3 4B. To compare with Qwen3 8B, `ollama pull qwen3:8b` (about 5.2 GB). Labess Q4 download ~4.3 GB. Keep one large model active at a time. Restart app and `ollama stop <model>` if switching to another heavy engine causes memory exhaustion.

## 2. Make it speak Tunisian (optional but necessary for full voice output)

Voice output is off by default, so you can verify text and speech recognition before installing heavy TTS packages. The two TTS models are noncommercial research/personal-test candidates. Use only your own voice or a reference you have permission to synthesize. Model weights in PyTorch checkpoint formats should only be loaded if you trust their publisher; they are not bundled or audited here.

Install FFmpeg from https://ffmpeg.org/download.html (Windows package option: `winget install --id Gyan.FFmpeg -e`), and reopen the terminal so `ffmpeg -version` works. Install the optional separate voice environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-voice.ps1
```

This installs CPU PyTorch by default. For supported NVIDIA GPUs, check driver compatibility at https://pytorch.org/get-started/locally/; `powershell -ExecutionPolicy Bypass -File .\setup-voice.ps1 -Cuda` installs CUDA 12.8 PyTorch 2.8. Set `TTS_DEVICE=cuda` in `.env` if the CUDA environment works. Restart the app. Allow additional disk space (10–20 GB or more for caches and dependencies). CPU synthesis can be slow; each voice request launches an isolated worker and reloads the model, so timings include model load.

In the UI:
- Select **SILMA Derja (local)**. Record or upload 6–15 seconds of your own clean Tunisian speech in the voice reference widget (not the question widget). For example say `عسلامة، أنا نحكي بالتونسي ونحب نجرب الصوت هذا.` Enter the exact words actually spoken in the reference transcript. Check the permission box.
- Type a message and click Send. The answer appears as text and, if synthesis succeeds, playable audio. First run downloads checkpoint/vocoder. If a long answer fails, edit the Speech text to a short Arabic-script Derja sentence, then click Speak.
- Compare **XTTS Tunisian (local)** using the same reference; its transcript is optional. This model expects Arabic script. If selecting Arabizi or English/French, the app does not auto-synthesize using Tunisian TTS; you can manually enter a suitable Arabic-script speech text.
- If installation or checkpoint loading fails, keep the text/STT prototype running. See troubleshooting below. You can independently check the public demos at https://huggingface.co/spaces/AVOiD/derja-tts and https://huggingface.co/spaces/Nouira-Oussema/TTS-Tounsi (availability may vary; these are external demos, not integrated endpoints).

## 3. Optional Groq cloud LLM (for a weak PC)

1. Sign up/sign in at https://console.groq.com/keys and create an API key. Verify your account is on the free plan, and check https://console.groq.com/settings/limits or https://console.groq.com/docs/rate-limits for your current quotas. Free plan is limited, not unlimited. Do not enable paid billing if you want to avoid charges.
2. In the extracted folder open `.env` in Notepad (`notepad .env`). If it does not exist, copy `.env.example` to `.env` first. Set `GROQ_API_KEY=your_actual_key` without quotes. Do not share the file or commit it. Restart the app.
3. Select **Groq (cloud)** and leave model ID `qwen/qwen3.8-27b` if your account has access. Otherwise choose an available text chat model from https://console.groq.com/docs/models and edit the model ID in the UI. This is a multilingual baseline, not Tunisian fine-tuned. If the free limit is exceeded, the app reports it and will not silently use another provider. No Ollama download needed if using Groq only.

## 4. Optional TounsiLM / FarukSTT advanced models

These are optional heavy engines, not the default. TounsiLM is a PEFT adapter on Aya Expanse 8B (research/noncommercial terms). Review https://huggingface.co/CohereLabs/aya-expanse-8b and accept any access conditions there while logged in, then create a read token at https://huggingface.co/settings/tokens. Add `HF_TOKEN=hf_...` in `.env` and restart. The token is for downloading weights, not paid inference. It is not required for the public Whisper or Labess models.

Install PyTorch in the **main** environment using https://pytorch.org/get-started/locally/. Example for a compatible NVIDIA system:

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-advanced.txt
```

For CPU replace `cu128` with `cpu`; CPU fp32 TounsiLM can require >32 GB of RAM, so not recommended. Default `TOUNSI_PRECISION=4bit` uses bitsandbytes on CUDA; set `TOUNSI_PRECISION=bf16` to use higher precision if your GPU supports it (~18–20 GB VRAM). FarukSTT requires a few GB more memory; use one heavy engine at a time. Select TounsiLM 8B (advanced) or FarukSTT (advanced) in the UI. The app downloads base and adapter or ASR weights when selected. If bitsandbytes is incompatible on Windows, use WSL2/Linux or a GPU notebook. These advanced paths are experimental, not end-to-end validated.

## 5. Evaluation

Start a fresh conversation before comparing models on the same questions. Use `examples/evaluation.json` as a starter set, then add your own recorded questions with regional accents and code-switching. Record human reference transcript separately. In UI, use the sliders to rate the latest answer; zero means not evaluated. Click Save rating, then Export evaluation JSON. Turn-level metrics include the raw recognized text (if transcribed), the corrected question, reply, model choices, STT/LLM/TTS times, generation parameters and ratings. Raw recordings are not exported. Transcription metadata refers to the last successful transcription preceding a sent question; if you type a completely unrelated question, reset first. Exports and generated WAVs are saved in `outputs/`; delete them yourself if sensitive. Gradio may also retain temporary uploaded audio in its OS temp cache. The app does not implement streaming, automatic dialect routing, semantic evaluation, or RAG. Audio synthesis is turn-based, not full duplex.

For French, English, MSA: choose the corresponding language and the multilingual Whisper model (not TN Whisper). For best multilingual responses choose Qwen or a cloud model. Tunisian TTS is the only implemented voice output in this version; French/English TTS and independent auto-language routing are future integration work.

## 6. Troubleshooting and verification

```powershell
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- 404 Ollama: pull selected model; run `ollama list` to confirm exact name.
- 429 Groq: quota reached. Check limits, wait until reset or choose local model.
- Whisper startup: first run downloads from Hugging Face; check internet/disk, retry. Default CPU int8 avoids CUDA DLL requirements. If CUDA is configured and fails, return to CPU/int8.
- Voice failed: verify FFmpeg, voice environment, reference length, permission, exact SILMA transcript, and available memory. Try XTTS or SILMA separately; exact compatibility of third-party checkpoints may change. If F5-TTS installation fails, install voice packages independently in a fresh `.venv-voice`, starting with PyTorch then `pip install coqui-tts==0.27.5 'transformers<5' soundfile huggingface-hub` (quote the version constraint in PowerShell, e.g. `'transformers<5'`). For SILMA install `f5-tts==1.1.7` separately. On Windows some audio/ML packages may require Visual C++ Build Tools or WSL2. Do not disable antivirus or SSL verification.
- Port 7860 busy: stop other instance or change `server_port` in `app.py`.
- App is bound only to localhost. No public Gradio sharing. Keep `.env` private. Stop with Ctrl+C.

## Model sources and licensing

- Labess: https://huggingface.co/linagora/Labess-7b-chat-gguf (Apache 2.0 as listed)
- Qwen3: https://ollama.com/library/qwen3
- Tunisian Whisper: https://huggingface.co/TheBiggyBang/whisper-small-tunisian-derja-ct2 (Apache 2.0)
- TounsiLM adapter: https://huggingface.co/alabenayed/TounsiLM-8b (review base and adapter licenses)
- FarukSTT: https://huggingface.co/medyas/FarukSTT (verify usage terms)
- SILMA Derja: https://huggingface.co/Ghazouaniwala/silma-tts-derja (CC BY-NC 4.0)
- XTTS Tunisian: https://huggingface.co/Nouira-Oussema/Tunisian-TTS (CC BY-NC 4.0 model card; also review XTTS base license)
- F5-TTS implementation: https://github.com/SWivid/F5-TTS
- Coqui installation: https://coqui-tts.readthedocs.io/en/latest/installation.html
- Groq: https://console.groq.com/docs/quickstart

No third-party weights are redistributed by this ZIP. Dependencies and models retain their own licenses. This is not a claim that all models are licensed for commercial or government deployments.
