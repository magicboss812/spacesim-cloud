## Task 6: Documentation

**Files:**
- Modify: `.claude/rules/hud-ui.md`
- Modify: `.claude/rules/predictor.md`
- Modify: `.claude/rules/camera-input.md`

**Interfaces:** none (docs only).

- [ ] **Step 1: `hud-ui.md` — widgets table + a short section**

In the `ui/widgets/` bullet (line ~193), add `HorizonSlider` to the list. Then add a section after the navball notes:

```markdown
> **The horizon slider is a RATE control, not a position one**
> (`ui/widgets/rate_slider.py`, bottom-left stack under FRAME + zoom). The
> knob rests at centre and springs back (`motion.fast`); displacement is the
> *speed* at which the drawn prediction length changes, integrated in
> `update()` as `mult *= exp(k·f(offset)·dt)` with `k` sized so a full
> deflection sweeps `horizon_slider_min_mult`→`max_mult` in
> `horizon_slider_sweep_seconds` (2.5). A ±0.06 deadzone and an `x^1.8`
> response curve keep it still at rest and fine near centre.
>
> It is smooth because it only ever calls `predictor.set_display_length()`
> — an O(1) clip of the already-computed curve. `apply_predictor_horizon()`
> in `test.py` reads `hud.horizon.is_grabbing` and, while the knob is held,
> pins the *computed* horizon (`set_length`, async/soft) to
> `horizon_slider_max_mult` via `horizon_targets()`, so `set_length` fires
> once per drag, not per frame. The `+` / `-` keys are unchanged (they still
> `predictor.reset()`).
```

- [ ] **Step 2: `predictor.md` — a note near `set_display_length` / `set_length`**

Add after the warp-step `set_length(soft)` note:

```markdown
> **The HUD horizon slider rides `set_display_length` every frame.** It is a
> rate control (`ui/widgets/rate_slider.py`): the drawn length tracks the
> knob through `set_display_length` (O(1), no recompute, independent of the
> hold / async swap / thrust), while the *computed* length trails via the
> already-soft `set_length`. `test.py::horizon_targets()` pins the computed
> target to `predictor.horizon_slider_max_mult` while
> `hud.horizon.is_grabbing`, so the `1e-9` guard in
> `apply_predictor_horizon()` trips once per drag and the async pipeline is
> never thrashed. No `reset()` on this path — that (still on `+` / `-`) is
> the synchronous `_compute_full` the slider exists to avoid.
```

- [ ] **Step 3: `camera-input.md` — controls table**

At the `+` / `-` row (line ~303), append:

```markdown
- `+` / `-` — predictor length ×2 / ÷2 (instant, full recompute). `9` / `0` —
  predictor precision (finer / coarser). The **HUD horizon slider**
  (bottom-left, under FRAME) is the smooth alternative to `+` / `-`: a
  centre-sprung rate control that changes only the *drawn* length per frame
  (`predictor.set_display_length`), with the computed horizon trailing
  asynchronously. See `.claude/rules/hud-ui.md`.
```

- [ ] **Step 4: Review checkpoint**

Summarise the three doc edits. Wait for approval.

---

