# Task 6 review package (docs only)

## diff: .claude/rules/hud-ui.md
```diff
--- .sdd-horizon-slider/snapshots/task-6-hud-ui.md.base	2026-09-02 22:46:44.853923600 +0200
+++ .claude/rules/hud-ui.md	2026-09-02 22:49:33.904136400 +0200
@@ -191,7 +191,8 @@
     cannot diverge. **Invariant: view state only, no physics** — the reference
     frame is a pure display transform.
   - `ui/widgets/` — Panel, Group, Label, Readout, Button, Toggle,
-    SegmentedControl, Slider (linear/log), Dropdown.
+    SegmentedControl, Slider (linear/log), HorizonSlider (centre-sprung rate),
+    Dropdown.
   - `ui/hud/` — the concrete HUD elements, restyled 2026-08-19 onto the KSP2
     instrument panel. `chrome.py` (**the form vocabulary — chamfer, double
     frame, notch tab, ruler, segmented arc; every surface goes through it**),
@@ -207,7 +208,7 @@
 > Top-left ship badge → reference selector → target block (one column, equal
 > widths, docked by sharp corners); top-right the warp bar with the UT clock;
 > bottom-centre the navball cluster with the snap rosette docked to its right;
-> bottom-left frame selector and zoom. The previous layout scattered eight
+> bottom-left frame selector, zoom and the predictor-horizon slider. The previous layout scattered eight
 > separate lozenges and built the bottom-centre column tall enough to sit on
 > top of the orbit — the one thing the screen exists to show.
 >
@@ -297,6 +298,26 @@
 > `UIState` cannot reach — `set_reference_index(None)` is a no-op — but
 > `Telemetry` accepts `ui_state=None`, so the test goes through that door).
 
+> **The horizon slider is a RATE control, not a position one**
+> (`ui/widgets/rate_slider.py::HorizonSlider`, bottom-left stack under FRAME +
+> the SYSTEM/LOCAL zoom buttons). The knob rests at centre and springs back
+> there (`ease` at `theme.motion.fast`); its displacement is the *speed* at
+> which the drawn prediction length changes, integrated in `update()` as
+> `mult *= exp(k·f(offset)·dt)`, `k = ln(max/min) / sweep` sized so a full
+> deflection sweeps `predictor.horizon_slider_min_mult` (0.25) → `_max_mult`
+> (4.0) in `_sweep_seconds` (2.5). A ±0.06 deadzone and an `x^1.8` response on
+> the deadzone-shifted magnitude keep it still at rest and fine near centre.
+>
+> It is smooth because moving the knob only writes a clamped multiplier
+> (`set_predictor_horizon_mult`); `apply_predictor_horizon()` in `test.py`
+> turns that into one `predictor.set_display_length()` per frame — an O(1)
+> clip of the already-computed curve. While the knob is held that function
+> reads `hud.horizon.is_grabbing` and, via `test.py::horizon_targets()`, pins
+> the *computed* horizon (`set_length`, async/soft) as if the manual factor
+> sat at the `_max_mult` ceiling, so the `1e-9` guard swallows every
+> `set_length` after the first — one recompute per drag, not per frame. The
+> `+` / `-` keys are unchanged (they still `predictor.reset()`).
+
 > **The reference list unfolds DOWNWARD out of its button.** `BodyBrowser`
 > keeps `open` as the *target* and `_open_t` as the drawn state, eased with
 > the project's usual framerate-independent `1 - exp(-rate·dt)` at
```

## diff: .claude/rules/predictor.md
```diff
--- .sdd-horizon-slider/snapshots/task-6-predictor.md.base	2026-09-02 22:46:44.874185100 +0200
+++ .claude/rules/predictor.md	2026-09-02 22:49:41.920655900 +0200
@@ -253,6 +253,18 @@
 >    O(1)), taken **mid-curve**, because `points[0]` is the ship and carries a
 >    deliberately short first chord.
 
+> **The HUD horizon slider rides `set_display_length` every frame.** It is a
+> rate control (`ui/widgets/rate_slider.py::HorizonSlider`): the drawn length
+> tracks the knob through `set_display_length` (O(1), no recompute,
+> independent of the hold / async swap / thrust), while the *computed* length
+> trails via the already-soft `set_length`. `test.py::horizon_targets()` pins
+> the computed target as if the manual factor sat at the config ceiling
+> `predictor.horizon_slider_max_mult` (4.0) while `hud.horizon.is_grabbing`,
+> so the `1e-9` guard in `apply_predictor_horizon()` trips once per drag and
+> the async pipeline is never thrashed. No `reset()` on this path — that
+> (still on `+` / `-`) is the synchronous `_compute_full` the slider exists to
+> avoid.
+
 > **Real time now uses the hold's mechanism too — the Ap/Pe markers were
 > jittering because it did not.** Fixed 2026-08-25. Outside the warp hold
 > `_anchor_first_point` translated the whole curve rigidly so its head sat on
```

## diff: .claude/rules/camera-input.md
```diff
--- .sdd-horizon-slider/snapshots/task-6-camera-input.md.base	2026-09-02 22:46:44.895048900 +0200
+++ .claude/rules/camera-input.md	2026-09-02 22:49:47.119551500 +0200
@@ -299,8 +299,12 @@
 - `P` — toggle predictor. `E` — toggle epicycle (Ptolemaic) mode.
 - `R` — cycle reference body. `1` — non-rotating frame.
   `2` — body-direction frame. `T` — target overlay.
-- `+` / `-` — predictor length ×2 / ÷2. `9` / `0` — predictor precision
-  (finer / coarser).
+- `+` / `-` — predictor length ×2 / ÷2 (instant, full recompute). `9` / `0` —
+  predictor precision (finer / coarser). The **HUD horizon slider**
+  (bottom-left, under FRAME) is the smooth alternative to `+` / `-`: a
+  centre-sprung rate control that changes only the *drawn* length per frame
+  (`predictor.set_display_length`), with the computed horizon trailing
+  asynchronously. See `.claude/rules/hud-ui.md`.
 - `PageUp` / `PageDown` — sim_dt up / down. `Esc` — quit.
 - **Warp steps are `1m/s, 10m/s, 1h/s, 1d/s, 7d/s, 30d/s, 100d/s, 1y/s`**
   (`ui/hud/layout.py::WARP_STEPS`, sim-seconds per real second). The top
```

