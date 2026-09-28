# Task 3 report: `horizon_targets()` — the pure length rule

## What was added / changed

### 1. New file: `spacesim/tests/horizon_targets_test.py` (new, 79 lines)
Transcribed verbatim from the brief (German comments intact). Head-test for
`test.horizon_targets`: (1) coincidence with `predictor_horizon_lengths` when
`grabbing=False`, (2) `wanted` pinned to the ceiling / `drawn` follows the real
`manual_mult` when `grabbing=True` + `ceiling_mult` set, (3) fallback to old
behaviour when `grabbing=True` but `ceiling_mult=None`.

### 2. `spacesim/test.py` — added `horizon_targets(...)` (module level)
Inserted immediately after `predictor_horizon_lengths` (which now ends at
line 36). New function spans **lines 39–62**. Signature:

```python
def horizon_targets(base_length, manual_mult, warp_mult, max_points,
                    base_spacing, *, grabbing=False, ceiling_mult=None):
```

Body per brief Step 3: calls `predictor_horizon_lengths` for `(drawn, wanted)`;
if `grabbing and ceiling_mult is not None`, recomputes `wanted` only, as if
`manual_mult == float(ceiling_mult)`. German docstring transcribed verbatim.

### 3. `spacesim/test.py` — routed `apply_predictor_horizon()` through it
One call changed inside `apply_predictor_horizon()` (now at **line 586**):
`predictor_horizon_lengths(` → `horizon_targets(` with the **same four
positional args** (`PREDICTOR_BASE_LENGTH, predictor_manual_mult,
predictor_warp_length_mult(), PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING`).
No `grabbing` / `ceiling_mult` passed — defaults make this a no-op; the
`grabbing` branch is dead until Task 4.

Nothing else in `test.py` changed.

## TDD evidence — `horizon_targets_test.py`

### RED (before Step 3)
```
Traceback (most recent call last):
  File ".../tests/horizon_targets_test.py", line 17, in <module>
    from test import horizon_targets, predictor_horizon_lengths
ImportError: cannot import name 'horizon_targets' from 'test'
```

### GREEN (after Steps 3–4)
```
1. deckungsgleich ohne grabbing            — 12/12 ok
2. grabbing pinnt die gerechnete laenge an die decke — 7/7 ok
3. grabbing ohne decke = normalverhalten   — 1/1 ok

test.horizon_targets: alle pruefungen bestanden
```
(exit 0)

## Regression — `tests/warp_predictor_test.py`

Full run completed, exit 0. Tail:

```
23. der zeitraffer aendert die gezeichnete linie nicht
  ok   manuell 1x: raffung x16 ... 0.0000e+00 m ... 10000 gegen 10000 punkte
  ok   manuell 1x: raffung x64 ... 0.0000e+00 m ... 10000 gegen 10000 punkte
  ok   manuell 8x: raffung x16 ... 0.0000e+00 m ... 40000 gegen 40000 punkte
  ok   manuell 8x: raffung x64 ... 0.0000e+00 m ... 40000 gegen 40000 punkte
  ok   gegenprobe: ohne deckel wandert dieselbe linie um megameter -- 2.2731e+06 m, 626 punkte

24. die schrittdecke ist ORTLICH, nicht global   — 9/9 ok

FEHLGESCHLAGEN: 3
  jede neue linie gehoert zu einem NEUEREN schiffszustand: 359 schnappschuesse, kleinste zunahme -0.035 m/s
  die decke senkt die teilschritte bei 1 y/s um mehr als das 20-fache: ohne decke 1408, mit decke 1280 (faktor 1)
  100d/s -> 1y/s: wechsel-frame bleibt im hauptthread billig: 11.5 ms (ruhe-median 4.3 ms)
```

### FAIL-line classification

| FAIL line | classification |
|---|---|
| `jede neue linie gehoert zu einem NEUEREN schiffszustand … kleinste zunahme -0.035 m/s` | **pre-existing** — listed in `.claude/rules/tests.md` "Known pre-existing failures" (snapshot goes backwards ~0.035 m/s) and in `.sdd-horizon-slider/snapshots/warp_predictor_test.BASELINE.txt` (identical: `-0.035 m/s`). |
| `die decke senkt die teilschritte bei 1 y/s … faktor 1` | **pre-existing** — listed in `tests.md` ("measured factor 1") and in BASELINE (`ohne decke 1408, mit decke 1280 (faktor 1)`; my run byte-identical). |
| `100d/s -> 1y/s: wechsel-frame bleibt im hauptthread billig: 11.5 ms` | **pre-existing / flaky** — `tests.md`: *"A third, 'wechsel-frame bleibt im hauptthread billig', is timing-sensitive and flakes."* Did not fire in BASELINE; timing noise on this machine under concurrent load. Not caused by this change — the change adds one extra pure-Python function call (two float multiplies) on the horizon path, nowhere near a frame-cost hot loop. An earlier partial run this session showed the same check *passing* at 0.7 ms. |

Baseline delta: BASELINE = 2 FAIL (the two deterministic known ones). This run
= those same 2 (byte-identical numbers) + the documented flaky timing check.
**No new failures.** §23 (`predictor_horizon_lengths` / drawn-line invariance)
fully passes — all 5 checks `0.0000e+00 m`.

## Game smoke

`cd spacesim && SPACESIM_MAX_FRAMES=120 python test.py` — exit 0, 120 frames of
`TIMING:` lines, `frame≈7.2 ms`, `pred_calc=19.8 ms` (off-thread), no
`Traceback` / `Error` / `Exception` in output.

## Self-review

- `horizon_targets` with default kwargs delegates unconditionally to
  `predictor_horizon_lengths` and returns its exact tuple → behaviour identical
  today. Confirmed by test block 1 (12 combos, `a == b`) and by §23 staying at
  `0.0000e+00 m`.
- The one routed call passes only the 4 positional args the brief specifies; no
  keyword args, so the `grabbing` branch cannot execute yet.
- `float(ceiling_mult)` guard matches the brief; `ceiling_mult=None` path
  covered by test block 3.
- No import changes, no new dependency.
- No `pygame.init()`; test file and game entry untouched in that respect.
- Function placement: directly after `predictor_horizon_lengths`, before
  `def main()`, mirroring the existing helper as instructed.

## Concerns

- None affecting correctness. The third `warp_predictor_test` FAIL
  (`wechsel-frame … billig`, 11.5 ms) is the documented timing-flaky check and
  was almost certainly aggravated by other Python processes running
  concurrently on this machine during the test. It is not a new failure and is
  unrelated to a two-float-multiply helper. A re-run in isolation is expected
  to drop it back to 2 FAIL matching BASELINE.
- No rule-doc update made: this task is a pure extraction with zero behaviour
  change (the brief explicitly defers wiring to Task 4). Per CLAUDE.md
  ("match the size of the note to the size of the change") the note belongs
  with Task 4 when `grabbing` goes live.
