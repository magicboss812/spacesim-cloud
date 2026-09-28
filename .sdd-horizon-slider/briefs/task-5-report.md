# Task 5 report — build the `HorizonSlider` into the HUD

## Edits

### `spacesim/ui/hud/layout.py`

1. **Line 35** — new import beside the other widget imports:
   ```python
   from ..widgets.rate_slider import HorizonSlider
   ```
   (`ui/widgets/__init__.py` already re-exports `HorizonSlider`; the explicit
   sub-module import is the brief's form and avoids leaning on `__init__` order.)

2. **`Hud.__init__` signature (now lines 91–96)** — five new keyword args with
   defaults, so the existing positional/kw call in `ui_hud_test.py` (~line 203)
   and `tools/hud_shot.py` keep working:
   ```python
   def __init__(self, ui_root, world, ship, ship_control, camera, renderer,
                predictor, ui_state, tick_rate=60.0, realtime_warp_max=60.0,
                warp_timescale_divisor=3.0,
                horizon_mult_get=None, horizon_mult_set=None,
                horizon_mult_min=0.25, horizon_mult_max=4.0,
                horizon_sweep_s=2.5):
   ```

3. **Lines 109–115** — stored before `self._build(ship_control)`:
   ```python
   self._horizon_mult_get = horizon_mult_get
   self._horizon_mult_set = horizon_mult_set
   self._horizon_mult_min = float(horizon_mult_min)
   self._horizon_mult_max = float(horizon_mult_max)
   self._horizon_sweep_s = float(horizon_sweep_s)
   self.horizon = None
   ```

4. **`_build`, lines ~208–223** — after `self.zoom_compact = ...`, guarded so
   `Hud.horizon` stays `None` when no closures are supplied:
   ```python
   # Der vorhersage-horizont: ein mittenzentrierter raten-regler. Nach
   # rechts ziehen verlaengert die gezeichnete linie, nach links
   # verkuerzt sie -- die auslenkung ist die geschwindigkeit. Er
   # aendert NUR predictor.set_display_length (O(1), kein neuaufbau);
   # siehe plans/predictor_horizon_slider_design.md.
   if self._horizon_mult_get is not None and self._horizon_mult_set is not None:
       self.horizon = self.left_stack.add(HorizonSlider(
           value=self._horizon_mult_get,
           minimum=self._horizon_mult_min,
           maximum=self._horizon_mult_max,
           on_change=self._horizon_mult_set,
           predictor=self.telemetry.predictor,
           sweep_seconds=self._horizon_sweep_s,
       ))
   ```

### `spacesim/test.py`

**`Hud(...)` call (now lines 389–399)** — five new kwargs added; nothing moved
(controller ruling (a): the closures and `HORIZON_*` constants were already
placed before this call by Task 4):
```python
    horizon_mult_get=get_predictor_horizon_mult,
    horizon_mult_set=set_predictor_horizon_mult,
    horizon_mult_min=HORIZON_MULT_MIN,
    horizon_mult_max=HORIZON_MULT_MAX,
    horizon_sweep_s=HORIZON_SWEEP_S,
```

### `spacesim/ui/widgets/rate_slider.py`  (ruling-(c) inset fix — applied, see below)

**`_track_rect` (lines 82–92)** — the track is now inset by `ctx.px(12.0)` on
each side so the `−`/`+` end glyphs (drawn `px(9)+px(3)` outside the track) no
longer overhang almost to the screen edge:
```python
def _track_rect(self, ctx):
    inset = ctx.px(12.0)
    h = ctx.px(5.0)
    top_band = self._tab_h(ctx) + self._readout_h(ctx)
    free = self.rect.h - top_band - h
    top = self.rect.y + top_band + max(0.0, free) * 0.5
    return Rect(self.rect.x + inset, top, self.rect.w - inset * 2.0, h)
```
`measure()` width stays `ctx.px(168.0)`; `_offset_from_x` routes through
`_track_rect`, so click→offset mapping follows the shorter track automatically.

### `tools/hud_shot.py`

**Lines ~117–123** — the design-preview tool now passes trivial box closures for
the horizon multiplier so the slider actually renders in the shot (in-game these
live in `test.py::main()`):
```python
_hmult = [1.0]
hud = Hud(ui_root, w, ship, ship_control, camera, renderer, predictor, ui_state,
          tick_rate=180.0,
          horizon_mult_get=lambda: _hmult[0],
          horizon_mult_set=lambda m: _hmult.__setitem__(0, max(0.25, min(4.0, float(m)))))
```
Not named in the brief's file list, but the Step 7 visual check is impossible
without it (`hud.horizon` would be `None`).

### `spacesim/tests/ui_hud_test.py`

**New section 14 "Horizont-Regler"** (next free integer; file previously ended at
§13), inserted after the §13 `frame()` at old line 858, before the final summary
block. Builds its **own** `Hud` (`hud_h`) with real closures over `_hmult = [1.0]`
(named `predictor_manual_mult_getter` / `_hmult_set` per the brief), then asserts:
`hud.horizon` exists; it is in `left_stack.children`; starts `is_grabbing is
False`; 30 `update()` frames with `pressed=True, _offset=1.0` raise the mult
(`1.000 → 1.741`) and report `is_grabbing is True`; releasing (`pressed=False`)
springs `_offset` back inside the deadzone (`0.0000`).

## TDD — RED / GREEN for §14

RED (before the `layout.py` / `test.py` edits):
```
14. Horizont-Regler
Traceback (most recent call last):
  File ".../tests/ui_hud_test.py", line 877, in <module>
    hud_h = Hud(root, world, sim_ship, control, camera, renderer, predictor, state,
TypeError: Hud.__init__() got an unexpected keyword argument 'horizon_mult_get'
```

GREEN (after):
```
14. Horizont-Regler
  ok   hud.horizon existiert -- <ui.widgets.rate_slider.HorizonSlider object at 0x...>
  ok   sitzt im linken stapel (unter FRAME + zoom)
  ok   startet ungegriffen
  ok   griff nach rechts verlaengert den horizont -- 1.000 -> 1.741
  ok   waehrend des griffs: is_grabbing
  ok   loslassen federt in die mitte zurueck -- offset 0.0000

ui/hud: alle pruefungen bestanden
```
No other §1–§13 section regressed.

## Test runs (Step 6)

| test | result |
|---|---|
| `tests/ui_hud_test.py` | **alle pruefungen bestanden** (§1–§14) |
| `tests/ui_horizon_slider_test.py` | **alle pruefungen bestanden** (§1–§10, incl. after the `_track_rect` inset) |
| `tests/horizon_targets_test.py` | **alle pruefungen bestanden** (§1–§4) |

## Visual check (Step 7) — both resolutions

`tools/hud_shot.py 1600 900` and `1280 800` (both render at `ui_scale 1.00`;
1280 is still ≥ the compact breakpoint, so both show the full-width zoom pair).
Crops of the bottom-left corner read at 4× (scratchpad `c2_*.png`;
full frames saved to `screenshots for debugging/horizon_slider_hud{,_compact}.png`).

Confirmed present and correct:
- Slider sits in the bottom-left `left_stack`, directly under FRAME (SRF/ORB/TGT)
  and the SYSTEM / LOCAL zoom buttons.
- `PREDICT` notch tab on the top edge, cyan (enabled).
- Centre detent (vertical tick) drawn; knob centred on it (`_offset` ≈ 0).
- `−` glyph on the left, `+` glyph (horizontal + vertical stroke) on the right.
- Distance readout right-aligned at the widget's top-right — shows `--` in the
  tool because `hud_shot.py` never steps `predictor.update(world)`, so
  `get_display_length()` has no value yet. In-game (`test.py`) the predictor runs
  every frame and the readout shows a real distance; the `--`/None path is the
  one `ui_horizon_slider_test.py` §10 already pins.

**Ruling-(c) inset fix: APPLIED.** In the first shot the `−` glyph's leftmost
pixel sat at screen x ≈ 4 px (track.x = MARGIN 16, minus drawn at
`track.x − px(9) − px(3)`), i.e. fully visible but ~4 px off the window edge and
~13 px outside the widget rect — tight enough to read as a layout slip and
constant at every resolution (the stack's left margin is fixed at 16 px). The
ruling left the call to me ("clips … or collides" not strictly met). I applied
the provided inset: with `inset = px(12)` the minus now lands at screen x ≈ 16,
flush with the SYSTEM button's left edge, and the plus at the widget's right
edge — symmetric and clean. Re-shot and re-verified at both sizes; all three
slider tests still green afterwards.

## Interaction smoke (Step 8)

`SPACESIM_MAX_FRAMES=180 python test.py` → clean exit (also verified
`MAX_FRAMES=60` → `exit: 0`). No traceback/exception. Widget is live in the HUD
with real closures. Last TIMING line:
```
TIMING: pred_calc=20.4ms pred_draw=1.7ms rend_calc=3.7ms ui_calc=2.3ms rend_draw=0.6ms frame=7.8ms pred_hz=0 pipe=1
```
`ui_calc` ≈ 2.2–2.7 ms across the run (the slider adds nothing measurable);
`frame` steady 7.5–8.4 ms. Headless frame-cap can't drive a mouse drag, so this
only confirms "no crash with the widget built and updating".

## Regression sweep (Step 9)

Run from `spacesim/`. `warp_predictor_test.py` run **alone** (nothing else
running), `PYTHONUNBUFFERED=1`.

| test | result | classification |
|---|---|---|
| `warp_predictor_test.py` | `FEHLGESCHLAGEN: 2` | both **pre-existing**, see below |
| `apsis_stability_test.py` | **Alle pruefungen bestanden** (§1–§4) | — |
| `prediction_detail_test.py` | **alle pruefungen bestanden** (incl. §7 view-aware 6/6, 2.02 px, 0.000 px drift) | — |
| `prediction_projection_test.py` | **alle pruefungen bestanden** (§1, all frames `0` sub-point / plausible arc) | — |
| `ui_hud_test.py` | **alle pruefungen bestanden** (§1–§14) | — |
| `ui_units_test.py` | **alle pruefungen bestanden** | — |
| `energy_test.py` | exit 0; RKN4 fixed `final_rel=-4.2571e-07`, Verlet `+4.2230e-10` — **exactly the pinned values** in `.claude/rules/tests.md` | — |

### `warp_predictor_test.py` per-FAIL classification

Diffed against `.sdd-horizon-slider/snapshots/warp_predictor_test.BASELINE.txt` —
**identical failure set**, no new failures:

| FAIL | in BASELINE? | verdict |
|---|---|---|
| `jede neue linie gehoert zu einem NEUEREN schiffszustand -- 359 schnappschuesse, kleinste zunahme -0.035 m/s` | yes (BASELINE + `tests.md` "Known pre-existing failures") | **pre-existing** |
| `die decke senkt die teilschritte bei 1 y/s um mehr als das 20-fache -- ohne decke 1408, mit decke 1280 (faktor 1)` | yes (BASELINE + `tests.md` "measured factor 1") | **pre-existing** |

- **§23** (time warp leaves the drawn line untouched): **passed in full** — all
  four "raffung … laesst die gezeichnete linie stehen" at `0.0000e+00 m`, plus
  the `2.2731e+06 m` no-cap counter-check.
- **§14** (no double-steps) and **§17** (`wechsel-frame … billig`, the
  timing-flaky one): **all `ok`** this run.

## Self-review

- New `Hud.__init__` params are keyword-only-safe: all have defaults, existing
  callers (`ui_hud_test.py` line 203, `hud_shot.py`) untouched by the signature
  change and get `hud.horizon is None` unless they opt in. Verified — §1–§13
  still pass with the old call.
- `self.horizon = None` is set in `__init__` **before** `_build`, so the
  attribute always exists (Task 4's `apply_predictor_horizon` reads
  `getattr(hud, 'horizon', None)` — still safe, now returns a real widget).
- The widget is added to `left_stack` (a `Stack`), so it inherits the stack's
  `gap=8` / `align='start'` / bottom-left anchor — no bare pixel literals; all
  sizes inside `HorizonSlider` go through `ctx.px(...)`.
- `predictor=self.telemetry.predictor` — same object `test.py` passes to `Hud`;
  the widget's `update()` disables itself when `predictor.num_points == 0`
  (predictor toggled off with `P`), matching `ui_horizon_slider_test.py` §9.
- `_track_rect` inset keeps `measure()` at 168 (ruling (c)); `_offset_from_x`
  already derives its half-width from `_track_rect`, so input mapping tracks the
  shorter bar with no extra change. Knob travel is now ±72 px instead of ±84 —
  irrelevant for a rate control (deflection = speed, not a target position).
- `tools/hud_shot.py` closure uses `list.__setitem__` in a lambda to stay a
  one-liner; functionally identical to the test's `_hmult_set`.
- German comment in `layout.py` is the brief's Step 4 text verbatim.

## Concerns

- **`hud_shot.py` was edited though not in the brief's file list.** Necessary for
  the Step 7 visual check. Low risk (design tool, not shipped, not covered by
  tests); the change is additive.
- **Readout shows `--` in `hud_shot.py`.** Not a bug — the tool doesn't step the
  predictor. If a future reviewer wants a real number in the design shot,
  `hud_shot.py` would need a `predictor.update(w)` call in its warm-up loop.
- Two pre-existing `warp_predictor_test.py` failures persist — unchanged by this
  task, documented in `tests.md` and the plan's BASELINE snapshot.
- `.claude/rules/hud-ui.md` / `camera-input.md`: the HUD-controls list and the
  bottom-left block description could gain one line about the horizon slider.
  Left for the plan's doc task (Task 6/7 touch `predictor.md` and the controls
  reference); flagging rather than editing mid-stream.
