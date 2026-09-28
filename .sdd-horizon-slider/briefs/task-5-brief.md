## Task 5: Build the slider into the HUD

**Files:**
- Modify: `spacesim/ui/hud/layout.py` (`Hud.__init__` params; build widget in `_build`)
- Modify: `spacesim/test.py` (pass closures + bounds to `Hud`)
- Test: `spacesim/tests/ui_hud_test.py` (add a wiring section); manual `hud_shot.py` + `test.py`

**Interfaces:**
- Consumes: `HorizonSlider` (Task 1–2); `get_predictor_horizon_mult` / `set_predictor_horizon_mult` / `HORIZON_MULT_MIN` / `HORIZON_MULT_MAX` / `HORIZON_SWEEP_S` (Task 4); `Stack.add(child)`; `telemetry.predictor`.
- Produces: `Hud.horizon` — a `HorizonSlider` instance, or `None` when `horizon_mult_get` is not supplied.

- [ ] **Step 1: Write the failing wiring test**

In `spacesim/tests/ui_hud_test.py`, find where a `Hud` is constructed for the "Bedienung gegen den simulationszustand" section (search `Hud(`). Add a new numbered section after it that reuses the same `hud` / `predictor` objects:

```python
# ═══════════════════════════════════ 14. horizont-regler ist verdrahtet
print("14. Horizont-Regler")

check(getattr(hud, 'horizon', None) is not None,
      "hud.horizon existiert", str(getattr(hud, 'horizon', None)))
check(hud.horizon in hud.left_stack.children,
      "sitzt im linken stapel (unter FRAME + zoom)", "")
check(hud.horizon.is_grabbing is False,
      "startet ungegriffen", "")

# ein simulierter griff nach rechts hebt den manuellen faktor
_start = predictor_manual_mult_getter()
hud.horizon.pressed = True
hud.horizon._offset = 1.0
for _ in range(30):
    hud.horizon.update(hud.ctx, 1.0 / 60.0)
check(predictor_manual_mult_getter() > _start,
      "griff nach rechts verlaengert den horizont",
      f"{_start:.3f} -> {predictor_manual_mult_getter():.3f}")
check(hud.horizon.is_grabbing is True, "waehrend des griffs: is_grabbing", "")

hud.horizon.pressed = False
for _ in range(30):
    hud.horizon.update(hud.ctx, 1.0 / 60.0)
check(abs(hud.horizon._offset) < 0.06,
      "loslassen federt in die mitte zurueck", f"offset {hud.horizon._offset:.4f}")
```

You will need a `predictor_manual_mult_getter` — when building the test's `Hud`, pass real closures over a mutable box:

```python
_hmult = [1.0]
def predictor_manual_mult_getter():
    return _hmult[0]
def _hmult_set(m):
    _hmult[0] = max(0.25, min(4.0, float(m)))
```

and pass `horizon_mult_get=predictor_manual_mult_getter, horizon_mult_set=_hmult_set` to that `Hud(...)` call.

- [ ] **Step 2: Run it, verify it fails**

Run: `cd spacesim && python tests/ui_hud_test.py 2>&1 | tail -30`
Expected: FAIL at section 14 — `Hud() got an unexpected keyword argument 'horizon_mult_get'` (or `hud.horizon` is `None`).

- [ ] **Step 3: Add the params to `Hud.__init__`**

In `spacesim/ui/hud/layout.py`, extend `Hud.__init__` (line ~90):

```python
    def __init__(self, ui_root, world, ship, ship_control, camera, renderer,
                 predictor, ui_state, tick_rate=60.0, realtime_warp_max=60.0,
                 warp_timescale_divisor=3.0,
                 horizon_mult_get=None, horizon_mult_set=None,
                 horizon_mult_min=0.25, horizon_mult_max=4.0,
                 horizon_sweep_s=2.5):
```

Store them before `self._build(ship_control)`:

```python
        self._horizon_mult_get = horizon_mult_get
        self._horizon_mult_set = horizon_mult_set
        self._horizon_mult_min = float(horizon_mult_min)
        self._horizon_mult_max = float(horizon_mult_max)
        self._horizon_sweep_s = float(horizon_sweep_s)
        self.horizon = None
```

- [ ] **Step 4: Build the widget in `_build`**

In `spacesim/ui/hud/layout.py`, add the import at the top with the other widget imports:

```python
from ..widgets import Stack
from ..widgets.rate_slider import HorizonSlider
```

Then in `_build`, in the "unten links" block, after `self.zoom_compact = self.left_stack.add(...)` (line ~200):

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

- [ ] **Step 5: Pass the closures from `test.py`**

In `spacesim/test.py`, the `Hud(...)` construction (line ~356):

```python
        hud = Hud(
            ui_root, w, ship, ship_control, camera, renderer, predictor, ui_state,
            tick_rate=float(max(1, FPS)),
            realtime_warp_max=REALTIME_WARP_MAX,
            warp_timescale_divisor=WARP_TIMESCALE_DIVISOR,
            horizon_mult_get=get_predictor_horizon_mult,
            horizon_mult_set=set_predictor_horizon_mult,
            horizon_mult_min=HORIZON_MULT_MIN,
            horizon_mult_max=HORIZON_MULT_MAX,
            horizon_sweep_s=HORIZON_SWEEP_S,
        )
```

**Ordering check:** `get_predictor_horizon_mult` / `set_predictor_horizon_mult` are defined right after `apply_predictor_horizon` (Task 4 Step 4), which is at line ~590 — *after* the `Hud(...)` call at ~356. **Move the two closure defs and the three `HORIZON_*` constants to before the `Hud(...)` construction** (e.g. just after `apply_frame_selection()` at line ~346, before `hud = None` at ~354). `apply_predictor_horizon` itself does not need to move — the closures do not call it. Verify `predictor_manual_mult` is already assigned by then (it is — line ~205).

- [ ] **Step 6: Run the tests**

Run: `cd spacesim && python tests/ui_hud_test.py 2>&1 | tail -30`
Expected: section 14 PASS; no new failures elsewhere.

Run: `cd spacesim && python tests/ui_horizon_slider_test.py && python tests/horizon_targets_test.py`
Expected: PASS.

- [ ] **Step 7: Visual + interaction check**

Run: `cd .. && python tools/hud_shot.py 1600 900 -o "$(pwd)/screenshots for debugging/horizon_slider_hud.png"`
Then read that PNG: the slider sits in the bottom-left stack under FRAME and the SYSTEM/LOCAL zoom buttons, with a `PREDICT` notch tab, a centre detent, a knob at centre, `−`/`+` end glyphs, and a distance readout (e.g. `10.0Gm`) at the right.

Run: `cd spacesim && python test.py` and manually: drag the knob right — the prediction line lengthens smoothly, no stutter in the `TIMING` line (`frame_ms` stays flat, `pred_hz` does not collapse); drag left — it shortens instantly; release — knob springs to centre and the length holds. Toggle predictor off with `P` — slider greys and ignores the mouse. Confirm `+`/`-` still work as before (instant step).

- [ ] **Step 8: Full regression sweep**

Run each, expect no new failures vs. the pre-plan baseline (mind the known pre-existing `warp_predictor_test.py` failures):

```
cd spacesim
python tests/warp_predictor_test.py 2>&1 | tail -40
python tests/apsis_stability_test.py
python tests/prediction_detail_test.py
python tests/prediction_projection_test.py
python tests/ui_hud_test.py
python tests/ui_units_test.py
python tests/energy_test.py
```

- [ ] **Step 9: Review checkpoint**

Summarise: widget in the HUD, closures wired, ordering fixed, screenshots + manual drag confirmed, regression sweep clean. Wait for approval.

---

