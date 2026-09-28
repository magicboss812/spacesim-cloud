# Task 1 report — `HorizonSlider` (spring, rate, input, enabled state)

## What was implemented

The centre-sprung "rate" slider **logic only** (no `draw()` — that is Task 2),
plus its headless test.

- `HorizonSlider(Widget)` — centre-sprung rate slider. Deflection is the
  *speed* of change, not a target value. Exponential (log-linear) rate so the
  horizon is perceived in decades; `_response()` applies a dead-zone and a
  `**1.8` curve; releasing eases `_offset` back to 0 at `motion.fast`;
  `enabled` tracks `predictor.num_points > 0` every frame; wheel notches
  multiply/divide by `wheel_step`, always clamped to `[minimum, maximum]`.
- Module-level `DEADZONE = 0.06` and `_response(offset)`.
- Code transcribed verbatim from the brief (German comments kept). Only imports
  are `..core` (`Rect`, `Widget`, `ease`) and `..theme` (`mix`) — no
  `ui/hud/...` import, so no import cycle.

## Files changed

- **Created** `spacesim/ui/widgets/rate_slider.py` — the widget (logic only).
- **Created** `spacesim/tests/ui_horizon_slider_test.py` — headless test
  (stub `_Ctx`/`_Theme`/`_Text`/`_Predictor`; no pygame, no GL).
- **Modified** `spacesim/ui/widgets/__init__.py` — added
  `from .rate_slider import HorizonSlider` and the `__all__` entry.

## TDD evidence

### RED — before `rate_slider.py` existed

```
$ python tests/ui_horizon_slider_test.py
Traceback (most recent call last):
  File ".../tests/ui_horizon_slider_test.py", line 20, in <module>
    from ui.widgets.rate_slider import DEADZONE, HorizonSlider, _response
ModuleNotFoundError: No module named 'ui.widgets.rate_slider'
```

### GREEN — after Steps 3 & 4

```
$ python tests/ui_horizon_slider_test.py
1. Totzone
  ok   innerhalb der totzone bleibt der wert stehen -- wert 1.0
  ok   ausserhalb der totzone steigt der wert -- wert 1.058
2. Raten-proportionalitaet
  ok   volle auslenkung fuer sweep_seconds -> min..max -- wert 4.000
  ok   halbe auslenkung ist deutlich langsamer -- wert 0.507
3. Rueckweg zur mitte
  ok   voll nach links -> zurueck auf min -- wert 0.2500
4. Federweg
  ok   offset zerfaellt in die totzone -- offset 0.0001
  ok   nach dem federweg keine weitere aenderung
  ok   gedrueckt haelt der offset -- offset 0.7
5. Klemmung auf [min, max]
  ok   der wert verlaesst [0.25, 4.0] nie -- wert 1.0825
6. is_grabbing
  ok   nicht gedrueckt -> kein grabbing
  ok   gedrueckt in der mitte -> kein grabbing
  ok   gedrueckt und ausgelenkt -> grabbing
7. Mausrad-raste
  ok   eine raste hoch = x wheel_step -- wert 2.0
  ok   eine raste runter = / wheel_step -- wert 1.0
  ok   das rad klemmt auch -- wert 4.0
8. _response
  ok   _response(0) == 0
  ok   _response in der totzone == 0
  ok   _response(1) == 1 -- 1.0
  ok   _response(-1) == -1 -- -1.0
  ok   _response(0.5) unter der geraden -- 0.255
9. Abgeschaltet ohne vorhersage
  ok   num_points == 0 -> enabled False
  ok   abgeschaltet aendert der regler nichts -- wert 1.0
  ok   abgeschaltet ignoriert er klicks -- wert 1.0
  ok   num_points zurueck -> enabled True

ui/widgets/rate_slider.py: alle pruefungen bestanden
```

All 25 checks pass. No widget bug was revealed; the transcribed code passed
as-is.

## Step 6 — regression check

```
$ python tests/ui_units_test.py
ui/units.py: alle pruefungen bestanden

$ python tests/devui_timing_test.py
devui timing: alle pruefungen bestanden
```

Both pass — the `ui.widgets` import still resolves with the new export.

## Self-review findings / concerns

- **`mix` import is currently unused** in `rate_slider.py` (it is only needed
  by `draw()` in Task 2). Kept because the brief's Step 3 code block includes
  it verbatim and instructs precise transcription. It will be used in Task 2;
  until then it is a dormant import, not a bug.
- **`update()` reassigns `self.enabled` every frame** from the predictor. This
  matches test 9 exactly. Note that when `predictor is None` the widget never
  touches `enabled`, so an externally set `enabled=False` is respected.
- **No `pygame.init()`**, no display/font init, no GL — the test is fully
  headless as required. `import pygame` still runs (via `ui.core` →
  `ui.draw`), printing the pygame banner, but nothing is initialised.
- Test invokes `on_wheel` / `on_mouse_down` directly rather than through
  `UIRoot`; that is the brief's design and is fine for unit-level logic.
- `draw()` is intentionally absent (Task 2). `HorizonSlider` inherits
  `Widget.draw` (a no-op), so it is safe to instantiate but not yet wired into
  any HUD layout.
