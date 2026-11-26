# Model and dataset selection — 26 November 2026

All published scores below come from authors, not Dalila experiments. They use different corpora, normalizers, decode settings and hardware. A provisional default is not a final ranking.

| Component | Candidate | Evidence | Decision |
|---|---|---|---|
| ASR | TheBiggyBang/whisper-small-tunisian-derja-ct2 | Whisper-small, CT2 250 MB INT8 export, Apache-2.0 declared. Author CPU greedy 80 clips WER 31.0%, CER 13.2%, RTF .889, 4 threads. GPU beam3 full held-out 482 clips WER 30.4%. | Provisional Tunisian default; own independent benchmark required. |
| ASR | montachouig/whisperX-tunisian | Direct repo and metadata unavailable. Exact architecture, license, size and scores unverified. | Candidate only; inspect prepared model metadata before using. Do not attribute sibling LoRA results to it. |
| ASR | oddadmix/Whisperv3-tunisian-codeswitch | Whisper-large-v3 full fine-tune; Tunisian/French/English focus. Author WER 17.26% validation, CER 6.91%, 15.22% blind WER; greedy Arabic decoding. No hosted inference provider listed. | GPU or converted INT8 challenger, license not established by inspected card. Research only after review. |
| ASR | Whisper-small, large-v3, turbo | General multilingual baselines. | Use multilingual models for the other seven target languages; measure own CPU latency. |
| LID | NUMALIA | 5.19M parameters, 20.8 MB float32; Arabic script, Arabizi, French; 8 Maghrebi classes including out-of-scope dialects. Published macro F1 91.59%, Tunisian recall 92.5%. CC BY-SA 4.0; requires custom code. | Audit source, then compare on supported languages only; no unreviewed remote code. |
| LLM | Labess 7B chat GGUF | Tunisian instruction-tuned Jais-derived model, card says Apache 2.0, Q4_K_M 4.26 GB. Review underlying model/data rights. | Recovered original chat adapter; compare against Qwen3 4B/8B. |
| LLM | Qwen3 4B/8B | Local quantized candidates via Ollama. | Test structured semantics; no measured scores yet. |
| LLM | ESPRIT-Derja-Qwen3-8B-v2, TounsiLM | Access to first exact repository returned unauthorized; TounsiLM legacy adapter remains optional. | Do not assume availability or license. |
| TTS | Ghazouaniwala/silma-tts-derja | F5-TTS Tunisian and French code-switching; CC BY-NC 4.0, no formal MOS, limited regional coverage. | Optional noncommercial research only after permission/license review. |
| TTS | Nouira-Oussema/Tunisian-TTS | Recovered XTTS worker; rights and actual model performance not verified. | Optional consented research only. |
| TTS | eSpeak/eSpeak NG | Actual WAV smoke tests in FR/EN/DE/TR; installed Arabic voice unavailable. | Generic fallback, not natural Derja. |

## Public corpus

LinTO `linagora/linto-dataset-audio-ar-tn`: declared CC BY 4.0; default dataset config includes train/test and audio_id/audio/segments/transcript. Downloader selects only test via streaming and records revision and hashes, but individual audio-source terms should be checked. It can overlap model training and evaluation (TheBiggyBang specifically used LinTO). Do not call it independent or include the raw clips in the ZIP. Public references have not been reviewed by the Dalila team. The scripted downloader was not able to run here. If streaming format changes, inspect schema instead of inventing labels.

TunSwitch `tunis-ai/TunSwitch` hosts separate annotated test archive `test_wavs.zip` (284 MB on inspected repo). Original dataset is at Zenodo 8370566. It contains Tunisian-only and code-switch test material; preserve original splits and review license, rights and contamination before use. The full repository is 18 GB, so don't download the entire thing unnecessarily. This archive importer is not implemented in this release; LinTO streaming is the first automated option.

## Sources inspected

- https://huggingface.co/TheBiggyBang/whisper-small-tunisian-derja-ct2
- https://huggingface.co/montachouig/whisperX-tunisian (access failed)
- https://huggingface.co/oddadmix/Whisperv3-tunisian-codeswitch
- https://huggingface.co/algerian-nlp/NUMALIA
- https://huggingface.co/linagora/Labess-7b-chat-gguf
- https://huggingface.co/Ghazouaniwala/silma-tts-derja
- https://huggingface.co/datasets/linagora/linto-dataset-audio-ar-tn
- https://huggingface.co/datasets/tunis-ai/TunSwitch/tree/main
- https://zenodo.org/records/8370566
- https://arxiv.org/abs/2309.11327

## Release gates

1. Pin model revisions, inspect licensing/upstream/data terms, and audit custom code. Resolve whisperX access rather than inventing metadata.
2. Collect a representative, speaker-disjoint, human-reviewed Tunisian test set. Include code-switch, urban/regional speech, noise, dates, numbers, plot identifiers and negations. Evaluate three or more model families on identical audio and separately report dialect and code-switch strata.
3. Establish target thresholds with team: semantic/critical-slot correctness takes priority; require coverage, numeric/negation correctness and p95 latency targets. No deployment if a critical slot can be silently changed.
4. Evaluate all eight text/voice languages, clarify uncertain dialects, conduct native-speaker TTS listening tests and review rights.
5. Benchmark actual host CPU/RAM/latency under concurrent workload and integrate only verified AFI sources. No factual answers until verified retrieval and answer-grounding tests pass.
