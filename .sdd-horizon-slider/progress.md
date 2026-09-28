# SDD ledger — plan: plans/2026-09-02-predictor-horizon-slider.md

Spec: plans/predictor_horizon_slider_design.md (read)
VCS: none — user ruled "execute without git". No commits; diffs built with `diff -u` against per-task snapshots under .sdd-horizon-slider/snapshots/. Recovery = this ledger + inspecting code state.

## Pre-flight conflict scan

Cross-task rows (shared file / interface):

| tasks | producer → consumer | finding |
|---|---|---|
| 1 → 5 | `HorizonSlider(value,minimum,maximum,on_change,predictor,sweep_seconds,wheel_step,role,size)` → `layout.py` builds it with `value=/minimum=/maximum=/on_change=/predictor=/sweep_seconds=` | consistent; layout omits `wheel_step`/`role`/`size` (all defaulted). clean |
| 1 → 2 | Task 1 leaves `# draw() kommt in Task 2` marker; Task 2 appends `draw` + `_horizon_metres` | clean; same file, additive |
| 1 → 4 | `HorizonSlider.is_grabbing` (bool property) → `apply_predictor_horizon` reads `hud.horizon.is_grabbing` | clean |
| 3 → 4 | `horizon_targets(...)` def (Task 3) → Task 4 adds `grabbing=`/`ceiling_mult=` kwargs at call site | clean; kwargs already in Task 3 signature |
| 3 → 4 | `apply_predictor_horizon` routed to `horizon_targets` (Task 3) → Task 4 edits same call to pass `grabbing` | clean; sequential edits to same block |
| 4 → 5 | closures `get_predictor_horizon_mult`/`set_predictor_horizon_mult` + `HORIZON_MULT_*` consts (Task 4) → passed to `Hud(...)` (Task 5) | ORDERING: Task 4 Step 4 places closures after `apply_predictor_horizon` (~line 590), Task 5 Step 5 requires them before `Hud(...)` (~line 356). Task 5 Step 5 explicitly instructs moving the closures + consts before the Hud construction. clean — handled in plan. |
| 4 → 5 | `Hud.__init__` new kwargs (Task 5 Step 3) ← `test.py` passes them (Task 5 Step 5) | same task, clean |
| 5 → 6 | `Hud.horizon`, `is_grabbing`, `horizon_targets` names → docs | clean |
| 4 → 7 | `_display_point_count` return (Task 7) independent of `horizon_targets`; Task 7 gated on a measurement in Task 5 Step 7 | clean; Task 7 optional |
| 1,3 → tests | new test files `ui_horizon_slider_test.py`, `horizon_targets_test.py` run via `python tests/x_test.py` (no pytest) | matches project convention (tests.md) |

Per-task self-consistency:

| task | tests vs code | finding |
|---|---|---|
| 1 | test imports `DEADZONE, HorizonSlider, _response` from `ui.widgets.rate_slider`; code defines all three module-level | clean |
| 1 | test stub `_Ctx` provides `.px`, `.theme.motion.fast`, `.text.measure`; widget `update`/`measure` touch exactly those | clean — `measure` also calls `ctx.text.measure('X','tab')` and `('X','mono_readout')`; stub `_Text.measure` ignores role, returns fixed tuple. OK |
| 1 | test never calls `draw()` (needs GL); draw deferred to Task 2 | clean |
| 2 | `hud_shot.py` run is a smoke check only (widget not in HUD yet); readout helper `_horizon_metres` tested headless | clean |
| 3 | `horizon_targets` test imports from `test` module; §23 already does `from test import predictor_horizon_lengths` so `import test` is headless-safe | clean |
| 3 | Task 3 Step 4 changes `apply_predictor_horizon` to call `horizon_targets` with no `grabbing` kwarg → defaults make it identical to `predictor_horizon_lengths` | clean — verified against Task 3 code: `grabbing=False` path returns `predictor_horizon_lengths(...)` unchanged |
| 4 | Task 4 Step 3 test section 4 monkeypatches `pred.set_length`/`set_display_length` with counters, replicates the `apply_predictor_horizon` tail | acceptable per project pattern (§23 replicates its rule too). Plan notes section 4 may already pass on Task 3 code — that is fine, it locks the contract |
| 4 | config.json edit: 3 keys inserted mid-object after `length_step_factor` | clean; plan includes a `json.load` verify step |
| 5 | `ui_hud_test.py` already builds `Hud(root, world, sim_ship, control, camera, renderer, predictor, state, ...)` at line ~203 positionally — new kwargs are keyword-only with defaults, existing call unaffected; new test section builds its own Hud with closures | clean |
| 6 | docs only | clean |
| 7 | optional; gated; plan says revert if any warp-hold section regresses | clean |

Rubric-vs-plan-mandate conflicts: none found. No task mandates an assertionless test or verbatim logic duplication. The Task 4 "replicate the apply_predictor_horizon tail in the test" is ~5 lines mirroring a rule, matching the existing `predictor_horizon_lengths`/§23 precedent — not flagged.

Scan verdict: clean. No rulings needed pre-execution.

## Task log

Task 1: complete (files: NEW ui/widgets/rate_slider.py, NEW tests/ui_horizon_slider_test.py [24 checks], MOD ui/widgets/__init__.py; review ✅ spec compliant, Approved, minors only).
  Task 1: minor (deferred): `mix` import unused until Task 2 — self-resolves in Task 2.
  Task 1: minor (deferred): tests/ui_horizon_slider_test.py ~L399 "ignoriert klicks" check is vacuous (on_mouse_down never calls on_change); real disabled-rate behaviour covered by the preceding check.
  Task 1: minor (deferred): __init__.py line endings flipped CRLF→LF. Repo is already mixed (~5 LF / ~4 CRLF in ui/); slider.py sibling is LF. Cosmetic — not fixing. Future diffs use `diff --strip-trailing-cr`.
  Task 1: minor (deferred): report said "25 checks", file has 24 check() calls. Cosmetic.

Task 2: complete (files: MOD ui/widgets/rate_slider.py [+_horizon_metres, +draw], MOD tests/ui_horizon_slider_test.py [+section 10]; review ✅ Approved, minors only).
  Task 2: minor (deferred): `_horizon_metres` `except Exception` is broad — could mask a real predictor-method bug as silent '--'. Brief's own choice.
  Task 2: minor (deferred): test section 10 doesn't exercise the `except` / `predictor is None` paths.
  Task 2: CARRY TO TASK 5 — endcap `−`/`+` glyphs render ~12 design-px outside the widget rect (`_track_rect` spans full `rect.w`; `measure()` reserves no horizontal room). Only clips if Task 5 places the widget <12px from a screen edge; vertical Stack = no sibling overlap. Reviewer's fix: inset `_track_rect` by `ctx.px(12.0)` on each side (input mapping follows automatically via `_offset_from_x`), keep `measure()` width at 168. Task 5 owns the decision.

Task 3: implementer DONE_WITH_CONCERNS — `horizon_targets()` added test.py ~L39-62; one call in `apply_predictor_horizon` (~L586) routed through it (same 4 positional args). NEW tests/horizon_targets_test.py (20/20). warp_predictor_test: 2 known pre-existing FAILs byte-identical to baseline + the documented timing-flaky `wechsel-frame billig` fired (11.5ms, machine was loaded — baseline + task ran concurrently). §23 passes 0.0000e+00. Game smoke 120 frames clean.
  Baseline: `.sdd-horizon-slider/snapshots/warp_predictor_test.BASELINE.txt` = FEHLGESCHLAGEN: 2 (`-0.035 m/s`, `faktor 1`).
  Controller re-running warp_predictor_test quiet (bg b4ksrtkjk) to confirm flaky check settles.
Task 3: complete (files: MOD test.py [+horizon_targets ~L39-58, 1 call rerouted L586], NEW tests/horizon_targets_test.py; review ✅ Approved). DONE_WITH_CONCERNS was the documented timing-flake — reviewer adjudicated it a non-regression (pure 2-float helper, not in any hot loop).
  Task 3: minor (deferred): task-3-report.md GREEN block miscounts section 2 as "7/7" (actually 8 ok lines). Cosmetic; test correct.

Ruling: Task 4 places the two closures (`get/set_predictor_horizon_mult`) immediately after `apply_frame_selection()` (currently test.py:368), BEFORE `hud = None` (L376) — not after `apply_predictor_horizon` as the plan's Task 4 Step 4 says. Why: Task 5 Step 5 otherwise has to move them before the `Hud(...)` call (L378); placing them there now eliminates that move and its risk. Closures only do `nonlocal predictor_manual_mult` (bound at L227) — no forward refs. HORIZON_* consts still go near predictor_min_precision (L236) per plan. Cost if wrong: the closures reference something not yet defined at L368 → NameError at call time (not import) → caught by Task 4 test + game smoke immediately; trivial to move down.

Current test.py line map (post-Task-3): predictor_manual_mult=1.0 @227; predictor_min_precision @236; apply_frame_selection() @368; hud=None @376; hud=Hud( @378; def apply_predictor_horizon @551; horizon_targets call inside it @586; +/- handlers @754/762; loop apply_predictor_horizon() @838.

Task 4: implementer DONE — config.json +3 keys (L61-63, JSON valid); test.py: HORIZON_* consts L237-239, closures L373-379 (after apply_frame_selection per ruling), `grabbing` guard + `ceiling_mult=HORIZON_MULT_MAX` into horizon_targets call L597-605; test section 4 added. horizon_targets_test all 4 sections PASS; ui_horizon_slider_test PASS; **implementer's warp_predictor_test run = FEHLGESCHLAGEN: 2 (clean, matches baseline)** — confirms the earlier 3-fail runs were load-polluted. Game smoke EXIT=0. Diff verified clean by controller (minimal, exactly spec + ruling). Serial warp re-run bxmsvybge started (quiet). Reviewer dispatched.
Task 4: complete (files: MOD config.json [+3 keys], MOD test.py [3 hunks: consts, closures, grabbing], MOD tests/horizon_targets_test.py [+section 4]; review ✅ Approved, minors only).
  Task 4: minor (deferred): consts use `float(config.get(...))` not `get_float()` typed accessor — brief-mandated, matches adjacent lines. Fine.
  Task 4: minor (deferred): test section 4 `import numpy as np` unused — verbatim from brief.
  Serial warp run bxmsvybge (machine quiet, post-Task-4) = FEHLGESCHLAGEN: 2, byte-identical to baseline (`-0.035 m/s`, `faktor 1`). CONFIRMED: Tasks 3+4 = zero warp-suite regression. Earlier 3-fail runs were 100% load-induced §14 flakiness.

Task 5: implementer DONE — layout.py (5 Hud params + widget build in left_stack, guarded), test.py (5 kwargs on Hud() call, nothing moved), rate_slider.py (`_track_rect` inset px(12)/side — ruling (c) applied; `−` glyph was ~4px off window edge), ui_hud_test.py (new §14), tools/hud_shot.py (box closures added — OUTSIDE brief file list, needed for visual check). Regression sweep clean: warp = 2 pre-existing (matches serial baseline), ui_hud/ui_horizon_slider/horizon_targets/apsis_stability/prediction_detail/prediction_projection/ui_units pass, energy pinned exact. §14 §17 §23 pass. Game smoke clean (frame≈7.8ms). Visual: slider in bottom-left stack under FRAME+zoom, PREDICT tab, detent, centred knob, glyphs OK post-inset. Screenshots at "screenshots for debugging/horizon_slider_hud{,_compact}.png". Concern: hud_shot.py edit outside file list. Reviewer dispatched.
Task 5: complete (files: MOD layout.py, MOD test.py [+5 kwargs], MOD rate_slider.py [_track_rect inset], MOD tests/ui_hud_test.py [+§14], MOD tools/hud_shot.py [+box closures]; review ✅ Approved, minors only — reviewer rendered a real 860px compact frame, no collision).
  Task 5: minor (deferred): hud_shot.py:314 lambda hardcodes 0.25/4.0 instead of HORIZON_MULT_MIN/MAX — dev-tool only.
  Task 5: minor (deferred): ui_hud_test §14 builds a 2nd Hud on the shared root — cosmetic, runs last.
  Task 5: minor (deferred → FINAL REVIEW): compact fit tight — slider `+` end ~2px from navball ORB flank at 860px. Not overlapping. Watch if min window width ever lowered.

Ruling: DO Task 7 despite the gate being indeterminate (Task 5's headless frame-cap runs couldn't measure an interactive drag). Rationale: code read confirms `get_points()` re-slices `self.points[:count]` nearly every frame of a live drag (count changes continuously) → `id(points)` churn → line-subdivision + apsis-scan cache miss per frame. Real (though ~= a zoom gesture's cost, which ships). User's stated priority is "smooth at almost all cost / errorfree". Task 7 (quantize count to mult of 8) is small, guarded by a warp-hold `array_equal` test, and the plan says revert if any hold section regresses. Cost if wrong: a predictor.py change that regresses the warp hold — caught by warp_predictor_test §18/§19/§21 + the new guard test; revert is clean (one function).

Task 6: implementer DONE — 3 rule files updated (hud-ui.md +HorizonSlider in widgets list, +RATE-control section, "…zoom and the predictor-horizon slider"; predictor.md +set_display_length note; camera-input.md +/- row extended). 3 brief→code corrections: (1) max_mult is a config key not a predictor attr; (2) two-step path (on_change writes predictor_manual_mult, apply_predictor_horizon calls set_display_length); (3) response curve `x^1.8` on deadzone-shifted magnitude. Review package built, reviewer dispatched.
Task 6: complete (files: MOD 3× .claude/rules/*.md; review ✅ Approved, minors only — every technical claim verified against shipped code).
  Task 6: minor (deferred): hud-ui.md uses non-greppable shorthands `_max_mult` / `_sweep_seconds` — should spell full `horizon_slider_max_mult` / `_sweep_seconds`.
  Task 6: minor (deferred): hud-ui.md & predictor.md notes overlap (both explain the set_display_length/set_length split) — brief asked for both, different altitudes, acceptable.
  Task 6: minor (deferred): "one recompute per drag" is really ~2 (grab pins, release settles); "while the knob is held" ignores the deadzone. Immaterial.
  Task 6: minor (deferred): neither note records that max_mult 4.0 = max_num_points/num_points (why the ceiling-pin needs no recompute).

Task 7: dispatched (RISKIEST — predictor.py). predictor.py:6259 `_display_point_count`, :6254 `_clear_display_view`, :2902 `display_length=None` init, get_points :6310. test.py:193 `config.apply_to_predictor`. Quantize count to mult of `predictor.display_length_quantum_points` (default 8); guard test for warp-hold `array_equal`. REVERT if any warp-hold section (§18/§19/§21) regresses.
Task 7: implementer DONE_WITH_CONCERNS — predictor.py: `_display_quantum=8` in __init__ L2909, quantise both return sites in `_display_point_count` L6309/6320, **removed `_clear_display_view()` from `set_display_length`** (necessary — eager clear defeats the quantise; get_points() self-invalidates via 3-way check). test.py L196 config wire. config.json L65 key. loader.py L365 registered the key. tests/horizon_targets_test.py +section 5 (view-identity). predictor.md: MERGED quantise para into Task 6's block (verified grep -c=1, NOT duplicated). tests.md +2 lines L84-85.
  Implementer reports: §18/§19/§21/§23 ALL PASS (quoted in report); warp = FEHLGESCHLAGEN: 2 byte-identical to serial baseline; prediction_detail/apsis_stability/prediction_projection pass; game smoke clean.
  Controller diff-check: all changes coherent & justified. `set_display_length` change well-commented, get_points() 3-way invalidation sound. loader.py registration = correct hygiene pattern.
  Task 7: minor (deferred → FINAL REVIEW): Task 4's `horizon_slider_min_mult/max_mult/sweep_seconds` NOT registered in loader.py's "nur von test.py ausgewertet" list (Task 7 registered only its own key). Consistency gap, no failure (no predictor config-key completeness test).
  Reviewer dispatched with elevated scrutiny on the set_display_length change + §23.
Task 7: complete (files: MOD predictor.py, MOD test.py, MOD config.json, MOD loader.py, MOD tests/horizon_targets_test.py [+§5], MOD .claude/rules/predictor.md + tests.md; review ✅ Approved — reviewer traced every `self.points` writer, removing eager clear is safe on all paths; revert gate §18/§19/§21/§23 all PASS).
  Task 7: minor (deferred → FINAL): predictor.md ~L267 + task-7-report "none of them set a display_length" is imprecise for §23 (§23 DOES call set_display_length but reads p.points directly, never get_points() — conclusion correct, wording wrong). Fix to "none of them draw via get_points()".
  Task 7: minor (deferred → FINAL): literal `8` in 4 code locations — could be `_DISPLAY_QUANTUM_DEFAULT` module const.
  Task 7: minor (deferred → FINAL): §5 report diagnostic numbers (992/992/1040) stale vs hand-calc — nitpick, test asserts identity not counts.

ALL 7 TASKS COMPLETE. Final whole-branch review (opus) = "Ready to merge: With fixes". Architecture sound, hard parts verified correct (grab-pin warp-invariance is real arithmetic not coincidence; eager-clear removal re-traced safe; frame ordering zero-latency; exp integration exact under variable dt). 3 Important + 1 Minor to fix:
  I-1: HORIZON_MULT_MAX=4.0 only works because 40000/10000=4.0 — if num_points raised, drag coarsens the line for the whole grab (§23 artefact). Fix: clamp to point-budget-derived value. test.py:241.
  I-2: `pressed` latches if mouseup lost (alt-tab mid-drag) → is_grabbing stuck True → horizon pinned at 4x cost forever. Fix: watchdog in UIRoot.begin_frame (pygame.mouse.get_pressed). Framework gap, benefits all draggables. core.py:445.
  I-3: Task 4's 3 horizon_slider_* keys unregistered in loader.py → startup prints "unbekannte Schlüssel ignoriert" for keys that ARE used. loader.py:365.
  M-1: predictor.md note names wrong warp sections (§23 DOES set display_length; §17 — the one that actually exercises the quantiser via get_points() — is omitted). + hud-ui.md ungreppable key shorthands.
  Deferred-minors triage: 11 of 13 = ACCEPTABLE-BACKLOG; #11 (=M-1) and #13 (=I-3) = MUST-FIX-NOW.
ONE fix wave dispatched (I-1+I-2+I-3+M-1). Baselines in snapshots/fixwave/. Then ONE scoped re-review.

Task 5: dispatched. Current test.py line map: closures @373/376, `hud = Hud(` @389 (ends ~394 before `)`). layout.py: `__init__` @90-92, `self._build` @108, `self.zoom_compact` add @198, `from ..widgets import Stack` @34.
  CARRY: (a) plan Task 5 Step 5 "move closures before Hud()" is now a NO-OP — Task 4 already placed them at L373-379, before the Hud() call at L389. Implementer just adds the 5 kwargs to the existing Hud() call.
  CARRY: (b) Task 2 glyph-overhang — reviewer's fix is to inset `_track_rect` by `ctx.px(12.0)` each side (input mapping follows via `_offset_from_x`, keep measure() width 168). Task 5 implementer decides based on the visual check at bottom-left corner / 1280x800.
  CARRY: (c) ui_hud_test.py builds Hud positionally @~L203 — new kwargs must be keyword-only w/ defaults so that call is unaffected; new test section builds its own Hud with closures.


NOTE on warp_predictor_test flakiness: it has MORE than the one documented timing-flaky check. Under concurrent CPU load, `wechsel-frame billig` (§17) AND `ein groesserer puffer glaettet weiter` / double-step counts (§14) both flake. Deterministic anchors for regression judgement: §23 (0.0 px), §10 memo bit-identity, §11 apsis on analytic ellipse, §20/§24 local step ceiling, and FEHLGESCHLAGEN count of the two deterministic fails (`-0.035 m/s`, `faktor 1`). Controller must run warp_predictor_test SERIALLY (nothing else running) for a clean read. My two "confirmation" re-runs both overlapped a task and are inconclusive.
  - BASELINE run (btki0c4it): concurrent only w/ Task 2 (light GL) → 2 fails. Best baseline.
  - AFTER-task3 run: concurrent w/ Task 4 dispatch → 3 fails (added §14 `puffer` double-step). Inconclusive — need a SERIAL run post-Task-4.
  - Assessment: Task 3 (2-float helper) + Task 4 (config reads, closures, 1 guarded bool, `grabbing` dead at runtime since hud.horizon=None) cannot touch the predictor compute / swap pipeline. §14 flake is load-induced. Confirm with a serial run before closing Task 4.



