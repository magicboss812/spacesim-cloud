# Task 4 report — wire `grabbing` + config into `apply_predictor_horizon`

## Edits

### `spacesim/config.json`
Inside `"predictor"`, after `"length_step_factor": 2.0,` (now lines 61–63):
```json
    "horizon_slider_min_mult": 0.25,
    "horizon_slider_max_mult": 4.0,
    "horizon_slider_sweep_seconds": 2.5,
```
JSON-valid check (`cd spacesim && python -c "import json; json.load(open('config.json')); print('ok')"`): **`ok`**

### `spacesim/test.py`
1. **Lines 237–239** — three constants added immediately after
   `predictor_min_precision = float(config.get('predictor.min_precision', 1.0))` (line 236):
   ```python
   HORIZON_MULT_MIN = float(config.get('predictor.horizon_slider_min_mult', 0.25))
   HORIZON_MULT_MAX = float(config.get('predictor.horizon_slider_max_mult', 4.0))
   HORIZON_SWEEP_S = float(config.get('predictor.horizon_slider_sweep_seconds', 2.5))
   ```
2. **Lines 373–379** — the two closures, placed immediately after
   `apply_frame_selection()` (line 371) and before `hud = None` (now line 385),
   per the controller ruling (not after `apply_predictor_horizon`):
   ```python
   def get_predictor_horizon_mult():
       return predictor_manual_mult

   def set_predictor_horizon_mult(mult):
       nonlocal predictor_manual_mult
       predictor_manual_mult = max(HORIZON_MULT_MIN,
                                   min(HORIZON_MULT_MAX, float(mult)))
   ```
   No forward references: `predictor_manual_mult` is bound at line 227,
   `HORIZON_MULT_MIN/MAX` at 237–238.
3. **Lines 597–605** — inside `apply_predictor_horizon()`, the `horizon_targets(...)`
   call now computes `grabbing` first and passes the two new kwargs:
   ```python
   grabbing = (hud is not None
               and getattr(hud, 'horizon', None) is not None
               and hud.horizon.is_grabbing)
   drawn, wanted = horizon_targets(
       PREDICTOR_BASE_LENGTH, predictor_manual_mult,
       predictor_warp_length_mult(),
       PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
       grabbing=grabbing, ceiling_mult=HORIZON_MULT_MAX,
   )
   ```
   `hud` is `None` until built (line ~387); `hud.horizon` is `None` until Task 5.
   Both guarded — the game smoke run exercises the `getattr(hud, 'horizon', None)`
   path with a real (non-None) `hud` that has no `horizon` attribute.

### `spacesim/tests/horizon_targets_test.py`
Added **section 4** ("griff-kontrakt gegen einen echten Predictor") verbatim from
brief Step 2, inserted before the final `print()` / summary block (after the
section-3 check, ~line 67). Builds a stub `_World` + `_Body` (Erde at origin,
ship in an eccentric LEO), constructs `Predictor(async_compute=False,
num_points=2000, precision=1.0e6)`, wraps `set_length` / `set_display_length`
with call counters, and replays the tail of `apply_predictor_horizon`:
- 30 "drag" frames with `grabbing=True`, rising mult → `set_length` called
  **≤ 1×**, `set_display_length` called **30×**.
- release frame (`grabbing=False`) → exactly **one more** `set_length`.

No change to `horizon_targets` or the widget; the stub bodies needed no
adjustment — `pred.initialize` succeeded as written.

## TDD evidence — section 4

The brief states section 4 is expected to **pass on first run** because Task 3
already shipped `grabbing` / `ceiling_mult` support in `horizon_targets`. That is
what was observed:

```
4. griff-kontrakt gegen einen echten Predictor
PRED_DBG_COMPUTE_FULL_ROLLING: took 0.867s roll_states=2000
  ok   set_length hoechstens 1x waehrend des griffs -- 1x
  ok   set_display_length jeden frame -- 30x
  ok   beim loslassen genau ein set_length -- 2 (war 1)
```

Contract locked: the `ceiling_mult` branch in `horizon_targets` is what pins
`wanted` constant during the grab (→ `set_length` skipped by the
`abs(current - wanted) <= wanted*1e-9` guard); the counter-check for that branch
is section 2 ("wanted konstant") and section 3 ("kein ceiling_mult -> unveraendert")
which already exist. Without a pinned `wanted`, the 30 rising-mult frames would
each drive a distinct `wanted` and call `set_length` up to 30×.

Full run: **`test.horizon_targets: alle pruefungen bestanden`** (sections 1–4).

## Other test runs

- `python tests/ui_horizon_slider_test.py` → **`ui/widgets/rate_slider.py: alle
  pruefungen bestanden`** (unchanged, sanity — sections 1–10 incl. §6 `is_grabbing`).

- `python tests/warp_predictor_test.py` → **`FEHLGESCHLAGEN: 2`**, exit 1.
  Matches `.sdd-horizon-slider/snapshots/warp_predictor_test.BASELINE.txt` exactly.
  Per-FAIL classification:
  | FAIL line | baseline? | verdict |
  |---|---|---|
  | `jede neue linie gehoert zu einem NEUEREN schiffszustand -- 359 schnappschuesse, kleinste zunahme -0.035 m/s` | yes (documented in `.claude/rules/tests.md` + BASELINE line 291) | pre-existing, not a regression |
  | `die decke senkt die teilschritte bei 1 y/s um mehr als das 20-fache -- ohne decke 1408, mit decke 1280 (faktor 1)` | yes (BASELINE line 292; tests.md "measured factor 1") | pre-existing, not a regression |

  The timing-flaky third check (`wechsel-frame ... billig`, §17) **passed** this
  run (all §17 lines `ok`). **§23 passed in full** — all four "raffung laesst
  die gezeichnete linie stehen" checks at 0.0000e+00 m plus the
  "ohne deckel ... 2.2731e+06 m" counter-check. No new failures anywhere.

## Game smoke

`SPACESIM_MAX_FRAMES=120 python test.py` → `EXIT=0`, no `traceback` / `error` /
`exception` in the log. Steady-state timing `frame≈6.6 ms`, `pred_calc≈18 ms`
(async, off-thread). The `getattr(hud, 'horizon', None)` guard held with a real
`hud` lacking a `horizon` attribute.

## Self-review

- Placement follows the controller ruling (closures at 373–379, before `hud`),
  not brief Step 4's "after apply_predictor_horizon".
- `HORIZON_SWEEP_S` and both closures are currently unused — intentional, they
  are consumed by Task 5's `Hud(...)` wiring. No lint gate in this project.
- Constant names are UPPER_CASE to match the surrounding `PREDICTOR_*` /
  `REALTIME_WARP_MAX` locals in `main()`.
- Config keys read through `config.get(...)` + `float(...)` — matches the exact
  pattern of the adjacent `length_step` / `precision_step` / `predictor_min_precision`
  lines (the typed-accessor rule in `config-loader.md` is about not treating a
  nested section as a scalar; these three are plain numbers and the file's own
  convention here is `float(config.get(...))`).
- `grabbing` expression short-circuits left-to-right: `hud is not None` first,
  then `getattr` default `None`, then the attribute access — safe at every
  lifecycle stage.
- JSON trailing-comma: the three new keys sit between existing keys, object still
  parses (`ok`).

## Concerns

- `hud.horizon.is_grabbing` attribute name is assumed from the brief; the widget
  in `ui/widgets/rate_slider.py` does expose `is_grabbing` (confirmed by
  `ui_horizon_slider_test.py` §6). Task 5 must attach the instance as
  `hud.horizon`.
- The two pre-existing warp_predictor_test failures remain; unchanged by this task.
