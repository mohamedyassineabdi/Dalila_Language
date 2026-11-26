# Advanced implementation status

Actual results in this environment (2026-11-26).

## Text experiments

| Set / method | Best-guess LID accuracy | Operational LID accuracy | LID coverage | Intent accuracy | Intent macro F1 |
|---|---:|---:|---:|---:|---:|
| 72 prior drafts / phase1_word | 70.83% | 70.83% | 100.00% | 48.61% | 44.14% |
| 72 prior drafts / phase1_char | 68.06% | 68.06% | 100.00% | 56.94% | 54.63% |
| 72 prior drafts / hybrid | 86.11% | 51.39% | 51.39% | 66.67% | 63.57% |
| 80 stress drafts / phase1_word | 87.50% | 87.50% | 100.00% | 83.75% | 83.46% |
| 80 stress drafts / phase1_char | 81.25% | 81.25% | 100.00% | 92.50% | 92.15% |
| 80 stress drafts / hybrid | 88.75% | 71.25% | 72.50% | 98.75% | 98.68% |

The hybrid abstains on uncertain dialects. On the prior drafts it accepts only 51.39% (including 37.5% of Tunisian items); this is not a reliable automatic LID system yet. On the new AI-authored stress drafts intent scores are high but the dataset is deliberately domain-shaped, not human or blind. Exact surface mention scores do not establish semantic entity extraction or negation scope.

## Executed software checks
- 40 advanced pytest tests passed; mocked model integration and fallback included.
- 9 recovered Gradio unit tests passed after correcting one stale mock fixture (Labess native generate response). First retest had 8 passes and 1 error because of stale fixture; original engine unchanged. Gradio emits nonfatal event-loop warnings.
- Browser JS syntax checked with Node; FastAPI endpoint smoke tests executed. No actual browser microphone test or Windows execution.
- Real generic WAV generation passed for French, English, German, Turkish. Arabic voice unavailable; no real Tunisian voice inference.
- Network attempts to Hugging Face, PyPI and Zenodo failed DNS. Model metadata attempts failed for all eight queried candidates. Download attempt for tn-small failed; subsequent tool execution timed out. No model weights or public audio downloaded.
- No API credentials from original upload were used or copied. No AFI project or external account changed.

## Decisions and limitations
- Provisional local ASR default: existing 250 MB Tunisian Whisper. Generic small for unknown and other languages.
- LLM optional structured classification; no factual generation; cloud explicitly disabled unless configured.
- Two safe acknowledgement styles for Tunisian, including Arabizi. Actual dialect quality not human-reviewed.
- NUMALIA evaluation path, model conversion, public audio downloader, PowerShell and Kaggle runner are implemented but cannot be end-to-end tested without network/model files.
- Final release NO-GO; research prototype GO.
