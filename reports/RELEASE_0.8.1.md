# Release 0.8.1 — measured verification (26 November 2026)

Source: GitHub Actions runs 45900749337 (regression), 45900749305 (4-step real OmniVoice), 45862449243 (16-step real OmniVoice), 45851892671 (Piper Windows). These are the reported job logs; no independent native-speaker listening scores exist.

- Windows Python 3.11: 82 passed, 3 warnings.
- Linux Python 3.11: 82 passed, 3 warnings.
- Real Piper: five voices generated on Windows.
- OmniVoice: seven prompts generated at both 16 and 4 steps on Linux CPU.

| Prompt | 16-step generation (s) | 4-step generation (s) | 4-step audio duration (s) |
|---|---:|---:|---:|
| greeting | 45.011 | 8.902 | 2.98 |
| project | 52.097 | 10.373 | 3.87 |
| question | 51.982 | 9.856 | 3.12 |
| negation | 47.912 | 9.806 | 3.40 |
| codeswitch | 60.643 | 11.709 | 4.61 |
| location | 54.393 | 10.309 | 3.95 |
| numbers | 48.705 | 9.731 | 3.41 |

Mean synthesis time: about 51.5 s vs 10.1 s (~5.1x faster). CI hardware and runtime differ from teammate PCs; results exclude ASR, LLM, model load, upload and playback time. Synthesis success does not prove pronunciation or naturalness. The worker's Windows installation, actual inference and concurrent memory use need local verification. The 4-step setting may reduce quality.

[Regression](https://github.com/mohamedyassineabdi/Dalila_Language/actions/runs/45900749337) · [4-step audio and artifacts](https://github.com/mohamedyassineabdi/Dalila_Language/actions/runs/45900749305) · [16-step audio](https://github.com/mohamedyassineabdi/Dalila_Language/actions/runs/45862449243) · [Piper audio](https://github.com/mohamedyassineabdi/Dalila_Language/actions/runs/45851892671)
