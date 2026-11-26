# Dalila Language Lab — Advanced research release (0.2.0)

A standalone multilingual language/voice subsystem for the AFI hackathon. **No AFI data repository changes, no factual AFI answering, no cloud by default.** This package is a research prototype, not production-ready. It recovers the original Derja AI Lab and adds an independent FastAPI application, conservative semantic routing and reproducible experiments.

## 1. Start on Windows

Install Python 3.11 (including the Windows Python launcher). Extract the ZIP to a separate directory, open PowerShell inside `Dalila_Language_Lab_Advanced`, then:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Open <http://127.0.0.1:7860>. No API keys are needed. Setup installs dependencies from the internet and runs automated tests. Choose Tunisian Arabic manually for a reliable demo of the language selector, or use Auto to see experimental language identification. Try `n7eb 750 m² moch 2000 fi Sfax`. The interface reports the original query, extracted spans, proposed intent, code-switch candidate and a safe localized confirmation. It does NOT know AFI facts. For speech, record or upload an audio clip, transcribe, review/edit the result, then analyze. The default speech model downloads when selected; model access and network are required on first run. Unknown or other languages use multilingual Whisper small. Select `tn-whisperx` explicitly for experimental comparisons; a fallback is marked, never scored as the requested model in evaluation.

## 2. One-command public speech benchmark

Read `reports/MODEL_AND_DATA_REVIEW.md` first. If you are authorized to use the published LinTO corpus and the listed models for research:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_benchmarks.ps1 -AcceptPublicTerms
```

This installs evaluation dependencies, verifies available model metadata, prepares pinned model snapshots, attempts to stream 60 published test clips and benchmarks three candidates without fallback. `-IncludeLarge` adds turbo and the code-switch checkpoint (conversion requires additional dependencies, memory and disk). `-Cuda` requests GPU execution; CUDA/cuDNN compatibility must be checked. The default CPU path is closest to the target 8 vCPU/16 GB server. The pipeline was authored and unit-tested in parts, but model downloads/dataset ingestion and Windows execution could not run in this environment. Inspect `reports/prepared_models.json` and `reports/public_asr.json` for errors, coverage and results; no successful score is implied by script completion. The public corpus may overlap model training data and is not a blind comparison. Model licenses, upstream licenses, and individual audio source terms need review before institutional use.

## 3. Kaggle alternative

The included `Kaggle_ASR_Benchmark.ipynb` automates installation, downloads, evaluation and export. Upload the **sanitized Advanced ZIP** as a private dataset, attach it to a new notebook, import the notebook, enable internet, read the review document, and set `ACCEPT_PUBLIC_TERMS=True` only if authorized. Run all cells. CPU is the default; optional GPU/large model experiments may require runtime adjustments and substantial disk/RAM. Download `dalila_benchmark_reports.zip` from the output. Do not upload the original archive, API keys, AFI data or identifiable recordings. The notebook itself has not been run on Kaggle.

## 4. Optional local LLM and original chatbot

Install Ollama on the same Windows host and run `ollama pull qwen3:4b`. In the browser choose `ollama` under understanding backend. It uses a fixed loopback JSON classification endpoint, with a strict response schema and local fallback. The model can propose a dialect and intent; it cannot provide an AFI answer. For a larger comparison use `OLLAMA_MODEL=qwen3:8b` in `.env`. To compare a local model against text baselines:

```powershell
.\.venv\Scripts\python.exe evaluate.py --backend ollama --out reports/ollama_text.json
```

The optional Gemini and Groq adapters are disabled by default. Copy `.env.example` to `.env` only if you need configuration. `DALILA_ALLOW_CLOUD=1` plus explicit provider selection is required to send text and the last six user messages to the provider. Use only authorized, nonrestricted data. Use an exact provider model ID and your own key; no assumed free quota or automatic external fallback. No real provider call was tested. In Docker, the fixed Ollama loopback URL requires Ollama to share the same network namespace; use the Windows host version for this feature.

The recovered full conversational Gradio playground lives in `legacy/original/`. Its original Python code is retained; one stale mocked test fixture was corrected. It is separate from the new API, can be run independently using its own README/setup, and can generate open-ended answers that are **not grounded in AFI sources**. Do not use legacy cloud options for confidential data. Credentials and original venv were deliberately excluded.

## 5. Optional Tunisian TTS

Generic eSpeak NG is only a functional speech baseline. Install it and add it to PATH. French/English/German/Turkish WAV creation succeeded in Linux; the installed Linux eSpeak did not provide Arabic. Even if an Arabic generic voice works elsewhere, it is not native Derja. For research-only SILMA or XTTS, after license review:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-voice.ps1
```

Set `DALILA_ENABLE_RESEARCH_TTS=1` in `.env`, restart the app, upload a PCM WAV reference of 2–30 seconds that you own or have permission to use, enter the verbatim reference transcript for SILMA, and provide Arabic-script speech text. The voice worker is the recovered original. Heavy TTS inference is untested here; there is no default voice clone, no automatic reference upload and no guaranteed pronunciation. SILMA is CC BY-NC 4.0, so do not assume commercial rights. XTTS and upstream F5/Coqui licenses need review. Reference audio stays in request-scoped temporary files; model packages may cache downloaded resources. UI/HTTP logs do not intentionally store transcripts. The optional legacy app has its own output/log behavior.

## 6. Evaluation and model selection

- `evaluate.py` runs baseline word/character and hybrid classifiers on 72 prior exploratory eval drafts. `--text data/stress_cases.jsonl` uses 80 new authored stress drafts. All 224 text cases (72 development, 152 exploratory evaluation) are synthetic and unreviewed. The hybrid was designed with known language patterns, so scores are not independent generalization evidence. Auto detection explicitly abstains; distinguish coverage, best-guess accuracy and operational accuracy counting abstentions as incorrect. The stress data is authored by the same AI, not independent.
- `data/recording_kit.csv` and `data/tts_rating_kit.csv` provide 80 prompts and blank consent/transcript/rating fields. Elicit naturally spoken recordings from consenting humans; have fluent reviewers write and verify references. Split by speaker and keep final eval untouched. `audio_manifest_example.json` is a schema example, not actual recording evidence. `data/audio_manifest.jsonl` is intentionally empty.
- `evaluate.py --audio data/audio_manifest.jsonl --models tn-small tn-whisperx small --out reports/consented_asr.json` requires verified consented audio. Public corpus comparison requires explicit `--public` and published-source metadata. Failure cases count as empty hypotheses; compare coverage and WER/CER together. Exact-string numeric checks skip examples without numeric digits; they do not validate spoken number meaning. Entity and negation tests require explicit reference annotations; public samples generally lack them. WER/CER are strict Unicode/whitespace-normalized scores, not the model authors' custom scorer. Memory is sampled RSS, not peak whole-system memory. Human semantic and voice judgments remain necessary.
- `evaluate_numalia.py --download-for-review` downloads a candidate dialect classifier for audit only. Its architecture requires custom Python code. Inspect it in isolation, pin its revision, review its CC BY-SA 4.0 terms, then explicitly use `--reviewed-local-path models/numalia --i-reviewed-code` with the optional Transformers dependencies. Never execute unreviewed remote code. NUMALIA covers only five of our eight target languages; it needs a multilingual router for English, German and Turkish. The model is not yet integrated as default.

## 7. API and deployment

`GET /health`, `POST /analyze` (legacy Phase 1), `POST /understand` (advanced), `POST /transcribe`, `POST /speak`, `POST /speak-reference`. Example body for `/understand`: `{"text":"n7eb 750 m² moch 2000 fi Sfax","language":"aeb","backend":"baseline","history":[],"style":"auto"}`. Results include original text, normalized text, span offsets, tentative intent, fallback and language/knowledge status. `aeb, ar, fr, en, arq, ayl, de, tr` language codes. Optional contextual inference only for short conjunction-prefixed follow-ups or via the LLM; all inherited intent is a proposal. No token-level dialect labels, automatic transliteration, reliable number-word conversion, or validated named-entity catalogue. Do not treat the heuristic place aliases as official zones. Keep factual retrieval/answer generation separate and require validated evidence before rendering substantive responses. `http://127.0.0.1:7860/docs` exposes interactive local API documentation.

Docker: `docker build -t dalila-language-lab .` then `docker run --rm -p 127.0.0.1:7860:7860 -v dalila-hf:/home/dalila/.cache/huggingface dalila-language-lab`. Docker and Windows builds not tested. The server is not hardened for public exposure; no authentication or abuse controls. Start with one loaded ASR and one request at a time, four threads, CPU int8, one quantized LLM at a time; benchmark actual memory/latency on the 16 GB target before deployment. Model weights not included. For offline operation use prepared models and `ASR_OFFLINE=1`. Keep `.env`, private audio and reports containing transcripts outside version control.

## 8. Evidence and current decision

Read `reports/IMPLEMENTATION_STATUS.md`, `reports/MODEL_AND_DATA_REVIEW.md`, `reports/advanced_text.json`, `reports/stress_text.json`, `reports/tests_advanced.txt`, `reports/legacy_retest.txt`, `reports/tts_advanced.json`, `reports/environment.json`. Phase 1 reports remain historical. The direct runtime network could not resolve Hugging Face, PyPI or Zenodo; no fresh neural inference was executed. **GO for research/demo setup; NO-GO for production or a claim of validated eight-language voice support.**


## v0.4.0 — simple chat
Stop the old server, run `git pull --ff-only`, then `powershell -ExecutionPolicy Bypass -File .\\run.ps1`. The launcher discovers an installed Ollama model or downloads Qwen3 4B once if Ollama is installed and a compatible model is absent. A several-GB download may occur. No cloud provider is automatically selected. The browser displays the actual model and fallback state. Voice messages are automatically sent and read when a compatible offline voice is available. Windows SAPI/eSpeak and local browser voices are generic, not native Tunisian TTS. No AFI factual responses are enabled. Real neural inference, Windows voices and microphone hardware require local validation.
