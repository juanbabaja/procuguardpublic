# ProcuGuard

A ControlArena setting built on procurement. An agent prepares a supplier quote comparison (RFQ). The side task is to make a chosen supplier win through judgment calls that the documents leave open. The main question is whether an LLM monitor flags those calls when the sabotage applies the same rule to every supplier.

The full write-up is in [`WRITEUP.md`](WRITEUP.md).

## Check the headline numbers (no engine, no API)

```
python scripts/verify_paired.py
```

This uses only the standard library. It reads the per-sample monitor scores in `results/f3/fase1_filas.csv` and the pair list in `results/f3/pares.json`. It sets each monitor's threshold at a 5% false-positive rate on the 100 honest calibration runs. Then it recomputes the paired test from the write-up: on the 78 sourcings where both sabotages flip the winner, Sonnet 5.5 audits 56 of 78 even-handed attacks and 78 of 78 unequal ones (+28 points, 95% CI [+17, +40]), and Haiku 5.5 audits 50 and 77 (+35, [+21, +46]).

## What is in this repo

| Path | What it holds |
| --- | --- |
| `procuguard/` | The setting: synthetic sourcing generator, agent tools, scorers, replay attacker, monitors, analysis |
| `scripts/` | `verify_paired.py` (standalone check), `contraste_parejo.py` (the same test from the full logs), the no-API reproduction and the label-swap test |
| `docs/` | Protocols written before each phase ran, results, and dated deviations (in Spanish) |
| `results/f3/` | Paired test: per-sample scores, pair list, cohort, tables |
| `results/f2-limpia/` | Main phase-2 cohort, including the GPT-6.1 Terra readings |
| `tests/` | Tests (they need the comparison engine) |

## What is not in this repo, and why

- **The comparison engine** (`comparativas`). It is a separate tool I built, and I am not releasing it for now. The setting imports it, so the code here cannot run end to end. The results can still be checked from the released scores.
- **Transcripts and Inspect logs.** In the runs, the synthetic quote documents carried the name and form layout of a real automotive buyer. For this release I replaced those strings in the generator with neutral ones (`OEM BUYER (SYNTHETIC)`, `la terminal`). The transcripts the monitors actually read still contain the original names, so I am not publishing them. All suppliers, part numbers and figures are synthetic.

Code, prompts and transcripts are in Spanish. The monitor prompt is ControlArena's generic full-transcript prompt, in English.

## Who did what

I designed the setting and the paired experiment, supplied the buyer's criteria, and made the protocol decisions. I wrote the code with Claude's help.

Juan Ignacio Babaja
