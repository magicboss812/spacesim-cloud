## Task 7 (OPTIONAL): stabilise the drawn-view identity

Only do this if, during Task 5 Step 7, the `TIMING` line shows a measurable
per-frame cost *while dragging* (line re-subdivision / apsis rescan from
`id(points)` churn). If dragging is already smooth, **skip this task** — the
un-quantised path is correct.

**Files:**
- Modify: `spacesim/predictor.py` (`_display_point_count`)
- Modify: `spacesim/config.json` (`predictor.display_length_quantum_points`)
- Test: `spacesim/tests/horizon_targets_test.py` (add a view-identity section)

**Interfaces:**
- Consumes: `Predictor._display_point_count() -> int | None`, `Predictor.get_points()`, `Predictor.points`.
- Produces: quantised `count` (multiple of `display_length_quantum_points`, default 8), clamped `[2, n]`.

- [ ] **Step 1: Write the failing test**

Add to `spacesim/tests/horizon_targets_test.py` (needs the real `Predictor` from section 4 — put this after it, reusing `pred` before `pred.close()`, or build a fresh one):

```python
# --- 5. view-identitaet bleibt stehen innerhalb eines quantums --------
print("5. get_points()-identitaet")
pred2 = Predictor(async_compute=False, num_points=2000, precision=1.0e6)
pred2.initialize(ship, w)
pred2._compute_full(pred2._make_snapshot(ship, w), w) if hasattr(pred2, '_make_snapshot') else pred2.update(ship, w)
pred2.set_length(2000 * 1.0e6)
pred2.update(ship, w)

pred2.set_display_length(1.0e9)
a = pred2.get_points()
pred2.set_display_length(1.0e9 + 1.0e6)      # < 8 punkte weiter
b = pred2.get_points()
check(a is b, "identische view innerhalb eines quantums", f"{id(a)} vs {id(b)}")
pred2.set_display_length(1.0e9 + 5.0e7)      # deutlich weiter
c = pred2.get_points()
check(c is not b, "quantum-grenze ueberschritten -> neue view", "")
pred2.close()
```

- [ ] **Step 2: Run, verify it fails** (`a is b` is False today — every `set_display_length` re-slices).

Run: `cd spacesim && python tests/horizon_targets_test.py`

- [ ] **Step 3: Quantise the count**

In `spacesim/predictor.py`, in `_display_point_count()` (line ~6259), read the quantum once in `__init__` (search for where other `predictor.*` config lands — or default it) as `self._display_quantum = 8`, then change both `return max(2, min(n, count))` sites:

```python
            count = int(math.ceil(limit / spacing)) + 1
            q = max(1, int(getattr(self, '_display_quantum', 8)))
            count = int(round(count / q)) * q
            return max(2, min(n, count))
```

and the fallback branch identically. Add to `Predictor.__init__` (near the other display fields, line ~2901):

```python
        self._display_quantum = 8
```

Wire the config in `test.py` where `config.apply_to_predictor(predictor)` runs (line ~171), or via `config.json` `"predictor": {... "display_length_quantum_points": 8}` plus `predictor._display_quantum = int(config.get('predictor.display_length_quantum_points', 8))` right after `config.apply_to_predictor(predictor)`.

- [ ] **Step 4: Run the view-identity test + the warp hold regression**

Run: `cd spacesim && python tests/horizon_targets_test.py`
Expected: section 5 PASS.

Run: `cd spacesim && python tests/warp_predictor_test.py 2>&1 | tail -40`
Expected: **no new failures** — especially the warp-hold sections (18, 19, 21) and §23. The hold consumes `self.points`, not the display view, so quantising the *drawn* count must not touch it; if any hold section regresses, **revert this task** (the un-quantised path is correct).

Run: `cd spacesim && python tests/prediction_detail_test.py && python tests/apsis_stability_test.py`
Expected: no new failures.

- [ ] **Step 5: Manual re-check**

Run: `cd spacesim && python test.py` — drag the slider slowly; confirm the line-end no longer visibly steps and the frame time is flat.

- [ ] **Step 6: Review checkpoint**

Summarise: quantum added, view identity stable, hold regressions clean — or: reverted because a hold section regressed. Wait for approval.

---

## Self-Review

**1. Spec coverage**

| spec section | task |
|---|---|
| §1 (two lengths, feasibility) | 3, 4 (`horizon_targets` + `set_display_length`/`set_length` split) |
| §2 goals — smooth, no `_compute_full`, no async breakage, cost = dialled-in | 1 (spring), 3–4 (`grabbing` pin), 5 (wiring) |
| §3 Approach B | 3, 4 |
| §4.1 continuous `predictor_manual_mult` + closures | 4 |
| §4.2 `apply_predictor_horizon` change | 3 (route), 4 (`grabbing`) |
| §4.3 `HorizonSlider` — state, input, `update`, `is_grabbing`, enabled, draw | 1 (all logic), 2 (draw) |
| §4.4 layout wiring, `Hud` params, `self.horizon` | 5 |
| §4.5 config keys | 4 |
| §4.6 optional view-identity quantisation | 7 |
| §5 testing (10-row table + regressions) | 1 (rows 1–7, 9), 2 (row: readout), 4 (row 8), 5 (wiring + regressions), 7 (row 10) |
| §6 files touched | all tasks + 6 (docs) |
| §7 risks (thrash, flicker, compact crowding, no VCS) | 4 Step 2–3 (thrash test), 5 Step 7 (compact visual check), Global Constraints (VCS) |

Gaps: none. The spec's "compact layout crowding" risk is checked visually in Task 5 Step 7 at 1280×800; if it collides, the fix (hide in `_apply_responsive`) is a one-line follow-up noted there, not its own task.

**2. Placeholder scan** — every code step carries complete code. Test bodies are full. No "TBD" / "handle errors" / "similar to". The one deliberately open decision (Task 7 runs or not) is gated on a measurement in Task 5 with both outcomes spelled out.

**3. Type consistency**
- `HorizonSlider(value, minimum, maximum, on_change, predictor=, sweep_seconds=, wheel_step=, role=, size=)` — same in Task 1 (def), Task 5 (call), tests.
- `is_grabbing` — property, `bool`; read in Task 4 Step 5 and Task 5 test.
- `horizon_targets(base_length, manual_mult, warp_mult, max_points, base_spacing, *, grabbing=False, ceiling_mult=None) -> (drawn, wanted)` — same in Task 3 (def), Task 3 Step 4 (call, defaults), Task 4 Step 5 (call, kwargs), both tests.
- `get_predictor_horizon_mult() -> float` / `set_predictor_horizon_mult(mult)` — defined Task 4 Step 4, passed Task 5 Step 5, mirrored in the Task 5 test as `predictor_manual_mult_getter` / `_hmult_set`.
- `Hud(..., horizon_mult_get=, horizon_mult_set=, horizon_mult_min=, horizon_mult_max=, horizon_sweep_s=)` — def Task 5 Step 3, call Task 5 Step 5.
- `Hud.horizon: HorizonSlider | None` — set Task 5 Step 3/4, read Task 4 Step 5 (`getattr(hud, 'horizon', None)`), Task 5 test.
- `_response(offset) -> float`, `DEADZONE = 0.06` — module-level in Task 1, imported in tests.

No mismatches found.
