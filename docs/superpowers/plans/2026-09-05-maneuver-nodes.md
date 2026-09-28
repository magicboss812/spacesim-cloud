# Maneuver Node Plan Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a maneuver-node planner to spacesim — up to five nodes on the predicted trajectory, each edited by ±prograde/±normal Δv through a HUD block docked to the navball and drag handles on the line, executed by an autopilot that ramps the throttle smoothly and lands the planned Δv exactly.

**Architecture:** One new package `ship/maneuver/` holds the whole feature: a pure throttle-profile module that *both* the preview and the executor call (so the drawn line and the flown burn cannot disagree), a plan container, a preview that chains coast→burn→coast segments through the existing `physics/kernels`, and an autopilot state machine. Rendering gets a fifth draw domain; the HUD gets one self-drawing block plus a gizmo widget that hit-tests screen positions the renderer publishes.

**Tech Stack:** Python 3.13, numpy, numba (`@njit`), pygame (display/font only), moderngl. No new dependencies.

**Spec:** Folded into this document — see **Design decisions** below. Brainstormed 2026-09-05; the user asked for the plan directly rather than a separate spec file.

## Global Constraints

Copied from `CLAUDE.md` and the path-scoped rules. Every task's requirements implicitly include this section.

- **SI units only.** Metres, seconds, kilograms, m/s, m/s². 2D only. Never introduce AU, days, or Earth-masses.
- **Physics stays in absolute (barycentric) space.** Reference frames are a render-time transform only. Never bake a frame into stored body state. A node stores `(prograde, normal)` components plus the world-space direction they resolve to; it never stores frame-space coordinates.
- **Numba kernels must stay pure.** `@njit` functions take plain arrays and scalars — no Python objects, no pygame, no OpenGL.
- **`Vec2` semantics.** `a + b`, `a - b`, `a * k` return new instances; only `+=` / `-=` / `*=` mutate.
- **Two Y conventions.** The world draws top-down; text and the ship draw ortho. `ui/` is entirely top-down and converts only in `UIDraw._submit` and `TextRenderer._blit`.
- **UI sizes are design units, never pixels.** `UIContext.px()` scales them. A literal pixel value in widget code is a bug at any resolution but the reference one.
- **Input priority is custom UI → ImGui → world.** Anything that polls the keyboard must check `ui_wants_keyboard` explicitly.
- **Never call `pygame.init()`.** Only `pygame.display.init()` and `pygame.font.init()`.
- **A negative corner radius is a CHAMFER.** All HUD surfaces go through `ui/hud/chrome.py`; never draw a raw rounded rect in a HUD block.
- **The palette is four colours, fixed** (`ui/theme.py::SCHEME`): cyan = data, magenta = second axis, amber = energy/caution, green = engaged/ready. This feature adds **no new colour** — it adds `ROLE_INDEX` entries that map onto the existing four.
- **No dependency manifest** — this feature adds no imports outside the standard set, so `README.md`'s install line is unchanged.
- **Tests are plain scripts**, run from inside `spacesim/` as `python tests/<name>.py`. There is no pytest. Each file collects into a `FAILURES` list and exits 1 if non-empty.
- **Git:** `spacesim/` is a repo; `Werk/` is not. Commit only inside `spacesim/`. `CLAUDE.md`, `.claude/rules/` and this plan are tracked by nothing — edit them, but they cannot be committed.
- German/English mix is intentional. New code in `ship/maneuver/` and `render/` may be commented in English; new code in `ui/` follows the German of its neighbours.

---

## Design decisions

These were settled during brainstorming. They are requirements, not suggestions.

### D1 — The burn is a symmetric ramp, and its duration is derived, never stored

Throttle rises at a fixed **rate** `r = a_max / ramp_seconds` (m/s³), holds, and falls at the same rate. The rate is what is conserved, not the ramp *time*: with a fixed ramp time a tiny Δv would produce a discontinuity in burn duration.

- `a_peak = min(a_max, sqrt(dv · r))`
- `ramp_time = a_peak / r`
- `hold_time = max(0, dv / a_peak − ramp_time)`
- `total_time = 2 · ramp_time + hold_time`

Both branches are symmetric, so **half the Δv is delivered before `total_time / 2`**. That gives the ignition time for free: `t_ignition = t_node − total_time / 2`. Nothing stores a duration or an ignition time; both are recomputed from the node's current Δv every time they are read, so they cannot go stale against a Δv the player just changed.

### D2 — `a_max` is a SIM-time acceleration, and it is derived from the manual thrust

`schiffcontrol.apply_thrust` adds `thrust_acc * real_dt` (600 m/s² × wall seconds) while the world advances `camera.sim_dt * tick_rate * real_dt` **sim** seconds. At the lowest warp step (`realtime_warp_max = 60` sim-s per real s) the effective acceleration *in simulation time* is therefore `600 / 60 = 10 m/s²`, not 600.

The preview integrates in sim time, so the profile's `a_max` must be a sim-time acceleration or the drawn line would show a burn ten times more violent than the manual thrust the player knows:

```
a_max_sim = ship.thrust_acc / realtime_warp_max        # 600 / 60 = 10.0 m/s²
```

`config.maneuver.max_accel` overrides it; `null` (the default) means derive. Task 4 pins this with a test that flies a manual full-throttle burn and an executor burn of the same sim duration and asserts the same Δv.

### D3 — The Δv direction is resolved once, at node time, and held

`(dv_prograde, dv_normal)` are resolved against the orbital basis at the node's own time — prograde = unit velocity relative to the reference body, normal = perpendicular, **positive inward** (the same sign rule as `physics/reference_frames.py::apparent_orbital_directions`, so the rosette, the ring markers and the gizmo handles cannot disagree). The result is one fixed world direction held for the whole burn.

This is what makes preview and execution identical: both integrate the same `a(t)` along the same constant direction.

### D4 — Execute always takes the earliest node

`ManeuverPlan.nodes` is kept sorted by `t_node`. `EXECUTE` arms `nodes[0]`. The other nodes are untouched; executing again after the first completes arms the next. Max five nodes.

### D5 — EXECUTE is disabled when the node carries no Δv

A node may exist with `dv_prograde == dv_normal == 0` (that is how you place one before deciding what to do with it). `ManeuverNode.is_executable` is `dv_total > config.maneuver.min_executable_dv` (1e-3 m/s). The HUD button sets `enabled` from it and draws with `palette.disabled` / `palette.text_dimmer`. `ManeuverExecutor.arm()` refuses independently — the button being grey is a courtesy, not the guard.

### D6 — Warp drops itself before ignition

Thrust is realtime-only. While armed:

- the sim step is clamped so a frame can never step *past* `t_ignition`;
- inside `orient_lead_seconds` of ignition, `camera.sim_dt` is forced down to realtime;
- during the burn the sim step is capped at `burn_step_max_s` so the kick-then-drift discretisation stays small.

### D7 — Placement: docked to the navball, mirroring the snap rosette

The `MANEUVER` block hangs on the **left** flank of `NavballCluster`, at the same dock gap and the same anchor rule the `SnapRosette` uses on the right. It is **one self-drawing widget** (like `NavballCluster`, not a `Stack`), built from `chrome.frame` / `chrome.plate` / `chrome.tab`, with a `MANEUVER` notch tab at the bottom edge. A fifth ring marker (`'node'`) shows the burn direction on the compass ring, and the throttle arc animates the ramp because the executor writes `Telemetry.set_thrust_level`.

### D8 — Colours reuse the fixed four

- ±prograde handles and the `PRO` row: **green** (`snap`) — the same colour the rosette gives prograde.
- ±normal handles and the `NRM` row: **magenta** (`normal`).
- Δv total, burn duration, countdown, the node marker, the ring marker: **amber** (`node` → index 2, energy).
- The planned trajectory: **green** (`node_path` → index 3) — it is the autopilot's promise, which is what green means here.

### D9 — Known limitation, to be stated in the docs

Node 5 is planned on a trajectory that is already four integrations deep. The chain is rebuilt from the live predictor curve whenever the base trajectory changes, which bounds the drift, but the tail of a five-node multi-year plan is approximate. This is inherent, not a defect.

---

## File structure

**Create:**

| file | responsibility |
|---|---|
| `spacesim/ship/maneuver/__init__.py` | re-exports `ManeuverNode`, `ManeuverPlan`, `BurnProfile`, `ManeuverPreview`, `ManeuverExecutor` |
| `spacesim/ship/maneuver/profile.py` | `BurnProfile` — the ramp. Pure maths, no imports beyond `math` |
| `spacesim/ship/maneuver/plan.py` | `ManeuverNode`, `ManeuverPlan`, `orbital_basis()`, `burn_direction_world()` |
| `spacesim/ship/maneuver/preview.py` | `ManeuverPreview` — the chained coast/burn/coast trajectory |
| `spacesim/ship/maneuver/executor.py` | `ManeuverExecutor` — the autopilot state machine |
| `spacesim/physics/kernels/burn.py` | `_burn_arc_numba` + `_profile_accel_numba` — RK4 over the burn arc with gravity plus constant-direction thrust |
| `spacesim/render/maneuver.py` | `ManeuverDrawMixin` — the planned line, node markers, gizmo handles; publishes `renderer.maneuver_node_hits` |
| `spacesim/ui/hud/maneuver.py` | `ManeuverBlock` (the panel) and `ManeuverGizmo` (the world-space drag widget) |
| `spacesim/tests/maneuver_profile_test.py` | the ramp maths and the Python↔njit twin bit-identity |
| `spacesim/tests/maneuver_plan_test.py` | plan container, basis, direction resolution |
| `spacesim/tests/maneuver_execute_test.py` | headless: preview vs. flown, abort, warp clamp |
| `spacesim/tests/maneuver_hud_test.py` | layout on screen, EXECUTE disabled at zero Δv, gizmo hit routing |
| `Werk/.claude/rules/maneuver.md` | the path-scoped note for the whole feature |

**Modify:**

| file | change |
|---|---|
| `spacesim/physics/kernels/__init__.py` | export the two burn kernels |
| `spacesim/render/renderer.py` | mix in `ManeuverDrawMixin`; init `maneuver_node_hits`, `maneuver_preview`, `maneuver_burn_direction`, `maneuver_drag_active`, `maneuver_curve_screen`; call the draw after `draw_prediction` |
| `spacesim/render/ship.py` | `orbital_frame_directions()` gains a `'node'` entry from `maneuver_burn_direction` |
| `spacesim/ship/control.py` | `NODE_SNAP_MODE = 'node'`; docstring note that the executor sets `snap_mode` directly |
| `spacesim/ui/theme.py` | two `ROLE_INDEX` entries: `'node': 2`, `'node_path': 3` |
| `spacesim/ui/hud/attitude.py` | `_MARKER_ORDER` gains `('node', 'NODE', 'node')` |
| `spacesim/ui/hud/telemetry.py` | maneuver sampling: selected node, Δv, burn duration, countdown, executor state, `marker_headings['node']` |
| `spacesim/ui/hud/controls.py` | `SnapRosette` tab reads `NODE` when `snap_mode == 'node'` |
| `spacesim/ui/hud/layout.py` | build and dock `ManeuverBlock` + `ManeuverGizmo`; responsive visibility |
| `spacesim/ui/hud/__init__.py` | correct the "es gibt keinen dauerschub" note; add `maneuver.py` to the module list |
| `spacesim/runtime/bootstrap.py` | build plan, preview, executor; hang them on `App` |
| `spacesim/runtime/loop.py` | maneuver step clamp, executor update, abort on manual input, preview refresh |
| `spacesim/runtime/input.py` | keys `N`, `Shift+N`, `X` |
| `spacesim/config/config.json` | new `"maneuver"` section |
| `spacesim/config/loader.py` | `maneuver_kwargs()` |
| `Werk/CLAUDE.md` | module-map row, controls table, one invariant, routing-table row |
| `Werk/.claude/rules/tests.md` | rows for the four new test files |
| `Werk/.claude/rules/hud-ui.md` | the maneuver block's placement note |

---

## Task 1: The burn profile

The load-bearing module. Preview and executor both call it, so a duration computed anywhere else is a bug.

**Files:**
- Create: `spacesim/ship/maneuver/__init__.py`
- Create: `spacesim/ship/maneuver/profile.py`
- Create: `spacesim/physics/kernels/burn.py` (the njit twin of `accel_at` only; the arc integrator lands in Task 3)
- Modify: `spacesim/physics/kernels/__init__.py`
- Test: `spacesim/tests/maneuver_profile_test.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BurnProfile(dv, a_max, ramp_seconds)` with float attributes `dv`, `a_max`, `ramp_rate`, `a_peak`, `ramp_time`, `hold_time`, `total_time`
  - `BurnProfile.accel_at(tau) -> float` — thrust acceleration `tau` seconds after ignition
  - `BurnProfile.throttle_at(tau) -> float` — `accel_at(tau) / a_max`, clamped to `[0, 1]`
  - `BurnProfile.dv_delivered(tau) -> float` — cumulative Δv from ignition to `tau`
  - `BurnProfile.dv_between(tau0, tau1) -> float` — closed-form Δv over one frame
  - `BurnProfile.lead_time -> float` — property, `total_time * 0.5`
  - `BurnProfile.ignition_time(t_node) -> float` — `t_node - lead_time`
  - `physics.kernels.burn._profile_accel_numba(tau, a_peak, ramp_time, hold_time, total_time, ramp_rate) -> float`

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_profile_test.py`:

```python
"""Das schubprofil eines manoeverknotens.

Drei ebenen:

1. **Die geschlossene form gegen von hand gerechnete werte.** Beide zweige
   (trapez und dreieck) mit sollwerten, die im test selbst hergeleitet sind.
2. **Die symmetrie**, die den zuendzeitpunkt traegt: bei total_time/2 ist
   genau die haelfte des delta-v geliefert. Ohne sie brennt der knoten
   einseitig und die vorschau zeigt eine andere bahn als geflogen wird.
3. **Der njit-zwilling gegen die Python-fassung.** _profile_accel_numba muss
   bitgleich zu BurnProfile.accel_at sein -- der kernel kann die methode
   nicht aufrufen, also gibt es sie zweimal, und genau deshalb wird die
   gleichheit geprueft.

Aufruf: python tests/maneuver_profile_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ship.maneuver.profile import BurnProfile
from physics.kernels.burn import _profile_accel_numba

FAILURES = []


def check(condition, name, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(name)


def close(a, b, rel=1e-9, abs_=1e-12):
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


print("\n1) trapez-zweig -- delta-v gross genug, dass a_max erreicht wird")
# a_max 600, ramp 0.5 -> rate 1200 m/s^3. Die spitze wird ab
# dv >= a_max*ramp = 300 m/s erreicht.
p = BurnProfile(1200.0, 600.0, 0.5)
check(close(p.ramp_rate, 1200.0), "rampenrate = a_max/ramp", f"{p.ramp_rate}")
check(close(p.a_peak, 600.0), "spitze = a_max", f"{p.a_peak}")
check(close(p.ramp_time, 0.5), "rampenzeit = ramp_seconds", f"{p.ramp_time}")
# hold = dv/a_max - ramp = 2.0 - 0.5 = 1.5
check(close(p.hold_time, 1.5), "haltezeit", f"{p.hold_time}")
# total = ramp + dv/a_max = 0.5 + 2.0 = 2.5
check(close(p.total_time, 2.5), "gesamtdauer = ramp + dv/a_max", f"{p.total_time}")

print("\n2) dreieck-zweig -- delta-v zu klein fuer die spitze")
q = BurnProfile(100.0, 600.0, 0.5)
# a_peak = sqrt(dv*r) = sqrt(100*1200) = 346.410...
check(close(q.a_peak, math.sqrt(100.0 * 1200.0)), "spitze = sqrt(dv*rate)",
      f"{q.a_peak:.6f}")
check(q.a_peak < 600.0, "spitze bleibt unter a_max", f"{q.a_peak:.3f}")
check(close(q.hold_time, 0.0), "keine haltephase", f"{q.hold_time}")
# total = 2*sqrt(dv/r) = 2*sqrt(100/1200) = 0.5773502...
check(close(q.total_time, 2.0 * math.sqrt(100.0 / 1200.0)),
      "gesamtdauer = 2*sqrt(dv/rate)", f"{q.total_time:.6f}")

print("\n3) die beiden zweige treffen sich stetig")
# Genau bei dv = a_max*ramp = 300 muessen beide dasselbe liefern.
lo = BurnProfile(299.999, 600.0, 0.5)
hi = BurnProfile(300.001, 600.0, 0.5)
check(abs(lo.total_time - hi.total_time) < 1e-5,
      "kein sprung in der dauer an der nahtstelle",
      f"{lo.total_time:.8f} vs {hi.total_time:.8f}")
check(abs(lo.a_peak - hi.a_peak) < 1e-2,
      "kein sprung in der spitze an der nahtstelle",
      f"{lo.a_peak:.6f} vs {hi.a_peak:.6f}")

print("\n4) das profil liefert GENAU das geplante delta-v")
for profile in (p, q, BurnProfile(0.75, 600.0, 0.5), BurnProfile(9000.0, 600.0, 0.5)):
    check(close(profile.dv_delivered(profile.total_time), profile.dv),
          f"dv_delivered(total) == dv  (dv={profile.dv})",
          f"{profile.dv_delivered(profile.total_time):.9f}")
    check(close(profile.dv_delivered(profile.total_time * 10.0), profile.dv),
          f"ueber das ende hinaus bleibt es stehen  (dv={profile.dv})", "")

print("\n5) SYMMETRIE -- bei total/2 ist die haelfte geliefert")
# Das ist die eigenschaft, aus der der zuendzeitpunkt folgt. Faellt sie,
# sitzt der knoten nicht mehr in der mitte des brennvorgangs.
for profile in (p, q, BurnProfile(3.0, 600.0, 0.5), BurnProfile(4321.0, 600.0, 0.5)):
    half = profile.dv_delivered(profile.total_time * 0.5)
    check(close(half, profile.dv * 0.5, rel=1e-9),
          f"halbes delta-v bei halber zeit  (dv={profile.dv})",
          f"{half:.9f} vs {profile.dv * 0.5:.9f}")
    check(close(profile.lead_time, profile.total_time * 0.5),
          f"lead_time == total/2  (dv={profile.dv})", "")
    check(close(profile.ignition_time(1000.0), 1000.0 - profile.total_time * 0.5),
          f"ignition_time zieht lead_time ab  (dv={profile.dv})", "")

print("\n6) dv_between ist bildratenunabhaengig")
# Eine feine und eine grobe zerlegung derselben brenndauer muessen dasselbe
# delta-v ergeben -- das ist der grund, warum der ausfuehrer die geschlossene
# form benutzt und nicht a*dt.
for steps in (7, 61, 1000):
    total = 0.0
    dt = p.total_time / steps
    for i in range(steps):
        total += p.dv_between(i * dt, (i + 1) * dt)
    check(close(total, p.dv, rel=1e-9),
          f"summe ueber {steps} schritte == dv", f"{total:.9f}")

print("\n7) randfaelle")
zero = BurnProfile(0.0, 600.0, 0.5)
check(close(zero.total_time, 0.0), "delta-v null -> dauer null", "")
check(close(zero.accel_at(0.0), 0.0) and close(zero.accel_at(5.0), 0.0),
      "delta-v null -> nie schub", "")
check(close(zero.dv_between(0.0, 10.0), 0.0), "delta-v null -> nie delta-v", "")
check(close(p.accel_at(-1.0), 0.0), "vor der zuendung kein schub", "")
check(close(p.accel_at(p.total_time + 1.0), 0.0), "nach dem ende kein schub", "")
peak = max(p.accel_at(p.total_time * i / 500.0) for i in range(501))
check(peak <= p.a_max + 1e-9, "schub ueberschreitet a_max nie", f"{peak:.6f}")
check(close(p.throttle_at(p.total_time * 0.5), 1.0),
      "voller hebel in der haltephase", f"{p.throttle_at(p.total_time*0.5):.6f}")

print("\n8) der njit-zwilling ist bitgleich zur Python-fassung")
# Der kernel kann BurnProfile.accel_at nicht aufrufen (numba nimmt keine
# Python-objekte), also steht dieselbe formel zweimal da. Genau deshalb
# wird sie hier verglichen -- ohne diese pruefung koennten vorschau und
# ausfuehrung unbemerkt auseinanderlaufen.
worst = 0.0
for profile in (p, q, BurnProfile(3.0, 600.0, 0.5), BurnProfile(9000.0, 600.0, 0.5)):
    span = profile.total_time * 1.2 + 0.1
    for i in range(501):
        tau = -0.05 + span * i / 500.0
        a_py = profile.accel_at(tau)
        a_nb = _profile_accel_numba(
            tau, profile.a_peak, profile.ramp_time, profile.hold_time,
            profile.total_time, profile.ramp_rate,
        )
        worst = max(worst, abs(a_py - a_nb))
check(worst == 0.0, "njit == Python an 2004 stuetzstellen, exakt",
      f"groesste abweichung {worst:g}")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    sys.exit(1)
print("ship/maneuver/profile: alle pruefungen bestanden")
```

- [ ] **Step 2: Run test to verify it fails**

Run from inside `spacesim/`: `python tests/maneuver_profile_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'ship.maneuver'`

- [ ] **Step 3: Write `ship/maneuver/profile.py`**

```python
"""Das schubprofil eines geplanten manoevers.

DIE EINE QUELLE fuer brenndauer, zuendzeitpunkt und geliefertes delta-v.
Vorschau (`ship/maneuver/preview.py`) und ausfuehrung
(`ship/maneuver/executor.py`) rufen dieselben funktionen auf. Stuende die
dauer an zwei stellen, zeigte die gezeichnete linie ein anderes manoever
als geflogen wird -- und zwar erst dann, wenn es zu spaet ist, es zu
bemerken.

KEIN IMPULS. Der schub faehrt mit fester RATE hoch, haelt, und faehrt mit
derselben rate wieder herunter:

    r = a_max / ramp_seconds        [m/s^3]

DIE RATE ist die erhaltene groesse, nicht die rampenZEIT. Bei einem kleinen
delta-v wird a_max nie erreicht; mit fester rampenzeit gaebe es dort einen
sprung in der dauer (das profil muesste ploetzlich ein dreieck sein, ohne
dass die formel es merkt). Mit fester rate gehen trapez und dreieck stetig
ineinander ueber -- siehe `tests/maneuver_profile_test.py` abschnitt 3.

    a
    |      ____________            a
    |     /            \\           |    /\\
    | a_p/              \\          |a_p/  \\
    +---+----------------+--- t    +--+----+--- t
      ramp   hold   ramp             r'   r'

BEIDE FORMEN SIND SYMMETRISCH, und daraus folgt der zuendzeitpunkt: bei
total_time/2 ist genau die haelfte des delta-v geliefert. Der knoten sitzt
also in der MITTE des brennvorgangs, halb davor, halb danach -- dieselbe
regel, die KSP benutzt, und die einzige, bei der eine endliche brenndauer
die geplante bahn trifft statt sie zu verfehlen.

Einheiten: a_max ist eine beschleunigung in SIMULATIONS-sekunden, nicht in
echtsekunden. Warum, steht in `.claude/rules/maneuver.md` (D2).
"""

import math


class BurnProfile:
    """Trapez- oder dreiecksprofil fuer ein gegebenes delta-v."""

    __slots__ = ('dv', 'a_max', 'ramp_rate', 'a_peak', 'ramp_time',
                 'hold_time', 'total_time')

    def __init__(self, dv, a_max, ramp_seconds):
        dv = abs(float(dv))
        a_max = max(1e-9, float(a_max))
        ramp_seconds = max(1e-9, float(ramp_seconds))
        rate = a_max / ramp_seconds

        self.dv = dv
        self.a_max = a_max
        self.ramp_rate = rate

        if dv <= 0.0:
            self.a_peak = 0.0
            self.ramp_time = 0.0
            self.hold_time = 0.0
            self.total_time = 0.0
            return

        # min() deckt beide zweige ab: unterhalb von dv = a_max*ramp liegt
        # sqrt(dv*rate) unter a_max und das profil wird ein dreieck.
        self.a_peak = min(a_max, math.sqrt(dv * rate))
        self.ramp_time = self.a_peak / rate
        self.hold_time = max(0.0, dv / self.a_peak - self.ramp_time)
        self.total_time = 2.0 * self.ramp_time + self.hold_time

    # ------------------------------------------------------------- ablesen

    @property
    def lead_time(self):
        """Zeit von der zuendung bis zum knoten -- die haelfte der dauer.

        Gilt, weil beide profilformen symmetrisch sind; geprueft in
        `tests/maneuver_profile_test.py` abschnitt 5.
        """
        return self.total_time * 0.5

    def ignition_time(self, t_node):
        """Absolute sim-zeit, zu der der schub einsetzen muss."""
        return float(t_node) - self.lead_time

    def accel_at(self, tau):
        """Schubbeschleunigung `tau` sekunden nach der zuendung.

        ACHTUNG: `physics/kernels/burn.py::_profile_accel_numba` ist der
        zwilling dieser funktion fuer den kernel (numba nimmt keine
        Python-objekte). Wer hier etwas aendert, aendert es DORT auch --
        abschnitt 8 des tests vergleicht beide exakt.
        """
        tau = float(tau)
        if tau <= 0.0 or tau >= self.total_time:
            return 0.0
        if tau < self.ramp_time:
            return self.ramp_rate * tau
        if tau < self.ramp_time + self.hold_time:
            return self.a_peak
        return self.ramp_rate * (self.total_time - tau)

    def throttle_at(self, tau):
        """Hebelstellung 0..1 -- was der schubbogen des HUDs anzeigt."""
        return max(0.0, min(1.0, self.accel_at(tau) / self.a_max))

    def dv_delivered(self, tau):
        """Aufsummiertes delta-v von der zuendung bis `tau`."""
        tau = float(tau)
        if tau <= 0.0:
            return 0.0
        if tau >= self.total_time:
            return self.dv
        if tau < self.ramp_time:
            return 0.5 * self.ramp_rate * tau * tau
        ramp_dv = 0.5 * self.a_peak * self.ramp_time
        if tau < self.ramp_time + self.hold_time:
            return ramp_dv + self.a_peak * (tau - self.ramp_time)
        rest = self.total_time - tau
        return self.dv - 0.5 * self.ramp_rate * rest * rest

    def dv_between(self, tau0, tau1):
        """Delta-v ueber ein zeitfenster, GESCHLOSSEN gerechnet.

        Der ausfuehrer benutzt das statt `accel_at(tau) * dt`: nur so ist
        das gelieferte delta-v unabhaengig von der bildrate und trifft am
        ende exakt den plan.
        """
        return self.dv_delivered(tau1) - self.dv_delivered(tau0)
```

- [ ] **Step 4: Write `ship/maneuver/__init__.py`**

```python
"""Manoeverknoten: planen, vorschau zeichnen, automatisch brennen.

    profile.py   das schubprofil -- DIE quelle fuer dauer und zuendzeitpunkt
    plan.py      knoten und plan (hoechstens fuenf), die orbitale basis
    preview.py   die kette coast -> burn -> coast als gezeichnete linie
    executor.py  der autopilot, der einen knoten wirklich fliegt

Die vollstaendigen begruendungen liegen in `.claude/rules/maneuver.md`.
"""

from .profile import BurnProfile

__all__ = ['BurnProfile']
```

(Later tasks extend this list; do not import `plan`/`preview`/`executor` here yet — they do not exist.)

- [ ] **Step 5: Write `physics/kernels/burn.py`**

```python
"""Der brennbogen: schwerkraft plus schub, als @njit-kern.

`_profile_accel_numba` ist der ZWILLING von
`ship/maneuver/profile.py::BurnProfile.accel_at`. Er steht hier ein zweites
mal, weil numba keine Python-objekte annimmt und die methode deshalb im
kernel nicht aufrufbar ist. Die doppelung ist bewusst und wird bewacht:
`tests/maneuver_profile_test.py` abschnitt 8 vergleicht beide an 2004
stuetzstellen auf EXAKTE gleichheit. Wer eine der beiden aendert, aendert
beide.

`_burn_arc_numba` kommt in Task 3 dazu.
"""

from numba import njit


@njit(cache=True, nogil=True, fastmath=True)
def _profile_accel_numba(tau, a_peak, ramp_time, hold_time, total_time, ramp_rate):
    if tau <= 0.0 or tau >= total_time:
        return 0.0
    if tau < ramp_time:
        return ramp_rate * tau
    if tau < ramp_time + hold_time:
        return a_peak
    return ramp_rate * (total_time - tau)
```

Note on `fastmath=True`: it matches every other kernel in `physics/kernels/`, and the test asserts exact equality against the Python twin — if `fastmath` ever reorders this arithmetic, section 8 fails and tells you.

- [ ] **Step 6: Export from `physics/kernels/__init__.py`**

Append at the end of the file, after the existing content:

```python
from .burn import _profile_accel_numba  # noqa: E402,F401
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python tests/maneuver_profile_test.py`
Expected: PASS — `ship/maneuver/profile: alle pruefungen bestanden`. The first run pays numba's compile cost (a few seconds); later runs hit the disk cache.

- [ ] **Step 8: Commit**

```bash
cd spacesim
git add ship/maneuver/__init__.py ship/maneuver/profile.py physics/kernels/burn.py physics/kernels/__init__.py tests/maneuver_profile_test.py
git commit -m "feat(maneuver): burn profile with a fixed ramp rate

Symmetric trapezoid/triangle profile; half the delta-v lands before
total_time/2, which is what gives the ignition lead. The njit twin of
accel_at is asserted bit-identical to the Python one.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 2: The plan container and the orbital basis

**Files:**
- Create: `spacesim/ship/maneuver/plan.py`
- Modify: `spacesim/ship/maneuver/__init__.py`
- Test: `spacesim/tests/maneuver_plan_test.py`

**Interfaces:**
- Consumes: `BurnProfile` from Task 1.
- Produces:
  - `MIN_EXECUTABLE_DV = 1e-3` (module constant, the default; config overrides per plan)
  - `orbital_basis(rel_px, rel_py, rel_vx, rel_vy) -> (px, py, nx, ny) | None` — unit prograde and unit inward-normal, world space
  - `burn_direction_world(basis, dv_prograde, dv_normal) -> (dx, dy, magnitude)` — unit direction and |Δv|; `(0.0, 0.0, 0.0)` when degenerate
  - `ManeuverNode(t_node, dv_prograde=0.0, dv_normal=0.0, reference_index=None)` with mutable attrs `t_node`, `dv_prograde`, `dv_normal`, `reference_index`, read-only `dv_total`, and `is_executable(min_dv=MIN_EXECUTABLE_DV) -> bool`
  - `ManeuverNode.profile(a_max, ramp_seconds) -> BurnProfile`
  - `ManeuverPlan(max_nodes=5, min_executable_dv=MIN_EXECUTABLE_DV)` with `nodes` (list, always sorted by `t_node`), `version` (int), `add(node) -> bool`, `remove(node) -> bool`, `remove_at(index) -> bool`, `clear()`, `first() -> ManeuverNode | None`, `touch()`, `is_full`, `__len__`, `__iter__`

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_plan_test.py`:

```python
"""Der manoeverplan: knoten, reihenfolge, und die orbitale basis.

Was hier geprueft wird, ist NICHT die physik der bahn, sondern die
buchhaltung darum herum -- und die eine geometrische festlegung, an der
rosette, ring-marker und ziehgriffe gemeinsam haengen: das VORZEICHEN von
normal. Laeuft es hier anders als in
reference_frames.apparent_orbital_directions(), zeigt der griff nach oben
und das schiff brennt nach unten.

Aufruf: python tests/maneuver_plan_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ship.maneuver.plan import (
    MIN_EXECUTABLE_DV,
    ManeuverNode,
    ManeuverPlan,
    burn_direction_world,
    orbital_basis,
)

FAILURES = []


def check(condition, name, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(name)


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol


print("\n1) die orbitale basis einer kreisbahn")
# Schiff bei (r, 0) relativ zum bezugskoerper, geschwindigkeit nach +y.
# Prograde ist dann (0, 1); normal zeigt NACH INNEN, also (-1, 0).
basis = orbital_basis(1.0e7, 0.0, 0.0, 7.5e3)
check(basis is not None, "basis existiert", "")
px, py, nx, ny = basis
check(close(px, 0.0, 1e-12) and close(py, 1.0, 1e-12),
      "prograde = einheitsvektor der relativgeschwindigkeit", f"({px:.6f}, {py:.6f})")
check(close(nx, -1.0, 1e-12) and close(ny, 0.0, 1e-12),
      "normal zeigt NACH INNEN (zum bezugskoerper)", f"({nx:.6f}, {ny:.6f})")
check(close(px * nx + py * ny, 0.0, 1e-12), "prograde steht senkrecht auf normal", "")
check(close(math.hypot(px, py), 1.0, 1e-12) and close(math.hypot(nx, ny), 1.0, 1e-12),
      "beide sind einheitsvektoren", "")

print("\n2) das vorzeichen von normal bleibt einwaerts, egal wo auf der bahn")
# Vier punkte rings herum, jeweils mit der kreisbahn-geschwindigkeit.
# normal . (-rel_pos) muss ueberall positiv sein -- das IST 'einwaerts'.
worst = 1.0
for k in range(16):
    ang = 2.0 * math.pi * k / 16.0
    rx, ry = 1.0e7 * math.cos(ang), 1.0e7 * math.sin(ang)
    vx, vy = -7.5e3 * math.sin(ang), 7.5e3 * math.cos(ang)
    b = orbital_basis(rx, ry, vx, vy)
    r = math.hypot(rx, ry)
    dot = b[2] * (-rx / r) + b[3] * (-ry / r)
    worst = min(worst, dot)
check(worst > 0.999, "normal . einwaerts > 0 an 16 punkten", f"kleinster wert {worst:.6f}")

print("\n3) entartete faelle")
check(orbital_basis(1.0e7, 0.0, 0.0, 0.0) is None,
      "geschwindigkeit null -> keine basis", "")
# Radial fliegend: es gibt keine 'innen'-richtung senkrecht zu v, die
# eindeutig waere -- die funktion muss trotzdem eine ORTHONORMALE basis
# liefern und darf nicht None werden, sonst laesst sich auf einer
# radialbahn kein knoten setzen.
b = orbital_basis(1.0e7, 0.0, 5.0e3, 0.0)
check(b is not None, "radial fliegend -> basis existiert trotzdem", "")
check(close(b[0] * b[2] + b[1] * b[3], 0.0, 1e-12),
      "und ist orthogonal", "")

print("\n4) die richtung aus (prograde, normal)")
basis = orbital_basis(1.0e7, 0.0, 0.0, 7.5e3)
dx, dy, mag = burn_direction_world(basis, 100.0, 0.0)
check(close(dx, 0.0, 1e-12) and close(dy, 1.0, 1e-12) and close(mag, 100.0, 1e-9),
      "reines prograde = die bahnrichtung", f"({dx:.6f}, {dy:.6f}) |{mag:.4f}|")
dx, dy, mag = burn_direction_world(basis, -100.0, 0.0)
check(close(dx, 0.0, 1e-12) and close(dy, -1.0, 1e-12) and close(mag, 100.0, 1e-9),
      "negatives prograde = retrograde", f"({dx:.6f}, {dy:.6f})")
dx, dy, mag = burn_direction_world(basis, 0.0, 100.0)
check(close(dx, -1.0, 1e-12) and close(dy, 0.0, 1e-12),
      "reines normal = einwaerts", f"({dx:.6f}, {dy:.6f})")
dx, dy, mag = burn_direction_world(basis, 0.0, -100.0)
check(close(dx, 1.0, 1e-12), "negatives normal = auswaerts", f"({dx:.6f}, {dy:.6f})")
dx, dy, mag = burn_direction_world(basis, 30.0, 40.0)
check(close(mag, 50.0, 1e-9), "betrag ist der pythagoras der beiden achsen",
      f"{mag:.6f}")
check(close(math.hypot(dx, dy), 1.0, 1e-12), "richtung ist ein einheitsvektor", "")
check(close(dx, -0.8, 1e-9) and close(dy, 0.6, 1e-9),
      "und mischt beide achsen richtig", f"({dx:.6f}, {dy:.6f})")
check(burn_direction_world(basis, 0.0, 0.0) == (0.0, 0.0, 0.0),
      "kein delta-v -> keine richtung", "")
check(burn_direction_world(None, 10.0, 0.0) == (0.0, 0.0, 0.0),
      "keine basis -> keine richtung", "")

print("\n5) der knoten")
n = ManeuverNode(1000.0)
check(close(n.dv_total, 0.0), "frischer knoten hat kein delta-v", "")
check(not n.is_executable(), "und ist damit NICHT ausfuehrbar", "")
n.dv_prograde = 3.0
n.dv_normal = 4.0
check(close(n.dv_total, 5.0, 1e-9), "delta-v ist der pythagoras", f"{n.dv_total}")
check(n.is_executable(), "mit delta-v ist er ausfuehrbar", "")
tiny = ManeuverNode(0.0, dv_prograde=MIN_EXECUTABLE_DV * 0.5)
check(not tiny.is_executable(),
      "unter der schwelle bleibt er gesperrt", f"{tiny.dv_total:g}")
prof = n.profile(10.0, 0.6)
check(close(prof.dv, 5.0, 1e-9), "profile() nimmt das delta-v des knotens", "")
check(prof.total_time > 0.0, "und liefert eine echte dauer", f"{prof.total_time:.4f}")

print("\n6) der plan haelt die knoten nach ZEIT sortiert")
# Weil EXECUTE immer den ersten nimmt, und 'der erste' heisst 'der
# zeitlich naechste' -- nicht 'der zuerst gesetzte'.
plan = ManeuverPlan(max_nodes=5)
for t in (300.0, 100.0, 200.0):
    plan.add(ManeuverNode(t, dv_prograde=1.0))
check([node.t_node for node in plan] == [100.0, 200.0, 300.0],
      "einfuegen sortiert", f"{[node.t_node for node in plan]}")
check(plan.first().t_node == 100.0, "first() ist der zeitlich naechste", "")

print("\n7) hoechstens fuenf knoten")
plan = ManeuverPlan(max_nodes=5)
added = [plan.add(ManeuverNode(float(i))) for i in range(7)]
check(added == [True] * 5 + [False, False], "der sechste wird abgelehnt", f"{added}")
check(len(plan) == 5, "es bleiben fuenf", f"{len(plan)}")
check(plan.is_full, "is_full meldet das", "")

print("\n8) die version zaehlt JEDE aenderung")
# Vorschau und renderer haengen daran: aendert sich die version nicht,
# wird die kette nicht neu gerechnet und die linie zeigt den alten plan.
plan = ManeuverPlan()
v0 = plan.version
plan.add(ManeuverNode(10.0))
check(plan.version > v0, "add zaehlt hoch", f"{v0} -> {plan.version}")
v1 = plan.version
plan.nodes[0].dv_prograde = 50.0
check(plan.version == v1, "eine direkte feldaenderung zaehlt NICHT von selbst", "")
plan.touch()
check(plan.version > v1, "touch() zaehlt sie nach", f"{v1} -> {plan.version}")
v2 = plan.version
plan.remove_at(0)
check(plan.version > v2, "remove zaehlt hoch", "")
v3 = plan.version
plan.add(ManeuverNode(1.0))
plan.clear()
check(plan.version > v3 and len(plan) == 0, "clear zaehlt hoch und leert", "")

print("\n9) touch() sortiert nach, wenn ein knoten verschoben wurde")
# Der ziehgriff verstellt t_node direkt; ohne nachsortieren waere 'der
# erste' danach der falsche.
plan = ManeuverPlan()
a = ManeuverNode(100.0, dv_prograde=1.0)
b = ManeuverNode(200.0, dv_prograde=1.0)
plan.add(a)
plan.add(b)
b.t_node = 50.0
plan.touch()
check(plan.first() is b, "der verschobene knoten ist jetzt der erste",
      f"{[node.t_node for node in plan]}")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    sys.exit(1)
print("ship/maneuver/plan: alle pruefungen bestanden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_plan_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'ship.maneuver.plan'`

- [ ] **Step 3: Write `ship/maneuver/plan.py`**

```python
"""Manoeverknoten und der plan, der sie haelt.

EIN KNOTEN SPEICHERT ZWEI ZAHLEN UND EINE ZEIT -- nicht mehr. Brenndauer,
zuendzeitpunkt und die weltrichtung des schubs sind ABGELEITET und werden
bei jedem lesen neu gerechnet (`profile()`, `burn_direction_world()`).
Gespeichert waeren sie genau so lange richtig, bis der spieler das delta-v
verstellt -- und der fehler faellt dann erst beim brennen auf.

DAS VORZEICHEN VON NORMAL IST FESTGELEGT UND WIRD NICHT NEU ERFUNDEN:
positiv heisst NACH INNEN, zum bezugskoerper. Dieselbe regel benutzt
`physics/reference_frames.py::apparent_orbital_directions` fuer
`normal_in`, und daran haengen die snap-rosette, die marker am kompassring
und die ziehgriffe an der linie. Waeren es zwei regeln, zeigte der griff
in die eine und das schiff bruennte in die andere richtung.

Die reihenfolge im plan ist die ZEITLICHE. `first()` ist der naechste
knoten, und genau den nimmt EXECUTE -- 'der erste' heisst nie 'der zuerst
gesetzte'.
"""

import math

from .profile import BurnProfile

#: Ab diesem betrag gilt ein knoten als ausfuehrbar. Darunter ist er ein
#: reiner PLATZHALTER -- man setzt ihn, um eine stelle der bahn zu
#: markieren, und entscheidet erst danach, was dort passieren soll. Der
#: EXECUTE-knopf ist so lange abgeblendet (siehe ui/hud/maneuver.py).
MIN_EXECUTABLE_DV = 1e-3

#: Voreinstellung fuer die plangroesse. Fuenf, weil ein transfer aus
#: abflug, korrektur und einfang besteht und zwei reserve genug sind; jeder
#: weitere knoten haengt an einer bahn, die schon eine integration mehr
#: tief ist (siehe .claude/rules/maneuver.md, D9).
MAX_NODES = 5


def orbital_basis(rel_px, rel_py, rel_vx, rel_vy):
    """Prograde und einwaerts-normal am ort des knotens, in WELTkoordinaten.

    `rel_*` sind position und geschwindigkeit RELATIV zum bezugskoerper.
    Zurueck kommt `(px, py, nx, ny)` -- zwei einheitsvektoren, orthogonal,
    `n` mit positivem anteil in richtung des bezugskoerpers. `None`, wenn
    die relativgeschwindigkeit verschwindet (dann gibt es kein prograde).

    Auf einer rein RADIALEN bahn steht `v` parallel zu `r`; 'einwaerts'
    laesst sich dann nicht mehr aus dem skalarprodukt entscheiden. Die
    funktion liefert trotzdem eine orthonormale basis (die erste
    kandidaten-senkrechte), statt None -- sonst liesse sich auf einer
    radialbahn ueberhaupt kein knoten setzen.
    """
    speed = math.hypot(float(rel_vx), float(rel_vy))
    if speed <= 1e-12:
        return None
    px = float(rel_vx) / speed
    py = float(rel_vy) / speed

    # Die beiden senkrechten. Welche 'einwaerts' ist, entscheidet das
    # skalarprodukt mit der richtung zum bezugskoerper (= -rel_pos).
    nx, ny = -py, px
    r = math.hypot(float(rel_px), float(rel_py))
    if r > 1e-12:
        ix = -float(rel_px) / r
        iy = -float(rel_py) / r
        if nx * ix + ny * iy < 0.0:
            nx, ny = py, -px
    return (px, py, nx, ny)


def burn_direction_world(basis, dv_prograde, dv_normal):
    """Weltrichtung und betrag des geplanten schubs.

    Zurueck kommt `(dx, dy, magnitude)` mit `(dx, dy)` als einheitsvektor.
    `(0.0, 0.0, 0.0)`, wenn keine basis vorliegt oder beide anteile null
    sind.
    """
    if basis is None:
        return (0.0, 0.0, 0.0)
    px, py, nx, ny = basis
    p = float(dv_prograde)
    n = float(dv_normal)
    dx = px * p + nx * n
    dy = py * p + ny * n
    magnitude = math.hypot(dx, dy)
    if magnitude <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (dx / magnitude, dy / magnitude, magnitude)


class ManeuverNode:
    """Ein geplanter impuls: wann, und wieviel prograde/normal."""

    __slots__ = ('t_node', 'dv_prograde', 'dv_normal', 'reference_index')

    def __init__(self, t_node, dv_prograde=0.0, dv_normal=0.0,
                 reference_index=None):
        #: Absolute sim-zeit des knotens -- die MITTE des brennvorgangs,
        #: nicht sein anfang (siehe BurnProfile.lead_time).
        self.t_node = float(t_node)
        self.dv_prograde = float(dv_prograde)
        self.dv_normal = float(dv_normal)
        #: Gegen welchen koerper prograde/normal gemeint sind. None heisst
        #: 'der gerade gewaehlte bezugskoerper'.
        self.reference_index = reference_index

    @property
    def dv_total(self):
        return math.hypot(self.dv_prograde, self.dv_normal)

    def is_executable(self, min_dv=MIN_EXECUTABLE_DV):
        return self.dv_total > float(min_dv)

    def profile(self, a_max, ramp_seconds):
        """Das schubprofil dieses knotens -- IMMER frisch gerechnet."""
        return BurnProfile(self.dv_total, a_max, ramp_seconds)

    def __repr__(self):
        return (f"ManeuverNode(t={self.t_node:.1f}, "
                f"pro={self.dv_prograde:+.1f}, nrm={self.dv_normal:+.1f})")


class ManeuverPlan:
    """Bis zu `max_nodes` knoten, nach zeit sortiert."""

    def __init__(self, max_nodes=MAX_NODES, min_executable_dv=MIN_EXECUTABLE_DV):
        self.max_nodes = max(1, int(max_nodes))
        self.min_executable_dv = float(min_executable_dv)
        self.nodes = []
        #: Zaehlt JEDE aenderung. Vorschau und renderer rechnen nur neu,
        #: wenn diese zahl sich bewegt hat -- eine kette aus fuenf
        #: integrationen je frame waere sonst der teuerste posten im bild.
        self.version = 0

    # ------------------------------------------------------------- abfragen

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        return iter(self.nodes)

    @property
    def is_full(self):
        return len(self.nodes) >= self.max_nodes

    def first(self):
        """Der zeitlich naechste knoten -- den fliegt EXECUTE."""
        return self.nodes[0] if self.nodes else None

    def index_of(self, node):
        for i, candidate in enumerate(self.nodes):
            if candidate is node:
                return i
        return None

    # ------------------------------------------------------------ aendern

    def _sort(self):
        self.nodes.sort(key=lambda node: node.t_node)

    def touch(self):
        """Nach einer direkten feldaenderung aufrufen.

        Sortiert nach (ein ziehgriff darf `t_node` verstellen) und zaehlt
        die version hoch. Ohne den aufruf bleibt die gezeichnete linie auf
        dem alten stand stehen.
        """
        self._sort()
        self.version += 1

    def add(self, node):
        if len(self.nodes) >= self.max_nodes:
            return False
        self.nodes.append(node)
        self.touch()
        return True

    def remove(self, node):
        index = self.index_of(node)
        if index is None:
            return False
        return self.remove_at(index)

    def remove_at(self, index):
        if not (0 <= int(index) < len(self.nodes)):
            return False
        self.nodes.pop(int(index))
        self.touch()
        return True

    def clear(self):
        if not self.nodes:
            return False
        self.nodes = []
        self.touch()
        return True
```

- [ ] **Step 4: Extend `ship/maneuver/__init__.py`**

Replace the import block and `__all__` with:

```python
from .plan import (
    MAX_NODES,
    MIN_EXECUTABLE_DV,
    ManeuverNode,
    ManeuverPlan,
    burn_direction_world,
    orbital_basis,
)
from .profile import BurnProfile

__all__ = [
    'MAX_NODES', 'MIN_EXECUTABLE_DV', 'BurnProfile', 'ManeuverNode',
    'ManeuverPlan', 'burn_direction_world', 'orbital_basis',
]
```

- [ ] **Step 5: Run both tests to verify they pass**

Run: `python tests/maneuver_plan_test.py` — Expected: PASS
Run: `python tests/maneuver_profile_test.py` — Expected: still PASS (the `__init__` change must not break it)

- [ ] **Step 6: Commit**

```bash
cd spacesim
git add ship/maneuver/plan.py ship/maneuver/__init__.py tests/maneuver_plan_test.py
git commit -m "feat(maneuver): node and plan container with the orbital basis

Nodes store only time and the two delta-v components; duration, ignition
and world direction are derived on every read. The plan keeps nodes sorted
by time, so first() is always the one EXECUTE flies.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 3: The burn-arc kernel

Split from the preview so the numerics get their own gate. This task adds only the kernel and its test.

**Files:**
- Modify: `spacesim/physics/kernels/burn.py`
- Modify: `spacesim/physics/kernels/__init__.py`
- Test: `spacesim/tests/maneuver_burn_kernel_test.py`

**Interfaces:**
- Consumes: `_profile_accel_numba` (Task 1); `physics.kernels.integrators._rkn_acc_time_numba`.
- Produces:

```
_burn_arc_numba(
    init_px, init_py, init_vx, init_vy, init_t,
    dir_x, dir_y,
    a_peak, ramp_time, hold_time, total_time, ramp_rate,
    ref_index, ref_px, ref_py,
    body_x, body_y, body_m, body_fixed,
    body_scripted, body_a, body_e, body_theta, body_arg, body_parent,
    G, use_time_dependent_bodies, body_memo,
    steps,
) -> (out, count)
```
  `out` is `(steps + 1, 5)` float64 with columns `x, y, t_local, vx, vy` — the same column layout as every other kernel in `physics/kernels/` (`POINT_COLUMNS`). `init_t` is LOCAL to the snapshot epoch, exactly like `_compute_distance_points_rkn_numba`'s `init_t`.

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_burn_kernel_test.py`:

```python
"""Der brennbogen-kernel: schwerkraft plus konstant gerichteter schub.

Die eine sache, die dieser kernel exakt treffen MUSS, ist das gelieferte
delta-v: die vorschau zeigt die bahn danach, und wenn der bogen 3 % zuviel
liefert, zeigt sie die falsche. Geprueft wird deshalb gegen zwei
unabhaengige referenzen:

1. **Ohne schwerkraft** (ein einziger, masseloser koerper): der bogen ist
   dann reine kinematik und das ergebnis steht analytisch fest --
   geschwindigkeitsaenderung = geplantes delta-v, exakt in schubrichtung.
2. **Mit schwerkraft, aber ohne schub**: der bogen muss dieselbe bahn
   liefern wie der bereits vorhandene RK4-kern
   `_compute_distance_points_numba_state`. Das ist die gegenprobe, ohne
   die punkt 1 auch bestuende, wenn die schwerkraft schlicht fehlte.

Aufruf: python tests/maneuver_burn_kernel_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import numpy as np

from physics.kernels.burn import _burn_arc_numba
from physics.kernels.propagate import _compute_distance_points_numba_state
from ship.maneuver.profile import BurnProfile

FAILURES = []


def check(condition, name, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(name)


G = 6.6730831e-11
EARTH_MASS = 5.97219e24
EARTH_MU = G * EARTH_MASS


def bodies(mass):
    """Ein einzelner, ruhender koerper im ursprung."""
    return (
        np.array([0.0], dtype=np.float64),      # x
        np.array([0.0], dtype=np.float64),      # y
        np.array([mass], dtype=np.float64),     # m
        np.array([1], dtype=np.int64),          # fixed
        np.array([0], dtype=np.int64),          # scripted
        np.zeros(1, dtype=np.float64),          # a
        np.zeros(1, dtype=np.float64),          # e
        np.zeros(1, dtype=np.float64),          # theta
        np.zeros(1, dtype=np.float64),          # arg
        np.array([-1], dtype=np.int64),         # parent
    )


NO_MEMO = np.zeros((0, 10), dtype=np.float64)


def run_burn(profile, dir_x, dir_y, px, py, vx, vy, mass, steps=400):
    bx, by, bm, bfix, bscr, ba, be, bth, barg, bpar = bodies(mass)
    return _burn_arc_numba(
        px, py, vx, vy, 0.0,
        dir_x, dir_y,
        profile.a_peak, profile.ramp_time, profile.hold_time,
        profile.total_time, profile.ramp_rate,
        -1, 0.0, 0.0,
        bx, by, bm, bfix, bscr, ba, be, bth, barg, bpar,
        G, 0, NO_MEMO,
        steps,
    )


print("\n1) ohne schwerkraft ist der bogen reine kinematik")
# masse 0 -> keine beschleunigung ausser dem schub. Die
# geschwindigkeitsaenderung muss dann GENAU das geplante delta-v sein,
# und genau in schubrichtung liegen.
prof = BurnProfile(120.0, 10.0, 0.6)
dir_x, dir_y = 0.6, 0.8      # einheitsvektor (3-4-5)
out, count = run_burn(prof, dir_x, dir_y, 1.0e7, 0.0, 0.0, 7.5e3, 0.0)
check(count >= 2, "der bogen liefert punkte", f"{count}")
dvx = float(out[count - 1, 3]) - 0.0
dvy = float(out[count - 1, 4]) - 7.5e3
delivered = math.hypot(dvx, dvy)
check(abs(delivered - prof.dv) <= 1e-6 * prof.dv,
      "geliefertes delta-v == geplantes", f"{delivered:.9f} vs {prof.dv}")
# Richtung: der einheitsvektor der aenderung muss die schubrichtung sein.
check(abs(dvx / delivered - dir_x) < 1e-9 and abs(dvy / delivered - dir_y) < 1e-9,
      "und liegt exakt in schubrichtung",
      f"({dvx/delivered:.9f}, {dvy/delivered:.9f})")
check(abs(float(out[count - 1, 2]) - prof.total_time) < 1e-9,
      "die letzte stuetzstelle liegt am brennende",
      f"{float(out[count-1, 2]):.9f} vs {prof.total_time:.9f}")

print("\n2) der schub baut sich WEICH auf, er springt nicht")
# Das ist der ganze punkt des profils. Die geschwindigkeitszunahme je
# schritt muss am anfang klein sein und erst zur haltephase hin ihren
# vollen wert erreichen.
speeds = [math.hypot(float(out[i, 3]), float(out[i, 4])) for i in range(count)]
steps_dv = [speeds[i + 1] - speeds[i] for i in range(count - 1)]
check(steps_dv[0] < steps_dv[len(steps_dv) // 2] * 0.2,
      "erster schritt liefert < 20 % eines mittleren",
      f"{steps_dv[0]:.6f} vs {steps_dv[len(steps_dv)//2]:.6f}")
check(steps_dv[-1] < steps_dv[len(steps_dv) // 2] * 0.2,
      "letzter schritt ebenso", f"{steps_dv[-1]:.6f}")
check(max(steps_dv) <= steps_dv[len(steps_dv) // 2] * 1.0001,
      "die haltephase ist das maximum, kein ueberschwinger", "")

print("\n3) HALBES delta-v bei halber brenndauer")
# Die eigenschaft, aus der der zuendzeitpunkt folgt -- hier am wirklich
# integrierten bogen nachgemessen, nicht nur an der formel.
mid = count // 2
v_mid = math.hypot(float(out[mid, 3]) - 0.0, float(out[mid, 4]) - 7.5e3)
check(abs(v_mid - prof.dv * 0.5) <= 1e-3 * prof.dv,
      "bei total/2 ist die haelfte geliefert",
      f"{v_mid:.6f} vs {prof.dv * 0.5:.6f}")

print("\n4) GEGENPROBE -- ohne schub muss der bogen die bahn des RK4-kerns treffen")
# Ohne diesen abschnitt wuerde abschnitt 1 auch dann bestehen, wenn die
# schwerkraft im kernel gar nicht ankaeme.
coast = BurnProfile(0.0, 10.0, 0.6)
coast.total_time = 600.0          # 10 minuten reines gleiten
bx, by, bm, bfix, bscr, ba, be, bth, barg, bpar = bodies(EARTH_MASS)
out_c, count_c = _burn_arc_numba(
    1.0e7, 0.0, 0.0, math.sqrt(EARTH_MU / 1.0e7), 0.0,
    1.0, 0.0,
    0.0, 0.0, 0.0, 600.0, 0.0,          # a_peak 0 -> kein schub
    -1, 0.0, 0.0,
    bx, by, bm, bfix, bscr, ba, be, bth, barg, bpar,
    G, 0, NO_MEMO,
    2000,
)
end_x, end_y = float(out_c[count_c - 1, 0]), float(out_c[count_c - 1, 1])
# Referenz: derselbe RK4, aber der vorhandene kern, mit demselben schritt.
ref_out, ref_used = _compute_distance_points_numba_state(
    1.0e7, 0.0, 0.0, math.sqrt(EARTH_MU / 1.0e7), 0.0,
    0, 0.0, 0.0, bx, by, bm, bfix, G,
    600.0 / 2000.0,          # dt gleich dem des brennbogens
    1.0,                     # precision: 1 m -> jeder schritt gibt punkte
    3000, 10000,
)
# Den referenzpunkt bei t = 600 s heraussuchen.
ref_x = ref_y = None
for i in range(ref_used):
    if float(ref_out[i, 2]) >= 600.0 - 1e-9:
        ref_x, ref_y = float(ref_out[i, 0]), float(ref_out[i, 1])
        break
check(ref_x is not None, "die referenz reicht bis 600 s", "")
if ref_x is not None:
    err = math.hypot(end_x - ref_x, end_y - ref_y)
    radius = math.hypot(end_x, end_y)
    check(err < 1.0e-6 * radius,
          "gleitbogen == RK4-referenz (relativ zum bahnradius)",
          f"{err:.6f} m auf r={radius:.3e} m")
    check(err > 0.0 or True, "", "")

print("\n5) der bogen bleibt auf einer plausiblen bahn")
r0 = 1.0e7
r_end = math.hypot(end_x, end_y)
check(abs(r_end - r0) < 1.0e-3 * r0,
      "kreisbahn bleibt kreisfoermig ueber 600 s",
      f"r {r0:.3e} -> {r_end:.3e}")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    sys.exit(1)
print("physics/kernels/burn: alle pruefungen bestanden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_burn_kernel_test.py`
Expected: FAIL with `ImportError: cannot import name '_burn_arc_numba'`

- [ ] **Step 3: Add `_burn_arc_numba` to `physics/kernels/burn.py`**

Add these imports at the top of the file, below the existing `from numba import njit`:

```python
import numpy as np

from .integrators import _rkn_acc_time_numba
```

Then append the kernel:

```python
@njit(cache=True, nogil=True, fastmath=True)
def _burn_arc_numba(
    init_px,
    init_py,
    init_vx,
    init_vy,
    init_t,
    dir_x,
    dir_y,
    a_peak,
    ramp_time,
    hold_time,
    total_time,
    ramp_rate,
    ref_index,
    ref_px,
    ref_py,
    body_x,
    body_y,
    body_m,
    body_fixed,
    body_scripted,
    body_a,
    body_e,
    body_theta,
    body_arg,
    body_parent,
    G,
    use_time_dependent_bodies,
    body_memo,
    steps,
):
    """RK4 ueber den brennbogen: schwerkraft plus konstant gerichteter schub.

    FESTE schrittweite, anders als die coast-kerne. Der bogen ist kurz und
    seine beschleunigung wechselt STETIG ueber die rampen -- eine adaptive
    steuerung haette hier nichts zu regeln und wuerde nur ihre eigene
    fehlerschaetzung bezahlen. Der aufrufer waehlt `steps` nach der dauer
    (siehe ship/maneuver/preview.py::_burn_steps).

    Die schubrichtung ist KONSTANT (in der welt festgehalten, siehe
    .claude/rules/maneuver.md, D3): sie wird beim scharfschalten einmal
    aufgeloest und aendert sich waehrend des brennens nicht mehr. Genau das
    macht vorschau und ausfuehrung identisch -- eine mitdrehende richtung
    kann die vorschau nicht im voraus kennen.

    `init_t` ist LOKAL zur schnappschuss-epoche, wie bei
    _compute_distance_points_rkn_numba. Spalten: x, y, t, vx, vy.

    `body_memo` wird mit NULL ZEILEN uebergeben. Der bogen ist ein paar
    hundert schritte lang, der notizblock haette also kaum wiederholungen
    zu sparen -- und den vorlauf, den _compute_distance_points_rkn_numba
    dafuer faehrt, hier zu wiederholen hiesse ihn zu verdoppeln.
    """
    n = steps if steps > 0 else 1
    out = np.empty((n + 1, 5), dtype=np.float64)

    px = init_px
    py = init_py
    vx = init_vx
    vy = init_vy
    t = init_t

    out[0, 0] = px
    out[0, 1] = py
    out[0, 2] = t
    out[0, 3] = vx
    out[0, 4] = vy

    if total_time <= 0.0:
        return out, 1

    h = total_time / n
    ref_enabled = 0

    for i in range(n):
        # tau = zeit SEIT DER ZUENDUNG; init_t ist der zuendzeitpunkt.
        tau = t - init_t

        # --- stufe 1
        gx, gy = _rkn_acc_time_numba(
            px, py, t, ref_enabled, ref_index, ref_px, ref_py,
            body_x, body_y, body_m, body_fixed, body_scripted,
            body_a, body_e, body_theta, body_arg, body_parent,
            G, use_time_dependent_bodies, body_memo,
        )
        th = _profile_accel_numba(tau, a_peak, ramp_time, hold_time,
                                  total_time, ramp_rate)
        k1ax = gx + dir_x * th
        k1ay = gy + dir_y * th
        k1vx = vx
        k1vy = vy

        # --- stufe 2
        p2x = px + k1vx * (h * 0.5)
        p2y = py + k1vy * (h * 0.5)
        v2x = vx + k1ax * (h * 0.5)
        v2y = vy + k1ay * (h * 0.5)
        gx, gy = _rkn_acc_time_numba(
            p2x, p2y, t + h * 0.5, ref_enabled, ref_index, ref_px, ref_py,
            body_x, body_y, body_m, body_fixed, body_scripted,
            body_a, body_e, body_theta, body_arg, body_parent,
            G, use_time_dependent_bodies, body_memo,
        )
        th = _profile_accel_numba(tau + h * 0.5, a_peak, ramp_time, hold_time,
                                  total_time, ramp_rate)
        k2ax = gx + dir_x * th
        k2ay = gy + dir_y * th
        k2vx = v2x
        k2vy = v2y

        # --- stufe 3
        p3x = px + k2vx * (h * 0.5)
        p3y = py + k2vy * (h * 0.5)
        v3x = vx + k2ax * (h * 0.5)
        v3y = vy + k2ay * (h * 0.5)
        gx, gy = _rkn_acc_time_numba(
            p3x, p3y, t + h * 0.5, ref_enabled, ref_index, ref_px, ref_py,
            body_x, body_y, body_m, body_fixed, body_scripted,
            body_a, body_e, body_theta, body_arg, body_parent,
            G, use_time_dependent_bodies, body_memo,
        )
        th = _profile_accel_numba(tau + h * 0.5, a_peak, ramp_time, hold_time,
                                  total_time, ramp_rate)
        k3ax = gx + dir_x * th
        k3ay = gy + dir_y * th
        k3vx = v3x
        k3vy = v3y

        # --- stufe 4
        p4x = px + k3vx * h
        p4y = py + k3vy * h
        v4x = vx + k3ax * h
        v4y = vy + k3ay * h
        gx, gy = _rkn_acc_time_numba(
            p4x, p4y, t + h, ref_enabled, ref_index, ref_px, ref_py,
            body_x, body_y, body_m, body_fixed, body_scripted,
            body_a, body_e, body_theta, body_arg, body_parent,
            G, use_time_dependent_bodies, body_memo,
        )
        th = _profile_accel_numba(tau + h, a_peak, ramp_time, hold_time,
                                  total_time, ramp_rate)
        k4ax = gx + dir_x * th
        k4ay = gy + dir_y * th
        k4vx = v4x
        k4vy = v4y

        px = px + (k1vx + 2.0 * k2vx + 2.0 * k3vx + k4vx) * (h / 6.0)
        py = py + (k1vy + 2.0 * k2vy + 2.0 * k3vy + k4vy) * (h / 6.0)
        vx = vx + (k1ax + 2.0 * k2ax + 2.0 * k3ax + k4ax) * (h / 6.0)
        vy = vy + (k1ay + 2.0 * k2ay + 2.0 * k3ay + k4ay) * (h / 6.0)
        t = init_t + (i + 1) * h

        out[i + 1, 0] = px
        out[i + 1, 1] = py
        out[i + 1, 2] = t
        out[i + 1, 3] = vx
        out[i + 1, 4] = vy

    return out, n + 1
```

- [ ] **Step 4: Export it**

In `physics/kernels/__init__.py`, change the line added in Task 1 to:

```python
from .burn import _burn_arc_numba, _profile_accel_numba  # noqa: E402,F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python tests/maneuver_burn_kernel_test.py`
Expected: PASS. First run compiles the kernel (~10–20 s); afterwards the numba disk cache makes it fast.

If section 1 fails by a *relative* amount around `1/steps`, the RK4 stages are wired wrong — check that stage 2 and 3 evaluate the profile at `tau + h/2` and stage 4 at `tau + h`, not all at `tau`.

- [ ] **Step 6: Commit**

```bash
cd spacesim
git add physics/kernels/burn.py physics/kernels/__init__.py tests/maneuver_burn_kernel_test.py
git commit -m "feat(maneuver): RK4 burn-arc kernel with a ramped, fixed-direction thrust

Fixed step over a short arc; the delivered delta-v matches the plan to
1e-6 relative, and the coast case reproduces the existing RK4 kernel.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 4: The preview — the drawn consequence of the plan

**Files:**
- Create: `spacesim/ship/maneuver/preview.py`
- Modify: `spacesim/ship/predictor/compute.py` (add one public seam)
- Modify: `spacesim/ship/maneuver/__init__.py`
- Test: `spacesim/tests/maneuver_preview_test.py`

**Interfaces:**
- Consumes: `BurnProfile`, `ManeuverPlan`, `ManeuverNode`, `orbital_basis`, `burn_direction_world` (Tasks 1–2); `_burn_arc_numba` (Task 3); `physics.kernels.propagate._compute_distance_points_rkn_numba`.
- Produces:
  - `Predictor.make_maneuver_snapshot(ship, world, max_points) -> dict` — public wrapper over `_make_snapshot`
  - `state_on_curve(points, t_abs) -> (px, py, vx, vy) | None` — cubic-Hermite sample of a `(n,5)` curve
  - `body_state_at(body, t_abs) -> (px, py, vx, vy)`
  - `ManeuverPreview(max_points=1200, burn_step_s=0.25, burn_min_steps=16, burn_max_steps=512, min_interval_s=0.15)`
  - attributes `points` (`(n,5)` float64, absolute time, or `None`), `node_markers` (list of dicts), `valid` (bool), `last_rebuild_ms` (float)
  - `ManeuverPreview.rebuild(plan, ship, world, predictor, reference_body, a_max, ramp_seconds) -> bool`
  - `ManeuverPreview.maybe_rebuild(plan, ship, world, predictor, reference_body, a_max, ramp_seconds, now_wall) -> bool`
  - `ManeuverPreview.invalidate()`
  - each entry of `node_markers` is `{'index': int, 'node': ManeuverNode, 't_node': float, 'x': float, 'y': float, 'dir_x': float, 'dir_y': float, 'pro_x': float, 'pro_y': float, 'nrm_x': float, 'nrm_y': float, 'dv': float, 'profile': BurnProfile}` — `pro_*`/`nrm_*` are the world-space basis vectors the gizmo handles point along

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_preview_test.py`:

```python
"""Die manoever-vorschau: was die geplanten knoten aus der bahn machen.

Die integration selbst ist in `maneuver_burn_kernel_test.py` geprueft. Hier
geht es um die KETTE darum herum, und die hat genau drei stellen, an denen
sie falsch sein kann:

1. Ein knoten OHNE delta-v darf die bahn nicht veraendern -- tut er es,
   stimmt der zustand nicht, den die kette an der knotenzeit abliest.
2. Die VORZEICHEN muessen stimmen: prograde hebt das apoapsis, retrograde
   senkt es. Das ist die pruefung, die einen vertauschten basisvektor
   findet.
3. Der ZWEITE knoten muss auf dem ergebnis des ersten sitzen, nicht auf der
   ursprungsbahn. Ohne diese pruefung waere die kette gar keine.

Aufruf: python tests/maneuver_preview_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import numpy as np

from config.loader import ConfigLoader
from physics.world import world as World
from runtime.system_loader import SystemLoader
from ship.maneuver.plan import ManeuverNode, ManeuverPlan
from ship.maneuver.preview import ManeuverPreview, state_on_curve
from ship.predictor import Predictor

FAILURES = []


def check(condition, name, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(name)


def build():
    """Welt + schiff auf einer kreisbahn um die Erde + predictor."""
    config = ConfigLoader()
    bodies = SystemLoader(
        config.get('simulation.system_file', 'solar_system.json')).load()
    w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
    w.body = bodies
    config.apply_to_world(w)
    w.update_planets(0.0)

    erde = next(b for b in w.body if b.name.lower().startswith('erde'))
    ship = next(b for b in w.body if getattr(b, 'is_ship', False))

    mu = w.G * erde.mass
    r = float(getattr(erde, 'radius', 6.371e6)) + 4.0e6
    ahead = erde.position_at_time(1.0)
    behind = erde.position_at_time(-1.0)
    evx = (float(ahead.x) - float(behind.x)) / 2.0
    evy = (float(ahead.y) - float(behind.y)) / 2.0
    ship.position.x = erde.position.x + r
    ship.position.y = erde.position.y
    ship.velocity.x = evx
    ship.velocity.y = evy + math.sqrt(mu / r)

    predictor = Predictor(**config.predictor_kwargs())
    config.apply_to_predictor(predictor)
    predictor.async_compute = False
    predictor.initialize(ship, w)
    predictor.update(ship, w)
    return w, erde, ship, predictor


def radius_range(points, erde, w):
    """Kleinster und groesster abstand der linie zur Erde."""
    lo, hi = None, None
    for i in range(len(points)):
        t = float(points[i, 2])
        ep = erde.position_at_time(t)
        d = math.hypot(float(points[i, 0]) - float(ep.x),
                       float(points[i, 1]) - float(ep.y))
        lo = d if lo is None else min(lo, d)
        hi = d if hi is None else max(hi, d)
    return lo, hi


print("\n0) aufbau")
w, erde, ship, predictor = build()
base = predictor.get_points()
check(base is not None and len(base) > 100,
      "der predictor liefert eine grundlinie", f"{0 if base is None else len(base)} punkte")
t0 = float(base[0, 2])
t_end = float(base[len(base) - 1, 2])
t_node = t0 + (t_end - t0) * 0.35
print(f"      horizont {t0:.1f} .. {t_end:.1f} s, knoten bei {t_node:.1f} s")

print("\n1) state_on_curve trifft die stuetzstellen exakt")
i = len(base) // 3
st = state_on_curve(base, float(base[i, 2]))
check(st is not None, "eine stuetzstelle laesst sich lesen", "")
err = math.hypot(st[0] - float(base[i, 0]), st[1] - float(base[i, 1]))
check(err < 1e-6, "auf der stuetzstelle == die stuetzstelle", f"{err:.3e} m")
check(state_on_curve(base, t0 - 1000.0) is None, "vor der linie -> None", "")
check(state_on_curve(base, t_end + 1000.0) is None, "hinter der linie -> None", "")

print("\n2) ein knoten OHNE delta-v laesst die bahn stehen")
plan = ManeuverPlan()
plan.add(ManeuverNode(t_node))
preview = ManeuverPreview(max_points=1200)
ok = preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
check(ok and preview.points is not None, "die vorschau baut", "")
worst = 0.0
for i in range(0, len(preview.points), 7):
    t = float(preview.points[i, 2])
    ref = state_on_curve(base, t)
    if ref is None:
        continue
    d = math.hypot(float(preview.points[i, 0]) - ref[0],
                   float(preview.points[i, 1]) - ref[1])
    worst = max(worst, d)
r_lo, r_hi = radius_range(base, erde, w)
check(worst < 1e-4 * r_hi,
      "die vorschau deckt sich mit der grundlinie",
      f"groesste abweichung {worst:.1f} m auf r~{r_hi:.3e} m")

print("\n3) VORZEICHEN -- prograde hebt, retrograde senkt")
base_lo, base_hi = radius_range(base, erde, w)

plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_prograde=+400.0))
preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
pro_lo, pro_hi = radius_range(preview.points, erde, w)
check(pro_hi > base_hi * 1.02,
      "prograde hebt das apoapsis",
      f"{base_hi:.4e} -> {pro_hi:.4e}")

plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_prograde=-400.0))
preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
ret_lo, ret_hi = radius_range(preview.points, erde, w)
check(ret_lo < base_lo * 0.98,
      "retrograde senkt das periapsis",
      f"{base_lo:.4e} -> {ret_lo:.4e}")

print("\n4) normal wirkt SENKRECHT -- es aendert die bahn, aber anders")
plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_normal=+400.0))
preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
nrm_lo, nrm_hi = radius_range(preview.points, erde, w)
# Ein rein einwaerts gerichteter impuls auf einer kreisbahn senkt das
# periapsis UND hebt das apoapsis -- er kippt die bahn, statt sie nur zu
# vergroessern. Prograde tut das nicht.
check(nrm_lo < base_lo * 0.98 and nrm_hi > base_hi * 1.005,
      "normal kippt die bahn (beide apsiden wandern)",
      f"lo {base_lo:.3e}->{nrm_lo:.3e}, hi {base_hi:.3e}->{nrm_hi:.3e}")

print("\n5) der knotenmarker sitzt auf der bahn")
plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_prograde=250.0))
preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
check(len(preview.node_markers) == 1, "ein marker je knoten", "")
m = preview.node_markers[0]
ref = state_on_curve(base, m['t_node'])
d = math.hypot(m['x'] - ref[0], m['y'] - ref[1])
check(d < 1e-3 * base_hi, "der marker liegt auf der grundlinie",
      f"{d:.1f} m")
check(abs(math.hypot(m['dir_x'], m['dir_y']) - 1.0) < 1e-9,
      "die schubrichtung ist ein einheitsvektor", "")
check(abs(m['dv'] - 250.0) < 1e-9, "der betrag ist das delta-v", f"{m['dv']}")
check(abs(m['pro_x'] * m['nrm_x'] + m['pro_y'] * m['nrm_y']) < 1e-9,
      "prograde und normal stehen senkrecht aufeinander", "")

print("\n6) KETTE -- der zweite knoten sitzt auf dem ergebnis des ersten")
t_node2 = t_node + (t_end - t_node) * 0.4
plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_prograde=400.0))
plan.add(ManeuverNode(t_node2, dv_prograde=100.0))
preview.rebuild(plan, ship, w, predictor, erde, a_max=10.0, ramp_seconds=0.6)
check(len(preview.node_markers) == 2, "zwei marker", f"{len(preview.node_markers)}")
m2 = preview.node_markers[1]
on_base = state_on_curve(base, m2['t_node'])
dist_to_base = (math.hypot(m2['x'] - on_base[0], m2['y'] - on_base[1])
                if on_base is not None else float('inf'))
check(dist_to_base > 1e-2 * base_hi,
      "der zweite marker liegt NICHT mehr auf der ursprungsbahn",
      f"{dist_to_base:.3e} m entfernt")

print("\n7) die linie ist zeitlich monoton und endlich")
times = preview.points[:, 2]
check(bool(np.all(np.isfinite(preview.points))), "keine NaN/inf in der linie", "")
check(bool(np.all(np.diff(times) >= -1e-9)), "die zeit laeuft nur vorwaerts", "")
check(len(preview.points) <= 1200, "das punktbudget wird eingehalten",
      f"{len(preview.points)}")

print("\n8) maybe_rebuild rechnet NICHT ohne aenderung")
# Eine kette aus fuenf integrationen je frame waere der teuerste posten im
# bild. Sie darf nur laufen, wenn plan oder grundbahn sich bewegt haben.
before = preview.last_rebuild_ms
did = preview.maybe_rebuild(plan, ship, w, predictor, erde, 10.0, 0.6, now_wall=1000.0)
check(did is False, "unveraendert -> kein neuaufbau", "")
plan.nodes[0].dv_prograde = 401.0
plan.touch()
did = preview.maybe_rebuild(plan, ship, w, predictor, erde, 10.0, 0.6, now_wall=1000.5)
check(did is True, "nach touch() -> neuaufbau", "")
did = preview.maybe_rebuild(plan, ship, w, predictor, erde, 10.0, 0.6, now_wall=1000.6)
check(did is False, "und danach wieder nicht", "")

print("\n9) ein leerer plan liefert keine linie")
preview.rebuild(ManeuverPlan(), ship, w, predictor, erde, 10.0, 0.6)
check(preview.points is None and not preview.valid,
      "kein knoten -> nichts zu zeichnen", "")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    sys.exit(1)
print("ship/maneuver/preview: alle pruefungen bestanden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_preview_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'ship.maneuver.preview'`

- [ ] **Step 3: Add the public seam on the Predictor**

In `spacesim/ship/predictor/compute.py`, directly **above** `def _make_snapshot(self, ship, world, max_points):`, insert:

```python
    def make_maneuver_snapshot(self, ship, world, max_points):
        """Ein schnappschuss fuer die manoever-vorschau.

        Die vorschau (ship/maneuver/preview.py) rechnet mit DENSELBEN
        koerper-arrays und derselben epoche wie die vorhersagelinie, gegen
        die sie ihre knoten setzt -- mit einem eigenen serialisierer waeren
        es zwei leicht verschiedene sonnensysteme und die kette saesse
        neben der linie. Ein oeffentlicher name dafuer, damit die kopplung
        greppbar ist und nicht als privatzugriff versteckt.
        """
        return self._make_snapshot(ship, world, int(max_points))
```

- [ ] **Step 4: Write `ship/maneuver/preview.py`**

```python
"""Die gezeichnete folge des plans: coast -> burn -> coast -> ...

WIE DIE KETTE LAEUFT. Fuer jeden knoten der reihe nach:

    1. den ZUSTAND zur zuendzeit von der bisherigen linie ablesen
       (kubische Hermite-auswertung, `state_on_curve`) -- fuer den ersten
       knoten ist das die vorhersagelinie des predictors, fuer jeden
       weiteren das ergebnis des vorigen knotens. GENAU DAS macht sie zu
       einer kette.
    2. den BRENNBOGEN integrieren (`_burn_arc_numba`)
    3. von dort weiter GLEITEN (`_compute_distance_points_rkn_numba`), bis
       zum naechsten knoten oder bis das punktbudget aufgebraucht ist

Es wird NICHTS neu propagiert, was der predictor schon gerechnet hat: der
abschnitt vor dem ersten knoten ist die vorhandene linie und wird nur
gelesen. Ein knoten jenseits des gezeichneten horizonts hat keinen
ablesbaren zustand -- die kette bricht dort ab, statt zu raten.

KOSTEN. Ein neuaufbau ist eine kette aus bis zu fuenf integrationen. Er
laeuft deshalb NUR, wenn der plan (`plan.version`) oder die grundbahn
(`predictor._trajectory_version`) sich bewegt hat, und hoechstens alle
`min_interval_s` sekunden. Je frame zu rechnen waere der teuerste posten
im bild.

Zeitrechnung: die kernel rechnen LOKAL zur schnappschuss-epoche
(`snapshot["sim_time"]`), die punktelisten hier aussen tragen ABSOLUTE
sim-zeit in spalte 2 -- dieselbe konvention wie `ship/predictor/`.
"""

import math
import time

import numpy as np

from physics.kernels.burn import _burn_arc_numba
from physics.kernels.propagate import _compute_distance_points_rkn_numba

from .plan import burn_direction_world, orbital_basis
from .profile import BurnProfile


def state_on_curve(points, t_abs):
    """Zustand `(x, y, vx, vy)` auf einer `(n,5)`-linie zur absoluten zeit.

    Kubische Hermite zwischen den beiden umgebenden stuetzstellen -- die
    linie IST eine stueckweise kubische kurve, ihre spalten 3/4 sind die
    tangenten (siehe physics/kernels/__init__.py, POINT_COLUMNS). Wo diese
    spalten NaN tragen (sehnen-kernel), faellt die auswertung auf linear
    zurueck; das ist kein fehlerfall, sondern die wahrheit ueber solche
    punkte.

    `None`, wenn `t_abs` ausserhalb der linie liegt.
    """
    if points is None:
        return None
    try:
        n = len(points)
    except Exception:
        return None
    if n < 2:
        return None

    t = float(t_abs)
    times = points[:, 2]
    if t < float(times[0]) or t > float(times[n - 1]):
        return None

    # searchsorted statt einer schleife: die linie hat bis zu 40 000 punkte
    # und die vorschau liest sie mehrmals je neuaufbau.
    i = int(np.searchsorted(times, t, side='right')) - 1
    i = max(0, min(i, n - 2))

    t0 = float(times[i])
    t1 = float(times[i + 1])
    dt = t1 - t0
    if dt <= 0.0:
        return (float(points[i, 0]), float(points[i, 1]),
                float(points[i, 3]), float(points[i, 4]))

    s = (t - t0) / dt
    p0x, p0y = float(points[i, 0]), float(points[i, 1])
    p1x, p1y = float(points[i + 1, 0]), float(points[i + 1, 1])
    v0x, v0y = float(points[i, 3]), float(points[i, 4])
    v1x, v1y = float(points[i + 1, 3]), float(points[i + 1, 4])

    if not (math.isfinite(v0x) and math.isfinite(v0y)
            and math.isfinite(v1x) and math.isfinite(v1y)):
        # Sehnenpunkt: geradlinig interpolieren, geschwindigkeit aus der
        # sehne. Eine kruemmung zu erfinden waere schlimmer als keine.
        return (p0x + (p1x - p0x) * s, p0y + (p1y - p0y) * s,
                (p1x - p0x) / dt, (p1y - p0y) / dt)

    s2 = s * s
    s3 = s2 * s
    h00 = 2.0 * s3 - 3.0 * s2 + 1.0
    h10 = s3 - 2.0 * s2 + s
    h01 = -2.0 * s3 + 3.0 * s2
    h11 = s3 - s2
    px = h00 * p0x + h10 * dt * v0x + h01 * p1x + h11 * dt * v1x
    py = h00 * p0y + h10 * dt * v0y + h01 * p1y + h11 * dt * v1y

    d00 = 6.0 * s2 - 6.0 * s
    d10 = 3.0 * s2 - 4.0 * s + 1.0
    d01 = -6.0 * s2 + 6.0 * s
    d11 = 3.0 * s2 - 2.0 * s
    vx = (d00 * p0x + d01 * p1x) / dt + d10 * v0x + d11 * v1x
    vy = (d00 * p0y + d01 * p1y) / dt + d10 * v0y + d11 * v1y
    return (px, py, vx, vy)


def body_state_at(body, t_abs, h=1.0):
    """Position und geschwindigkeit eines koerpers zur absoluten zeit.

    Die geschwindigkeit kommt als ZENTRALE DIFFERENZ aus
    `position_at_time()`, nie aus `body.velocity`: skriptgefuehrte koerper
    behalten dort ihren ladewert 0, und die orbitale basis waere dann gegen
    einen stillstehenden planeten gerechnet. Dieselbe falle steht in
    `ui/hud/telemetry.py::body_velocity`.
    """
    if body is None:
        return (0.0, 0.0, 0.0, 0.0)
    try:
        here = body.position_at_time(float(t_abs))
        px, py = float(here.x), float(here.y)
    except Exception:
        try:
            px, py = float(body.position.x), float(body.position.y)
        except Exception:
            return (0.0, 0.0, 0.0, 0.0)
    if not getattr(body, 'scripted_orbit', False):
        try:
            return (px, py, float(body.velocity.x), float(body.velocity.y))
        except Exception:
            return (px, py, 0.0, 0.0)
    try:
        ahead = body.position_at_time(float(t_abs) + h)
        behind = body.position_at_time(float(t_abs) - h)
        return (px, py,
                (float(ahead.x) - float(behind.x)) / (2.0 * h),
                (float(ahead.y) - float(behind.y)) / (2.0 * h))
    except Exception:
        return (px, py, 0.0, 0.0)


class ManeuverPreview:
    """Die kette, ihre marker, und der riegel gegen zu haeufiges rechnen."""

    def __init__(self, max_points=1200, burn_step_s=0.25, burn_min_steps=16,
                 burn_max_steps=512, min_interval_s=0.15):
        self.max_points = max(64, int(max_points))
        self.burn_step_s = max(1e-3, float(burn_step_s))
        self.burn_min_steps = max(4, int(burn_min_steps))
        self.burn_max_steps = max(self.burn_min_steps, int(burn_max_steps))
        self.min_interval_s = max(0.0, float(min_interval_s))

        self.points = None
        self.node_markers = []
        self.valid = False
        self.last_rebuild_ms = 0.0

        self._plan_version = None
        self._trajectory_version = None
        self._last_wall = -1e18

    # ---------------------------------------------------------------- riegel

    def invalidate(self):
        self._plan_version = None
        self._trajectory_version = None

    def maybe_rebuild(self, plan, ship, world, predictor, reference_body,
                      a_max, ramp_seconds, now_wall=None):
        """Nur rechnen, wenn sich etwas bewegt hat. Liefert True, wenn gerechnet."""
        if now_wall is None:
            now_wall = time.perf_counter()
        plan_version = int(getattr(plan, 'version', 0)) if plan is not None else -1
        traj_version = int(getattr(predictor, '_trajectory_version', 0))
        if (plan_version == self._plan_version
                and traj_version == self._trajectory_version):
            return False
        if (float(now_wall) - self._last_wall) < self.min_interval_s:
            return False
        self._last_wall = float(now_wall)
        self._plan_version = plan_version
        self._trajectory_version = traj_version
        self.rebuild(plan, ship, world, predictor, reference_body,
                     a_max, ramp_seconds)
        return True

    # ----------------------------------------------------------- neuaufbau

    def _burn_steps(self, total_time):
        steps = int(math.ceil(float(total_time) / self.burn_step_s))
        return max(self.burn_min_steps, min(self.burn_max_steps, steps))

    def rebuild(self, plan, ship, world, predictor, reference_body,
                a_max, ramp_seconds):
        t_start = time.perf_counter()
        self.points = None
        self.node_markers = []
        self.valid = False

        try:
            ok = self._rebuild_impl(plan, ship, world, predictor,
                                    reference_body, a_max, ramp_seconds)
        except Exception:
            ok = False
        self.last_rebuild_ms = (time.perf_counter() - t_start) * 1000.0
        return ok

    def _rebuild_impl(self, plan, ship, world, predictor, reference_body,
                      a_max, ramp_seconds):
        if plan is None or len(plan) == 0 or ship is None or predictor is None:
            return False
        base = predictor.get_points()
        if base is None or len(base) < 2:
            return False

        snapshot = predictor.make_maneuver_snapshot(ship, world, self.max_points)
        epoch = float(snapshot.get('sim_time', 0.0))
        ref_index = int(snapshot.get('reference_body_index', -1))
        no_memo = np.zeros((0, 10), dtype=np.float64)
        use_time = 1 if snapshot.get('use_time_dependent_bodies', True) else 0

        segments = []
        markers = []
        source = base
        budget = self.max_points

        for index, node in enumerate(plan.nodes):
            if budget <= 8:
                break

            # -- 1. zustand an der knotenzeit, von der bisherigen linie
            at_node = state_on_curve(source, node.t_node)
            if at_node is None:
                # Der knoten liegt jenseits dessen, was gezeichnet ist.
                # Raten waere schlimmer als abbrechen.
                break

            rpx, rpy, rvx, rvy = body_state_at(reference_body, node.t_node)
            basis = orbital_basis(at_node[0] - rpx, at_node[1] - rpy,
                                  at_node[2] - rvx, at_node[3] - rvy)
            dir_x, dir_y, dv = burn_direction_world(
                basis, node.dv_prograde, node.dv_normal)
            profile = BurnProfile(dv, a_max, ramp_seconds)

            markers.append({
                'index': index,
                'node': node,
                't_node': float(node.t_node),
                'x': at_node[0], 'y': at_node[1],
                'dir_x': dir_x, 'dir_y': dir_y,
                'pro_x': basis[0] if basis else 0.0,
                'pro_y': basis[1] if basis else 0.0,
                'nrm_x': basis[2] if basis else 0.0,
                'nrm_y': basis[3] if basis else 0.0,
                'dv': dv,
                'profile': profile,
            })

            if profile.total_time <= 0.0:
                # Platzhalter-knoten: er markiert eine stelle, veraendert
                # aber nichts. Die kette laeuft auf derselben linie weiter.
                continue

            # -- 2. der brennbogen, ab der zuendung
            t_ign = profile.ignition_time(node.t_node)
            at_ign = state_on_curve(source, t_ign)
            if at_ign is None:
                break
            steps = self._burn_steps(profile.total_time)
            arc, arc_count = _burn_arc_numba(
                at_ign[0], at_ign[1], at_ign[2], at_ign[3], t_ign - epoch,
                dir_x, dir_y,
                profile.a_peak, profile.ramp_time, profile.hold_time,
                profile.total_time, profile.ramp_rate,
                ref_index, float(snapshot.get('ref_px', 0.0)),
                float(snapshot.get('ref_py', 0.0)),
                snapshot['body_x'], snapshot['body_y'], snapshot['body_m'],
                snapshot['body_fixed'], snapshot['body_scripted'],
                snapshot['body_a'], snapshot['body_e'], snapshot['body_theta'],
                snapshot['body_arg'], snapshot['body_parent'],
                snapshot['G'], use_time, no_memo,
                steps,
            )
            arc = np.array(arc[:arc_count], dtype=np.float64, copy=True)
            arc[:, 2] += epoch
            segments.append(arc)
            budget -= len(arc)

            # -- 3. weiter gleiten, ab dem brennende
            end = arc[len(arc) - 1]
            coast_points = max(16, min(budget, self.max_points))
            out, used, _stats = _compute_distance_points_rkn_numba(
                float(end[0]), float(end[1]), float(end[3]), float(end[4]),
                0,
                float(snapshot.get('ref_px', 0.0)),
                float(snapshot.get('ref_py', 0.0)),
                snapshot['body_x'], snapshot['body_y'], snapshot['body_m'],
                snapshot['body_fixed'], snapshot['body_scripted'],
                snapshot['body_a'], snapshot['body_e'], snapshot['body_theta'],
                snapshot['body_arg'], snapshot['body_parent'],
                snapshot['G'], snapshot['dt'], snapshot['precision'],
                coast_points, int(snapshot['max_iters']),
                snapshot['rkn_min_dt'], snapshot['rkn_max_dt'],
                snapshot['rkn_rtol'], snapshot['rkn_atol_pos'],
                snapshot['rkn_atol_vel'], snapshot['rkn_safety'],
                snapshot['rkn_min_factor'], snapshot['rkn_max_factor'],
                snapshot['rkn_max_rejects'], use_time, ref_index,
                float(end[2]) - epoch, 0.0, 0.0,
                1 if snapshot.get('use_body_memo', True) else 0,
                snapshot['rkn_max_dt_floor'],
                snapshot['rkn_max_dt_timescale_divisor'],
            )
            if used < 2:
                break
            coast = np.array(out[:used], dtype=np.float64, copy=True)
            coast[:, 2] += epoch
            segments.append(coast)
            budget -= len(coast)

            # Der naechste knoten liest seinen zustand von DIESER linie.
            source = coast

        if not segments:
            self.node_markers = markers
            self.valid = bool(markers)
            return bool(markers)

        self.points = np.concatenate(segments, axis=0)
        self.node_markers = markers
        self.valid = True
        return True
```

- [ ] **Step 5: Extend `ship/maneuver/__init__.py`**

Add to the imports and `__all__`:

```python
from .preview import ManeuverPreview, body_state_at, state_on_curve
```
and add `'ManeuverPreview'`, `'body_state_at'`, `'state_on_curve'` to `__all__`.

- [ ] **Step 6: Run the test**

Run: `python tests/maneuver_preview_test.py`
Expected: PASS.

Two failures worth recognising:
- Section 2 failing by a *large* margin usually means `arc[:, 2] += epoch` was applied twice or not at all — check that every segment is rebased exactly once.
- Section 6 passing but section 3 failing means the basis sign is wrong; re-read `orbital_basis` against `tests/maneuver_plan_test.py` section 2.

- [ ] **Step 7: Run the whole existing suite to prove nothing moved**

The `compute.py` edit touches the predictor's file, so re-run its guards:

```
python tests/warp_predictor_test.py
python tests/apsis_stability_test.py
python tests/energy_test.py
```
Expected: the same results as before this task. `warp_predictor_test.py` has **three known pre-existing failures** (see `.claude/rules/tests.md`) — those, and only those, may fail.

- [ ] **Step 8: Commit**

```bash
cd spacesim
git add ship/maneuver/preview.py ship/maneuver/__init__.py ship/predictor/compute.py tests/maneuver_preview_test.py
git commit -m "feat(maneuver): chained coast/burn/coast preview

Each node reads its state off the previous node's result, so the chain is
a real chain. Rebuilds only when the plan version or the base trajectory
version moves, and never more often than min_interval_s.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 5: The executor — flying the node

**Files:**
- Create: `spacesim/ship/maneuver/executor.py`
- Modify: `spacesim/ship/control.py`
- Modify: `spacesim/ship/maneuver/__init__.py`
- Test: `spacesim/tests/maneuver_execute_test.py`

**Interfaces:**
- Consumes: `BurnProfile`, `ManeuverPlan`, `ManeuverPreview` (Tasks 1, 2, 4).
- Produces:
  - `ship.control.NODE_SNAP_MODE = 'node'`
  - `IDLE`, `ARMED`, `BURNING`, `DONE`, `ABORTED` (module string constants)
  - `ManeuverExecutor(plan, ship, ship_control, camera=None, telemetry=None, thrust_acc_max=600.0, realtime_warp_max=60.0, tick_rate=180.0, ramp_seconds=0.6, max_accel=None, orient_lead_seconds=5.0, burn_step_max_s=0.5, min_executable_dv=1e-3)`
  - attributes `state`, `node`, `profile`, `dir_x`, `dir_y`, `t_ignition`, `dv_delivered`, `abort_reason`
  - `ManeuverExecutor.a_max_sim() -> float`
  - `ManeuverExecutor.is_active -> bool` (`state in (ARMED, BURNING)`)
  - `ManeuverExecutor.can_arm() -> bool`
  - `ManeuverExecutor.arm(world, reference_body, preview=None) -> bool`
  - `ManeuverExecutor.disarm()`
  - `ManeuverExecutor.abort(reason)`
  - `ManeuverExecutor.notify_manual_input()`
  - `ManeuverExecutor.max_sim_seconds(world) -> float | None`
  - `ManeuverExecutor.wants_realtime(world) -> bool`
  - `ManeuverExecutor.update(world, sim_seconds)` — call **before** `world.step(sim_seconds)`
  - `ManeuverExecutor.time_to_ignition(world) -> float | None`
  - `ManeuverExecutor.throttle_level() -> float`

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_execute_test.py`:

```python
"""Der manoever-autopilot: scharfschalten, zuenden, brennen, aufraeumen.

Der test, an dem das ganze feature haengt, ist abschnitt 6: die
GEFLOGENE bahn muss die VORGESCHAUTE treffen. Alles davor sind die
voraussetzungen dafuer.

Abschnitt 1 klaert die einheitenfrage, die man leicht uebersieht:
schiffcontrol.apply_thrust rechnet in ECHT-sekunden, die welt laeuft aber
in SIM-sekunden und auf der untersten raffungsstufe 60x schneller. Die
beschleunigung des profils ist deshalb thrust_acc/realtime_warp_max und
nicht thrust_acc -- sonst braennte der autopilot 60-mal so hart wie die
pfeiltaste.

Aufruf: python tests/maneuver_execute_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from config.loader import ConfigLoader
from physics.world import world as World
from runtime.system_loader import SystemLoader
from ship.control import schiffcontrol
from ship.maneuver.executor import (
    ARMED,
    BURNING,
    DONE,
    IDLE,
    ManeuverExecutor,
)
from ship.maneuver.plan import ManeuverNode, ManeuverPlan
from ship.maneuver.preview import ManeuverPreview, state_on_curve
from ship.predictor import Predictor

FAILURES = []


def check(condition, name, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(name)


TICK_RATE = 180.0
REALTIME_WARP_MAX = 60.0
THRUST_ACC = 600.0
RAMP_SECONDS = 0.6
MAX_SUBSTEP = 1000.0


def build():
    config = ConfigLoader()
    bodies = SystemLoader(
        config.get('simulation.system_file', 'solar_system.json')).load()
    w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
    w.body = bodies
    config.apply_to_world(w)
    w.update_planets(0.0)

    erde = next(b for b in w.body if b.name.lower().startswith('erde'))
    ship = next(b for b in w.body if getattr(b, 'is_ship', False))

    mu = w.G * erde.mass
    r = float(getattr(erde, 'radius', 6.371e6)) + 4.0e6
    ahead = erde.position_at_time(1.0)
    behind = erde.position_at_time(-1.0)
    ship.position.x = erde.position.x + r
    ship.position.y = erde.position.y
    ship.velocity.x = (float(ahead.x) - float(behind.x)) / 2.0
    ship.velocity.y = (float(ahead.y) - float(behind.y)) / 2.0 + math.sqrt(mu / r)

    control = schiffcontrol(ship)
    config.apply_to_ship_control(control)

    predictor = Predictor(**config.predictor_kwargs())
    config.apply_to_predictor(predictor)
    predictor.async_compute = False
    predictor.initialize(ship, w)
    predictor.update(ship, w)
    return config, w, erde, ship, control, predictor


def make_executor(plan, ship, control):
    return ManeuverExecutor(
        plan, ship, control,
        thrust_acc_max=THRUST_ACC,
        realtime_warp_max=REALTIME_WARP_MAX,
        tick_rate=TICK_RATE,
        ramp_seconds=RAMP_SECONDS,
        max_accel=None,
        orient_lead_seconds=5.0,
        burn_step_max_s=0.5,
    )


print("\n1) EINHEITEN -- der autopilot brennt so hart wie die pfeiltaste")
_config, w, erde, ship, control, predictor = build()
plan = ManeuverPlan()
ex = make_executor(plan, ship, control)
a_max = ex.a_max_sim()
check(abs(a_max - THRUST_ACC / REALTIME_WARP_MAX) < 1e-12,
      "a_max = thrust_acc / realtime_warp_max", f"{a_max} m/s^2 (sim)")
# Gegenrechnung: eine echtsekunde volle pfeiltaste liefert thrust_acc m/s
# und laesst die welt realtime_warp_max sim-sekunden vorruecken. Dieselbe
# spanne beim autopiloten muss dasselbe delta-v ergeben.
manual_dv = THRUST_ACC * 1.0
auto_dv = a_max * (REALTIME_WARP_MAX * 1.0)
check(abs(manual_dv - auto_dv) < 1e-9,
      "eine echtsekunde beider wege liefert dasselbe delta-v",
      f"{manual_dv} vs {auto_dv}")

print("\n2) ein knoten ohne delta-v laesst sich nicht scharfschalten")
plan.add(ManeuverNode(w.time + 600.0))
check(ex.can_arm() is False, "can_arm() ist False", "")
check(ex.arm(w, erde) is False, "arm() lehnt ab", "")
check(ex.state == IDLE, "und bleibt im leerlauf", f"{ex.state}")

print("\n3) scharfschalten setzt zuendzeitpunkt und richtung")
plan.clear()
base = predictor.get_points()
t_node = float(base[0, 2]) + (float(base[len(base) - 1, 2]) - float(base[0, 2])) * 0.3
node = ManeuverNode(t_node, dv_prograde=120.0)
plan.add(node)
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, a_max, RAMP_SECONDS)
check(ex.can_arm() is True, "can_arm() ist True", "")
check(ex.arm(w, erde, preview) is True, "arm() nimmt den knoten", "")
check(ex.state == ARMED, "zustand ARMED", f"{ex.state}")
check(abs(ex.t_ignition - (t_node - ex.profile.total_time * 0.5)) < 1e-9,
      "zuendung liegt eine halbe brenndauer vor dem knoten",
      f"t_ign={ex.t_ignition:.3f}, t_node={t_node:.3f}, "
      f"dauer={ex.profile.total_time:.3f}")
check(abs(math.hypot(ex.dir_x, ex.dir_y) - 1.0) < 1e-9,
      "die schubrichtung ist ein einheitsvektor", "")
check(getattr(control, 'snap_mode', None) == 'node',
      "die nase wird auf den knoten gerastet", f"{control.snap_mode}")

print("\n4) die schrittklemme springt NIE ueber die zuendung")
# Ohne sie ruecken ein paar frames im zeitraffer um stunden vor und der
# brennvorgang faellt komplett zwischen zwei bilder.
worst_overshoot = -1e18
t = w.time
guard = 0
while t < ex.t_ignition and guard < 200000:
    nominal = 3600.0            # eine stunde je frame -- grober zeitraffer
    cap = ex.max_sim_seconds_value(t)
    step = nominal if cap is None else min(nominal, cap)
    worst_overshoot = max(worst_overshoot, (t + step) - ex.t_ignition)
    t += step
    guard += 1
check(worst_overshoot <= 1e-9,
      "kein schritt landet hinter der zuendung",
      f"groesster ueberschuss {worst_overshoot:.3e} s")
check(abs(t - ex.t_ignition) < 1e-6, "die kette landet exakt darauf",
      f"{t:.6f} vs {ex.t_ignition:.6f}")

print("\n5) der volle brennvorgang liefert GENAU das geplante delta-v")
_config, w, erde, ship, control, predictor = build()
plan = ManeuverPlan()
base = predictor.get_points()
t0 = float(base[0, 2])
t_node = t0 + (float(base[len(base) - 1, 2]) - t0) * 0.3
plan.add(ManeuverNode(t_node, dv_prograde=120.0))
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, THRUST_ACC / REALTIME_WARP_MAX,
                RAMP_SECONDS)
ex = make_executor(plan, ship, control)
ex.arm(w, erde, preview)
v_before = (float(ship.velocity.x), float(ship.velocity.y))
dir_x, dir_y = ex.dir_x, ex.dir_y

# Die eigentliche schleife, so wie runtime/loop.py sie fahren wird.
nominal = 1.0                    # 1 sim-sekunde je frame
guard = 0
while ex.state in (ARMED, BURNING) and guard < 2000000:
    cap = ex.max_sim_seconds(w)
    step = nominal if cap is None else min(nominal, max(1e-9, cap))
    ex.update(w, step)
    w.step(step, MAX_SUBSTEP)
    guard += 1
check(ex.state == DONE, "der brennvorgang endet von selbst", f"{ex.state}")
check(abs(ex.dv_delivered - 120.0) < 1e-6,
      "geliefertes delta-v == geplantes", f"{ex.dv_delivered:.9f}")

print("\n6) aufraeumen nach dem brennen")
check(len(plan) == 0, "der geflogene knoten ist aus dem plan verschwunden",
      f"{len(plan)}")
check(getattr(control, 'snap_mode', None) is None,
      "die rastung ist geloest", f"{control.snap_mode}")
check(abs(float(control.thrust_acc) - THRUST_ACC) < 1e-9,
      "die schubstufe steht wieder auf ihrem alten wert",
      f"{control.thrust_acc}")

print("\n7) abbruch durch handeingabe")
_config, w, erde, ship, control, predictor = build()
plan = ManeuverPlan()
base = predictor.get_points()
t0 = float(base[0, 2])
t_node = t0 + (float(base[len(base) - 1, 2]) - t0) * 0.3
plan.add(ManeuverNode(t_node, dv_prograde=120.0))
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, THRUST_ACC / REALTIME_WARP_MAX,
                RAMP_SECONDS)
ex = make_executor(plan, ship, control)
ex.arm(w, erde, preview)
# Bis kurz in den brennvorgang laufen, dann die pfeiltaste 'druecken'.
guard = 0
while ex.state != BURNING and guard < 2000000:
    cap = ex.max_sim_seconds(w)
    step = 1.0 if cap is None else min(1.0, max(1e-9, cap))
    ex.update(w, step)
    w.step(step, MAX_SUBSTEP)
    guard += 1
ex.update(w, 0.2)
w.step(0.2, MAX_SUBSTEP)
partial = ex.dv_delivered
check(partial > 0.0, "es wurde bereits etwas geliefert", f"{partial:.4f}")
ex.notify_manual_input()
check(not ex.is_active, "der autopilot ist aus", f"{ex.state}")
check(len(plan) == 1, "der knoten BLEIBT im plan", f"{len(plan)}")
v_at_abort = (float(ship.velocity.x), float(ship.velocity.y))
ex.update(w, 1.0)
check(abs(float(ship.velocity.x) - v_at_abort[0]) < 1e-12
      and abs(float(ship.velocity.y) - v_at_abort[1]) < 1e-12,
      "nach dem abbruch wird nicht mehr beschleunigt", "")

print("\n8) DIE HAUPTSACHE -- geflogen == vorgeschaut")
_config, w, erde, ship, control, predictor = build()
plan = ManeuverPlan()
base = predictor.get_points()
t0 = float(base[0, 2])
t_node = t0 + (float(base[len(base) - 1, 2]) - t0) * 0.3
plan.add(ManeuverNode(t_node, dv_prograde=120.0))
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, THRUST_ACC / REALTIME_WARP_MAX,
                RAMP_SECONDS)
ex = make_executor(plan, ship, control)
ex.arm(w, erde, preview)

t_check = t_node + 900.0        # 15 minuten nach dem knoten
guard = 0
while w.time < t_check and guard < 2000000:
    cap = ex.max_sim_seconds(w)
    step = 1.0 if cap is None else min(1.0, max(1e-9, cap))
    remaining = t_check - w.time
    step = min(step, remaining) if remaining > 1e-9 else step
    ex.update(w, step)
    w.step(step, MAX_SUBSTEP)
    guard += 1

expected = state_on_curve(preview.points, t_check)
check(expected is not None, "die vorschau reicht bis zum pruefzeitpunkt", "")
if expected is not None:
    ep = erde.position_at_time(w.time)
    r_flown = math.hypot(float(ship.position.x) - float(ep.x),
                         float(ship.position.y) - float(ep.y))
    dp = math.hypot(float(ship.position.x) - expected[0],
                    float(ship.position.y) - expected[1])
    dv = math.hypot(float(ship.velocity.x) - expected[2],
                    float(ship.velocity.y) - expected[3])
    speed = math.hypot(expected[2], expected[3])
    # Der rest ist die kick-then-drift-diskretisierung: der ausfuehrer legt
    # das delta-v eines schrittes VOR dem schritt an, die vorschau
    # integriert den schub stetig. Der fehler ist durch burn_step_max_s
    # begrenzt und waechst danach nicht mehr.
    check(dv < 1e-3 * speed,
          "die geschwindigkeit trifft die vorschau (< 0.1 %)",
          f"{dv:.4f} m/s auf {speed:.1f} m/s")
    check(dp < 5e-3 * r_flown,
          "die position trifft die vorschau (< 0.5 % des bahnradius)",
          f"{dp:.1f} m auf r={r_flown:.4e} m")

print("\n9) zwei knoten -- EXECUTE nimmt immer den naechsten")
_config, w, erde, ship, control, predictor = build()
plan = ManeuverPlan()
base = predictor.get_points()
t0 = float(base[0, 2])
span = float(base[len(base) - 1, 2]) - t0
early = ManeuverNode(t0 + span * 0.3, dv_prograde=60.0)
late = ManeuverNode(t0 + span * 0.6, dv_prograde=60.0)
plan.add(late)
plan.add(early)
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, THRUST_ACC / REALTIME_WARP_MAX,
                RAMP_SECONDS)
ex = make_executor(plan, ship, control)
ex.arm(w, erde, preview)
check(ex.node is early, "scharf ist der zeitlich naechste knoten", "")
check(len(plan) == 2, "der andere bleibt unangetastet", f"{len(plan)}")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    sys.exit(1)
print("ship/maneuver/executor: alle pruefungen bestanden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_execute_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'ship.maneuver.executor'`

- [ ] **Step 3: Add the node snap mode to `ship/control.py`**

Directly below the existing `SNAP_MODES = (...)` tuple, add:

```python
#: Die FUENFTE rastung: die schubrichtung eines scharfgeschalteten
#: manoeverknotens. Sie steht bewusst NICHT in SNAP_MODES -- die rosette
#: bildet vier richtungen ab, die der spieler selbst waehlt, und diese hier
#: waehlt der autopilot. `ManeuverExecutor` setzt `snap_mode` direkt (nicht
#: ueber toggle_snap), und `Renderer.orbital_frame_directions` liefert den
#: passenden eintrag im richtungs-woerterbuch.
NODE_SNAP_MODE = 'node'
```

- [ ] **Step 4: Write `ship/maneuver/executor.py`**

```python
"""Der autopilot, der einen knoten wirklich fliegt.

    IDLE --arm()--> ARMED --zuendung--> BURNING --profil zuende--> DONE
                      |                    |
                      +---- abort() -------+--> ABORTED

WAS DER AUSFUEHRER NICHT TUT: er rechnet keine richtung und keine dauer
selbst. Beides kommt aus `ship/maneuver/` -- die richtung aus dem marker,
den die vorschau aufgeloest hat, die dauer aus `BurnProfile`. Waere hier
eine zweite rechnung, fluege das schiff etwas anderes als die linie zeigt,
und genau das ist der fehler, den dieses ganze modul verhindern soll.

DIE EINHEITENFRAGE. `schiffcontrol.apply_thrust` addiert
`thrust_acc * real_dt` -- 600 m/s^2 mal ECHTsekunden -- waehrend die welt
um `sim_dt * tick_rate * real_dt` SIM-sekunden vorrueckt. Auf der untersten
raffungsstufe sind das 60 sim-sekunden je echtsekunde. In SIM-zeit
gerechnet betraegt die beschleunigung der pfeiltaste also
`600 / 60 = 10 m/s^2`. Die vorschau integriert in sim-zeit, folglich muss
das profil dieselbe zahl benutzen:

    a_max_sim = thrust_acc / realtime_warp_max

Mit `thrust_acc` direkt braennte der autopilot 60-mal so hart wie die
pfeiltaste -- und die vorschau zeigte diesen brennvorgang auch noch
korrekt an, so dass nichts auf dem schirm den fehler verraten wuerde.
`config.maneuver.max_accel` ueberschreibt die ableitung.

KICK-THEN-DRIFT. `update()` legt das delta-v EINES schrittes an, BEVOR
`world.step()` diesen schritt geht. Die vorschau integriert den schub
dagegen stetig (RK4). Der unterschied ist erster ordnung in der
schrittweite und deshalb ist die schrittweite waehrend des brennens auf
`burn_step_max_s` gedeckelt. Gemessen wird der rest in
`tests/maneuver_execute_test.py` abschnitt 8.
"""

import math

from .plan import MIN_EXECUTABLE_DV
from .profile import BurnProfile

IDLE = 'idle'
ARMED = 'armed'
BURNING = 'burning'
DONE = 'done'
ABORTED = 'aborted'

#: Wert fuer `schiffcontrol.snap_mode`, waehrend der autopilot laeuft.
NODE_SNAP_MODE = 'node'


class ManeuverExecutor:
    """Scharfschalten, ausrichten, zuenden, brennen, aufraeumen."""

    def __init__(self, plan, ship, ship_control, camera=None, telemetry=None,
                 thrust_acc_max=600.0, realtime_warp_max=60.0, tick_rate=180.0,
                 ramp_seconds=0.6, max_accel=None, orient_lead_seconds=5.0,
                 burn_step_max_s=0.5, min_executable_dv=MIN_EXECUTABLE_DV):
        self.plan = plan
        self.ship = ship
        self.ship_control = ship_control
        self.camera = camera
        self.telemetry = telemetry

        self.thrust_acc_max = float(thrust_acc_max)
        self.realtime_warp_max = max(1e-9, float(realtime_warp_max))
        self.tick_rate = max(1.0, float(tick_rate))
        self.ramp_seconds = max(1e-6, float(ramp_seconds))
        self.max_accel = None if max_accel is None else float(max_accel)
        self.orient_lead_seconds = max(0.0, float(orient_lead_seconds))
        self.burn_step_max_s = max(1e-3, float(burn_step_max_s))
        self.min_executable_dv = float(min_executable_dv)

        self.state = IDLE
        self.node = None
        self.profile = None
        self.dir_x = 0.0
        self.dir_y = 0.0
        self.t_ignition = 0.0
        self.dv_delivered = 0.0
        self.abort_reason = None

        #: Beim scharfschalten festgehalten. `a_max` DARF nicht waehrend des
        #: brennens neu aus `ship_control.thrust_acc` gelesen werden -- der
        #: schubregler des HUDs schreibt genau dieses feld, und der
        #: brennvorgang wuerde sich dann unter sich selbst veraendern.
        self._a_max_armed = 0.0
        self._thrust_acc_before = None
        self._thrust_level_before = None

    # ------------------------------------------------------------- ableitung

    def a_max_sim(self):
        """Schubbeschleunigung in SIM-sekunden (siehe modulkopf)."""
        if self.max_accel is not None:
            return max(1e-9, self.max_accel)
        return max(1e-9, self.thrust_acc_max / self.realtime_warp_max)

    @property
    def is_active(self):
        return self.state in (ARMED, BURNING)

    def can_arm(self):
        node = self.plan.first() if self.plan is not None else None
        return node is not None and node.is_executable(self.min_executable_dv)

    def time_to_ignition(self, world):
        if not self.is_active:
            return None
        return self.t_ignition - float(getattr(world, 'time', 0.0))

    def throttle_level(self):
        if self.state != BURNING or self.profile is None:
            return 0.0
        tau = self._tau_now
        return self.profile.throttle_at(tau)

    # ----------------------------------------------------------- schalten

    def _marker_for(self, preview, node):
        if preview is None:
            return None
        for marker in getattr(preview, 'node_markers', ()) or ():
            if marker.get('node') is node:
                return marker
        return None

    def arm(self, world, reference_body=None, preview=None):
        """Den naechsten knoten scharfschalten. False, wenn das nicht geht."""
        if self.is_active:
            return False
        node = self.plan.first() if self.plan is not None else None
        if node is None or not node.is_executable(self.min_executable_dv):
            return False

        marker = self._marker_for(preview, node)
        if marker is None:
            # Ohne aufgeloeste richtung gibt es nichts zu fliegen. Sie kommt
            # aus der vorschau, weil dort der zustand an der knotenzeit
            # bereits steht -- hier ein zweites mal zu propagieren waere
            # eine zweite wahrheit.
            return False

        a_max = self.a_max_sim()
        profile = BurnProfile(node.dv_total, a_max, self.ramp_seconds)
        t_ignition = profile.ignition_time(node.t_node)
        now = float(getattr(world, 'time', 0.0))
        if now > t_ignition + profile.total_time:
            # Der knoten liegt vollstaendig in der vergangenheit.
            return False

        self.node = node
        self.profile = profile
        self.dir_x = float(marker['dir_x'])
        self.dir_y = float(marker['dir_y'])
        self.t_ignition = t_ignition
        self.dv_delivered = 0.0
        self.abort_reason = None
        self._a_max_armed = a_max
        self._tau_now = 0.0
        self.state = ARMED

        if self.ship_control is not None:
            self._thrust_acc_before = float(
                getattr(self.ship_control, 'thrust_acc', self.thrust_acc_max))
            # Die nase auf die schubrichtung rasten. Direkt gesetzt, nicht
            # ueber toggle_snap: 'node' ist keine der vier rosetten-modi.
            self.ship_control.snap_mode = NODE_SNAP_MODE
            self.ship_control._snap_locked = False
        if self.telemetry is not None:
            self._thrust_level_before = float(
                getattr(self.telemetry, 'thrust_level', 1.0))
        return True

    def disarm(self):
        self._restore()
        self.state = IDLE
        self.node = None
        self.profile = None
        self.abort_reason = None

    def abort(self, reason='aborted'):
        if not self.is_active:
            return False
        self._restore()
        self.state = ABORTED
        self.abort_reason = str(reason)
        return True

    def notify_manual_input(self):
        """Von der hauptschleife gerufen, sobald der spieler selbst steuert.

        Handeingabe schlaegt den autopiloten, immer. Ein brennvorgang, den
        man nicht durch anfassen der steuerung stoppen kann, ist eine
        falle.
        """
        return self.abort('manual input')

    def _restore(self):
        if self.ship_control is not None:
            try:
                self.ship_control.clear_snap()
            except Exception:
                self.ship_control.snap_mode = None
            if self._thrust_acc_before is not None:
                self.ship_control.thrust_acc = self._thrust_acc_before
        if self.telemetry is not None and self._thrust_level_before is not None:
            try:
                self.telemetry.set_thrust_level(self._thrust_level_before)
            except Exception:
                pass
        self._thrust_acc_before = None
        self._thrust_level_before = None

    # -------------------------------------------------------- zeitschritte

    def max_sim_seconds_value(self, now):
        """Die schrittklemme fuer eine gegebene sim-zeit (testbar ohne welt)."""
        if self.state == ARMED:
            remaining = self.t_ignition - float(now)
            return remaining if remaining > 0.0 else self.burn_step_max_s
        if self.state == BURNING:
            return self.burn_step_max_s
        return None

    def max_sim_seconds(self, world):
        """Wie weit die welt in DIESEM frame hoechstens vorruecken darf.

        Scharf: hoechstens bis zur zuendung -- ein zeitraffer-frame rueckt
        sonst um stunden vor und der ganze brennvorgang faellt zwischen zwei
        bilder. Brennend: `burn_step_max_s`, damit die kick-then-drift-
        naeherung klein bleibt.
        """
        return self.max_sim_seconds_value(float(getattr(world, 'time', 0.0)))

    def wants_realtime(self, world):
        """Muss die raffung jetzt auf echtzeit herunter?

        Ja, sobald die zuendung naeher liegt als die zeit, die das schiff
        zum drehen braucht -- gerechnet wird mit `orient_lead_seconds`, das
        eine halbe umdrehung bei `rotation_speed` mit reserve abdeckt.
        """
        if self.state == BURNING:
            return True
        if self.state != ARMED:
            return False
        remaining = self.t_ignition - float(getattr(world, 'time', 0.0))
        return remaining <= self.orient_lead_seconds

    # ------------------------------------------------------------- fahren

    def update(self, world, sim_seconds):
        """VOR `world.step(sim_seconds)` aufrufen.

        Legt das delta-v des bevorstehenden schrittes an, damit die
        positionsintegration dieses schrittes es bereits traegt.
        """
        if not self.is_active or self.profile is None:
            return
        now = float(getattr(world, 'time', 0.0))
        step = max(0.0, float(sim_seconds))

        if self.state == ARMED:
            if now + 1e-9 < self.t_ignition:
                return
            self.state = BURNING

        tau0 = now - self.t_ignition
        tau1 = tau0 + step
        self._tau_now = max(0.0, tau0)

        dv = self.profile.dv_between(tau0, tau1)
        if dv > 0.0 and self.ship is not None:
            self.ship.velocity.x += self.dir_x * dv
            self.ship.velocity.y += self.dir_y * dv
            self.dv_delivered += dv
            try:
                self.ship.last_thrust_direction = None
            except Exception:
                pass

        # Der schubbogen des HUDs zeigt die rampe -- kostenlos, weil der
        # regler ohnehin gezeichnet wird.
        if self.telemetry is not None:
            try:
                self.telemetry.set_thrust_level(
                    self.profile.throttle_at(max(0.0, (tau0 + tau1) * 0.5)))
            except Exception:
                pass

        if tau1 >= self.profile.total_time:
            self._finish()

    def _finish(self):
        node = self.node
        self._restore()
        self.state = DONE
        if node is not None and self.plan is not None:
            self.plan.remove(node)
        self.node = None
```

- [ ] **Step 5: Extend `ship/maneuver/__init__.py`**

```python
from .executor import ARMED, BURNING, DONE, IDLE, ManeuverExecutor
```
and add `'ARMED'`, `'BURNING'`, `'DONE'`, `'IDLE'`, `'ManeuverExecutor'` to `__all__`.

- [ ] **Step 6: Run the test**

Run: `python tests/maneuver_execute_test.py`
Expected: PASS.

If section 5 delivers slightly *less* than planned, the loop exited before `tau1 >= total_time` — check that `update()` runs before `world.step()` and that the loop condition tests `ex.state in (ARMED, BURNING)` and not `state == BURNING`.

- [ ] **Step 7: Commit**

```bash
cd spacesim
git add ship/maneuver/executor.py ship/maneuver/__init__.py ship/control.py tests/maneuver_execute_test.py
git commit -m "feat(maneuver): autopilot that flies a node with a ramped burn

Direction and duration come from the preview and BurnProfile, never from a
second calculation here. a_max is a sim-time acceleration derived from the
manual thrust, so the autopilot burns exactly as hard as the arrow key.
Manual input always aborts.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 6: Wiring — config, bootstrap, the frame loop, the keys

After this task the feature *works* (nodes can be placed, planned and flown); it is just not drawn yet. That is the point of the split: the mechanism gets its own gate before any pixels are involved.

**Files:**
- Modify: `spacesim/config/config.json`
- Modify: `spacesim/config/loader.py`
- Modify: `spacesim/runtime/bootstrap.py`
- Modify: `spacesim/runtime/loop.py`
- Modify: `spacesim/runtime/input.py`

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces:
  - `ConfigLoader.maneuver_kwargs() -> dict` with keys `enabled`, `max_nodes`, `ramp_seconds`, `max_accel`, `orient_lead_seconds`, `burn_step_max_s`, `min_executable_dv`, `preview_max_points`, `preview_min_interval_s`, `burn_step_s`, `burn_min_steps`, `burn_max_steps`, `default_node_lead_fraction`, `handle_dv_per_px`
  - `App.maneuver_plan`, `App.maneuver_preview`, `App.maneuver_executor`, `App.maneuver_config` (added to `App.__slots__`)
  - `InputRouter.add_node_at_cursor()`, `InputRouter.delete_selected_node()`, `InputRouter.toggle_execute()`
  - `App.selected_node_index` (int, defaults to 0) — which node the HUD block edits

- [ ] **Step 1: Add the config section**

In `spacesim/config/config.json`, insert a new `"maneuver"` block between the existing `"predictor"` and `"renderer"` blocks (JSON key order is cosmetic, but keeping it next to `predictor` matches how the file is read):

```json
  "maneuver": {
    "enabled": true,
    "max_nodes": 5,
    "ramp_seconds": 0.6,
    "max_accel": null,
    "orient_lead_seconds": 5.0,
    "burn_step_max_s": 0.5,
    "min_executable_dv": 0.001,
    "preview_max_points": 1200,
    "preview_min_interval_s": 0.15,
    "burn_step_s": 0.25,
    "burn_min_steps": 16,
    "burn_max_steps": 512,
    "default_node_lead_fraction": 0.5,
    "handle_dv_per_px": 0.75
  },
```

Meaning of the two that are not obvious:
- `max_accel: null` means *derive* `thrust_acc / realtime_warp_max` (see Task 5's module header). A number here overrides it, in m/s² of **sim** time.
- `default_node_lead_fraction: 0.5` — where along the drawn horizon a new node lands when the cursor is nowhere near the line.

- [ ] **Step 2: Add `maneuver_kwargs()` to the loader**

In `spacesim/config/loader.py`, directly **after** the existing `predictor_kwargs()` method, add:

```python
    def maneuver_kwargs(self):
        """maneuver-abschnitt -> plan, vorschau und ausfuehrer.

        Ein reines woerterbuch statt eines `_assign` auf ein objekt: die drei
        empfaenger (ManeuverPlan, ManeuverPreview, ManeuverExecutor) teilen
        sich den abschnitt, und keiner von ihnen soll alle schluessel
        besitzen.

        `max_accel: null` heisst ABLEITEN (thrust_acc / realtime_warp_max),
        nicht 'null m/s^2' -- siehe ship/maneuver/executor.py.
        """
        raw_accel = self.get('maneuver.max_accel', None)
        return {
            'enabled': bool(self.get('maneuver.enabled', True)),
            'max_nodes': int(self.get('maneuver.max_nodes', 5)),
            'ramp_seconds': float(self.get('maneuver.ramp_seconds', 0.6)),
            'max_accel': None if raw_accel is None else float(raw_accel),
            'orient_lead_seconds': float(
                self.get('maneuver.orient_lead_seconds', 5.0)),
            'burn_step_max_s': float(self.get('maneuver.burn_step_max_s', 0.5)),
            'min_executable_dv': float(
                self.get('maneuver.min_executable_dv', 1e-3)),
            'preview_max_points': int(
                self.get('maneuver.preview_max_points', 1200)),
            'preview_min_interval_s': float(
                self.get('maneuver.preview_min_interval_s', 0.15)),
            'burn_step_s': float(self.get('maneuver.burn_step_s', 0.25)),
            'burn_min_steps': int(self.get('maneuver.burn_min_steps', 16)),
            'burn_max_steps': int(self.get('maneuver.burn_max_steps', 512)),
            'default_node_lead_fraction': float(
                self.get('maneuver.default_node_lead_fraction', 0.5)),
            'handle_dv_per_px': float(
                self.get('maneuver.handle_dv_per_px', 0.75)),
        }
```

- [ ] **Step 3: Build the three objects in `bootstrap.py`**

Add to the import block at the top:

```python
from ship.maneuver import ManeuverExecutor, ManeuverPlan, ManeuverPreview
```

Extend `App.__slots__` — add these five names to the existing tuple:

```python
        'maneuver_plan', 'maneuver_preview', 'maneuver_executor',
        'maneuver_config', 'selected_node_index',
```

Then, in `build_app`, insert this block **directly after** `config.apply_to_ship_control(app.ship_control)` and **before** `app.renderer = Renderer(...)` — the plan must exist before the renderer and the HUD, both of which read it:

```python
    # -- manoeverknoten ------------------------------------------------------
    # Muss VOR renderer und HUD stehen: beide bekommen den plan als verweis
    # gereicht und lesen ihn je frame.
    app.maneuver_config = config.maneuver_kwargs()
    mc = app.maneuver_config
    app.maneuver_plan = ManeuverPlan(
        max_nodes=mc['max_nodes'],
        min_executable_dv=mc['min_executable_dv'],
    )
    app.maneuver_preview = ManeuverPreview(
        max_points=mc['preview_max_points'],
        burn_step_s=mc['burn_step_s'],
        burn_min_steps=mc['burn_min_steps'],
        burn_max_steps=mc['burn_max_steps'],
        min_interval_s=mc['preview_min_interval_s'],
    )
    app.maneuver_executor = ManeuverExecutor(
        app.maneuver_plan, app.ship, app.ship_control, camera=app.camera,
        # `thrust_acc_max` kommt aus der KONFIGURATION, nicht aus
        # ship_control.thrust_acc: der schubregler des HUDs schreibt jenes
        # feld, und der ausfuehrer wuerde dann seine eigene brennstaerke
        # vom regler abhaengig machen.
        thrust_acc_max=float(config.get('ship.thrust_acc', 600.0)),
        realtime_warp_max=app.realtime_warp_max,
        tick_rate=float(max(1, app.window.fps)),
        ramp_seconds=mc['ramp_seconds'],
        max_accel=mc['max_accel'],
        orient_lead_seconds=mc['orient_lead_seconds'],
        burn_step_max_s=mc['burn_step_max_s'],
        min_executable_dv=mc['min_executable_dv'],
    )
    #: Welchen knoten der HUD-block gerade bearbeitet.
    app.selected_node_index = 0
```

- [ ] **Step 4: Hand the executor its telemetry after the HUD exists**

The executor writes the throttle arc through `Telemetry.set_thrust_level`, but the HUD is built later. Add this **directly after** the `if bool(config.get('renderer.hud_enabled', True)):` block that constructs `app.hud`:

```python
    # Der ausfuehrer treibt den schubbogen des HUDs -- die rampe wird damit
    # sichtbar, ohne dass irgendetwas zusaetzlich gezeichnet werden muss.
    # Nachgereicht, weil das HUD erst hier existiert; ohne telemetrie laeuft
    # der ausfuehrer trotzdem, nur ohne anzeige.
    if app.hud is not None:
        app.maneuver_executor.telemetry = app.hud.telemetry
```

- [ ] **Step 5: Wire the frame loop**

Three edits in `spacesim/runtime/loop.py`.

**(a)** Abort on manual input. Inside `run()`, in the ship-control block, replace

```python
                if app.thrust_allowed():
                    app.ship_control.apply_thrust(keys, frame_dt)
```

with

```python
                # Handeingabe schlaegt den autopiloten. Geprueft werden alle
                # vier steuertasten, nicht nur der schub: wer im brennvorgang
                # dreht, meint es ebenso ernst, und eine gedrehte nase macht
                # die restliche brenndauer ohnehin ungueltig.
                if (app.maneuver_executor is not None
                        and app.maneuver_executor.is_active
                        and (keys[pygame.K_UP] or keys[pygame.K_DOWN]
                             or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT])):
                    app.maneuver_executor.notify_manual_input()
                    print("MANEUVER: abgebrochen (handeingabe)")
                if app.thrust_allowed():
                    app.ship_control.apply_thrust(keys, frame_dt)
```

**(b)** The step clamp and the executor tick. Replace the single call

```python
        app.world.step(app.camera.sim_dt * app.tick_rate * frame_dt,
                       app.max_substep)
```

with

```python
        sim_step = app.camera.sim_dt * app.tick_rate * frame_dt
        # Ein scharfgeschalteter knoten deckelt den schritt: sonst rueckt ein
        # zeitraffer-frame um stunden vor und der ganze brennvorgang faellt
        # zwischen zwei bilder. Waehrend des brennens haelt die decke die
        # kick-then-drift-naeherung klein (siehe ship/maneuver/executor.py).
        cap = (app.maneuver_executor.max_sim_seconds(app.world)
               if app.maneuver_executor is not None else None)
        if cap is not None:
            sim_step = min(sim_step, max(1e-9, cap))
        # Das delta-v des SCHRITTES anlegen, BEVOR er gegangen wird -- so
        # traegt die positionsintegration dieses schrittes es bereits.
        if app.maneuver_executor is not None:
            app.maneuver_executor.update(app.world, sim_step)
        app.world.step(sim_step, app.max_substep)
```

**(c)** Warp handover and preview refresh. Insert `_apply_maneuver(app)` into the existing sequence, directly **after** `_clamp_warp(app)` and **before** `_apply_horizon(app)`:

```python
        _clamp_warp(app)
        _apply_maneuver(app)
        _apply_horizon(app)
```

and add these two module-level functions beside `_clamp_warp` / `_apply_horizon`:

```python
def _apply_maneuver(app):
    """Raffung auf echtzeit ziehen, sobald die zuendung naeherrueckt.

    Der spieler darf zum knoten hin raffen; kurz davor muss die welt aber
    zurueck auf echtzeit, weil der schub nur dort ueberhaupt erlaubt ist
    (app.thrust_allowed()). Ohne diesen griff steht der spieler bei 1 d/s
    vor einem brennvorgang, der nie beginnt.
    """
    executor = getattr(app, 'maneuver_executor', None)
    if executor is None or not executor.wants_realtime(app.world):
        return
    ceiling = app.realtime_warp_max / max(1.0, app.tick_rate)
    if app.camera.sim_dt > ceiling:
        app.camera.sim_dt = ceiling


def _update_maneuver_preview(app):
    """Die geplante bahn nachfuehren -- nur bei aenderung, nie je frame."""
    preview = getattr(app, 'maneuver_preview', None)
    if preview is None or app.ship is None:
        return
    preview.maybe_rebuild(
        app.maneuver_plan, app.ship, app.world, app.predictor,
        app.ui_state.reference_body,
        app.maneuver_executor.a_max_sim(),
        app.maneuver_config['ramp_seconds'],
    )
```

Finally, call the preview refresh right after the predictor update, replacing

```python
        points = _update_predictor(app)
```

with

```python
        points = _update_predictor(app)
        # NACH dem predictor: die vorschau liest dessen linie, und mit der
        # linie des vorframes saesse sie einen frame lang daneben.
        _update_maneuver_preview(app)
```

- [ ] **Step 6: Add the three keys in `input.py`**

Add to the imports at the top of `spacesim/runtime/input.py`:

```python
from ship.maneuver import ManeuverNode
```

Inside `handle_keydown`, add these branches to the existing `elif` chain — put them directly after the `elif key == pygame.K_t:` block:

```python
        # N: knoten setzen. Shift+N: den gewaehlten knoten loeschen.
        elif key == pygame.K_n:
            if event.mod & pygame.KMOD_SHIFT:
                self.delete_selected_node()
            else:
                self.add_node_at_cursor()

        # X: den naechsten knoten scharfschalten bzw. abbrechen.
        elif key == pygame.K_x:
            self.toggle_execute()
```

Then add these three methods at the end of the class, beside `_toggle_epicycles`:

```python
    # -- manoeverknoten ------------------------------------------------------

    def _node_time_from_cursor(self):
        """Zeit auf der vorhersagelinie, die dem mauszeiger am naechsten liegt.

        Der renderer legt die linie in schirmkoordinaten ab, waehrend ein
        griff gezogen wird oder ein knoten gesetzt werden soll
        (`renderer.maneuver_curve_screen`, siehe render/maneuver.py). Ist
        sie nicht da oder der zeiger zu weit weg, faellt die zeit auf einen
        festen bruchteil des horizonts zurueck -- ein knoten muss auch dann
        entstehen, wenn die maus gerade woanders ist.
        """
        app = self.app
        points = app.predictor.get_points()
        if points is None or len(points) < 2:
            return None
        t0 = float(points[0, 2])
        t_end = float(points[len(points) - 1, 2])

        curve = getattr(app.renderer, 'maneuver_curve_screen', None)
        if curve is not None and len(curve) > 1:
            mx, my = pygame.mouse.get_pos()
            best_t = None
            best_d2 = None
            for i in range(len(curve)):
                dx = float(curve[i][0]) - float(mx)
                dy = float(curve[i][1]) - float(my)
                d2 = dx * dx + dy * dy
                if best_d2 is None or d2 < best_d2:
                    best_d2 = d2
                    best_t = float(curve[i][2])
            # 64 px: weit genug, um die linie nicht pixelgenau treffen zu
            # muessen, eng genug, dass ein klick am bildrand nicht zaehlt.
            if best_d2 is not None and best_d2 <= 64.0 * 64.0:
                return best_t

        fraction = float(app.maneuver_config['default_node_lead_fraction'])
        return t0 + (t_end - t0) * max(0.02, min(0.98, fraction))

    def add_node_at_cursor(self):
        app = self.app
        if app.maneuver_plan.is_full:
            print(f"MANEUVER: plan voll ({app.maneuver_plan.max_nodes} knoten)")
            return
        t_node = self._node_time_from_cursor()
        if t_node is None:
            print("MANEUVER: keine vorhersagelinie, kein knoten")
            return
        node = ManeuverNode(t_node)
        app.maneuver_plan.add(node)
        # Den frischen knoten gleich bearbeitbar machen.
        index = app.maneuver_plan.index_of(node)
        app.selected_node_index = 0 if index is None else index
        print(f"MANEUVER: knoten bei T+{t_node:.1f} s "
              f"({len(app.maneuver_plan)}/{app.maneuver_plan.max_nodes})")

    def delete_selected_node(self):
        app = self.app
        if app.maneuver_plan.remove_at(app.selected_node_index):
            app.selected_node_index = max(
                0, min(app.selected_node_index, len(app.maneuver_plan) - 1))
            print(f"MANEUVER: knoten geloescht ({len(app.maneuver_plan)} uebrig)")

    def toggle_execute(self):
        app = self.app
        executor = app.maneuver_executor
        if executor.is_active:
            executor.abort('cancelled')
            print("MANEUVER: abgebrochen")
            return
        ok = executor.arm(app.world, app.ui_state.reference_body,
                          app.maneuver_preview)
        if ok:
            print(f"MANEUVER: scharf, zuendung T+{executor.t_ignition:.1f} s, "
                  f"dauer {executor.profile.total_time:.2f} s")
        else:
            print("MANEUVER: nicht ausfuehrbar (kein knoten, kein delta-v, "
                  "oder er liegt in der vergangenheit)")
```

- [ ] **Step 7: Verify nothing regressed and the wiring holds**

Run the four maneuver tests plus the guards the touched files carry:

```
python tests/maneuver_profile_test.py
python tests/maneuver_plan_test.py
python tests/maneuver_burn_kernel_test.py
python tests/maneuver_preview_test.py
python tests/maneuver_execute_test.py
python tests/warp_predictor_test.py
python tests/ui_hud_test.py
```
Expected: all pass, except `warp_predictor_test.py`'s three known pre-existing failures.

- [ ] **Step 8: Smoke-run the real app**

```
SPACESIM_MAX_FRAMES=120 python main.py
```
Expected: the window opens, runs 120 frames and exits with no traceback. Nothing new is drawn yet — that is Task 7 — but `App` now carries a plan, a preview and an executor, and `N` / `X` print to the console.

- [ ] **Step 9: Commit**

```bash
cd spacesim
git add config/config.json config/loader.py runtime/bootstrap.py runtime/loop.py runtime/input.py
git commit -m "feat(maneuver): wire plan, preview and executor into the app

Config section, bootstrap construction, the frame-loop step clamp and the
warp handover before ignition, plus the N / Shift+N / X keys. Nothing is
drawn yet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 7: Drawing the plan — the fifth render domain

**Files:**
- Create: `spacesim/render/maneuver.py`
- Modify: `spacesim/render/renderer.py`
- Test: `spacesim/tests/maneuver_render_test.py`

**Interfaces:**
- Consumes: `ManeuverPreview` (Task 4); `Renderer._active_frame()`, `Renderer._frame_camera_xy(camera)`, `Renderer._world_to_screen_xy_at_time(wx, wy, camera, t, camera_frame_xy)`, `Renderer._is_on_screen(sx, sy, margin_px)`, `Renderer._draw_polyline(run, color, width)`, `Renderer._draw_line_segments(points, color, width)`.
- Produces:
  - `ManeuverDrawMixin` — mixed into `Renderer` after `PredictionDrawMixin`
  - `Renderer.draw_maneuver(camera)` — the frame entry point
  - `Renderer.maneuver_plan` / `Renderer.maneuver_preview` — set by bootstrap, read here
  - `Renderer.maneuver_node_hits` — list of dicts, refilled every call:
    `{'index': int, 'sx': float, 'sy': float, 'radius_px': float, 'handles': [{'kind': str, 'sx': float, 'sy': float, 'radius_px': float, 'dir_sx': float, 'dir_sy': float}, ...]}`
    with `kind` in `('prograde', 'retrograde', 'normal', 'antinormal')` and `dir_s*` the **screen-space unit vector** the handle points along
  - `Renderer.maneuver_curve_screen` — `list[(sx, sy, t_abs)]`, filled only while `maneuver_drag_active` is true
  - `Renderer.maneuver_drag_active` — set by the gizmo widget (Task 9) and by `InputRouter`
  - `Renderer.maneuver_selected_index` — which node draws highlighted
  - `Renderer.maneuver_burn_direction` — `(dx, dy)` world unit vector while a node is armed, else `None`

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_render_test.py`:

```python
"""Die manoever-zeichnung auf einem echten GL-context.

Was hier geprueft wird, ist NICHT wie es aussieht, sondern was das HUD
danach anfassen kann: `renderer.maneuver_node_hits`. Der ziehgriff
(ui/hud/maneuver.py) trifft genau diese schirmpositionen -- rechnete er sie
selbst nach, laege der griff neben dem gezeichneten pfeil, und zwar in
jedem bewegten bezugsrahmen anders.

Dieselbe bauart wie `tests/background_gl_test.py`.

Aufruf: python tests/maneuver_render_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS', 'permonitorv2')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import moderngl
import pygame
from pygame.locals import DOUBLEBUF, OPENGL

W, H = 1024, 640
FAILURES = []


def check(condition, label, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {label}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(label)


# NUR display+font -- pygame.init() zaehlt mixer/joystick auf (siehe CLAUDE.md).
pygame.display.init()
pygame.font.init()
pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
gl = moderngl.create_context()
gl.enable(moderngl.BLEND)
gl.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

from config.loader import ConfigLoader
from physics.world import world as World
from render.renderer import Renderer
from runtime.system_loader import SystemLoader
from ship.camera import Camera
from ship.maneuver.plan import ManeuverNode, ManeuverPlan
from ship.maneuver.preview import ManeuverPreview
from ship.predictor import Predictor

config = ConfigLoader()
bodies = SystemLoader(config.get('simulation.system_file', 'solar_system.json')).load()
w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
w.body = bodies
config.apply_to_world(w)
w.update_planets(0.0)

erde = next(b for b in w.body if b.name.lower().startswith('erde'))
ship = next(b for b in w.body if getattr(b, 'is_ship', False))
mu = w.G * erde.mass
r = float(getattr(erde, 'radius', 6.371e6)) + 4.0e6
ahead = erde.position_at_time(1.0)
behind = erde.position_at_time(-1.0)
ship.position.x = erde.position.x + r
ship.position.y = erde.position.y
ship.velocity.x = (float(ahead.x) - float(behind.x)) / 2.0
ship.velocity.y = (float(ahead.y) - float(behind.y)) / 2.0 + math.sqrt(mu / r)

camera = Camera(None, W, H)
config.apply_to_camera(camera)
camera.target = ship
camera.scale = 2.0e-5
camera.snap_to_targets()

predictor = Predictor(**config.predictor_kwargs())
config.apply_to_predictor(predictor)
predictor.async_compute = False
predictor.initialize(ship, w)
predictor.update(ship, w)

renderer = Renderer(W, H, enable_fxaa=False, ctx=gl)
config.apply_to_renderer(renderer)
renderer.set_frame_time(w.time)
renderer.current_reference_body = erde

base = predictor.get_points()
t0 = float(base[0, 2])
t_end = float(base[len(base) - 1, 2])
t_node = t0 + (t_end - t0) * 0.25

plan = ManeuverPlan()
plan.add(ManeuverNode(t_node, dv_prograde=150.0, dv_normal=-40.0))
preview = ManeuverPreview(max_points=1200)
preview.rebuild(plan, ship, w, predictor, erde, 10.0, 0.6)

renderer.maneuver_plan = plan
renderer.maneuver_preview = preview

print("\n1) die vorgabewerte stehen")
check(hasattr(renderer, 'maneuver_node_hits'), "maneuver_node_hits existiert", "")
check(renderer.maneuver_node_hits == [], "und beginnt leer", "")
check(renderer.maneuver_drag_active is False, "kein zug im gange", "")
check(renderer.maneuver_curve_screen == [], "keine schirmkurve abgelegt", "")

print("\n2) ein zeichendurchgang meldet den knoten ans HUD")
gl.screen.use()
gl.viewport = (0, 0, W, H)
gl.clear(0.0, 0.0, 0.0, 1.0)
renderer.draw_maneuver(camera)
hits = renderer.maneuver_node_hits
check(len(hits) == 1, "ein treffer je knoten", f"{len(hits)}")
if hits:
    hit = hits[0]
    check(math.isfinite(hit['sx']) and math.isfinite(hit['sy']),
          "die schirmposition ist endlich", f"({hit['sx']:.1f}, {hit['sy']:.1f})")
    check(0.0 <= hit['sx'] <= W and 0.0 <= hit['sy'] <= H,
          "und liegt im bild", f"({hit['sx']:.1f}, {hit['sy']:.1f})")
    check(len(hit['handles']) == 4, "vier griffe", f"{len(hit['handles'])}")
    kinds = sorted(h['kind'] for h in hit['handles'])
    check(kinds == ['antinormal', 'normal', 'prograde', 'retrograde'],
          "und zwar die vier erwarteten", f"{kinds}")

print("\n3) die griffe stehen paarweise GEGENUEBER")
# prograde und retrograde muessen entgegengesetzte schirmrichtungen tragen,
# normal und antinormal ebenso. Ein vertauschtes vorzeichen faellt hier auf.
if hits:
    by_kind = {h['kind']: h for h in hits[0]['handles']}
    for a, b in (('prograde', 'retrograde'), ('normal', 'antinormal')):
        dot = (by_kind[a]['dir_sx'] * by_kind[b]['dir_sx']
               + by_kind[a]['dir_sy'] * by_kind[b]['dir_sy'])
        check(dot < -0.999, f"{a} steht {b} gegenueber", f"skalarprodukt {dot:.6f}")
    dot = (by_kind['prograde']['dir_sx'] * by_kind['normal']['dir_sx']
           + by_kind['prograde']['dir_sy'] * by_kind['normal']['dir_sy'])
    check(abs(dot) < 1e-6, "prograde steht senkrecht auf normal",
          f"skalarprodukt {dot:.3e}")
    for handle in hits[0]['handles']:
        length = math.hypot(handle['dir_sx'], handle['dir_sy'])
        check(abs(length - 1.0) < 1e-6, f"{handle['kind']}: einheitsrichtung",
              f"{length:.9f}")

print("\n4) die trefferliste wird JEDEN durchgang geleert")
# Sonst steht ein griff noch im bild, den es nicht mehr gibt -- dieselbe
# regel wie bei Renderer.apsis_marker_hits.
plan.clear()
preview.rebuild(plan, ship, w, predictor, erde, 10.0, 0.6)
renderer.draw_maneuver(camera)
check(renderer.maneuver_node_hits == [],
      "ohne knoten bleibt nichts stehen", f"{len(renderer.maneuver_node_hits)}")

print("\n5) die schirmkurve entsteht NUR waehrend eines zugs")
plan.add(ManeuverNode(t_node, dv_prograde=150.0))
preview.rebuild(plan, ship, w, predictor, erde, 10.0, 0.6)
renderer.draw_maneuver(camera)
check(renderer.maneuver_curve_screen == [],
      "ohne zug wird sie nicht gebaut", f"{len(renderer.maneuver_curve_screen)}")
renderer.maneuver_drag_active = True
renderer.draw_maneuver(camera)
curve = renderer.maneuver_curve_screen
check(len(curve) > 8, "mit zug liegt sie vor", f"{len(curve)} punkte")
if curve:
    check(all(math.isfinite(p[0]) and math.isfinite(p[1]) for p in curve),
          "und ist durchweg endlich", "")
    times = [p[2] for p in curve]
    check(all(times[i] <= times[i + 1] + 1e-9 for i in range(len(times) - 1)),
          "die zeiten laufen vorwaerts", "")
renderer.maneuver_drag_active = False

print("\n6) abgeschaltet wird nichts gemeldet")
renderer.maneuver_enabled = False
renderer.draw_maneuver(camera)
check(renderer.maneuver_node_hits == [], "maneuver_enabled = False schweigt", "")
renderer.maneuver_enabled = True

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    pygame.quit()
    sys.exit(1)
print("render/maneuver: alle pruefungen bestanden")
pygame.quit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_render_test.py`
Expected: FAIL — `AttributeError: 'Renderer' object has no attribute 'maneuver_node_hits'`

- [ ] **Step 3: Write `render/maneuver.py`**

```python
"""Die fuenfte zeichen-domaene: der manoeverplan.

Sie zeichnet drei dinge und meldet EINES:

    - die geplante bahn (die kette aus ship/maneuver/preview.py)
    - je knoten einen marker auf der aktuellen linie
    - je knoten vier ziehgriffe: +/- prograde, +/- normal

Gemeldet wird `renderer.maneuver_node_hits` -- die SCHIRMpositionen von
marker und griffen. Dasselbe muster wie `apsis_marker_hits`, und aus
demselben grund: nur der renderer kennt die zeitabhaengige
frame-transformation, die den marker auf der gezeichneten linie haelt. Ein
HUD-widget, das die position selbst nachrechnete, laege in jedem bewegten
bezugsrahmen daneben -- siehe `.claude/rules/hud-ui.md`.

DIE GRIFFRICHTUNGEN KOMMEN AUS `to_this_frame_vector_xy`, nicht aus einer
differenz zweier transformierter punkte. Ein epsilon-schritt neben einem
ort bei 1.5e11 m verliert sechs stellen, bevor er ueberhaupt gerechnet ist;
der frame kann den vektor exakt.

FARBEN. Sie stehen hier als zahlen, weil der renderer die HUD-palette nicht
kennt -- und sie sind WORTGLEICH zu `ui/theme.py::SCHEME`. Aendert sich das
schema, aendern sich diese drei zeilen mit, sonst traegt der griff an der
linie eine andere farbe als derselbe knopf in der rosette.
"""

import math

import numpy as np

#: = SCHEME[3], gruen -- eingerastet/bereit: der autopilot und seine bahn.
_GREEN = (0.282, 0.851, 0.486)
#: = SCHEME[1], magenta -- die zweite achse: normal/antinormal.
_MAGENTA = (0.851, 0.318, 0.624)
#: = SCHEME[2], amber -- energie: der knoten selbst ist ein brennvorgang.
_AMBER = (0.929, 0.651, 0.235)


class ManeuverDrawMixin:
    """Geplante bahn, knotenmarker und ziehgriffe."""

    # ------------------------------------------------------------ hilfsmittel

    def _maneuver_screen_direction(self, world_dx, world_dy, camera, t_abs):
        """Weltrichtung -> SCHIRMrichtung (einheitsvektor), oder None.

        Zwei schritte: der bezugsrahmen dreht den vektor
        (`to_this_frame_vector_xy`), dann kippt die y-achse -- die welt wird
        top-down gezeichnet (siehe `.claude/rules/rendering.md`). Der
        kamera-massstab faellt beim normieren wieder heraus, er steht hier
        nur der klarheit halber.
        """
        try:
            frame = self._active_frame()
            fx, fy = frame.to_this_frame_vector_xy(
                float(t_abs), float(world_dx), float(world_dy))
        except Exception:
            fx, fy = float(world_dx), float(world_dy)
        sx = fx
        sy = -fy
        length = math.hypot(sx, sy)
        if not math.isfinite(length) or length <= 1e-30:
            return None
        return (sx / length, sy / length)

    def _maneuver_screen_polyline(self, points, camera, camera_frame_xy,
                                  max_points):
        """Eine (n,5)-linie in schirmpunkte, ausgeduennt auf `max_points`."""
        try:
            count = len(points)
        except Exception:
            return []
        if count < 2:
            return []
        stride = max(1, int(math.ceil(count / float(max(2, max_points)))))
        run = []
        for i in range(0, count, stride):
            sx, sy = self._world_to_screen_xy_at_time(
                float(points[i, 0]), float(points[i, 1]), camera,
                float(points[i, 2]), camera_frame_xy)
            if math.isfinite(sx) and math.isfinite(sy):
                run.append((sx, sy, float(points[i, 2])))
        return run

    # ---------------------------------------------------------- frame-einstieg

    def draw_maneuver(self, camera):
        """Den plan zeichnen und seine schirmpositionen melden.

        Die trefferliste wird bei JEDEM aufruf geleert, auch wenn nichts
        gezeichnet wird -- sonst haengt ein griff im bild, den es nicht mehr
        gibt (dieselbe regel wie bei `_draw_apsis_markers`).
        """
        self.maneuver_node_hits = []
        self.maneuver_curve_screen = []
        if not getattr(self, 'maneuver_enabled', True):
            return
        preview = getattr(self, 'maneuver_preview', None)
        if preview is None or not getattr(preview, 'valid', False):
            return

        camera_frame_xy = self._frame_camera_xy(camera)

        # -- die geplante bahn
        points = getattr(preview, 'points', None)
        if points is not None and len(points) >= 2:
            run = self._maneuver_screen_polyline(
                points, camera, camera_frame_xy,
                int(self.maneuver_max_draw_points))
            if len(run) >= 2:
                self._draw_polyline(
                    [(p[0], p[1]) for p in run],
                    (_GREEN[0], _GREEN[1], _GREEN[2],
                     float(self.maneuver_path_alpha)),
                    width=float(self.maneuver_path_width),
                )

        # -- waehrend eines zugs: die BASISlinie in schirmkoordinaten, damit
        #    der marker an ihr entlang geschoben werden kann. Nur dann,
        #    weil sie sonst je frame umsonst gerechnet wuerde.
        if getattr(self, 'maneuver_drag_active', False):
            base = None
            predictor = getattr(self, '_maneuver_predictor', None)
            if predictor is not None:
                try:
                    base = predictor.get_points()
                except Exception:
                    base = None
            if base is not None:
                self.maneuver_curve_screen = self._maneuver_screen_polyline(
                    base, camera, camera_frame_xy,
                    int(self.maneuver_curve_screen_points))

        # -- marker und griffe
        selected = int(getattr(self, 'maneuver_selected_index', 0))
        marker_r = float(self.maneuver_marker_radius_px)
        offset = float(self.maneuver_handle_offset_px)
        handle_r = float(self.maneuver_handle_radius_px)

        for entry in getattr(preview, 'node_markers', ()) or ():
            t_abs = float(entry['t_node'])
            sx, sy = self._world_to_screen_xy_at_time(
                float(entry['x']), float(entry['y']), camera, t_abs,
                camera_frame_xy)
            if not (math.isfinite(sx) and math.isfinite(sy)):
                continue
            if not self._is_on_screen(sx, sy, offset + handle_r + 16.0):
                continue

            active = int(entry['index']) == selected
            self._draw_maneuver_marker(sx, sy, marker_r, active)

            pro = self._maneuver_screen_direction(
                entry['pro_x'], entry['pro_y'], camera, t_abs)
            nrm = self._maneuver_screen_direction(
                entry['nrm_x'], entry['nrm_y'], camera, t_abs)
            if pro is None or nrm is None:
                self.maneuver_node_hits.append({
                    'index': int(entry['index']), 'sx': sx, 'sy': sy,
                    'radius_px': marker_r, 'handles': [],
                })
                continue

            handles = []
            for kind, (dx, dy), color in (
                ('prograde', pro, _GREEN),
                ('retrograde', (-pro[0], -pro[1]), _GREEN),
                ('normal', nrm, _MAGENTA),
                ('antinormal', (-nrm[0], -nrm[1]), _MAGENTA),
            ):
                hx = sx + dx * offset
                hy = sy + dy * offset
                self._draw_maneuver_handle(sx, sy, hx, hy, dx, dy, handle_r,
                                           color, active)
                handles.append({
                    'kind': kind, 'sx': hx, 'sy': hy,
                    'radius_px': handle_r, 'dir_sx': dx, 'dir_sy': dy,
                })

            self.maneuver_node_hits.append({
                'index': int(entry['index']), 'sx': sx, 'sy': sy,
                'radius_px': marker_r, 'handles': handles,
            })

    # ------------------------------------------------------------- die formen

    def _draw_maneuver_marker(self, sx, sy, radius, active):
        """Ein sechseck -- die form, die sonst nichts im bild traegt.

        Die raute gehoert Ap/Pe, der kreis den koerpern, der pfeil dem
        schiff. Ein knoten braucht eine eigene silhouette, sonst ist er auf
        einen blick nicht von einer apsis zu unterscheiden.
        """
        alpha = 1.0 if active else 0.72
        color = (_AMBER[0], _AMBER[1], _AMBER[2], alpha)
        pts = []
        for i in range(7):
            ang = math.pi / 6.0 + i * (math.pi / 3.0)
            pts.append((sx + math.cos(ang) * radius,
                        sy + math.sin(ang) * radius))
        self._draw_polyline(pts, color,
                            width=2.0 if active else 1.4)
        if active:
            inner = []
            for i in range(7):
                ang = math.pi / 6.0 + i * (math.pi / 3.0)
                inner.append((sx + math.cos(ang) * radius * 0.42,
                              sy + math.sin(ang) * radius * 0.42))
            self._draw_polyline(inner, color, width=1.4)

    def _draw_maneuver_handle(self, sx, sy, hx, hy, dx, dy, radius, color,
                              active):
        """Ein stiel vom marker weg und eine pfeilspitze am ende."""
        alpha = 0.95 if active else 0.5
        rgba = (color[0], color[1], color[2], alpha)
        # Der stiel beginnt AUSSERHALB des markers, sonst laeuft er durch
        # dessen sechseck hindurch.
        start_x = sx + dx * (radius * 0.9)
        start_y = sy + dy * (radius * 0.9)
        tip_x = hx + dx * radius
        tip_y = hy + dy * radius
        px, py = -dy, dx
        self._draw_line_segments(
            [(start_x, start_y), (hx, hy),
             (tip_x, tip_y), (hx + px * radius * 0.62, hy + py * radius * 0.62),
             (tip_x, tip_y), (hx - px * radius * 0.62, hy - py * radius * 0.62)],
            rgba, width=2.0 if active else 1.4,
        )
```

- [ ] **Step 4: Mix it into the Renderer**

In `spacesim/render/renderer.py`:

Add the import beside the other domain imports:

```python
from render.maneuver import ManeuverDrawMixin
```

Add it to the base list, after `PredictionDrawMixin`:

```python
class Renderer(
    GLDeviceMixin,
    ShaderPipelineMixin,
    DrawMixin,
    TextMixin,
    BackgroundDrawMixin,
    BodyDrawMixin,
    ShipDrawMixin,
    OrbitDrawMixin,
    PredictionDrawMixin,
    ManeuverDrawMixin,
):
```

In `Renderer.__init__`, directly **after** the existing `self.apsis_marker_hits = []` line, add:

```python
        # -- manoeverknoten (render/maneuver.py) ---------------------------
        #: Vom bootstrap gesetzt; der renderer besitzt sie nicht.
        self.maneuver_plan = None
        self.maneuver_preview = None
        self._maneuver_predictor = None
        self.maneuver_enabled = True
        #: Schirmpositionen fuer das HUD -- je zeichendurchgang geleert und
        #: neu gefuellt, wie apsis_marker_hits.
        self.maneuver_node_hits = []
        #: Die BASISlinie in schirmkoordinaten. Nur waehrend eines zugs
        #: gefuellt (das bauen kostet einen frame-transform je punkt).
        self.maneuver_curve_screen = []
        self.maneuver_drag_active = False
        self.maneuver_selected_index = 0
        #: Weltrichtung des laufenden brennvorgangs, oder None. Der
        #: orientierungs-snap liest sie (render/ship.py).
        self.maneuver_burn_direction = None
        self.maneuver_marker_radius_px = 8.0
        self.maneuver_handle_offset_px = 30.0
        self.maneuver_handle_radius_px = 7.0
        self.maneuver_path_width = 1.8
        self.maneuver_path_alpha = 0.85
        self.maneuver_max_draw_points = 900
        self.maneuver_curve_screen_points = 400
```

In `Renderer.render(...)`, call the draw directly **before** `self._draw_selection_marker(camera)`:

```python
        # Die geplante bahn und ihre griffe NACH dem FXAA-resolve: es sind
        # duenne linien und kleine pfeilspitzen, und ein kantenfilter
        # verschmiert genau die.
        self.draw_maneuver(camera)

        self._draw_selection_marker(camera)
```

- [ ] **Step 5: Feed the renderer its references from bootstrap**

In `spacesim/runtime/bootstrap.py`, directly after `config.apply_to_renderer(app.renderer)`, add:

```python
    # Der renderer BESITZT den plan nicht, er liest ihn. Verweise statt
    # durchreichen durch render(): die signatur traegt schon neun argumente,
    # und der plan aendert sich nicht je frame.
    app.renderer.maneuver_plan = app.maneuver_plan
    app.renderer.maneuver_preview = app.maneuver_preview
    app.renderer._maneuver_predictor = app.predictor
    app.renderer.maneuver_enabled = bool(app.maneuver_config['enabled'])
```

And in `runtime/loop.py`'s `_update_maneuver_preview`, publish the armed direction so the orientation snap can find it — append at the end of that function:

```python
    executor = getattr(app, 'maneuver_executor', None)
    app.renderer.maneuver_burn_direction = (
        (executor.dir_x, executor.dir_y)
        if executor is not None and executor.is_active else None)
    app.renderer.maneuver_selected_index = int(
        getattr(app, 'selected_node_index', 0))
```

- [ ] **Step 6: Add the `'node'` direction to `render/ship.py`**

In `orbital_frame_directions`, replace the `return` statement with:

```python
        directions = apparent_orbital_directions(
            frame, self._frame_time_s, ship.position, ship.velocity, ref_pos,
            points=prediction_points,
        )
        # Die fuenfte richtung: die schubrichtung eines scharfgeschalteten
        # knotens. Sie kommt als WELTvektor herein (der ausfuehrer loest sie
        # einmal auf und haelt sie fest) und wird hier in frame-koordinaten
        # gedreht, damit _apply_orientation_snap sie wie jede andere
        # behandeln kann -- ohne sonderweg fuer den autopiloten.
        burn = getattr(self, 'maneuver_burn_direction', None)
        if burn is not None:
            try:
                fx, fy = frame.to_this_frame_vector_xy(
                    self._frame_time_s, float(burn[0]), float(burn[1]))
                length = math.hypot(fx, fy)
                if length > 1e-30:
                    directions['node'] = Vec2(fx / length, fy / length)
            except Exception:
                pass
        return frame, directions
```

`Vec2` must be importable in that file — if `from physics.vec import Vec2` is not already at the top of `render/ship.py`, add it.

- [ ] **Step 7: Run the tests**

```
python tests/maneuver_render_test.py
python tests/maneuver_execute_test.py
python tests/ui_render_test.py
python tests/ship_scale_test.py
```
Expected: all pass. `ui_render_test.py` and `ship_scale_test.py` are the guards on the renderer files this task touched.

- [ ] **Step 8: Add a working screenshot tool, and look at it**

`tools/hud_shot.py` is **stale** — it still imports `from camera import Camera`, `from loader import ConfigLoader`, `from rendering import Renderer`, `from schiff import schiffcontrol`, all of which moved in the 2026-09-03 restructure, and it only draws the HUD without the world. Create `spacesim/tools/game_shot.py` instead — a real frame of the game, world and HUD together, at any size:

```python
"""Ein echter frame des SPIELS (welt + HUD) als PNG.

`hud_shot.py` zeichnet nur das HUD und benutzt die flache modulaufteilung
von vor der umstrukturierung. Dieses hier faehrt `runtime/bootstrap.py`
hoch, laeuft N frames ohne ereignisse und liest den framebuffer VOR
present() -- also genau das, was im fenster stuende.

    python tools/game_shot.py [breite hoehe] [-o datei.png] [--frames N]
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPACESIM = os.path.dirname(HERE)
sys.path.insert(0, SPACESIM)
os.chdir(SPACESIM)
os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS', 'permonitorv2')

parser = argparse.ArgumentParser()
parser.add_argument('width', nargs='?', type=int, default=1920)
parser.add_argument('height', nargs='?', type=int, default=1080)
parser.add_argument('-o', '--out', default=None)
parser.add_argument('--frames', type=int, default=90)
args = parser.parse_args()

W, H = args.width, args.height

with open(os.path.join(SPACESIM, 'config', 'config.json'), 'r',
          encoding='utf-8-sig') as fh:
    cfg = json.load(fh)
cfg['window']['width'] = W
cfg['window']['height'] = H
cfg['window']['vsync'] = False
cfg['debug']['print_frame_timings'] = False
cfg['debug']['print_loader_info'] = False
tmp_cfg = os.path.join(tempfile.gettempdir(), 'spacesim_shot_config.json')
with open(tmp_cfg, 'w', encoding='utf-8') as fh:
    json.dump(cfg, fh)
os.environ['SPACESIM_CONFIG'] = tmp_cfg

import numpy as np
import pygame

from runtime.bootstrap import build_app, load_config

app = build_app(load_config())
gl = app.window.ctx
frame_dt = 1.0 / 60.0

for i in range(max(1, args.frames)):
    pygame.event.pump()
    if app.hud is not None:
        app.hud.update()
    app.ui_root.begin_frame(frame_dt)
    # devui wird BEWUSST uebersprungen: ohne die passende
    # new_frame/render-paarung wirft ImGui beim zweiten frame ein
    # IM_ASSERT, und fuer einen abzug wird es nicht gebraucht.
    app.world.step(app.camera.sim_dt * app.tick_rate * frame_dt, app.max_substep)
    app.camera.update(frame_dt, ui_wants_keyboard=False)
    if app.predictor.num_points > 0 and app.ship is not None:
        app.predictor.set_hold(not app.thrust_allowed())
        app.predictor.set_view_scale(app.camera.target_scale)
        app.predictor.update(app.ship, app.world)
    app.renderer.render(
        app.world.body, app.camera, app.predictor.get_points(),
        predictor=app.predictor, sim_time=app.world.time,
        reference_body=app.ui_state.reference_body,
        ship_control=app.ship_control, real_dt=frame_dt,
        selected_body=app.ui_state.selected_body,
    )
    app.ui_root.render()
    if i < args.frames - 1:
        app.renderer.present()

data = gl.screen.read(viewport=(0, 0, W, H), components=3, dtype='f1')
frame = np.frombuffer(data, dtype=np.uint8).reshape(H, W, 3)[::-1]
out = args.out or os.path.join(
    os.path.dirname(SPACESIM), 'screenshots for debugging', 'game_current.png')
pygame.image.save(pygame.surfarray.make_surface(frame.transpose(1, 0, 2)), out)
print('geschrieben:', out, f'({W}x{H})')
app.window.close()
```

Then:

```
SPACESIM_MAX_FRAMES=300 python main.py
```
Press `N` once and confirm the hexagon sits on the line with four arrows radiating from it, then take the reference shot the HUD work in Task 8 builds on:

```
python tools/game_shot.py 1920 1080 --frames 120
```

- [ ] **Step 9: Commit**

```bash
cd spacesim
git add render/maneuver.py render/renderer.py render/ship.py runtime/bootstrap.py runtime/loop.py tools/game_shot.py tests/maneuver_render_test.py
git commit -m "feat(maneuver): draw the planned path, node markers and drag handles

Fifth render domain. Screen positions are published as maneuver_node_hits
so the HUD hit-tests what was actually drawn, the apsis_marker_hits
pattern. Handle directions come from to_this_frame_vector_xy, not from an
epsilon difference.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 8: The MANEUVER block, docked to the navball

**Files:**
- Create: `spacesim/ui/hud/maneuver.py`
- Modify: `spacesim/ui/theme.py`
- Modify: `spacesim/ui/hud/attitude.py`
- Modify: `spacesim/ui/hud/controls.py`
- Modify: `spacesim/ui/hud/telemetry.py`
- Modify: `spacesim/ui/hud/layout.py`
- Modify: `spacesim/ui/hud/__init__.py`
- Modify: `spacesim/config/config.json`, `spacesim/config/loader.py`
- Modify: `spacesim/runtime/bootstrap.py`
- Test: `spacesim/tests/maneuver_hud_test.py`

**Interfaces:**
- Consumes: `ManeuverPlan`, `ManeuverPreview`, `ManeuverExecutor` (Tasks 2, 4, 5); `renderer.maneuver_node_hits` (Task 7); `chrome.frame/plate/tab/tab_text`, `controls._button_colors`, `ui.units.delta_v/duration/countdown`.
- Produces:
  - `ui.theme.ROLE_INDEX['node'] = 2`, `ROLE_INDEX['node_path'] = 3`
  - `ui.hud.maneuver.ManeuverBlock(telemetry, **kwargs)` with class constants `WIDTH`, `HEIGHT` and methods `_regions(ctx) -> dict[str, tuple]`, `execute_enabled() -> bool`
  - `Telemetry` fields `maneuver_count`, `maneuver_max`, `maneuver_selected`, `maneuver_node`, `maneuver_dv_prograde`, `maneuver_dv_normal`, `maneuver_dv_total`, `maneuver_burn_seconds`, `maneuver_time_to_node`, `maneuver_time_to_ignition`, `maneuver_state`, `maneuver_can_arm`
  - `Telemetry.adjust_node_dv(axis, amount)`, `Telemetry.select_node(index)`, `Telemetry.add_node()`, `Telemetry.delete_node()`, `Telemetry.toggle_execute()`
  - `Hud.maneuver` — the block instance
  - `Hud.__init__` gains `maneuver_plan=None, maneuver_preview=None, maneuver_executor=None, maneuver_selected_get=None, maneuver_selected_set=None, maneuver_add=None, maneuver_delete=None, maneuver_execute=None, maneuver_dv_step_fine=1.0, maneuver_dv_step_coarse=10.0`

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/maneuver_hud_test.py`:

```python
"""Der MANEUVER-block am navball.

Drei ebenen, wie in `ui_hud_test.py`:

1. **Lage** -- der block liegt im bild und ueberlappt weder den
   navball-block noch die snap-rosette, in jeder gepruefen fenstergroesse.
2. **Sperre** -- der EXECUTE-knopf ist abgeblendet, solange der knoten kein
   delta-v traegt. Ein knoten ohne delta-v ist ein PLATZHALTER, und ein
   knopf, der dann etwas ausloest, waere eine luege.
3. **Wirkung** -- ein klick auf einen schrittknopf aendert wirklich das
   delta-v des knotens und zaehlt plan.version hoch. Ohne den zaehler
   bliebe die gezeichnete linie auf dem alten stand.

Aufruf: python tests/maneuver_hud_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS', 'permonitorv2')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import moderngl
import pygame
from pygame.locals import DOUBLEBUF, OPENGL

W, H = 1600, 900
FAILURES = []


def check(condition, label, detail=''):
    status = 'OK  ' if condition else 'FEHL'
    print(f"  [{status}] {label}" + (f"  ({detail})" if detail else ''))
    if not condition:
        FAILURES.append(label)


pygame.display.init()
pygame.font.init()
pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
gl = moderngl.create_context()
gl.enable(moderngl.BLEND)
gl.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

from config.loader import ConfigLoader
from physics.vec import G
from physics.world import world as World
from render.renderer import Renderer
from runtime.system_loader import SystemLoader
from ship.camera import Camera
from ship.control import schiffcontrol
from ship.maneuver import (
    ManeuverExecutor,
    ManeuverNode,
    ManeuverPlan,
    ManeuverPreview,
)
from ship.predictor import Predictor
from ui import UIContext, UIRoot, UIState
from ui.hud import Hud
from ui.hud.navball import WIDTH as NAVBALL_WIDTH

config = ConfigLoader(None)
config.load()
bodies = SystemLoader("solar_system.json").load()
world = World(G)
world.body = bodies
config.apply_to_world(world)
world.update_planets(0.0)
sim_ship = next(b for b in bodies if b.is_ship)
earth = next(b for b in bodies if b.name == "Erde")
control = schiffcontrol(sim_ship)
config.apply_to_ship_control(control)

mu = world.G * earth.mass
r = float(getattr(earth, 'radius', 6.371e6)) + 4.0e6
ahead = earth.position_at_time(1.0)
behind = earth.position_at_time(-1.0)
sim_ship.position.x = earth.position.x + r
sim_ship.position.y = earth.position.y
sim_ship.velocity.x = (float(ahead.x) - float(behind.x)) / 2.0
sim_ship.velocity.y = (float(ahead.y) - float(behind.y)) / 2.0 + math.sqrt(mu / r)

camera = Camera(None, W, H)
config.apply_to_camera(camera)
camera.follow(sim_ship)
camera.snap_to_targets()
renderer = Renderer(W, H, enable_fxaa=False, ctx=gl)
config.apply_to_renderer(renderer)
predictor = Predictor(recompute_every_update=True, **config.predictor_kwargs())
config.apply_to_predictor(predictor)
predictor.async_compute = False
predictor.initialize(sim_ship, world)
predictor.update(sim_ship, world)

mc = config.maneuver_kwargs()
plan = ManeuverPlan(max_nodes=mc['max_nodes'],
                    min_executable_dv=mc['min_executable_dv'])
preview = ManeuverPreview(max_points=mc['preview_max_points'])
executor = ManeuverExecutor(plan, sim_ship, control,
                            thrust_acc_max=600.0, realtime_warp_max=60.0)
selected = [0]

state = UIState(world.body, initial_reference_index=world.body.index(earth))
ui = UIContext(gl, W, H, ui_scale=renderer.ui_scale)
root = UIRoot(ui)
hud = Hud(root, world, sim_ship, control, camera, renderer, predictor, state,
          maneuver_plan=plan, maneuver_preview=preview,
          maneuver_executor=executor,
          maneuver_selected_get=lambda: selected[0],
          maneuver_selected_set=lambda i: selected.__setitem__(0, int(i)),
          maneuver_dv_step_fine=mc['dv_step_fine'],
          maneuver_dv_step_coarse=mc['dv_step_coarse'])


def frame():
    hud.update()
    root.begin_frame(1.0 / 60.0)


def click(x, y):
    """Einen vollstaendigen klick auf den widget-baum schicken."""
    root.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {'pos': (x, y), 'button': 1}))
    root.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONUP, {'pos': (x, y), 'button': 1}))


frame()

print("\n1) der block existiert und haengt LINKS am navball")
check(getattr(hud, 'maneuver', None) is not None, "hud.maneuver existiert", "")
block = hud.maneuver
check(block.rect.w > 0 and block.rect.h > 0, "er hat ein rechteck",
      f"{block.rect.w:.0f}x{block.rect.h:.0f}")
check(block.rect.right <= hud.navball.rect.left + 1.0,
      "er liegt links vom navball-block",
      f"block.right={block.rect.right:.0f}, navball.left={hud.navball.rect.left:.0f}")
check(hud.snaps.rect.left >= hud.navball.rect.right - 1.0,
      "die rosette liegt weiterhin rechts davon", "")

print("\n2) lage in drei fenstergroessen")
for width, height in ((1280, 800), (1600, 900), (1920, 1080)):
    root.resize(width, height, ui_scale=renderer.ui_scale)
    frame()
    b = hud.maneuver
    if not b.visible:
        check(True, f"{width}x{height}: block ausgeblendet (schmale fassung)", "")
        continue
    inside = (b.rect.left >= 0 and b.rect.top >= 0
              and b.rect.right <= width and b.rect.bottom <= height)
    check(inside, f"{width}x{height}: vollstaendig im bild",
          f"({b.rect.left:.0f},{b.rect.top:.0f})-({b.rect.right:.0f},{b.rect.bottom:.0f})")
    n = hud.navball.rect
    overlap = not (b.rect.right <= n.left or b.rect.left >= n.right
                   or b.rect.bottom <= n.top or b.rect.top >= n.bottom)
    check(not overlap, f"{width}x{height}: keine ueberlappung mit dem navball", "")
root.resize(W, H, ui_scale=renderer.ui_scale)
frame()

print("\n3) SPERRE -- ohne delta-v ist EXECUTE abgeblendet")
check(block.execute_enabled() is False, "ohne knoten: gesperrt", "")
node = ManeuverNode(world.time + 1800.0)
plan.add(node)
frame()
check(len(plan) == 1, "ein knoten liegt vor", "")
check(block.execute_enabled() is False,
      "knoten OHNE delta-v: weiterhin gesperrt", f"dv={node.dv_total}")
node.dv_prograde = 50.0
plan.touch()
frame()
check(block.execute_enabled() is True, "mit delta-v: frei", f"dv={node.dv_total}")
node.dv_prograde = 0.0
plan.touch()
frame()
check(block.execute_enabled() is False, "und wieder gesperrt, wenn es weg ist", "")

print("\n4) WIRKUNG -- die schrittknoepfe verstellen den knoten")
regions = block._regions(ui)
before_version = plan.version
x, y, w, h = regions['pro_plus_coarse']
click(x + w * 0.5, y + h * 0.5)
frame()
check(abs(node.dv_prograde - mc['dv_step_coarse']) < 1e-9,
      "grosser schritt prograde", f"{node.dv_prograde}")
check(plan.version > before_version, "und plan.version zaehlt hoch",
      f"{before_version} -> {plan.version}")

x, y, w, h = regions['pro_minus_fine']
click(x + w * 0.5, y + h * 0.5)
frame()
check(abs(node.dv_prograde - (mc['dv_step_coarse'] - mc['dv_step_fine'])) < 1e-9,
      "kleiner schritt zurueck", f"{node.dv_prograde}")

x, y, w, h = regions['nrm_plus_fine']
click(x + w * 0.5, y + h * 0.5)
frame()
check(abs(node.dv_normal - mc['dv_step_fine']) < 1e-9,
      "kleiner schritt normal", f"{node.dv_normal}")

print("\n5) die pips waehlen den knoten")
plan.add(ManeuverNode(world.time + 3600.0, dv_prograde=10.0))
frame()
regions = block._regions(ui)
x, y, w, h = regions['pip_1']
click(x + w * 0.5, y + h * 0.5)
frame()
check(selected[0] == 1, "der zweite pip waehlt knoten 1", f"{selected[0]}")
check(hud.telemetry.maneuver_node is plan.nodes[1],
      "die telemetrie zeigt jetzt auf ihn", "")

print("\n6) der block verbraucht die maus nur ueber sich selbst")
# Sonst schwenkt ein klick daneben nicht mehr die kamera.
check(block.hit_test(ui, block.rect.center_x, block.rect.center_y) is not None,
      "ein klick auf den block trifft ihn", "")
outside_x = block.rect.left - 40.0
check(root._pick(outside_x, block.rect.center_y) is not block,
      "ein klick daneben nicht", "")

print("\n7) der ring bekommt einen fuenften marker, sobald scharf ist")
from ui.hud.attitude import _MARKER_ORDER
check(any(entry[0] == 'node' for entry in _MARKER_ORDER),
      "'node' steht in _MARKER_ORDER", f"{[e[0] for e in _MARKER_ORDER]}")
node.dv_prograde = 60.0
plan.touch()
preview.rebuild(plan, sim_ship, world, predictor, earth,
                executor.a_max_sim(), mc['ramp_seconds'])
armed = executor.arm(world, earth, preview)
check(armed, "der knoten laesst sich scharfschalten", "")
renderer.maneuver_burn_direction = (executor.dir_x, executor.dir_y)
frame()
check('node' in hud.telemetry.marker_headings,
      "die telemetrie liefert seinen kurs",
      f"{sorted(hud.telemetry.marker_headings)}")
executor.abort('test')
renderer.maneuver_burn_direction = None

print("\n8) unter dem umbruch verschwindet der block")
root.resize(700, 640, ui_scale=renderer.ui_scale)
frame()
check(hud.maneuver.visible is False,
      "schmale fassung: ausgeblendet (die tasten N/X bleiben)",
      f"visible={hud.maneuver.visible}")
root.resize(W, H, ui_scale=renderer.ui_scale)
frame()
check(hud.maneuver.visible is True, "breite fassung: wieder da", "")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  {failure}")
    pygame.quit()
    sys.exit(1)
print("ui/hud/maneuver: alle pruefungen bestanden")
pygame.quit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/maneuver_hud_test.py`
Expected: FAIL — `TypeError: Hud.__init__() got an unexpected keyword argument 'maneuver_plan'`

- [ ] **Step 3: Two more config keys**

In `config/config.json`, add to the `"maneuver"` block:

```json
    "dv_step_fine": 1.0,
    "dv_step_coarse": 10.0,
```

In `config/loader.py`'s `maneuver_kwargs()`, add to the returned dict:

```python
            'dv_step_fine': float(self.get('maneuver.dv_step_fine', 1.0)),
            'dv_step_coarse': float(self.get('maneuver.dv_step_coarse', 10.0)),
```

- [ ] **Step 4: Two palette roles**

In `ui/theme.py`, add to `ROLE_INDEX` — **no new colour**, both map onto the existing four:

```python
    'node': 2,        # manoeverknoten: ein brennvorgang, also energie
    'node_path': 3,   # die geplante bahn: das versprechen des autopiloten
```

- [ ] **Step 5: The fifth ring marker**

In `ui/hud/attitude.py`, extend `_MARKER_ORDER`:

```python
_MARKER_ORDER = (
    ('prograde', 'PRO', 'velocity'),
    ('retrograde', 'RETRO', 'velocity'),
    ('normal_in', 'NORM', 'normal'),
    ('antinormal_out', 'ANTI', 'normal'),
    # Die schubrichtung eines scharfgeschalteten knotens. Sie erscheint nur,
    # wenn wirklich einer scharf ist -- `marker_headings` traegt den
    # schluessel sonst gar nicht, und _draw_markers ueberspringt ihn dann.
    ('node', 'NODE', 'node'),
)
```

and give it a glyph — in `_draw_marker_glyph`, before the final `else:` branch:

```python
        elif key == 'node':
            # Dasselbe sechseck wie der marker an der linie
            # (render/maneuver.py::_draw_maneuver_marker) -- eine form, eine
            # bedeutung, an beiden orten.
            pts = []
            for i in range(7):
                ang = math.pi / 6.0 + i * (math.pi / 3.0)
                pts.append((x + math.cos(ang) * radius * 0.55,
                            y + math.sin(ang) * radius * 0.55))
            for i in range(6):
                ctx.draw.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                              color, width=max(1.0, 1.4 * scale), cap='round')
```

- [ ] **Step 6: The rosette tab must say NODE**

In `ui/hud/controls.py`, inside `SnapRosette.draw`, replace the label lookup:

```python
        if not self.compact:
            if active_mode == 'node':
                # Der autopilot haelt den kurs, nicht der spieler -- und
                # 'FREE' waere hier schlicht falsch.
                label = 'NODE'
            else:
                label = (dict((m, l) for m, l, _c, _r in self.MODES).get(active_mode)
                         if active_mode else 'FREE')
            chrome.tab(ctx, chrome.tab_text('SNAP', label),
                       cx, cy + span * 0.5,
                       color=palette.snap if active_mode else palette.text_dim,
                       align='center', edge='bottom')
```

- [ ] **Step 7: Telemetry sampling**

In `ui/hud/telemetry.py`, extend `Telemetry.__init__`'s signature with the maneuver bindings (add after `tick_rate=60.0`):

```python
                 maneuver_plan=None, maneuver_preview=None,
                 maneuver_executor=None, maneuver_selected_get=None,
                 maneuver_selected_set=None, maneuver_add=None,
                 maneuver_delete=None, maneuver_execute=None,
                 maneuver_dv_step_fine=1.0, maneuver_dv_step_coarse=10.0,
```

and in the body, after the existing `self.thrust_level = 1.0`:

```python
        # -- manoeverknoten -------------------------------------------------
        # Die telemetrie BESITZT nichts davon; sie liest den plan und reicht
        # die drei aktionen weiter. Dieselbe regel wie beim horizont-regler:
        # das HUD ruft closures, die die hauptschleife gebaut hat, damit
        # tastatur und knopf denselben weg nehmen.
        self.maneuver_plan = maneuver_plan
        self.maneuver_preview = maneuver_preview
        self.maneuver_executor = maneuver_executor
        self._maneuver_selected_get = maneuver_selected_get
        self._maneuver_selected_set = maneuver_selected_set
        self._maneuver_add = maneuver_add
        self._maneuver_delete = maneuver_delete
        self._maneuver_execute = maneuver_execute
        self.maneuver_dv_step_fine = float(maneuver_dv_step_fine)
        self.maneuver_dv_step_coarse = float(maneuver_dv_step_coarse)

        self.maneuver_count = 0
        self.maneuver_max = 0
        self.maneuver_selected = 0
        self.maneuver_node = None
        self.maneuver_dv_prograde = 0.0
        self.maneuver_dv_normal = 0.0
        self.maneuver_dv_total = 0.0
        self.maneuver_burn_seconds = None
        self.maneuver_time_to_node = None
        self.maneuver_time_to_ignition = None
        self.maneuver_state = 'idle'
        self.maneuver_can_arm = False
```

Add `self._sample_maneuver()` as the last call inside `sample()`, and the method itself:

```python
    def _sample_maneuver(self):
        """Alles, was der MANEUVER-block je frame zeigt -- einmal gelesen.

        Brenndauer und zuendzeitpunkt werden hier NICHT gerechnet, sondern
        von `BurnProfile` geholt. Eine zweite rechnung im HUD waere genau
        die zweite wahrheit, die ship/maneuver/profile.py verhindern soll.
        """
        plan = self.maneuver_plan
        executor = self.maneuver_executor
        self.maneuver_state = (getattr(executor, 'state', 'idle')
                               if executor is not None else 'idle')
        self.maneuver_can_arm = bool(
            executor is not None and executor.can_arm())

        if plan is None:
            self.maneuver_count = 0
            self.maneuver_max = 0
            self.maneuver_node = None
            return

        self.maneuver_count = len(plan)
        self.maneuver_max = int(getattr(plan, 'max_nodes', 5))

        index = 0
        if self._maneuver_selected_get is not None:
            try:
                index = int(self._maneuver_selected_get())
            except Exception:
                index = 0
        index = max(0, min(index, self.maneuver_count - 1)) if self.maneuver_count else 0
        self.maneuver_selected = index

        node = plan.nodes[index] if self.maneuver_count else None
        self.maneuver_node = node
        if node is None:
            self.maneuver_dv_prograde = 0.0
            self.maneuver_dv_normal = 0.0
            self.maneuver_dv_total = 0.0
            self.maneuver_burn_seconds = None
            self.maneuver_time_to_node = None
            self.maneuver_time_to_ignition = None
            return

        self.maneuver_dv_prograde = float(node.dv_prograde)
        self.maneuver_dv_normal = float(node.dv_normal)
        self.maneuver_dv_total = float(node.dv_total)

        now = float(getattr(self.world, 'time', 0.0))
        self.maneuver_time_to_node = float(node.t_node) - now
        if executor is not None and self.maneuver_dv_total > 0.0:
            profile = node.profile(executor.a_max_sim(), executor.ramp_seconds)
            self.maneuver_burn_seconds = profile.total_time
            self.maneuver_time_to_ignition = profile.ignition_time(node.t_node) - now
        else:
            self.maneuver_burn_seconds = None
            self.maneuver_time_to_ignition = None

    # -- die fuenf aktionen des MANEUVER-blocks ---------------------------

    def adjust_node_dv(self, axis, amount):
        """`axis` ist 'prograde' oder 'normal'. Zaehlt plan.version hoch."""
        node = self.maneuver_node
        if node is None or self.maneuver_plan is None:
            return False
        if axis == 'prograde':
            node.dv_prograde = float(node.dv_prograde) + float(amount)
        elif axis == 'normal':
            node.dv_normal = float(node.dv_normal) + float(amount)
        else:
            return False
        # OHNE touch() bliebe die gezeichnete linie auf dem alten stand --
        # die vorschau rechnet nur bei geaenderter version neu.
        self.maneuver_plan.touch()
        return True

    def select_node(self, index):
        if self._maneuver_selected_set is None:
            return False
        self._maneuver_selected_set(int(index))
        return True

    def add_node(self):
        if self._maneuver_add is None:
            return False
        self._maneuver_add()
        return True

    def delete_node(self):
        if self._maneuver_delete is None:
            return False
        self._maneuver_delete()
        return True

    def toggle_execute(self):
        if self._maneuver_execute is None:
            return False
        self._maneuver_execute()
        return True
```

- [ ] **Step 8: Write `ui/hud/maneuver.py`**

```python
"""Der MANEUVER-block -- angedockt an die LINKE flanke des navball-blocks.

WARUM DORT. Rechts vom navball haengt die snap-rosette; links stand nichts.
Der block spiegelt sie: derselbe dock-abstand, dieselbe verankerung an der
unteren bildmitte, ein notch-tab auf der unterkante. Die untere bildmitte
liest sich damit als EINE instrumentenreihe -- manoever, kurs, rastung --
statt als navball mit einem anhaengsel. Nebenbei richtet er die
komposition auf: bisher hing alles rechts.

EIN WIDGET, KEIN STAPEL. Genau wie `NavballCluster` zeichnet der block alle
seine teile selbst und haelt seine trefferflaechen in `_regions()`. Als
kinder waeren es wieder einzelne kaesten -- und die verdichtung ist der
ganze punkt dieser oberflaeche.

`_regions()` ist die EINZIGE geometriequelle: zeichnen und treffertest
lesen dasselbe woerterbuch. Zwei rechnungen waeren zwei layouts, und der
knopf laege irgendwann neben seiner eigenen flaeche.

DER EXECUTE-KNOPF IST GESPERRT, SOLANGE DER KNOTEN KEIN DELTA-V TRAEGT.
Ein frischer knoten ist ein platzhalter: man setzt ihn an eine stelle der
bahn und entscheidet erst danach, was dort geschehen soll. Ein knopf, der
in diesem zustand etwas ausloeste, waere eine luege -- und
`ManeuverExecutor.arm()` lehnt ohnehin ab, die sperre ist also die
SICHTBARE haelfte einer regel, die zweimal gilt.

Farben: prograde gruen, normal magenta -- dieselben, die die rosette den
beiden achsen gibt (`controls.SnapRosette.MODES`) und die griffe an der
linie tragen (`render/maneuver.py`). Delta-v, brenndauer und countdown in
amber, weil ein brennvorgang energie ist. Nichts davon ist eine neue farbe.

KOORDINATEN top-down, MASSE in design-einheiten.
"""

import math

from .. import units
from ..core import Widget
from ..theme import with_alpha
from . import chrome
from .controls import _button_colors

# Alle masse in DESIGN-EINHEITEN (siehe .claude/rules/hud-ui.md).
WIDTH = 176.0
HEIGHT = 206.0

_PAD = 10.0
_GAP = 6.0
_PIP_H = 12.0
_PIP_GAP = 3.0
_ROW_H = 22.0
_LINE_H = 16.0
_EXEC_H = 26.0
_FOOT_H = 18.0
#: Breite eines der vier schrittknoepfe je achse.
_STEP_W = 15.0
_STEP_GAP = 2.0

#: Die vier achsen-schrittknoepfe je zeile, als (name, faktor, beschriftung).
#: Doppelpfeil = grober schritt. Zwei groessen statt eines modifikators:
#: das HUD sieht keine umschalttaste, und ein zweiter knopf ist ehrlicher
#: als eine unsichtbare regel.
_STEPPERS = (
    ('minus_coarse', -1.0, True, '◀◀'),
    ('minus_fine', -1.0, False, '◀'),
    ('plus_fine', +1.0, False, '▶'),
    ('plus_coarse', +1.0, True, '▶▶'),
)


class ManeuverBlock(Widget):
    """Knotenwahl, die beiden delta-v-achsen, die brenndaten, EXECUTE."""

    WIDTH = WIDTH
    HEIGHT = HEIGHT

    def __init__(self, telemetry, **kwargs):
        kwargs.setdefault('size', (WIDTH, HEIGHT))
        super().__init__(**kwargs)
        self.telemetry = telemetry
        # Der block faengt die maus ab: er sitzt ueber der bahn, und ein
        # klick, der zwischen zwei knoepfen durchfaellt, wuerde die kamera
        # darunter schwenken.
        self.blocks_mouse = True
        self._hover_key = None

    # ------------------------------------------------------------ geometrie

    def measure(self, ctx):
        return (ctx.px(WIDTH), ctx.px(HEIGHT))

    def _regions(self, ctx):
        """Alle trefferflaechen, in top-down bildschirmpixeln.

        EINE quelle fuer zeichnen und treffertest -- siehe modulkopf.
        """
        pad = ctx.px(_PAD)
        gap = ctx.px(_GAP)
        x = self.rect.x + pad
        w = self.rect.w - pad * 2.0
        y = self.rect.y + pad

        regions = {}

        # -- knotenwahl: bis zu max_nodes pips nebeneinander
        count = max(1, int(getattr(self.telemetry, 'maneuver_max', 5)))
        pip_gap = ctx.px(_PIP_GAP)
        pip_w = (w - pip_gap * (count - 1)) / float(count)
        pip_h = ctx.px(_PIP_H)
        for i in range(count):
            regions[f'pip_{i}'] = (x + i * (pip_w + pip_gap), y, pip_w, pip_h)
        y += pip_h + gap

        # -- die beiden achsen
        row_h = ctx.px(_ROW_H)
        step_w = ctx.px(_STEP_W)
        step_gap = ctx.px(_STEP_GAP)
        for prefix in ('pro', 'nrm'):
            left = x
            for index, (name, _sign, _coarse, _glyph) in enumerate(_STEPPERS[:2]):
                regions[f'{prefix}_{name}'] = (
                    left + index * (step_w + step_gap), y, step_w, row_h)
            right = x + w
            for index, (name, _sign, _coarse, _glyph) in enumerate(_STEPPERS[2:]):
                regions[f'{prefix}_{name}'] = (
                    right - (2 - index) * (step_w + step_gap) + step_gap,
                    y, step_w, row_h)
            inner_l = x + 2.0 * (step_w + step_gap)
            inner_r = x + w - 2.0 * (step_w + step_gap)
            regions[f'{prefix}_value'] = (inner_l, y, inner_r - inner_l, row_h)
            y += row_h + ctx.px(4.0)

        y += gap
        regions['divider'] = (x, y, w, 1.0)
        y += gap

        # -- die drei abgeleiteten werte
        line_h = ctx.px(_LINE_H)
        for key in ('dv_total', 'burn', 'countdown'):
            regions[key] = (x, y, w, line_h)
            y += line_h + ctx.px(2.0)

        y += gap - ctx.px(2.0)
        exec_h = ctx.px(_EXEC_H)
        regions['execute'] = (x, y, w, exec_h)
        y += exec_h + ctx.px(4.0)

        foot_h = ctx.px(_FOOT_H)
        half = (w - ctx.px(4.0)) * 0.5
        regions['add'] = (x, y, half, foot_h)
        regions['delete'] = (x + half + ctx.px(4.0), y, half, foot_h)
        return regions

    # -------------------------------------------------------------- zustand

    def execute_enabled(self):
        """Darf EXECUTE gedrueckt werden?

        Nur mit einem knoten, der wirklich delta-v traegt. Waehrend eines
        laufenden manoevers ist der knopf ebenfalls aktiv -- er heisst dann
        ABORT.
        """
        telemetry = self.telemetry
        executor = getattr(telemetry, 'maneuver_executor', None)
        if executor is not None and executor.is_active:
            return True
        return bool(getattr(telemetry, 'maneuver_can_arm', False))

    def _hit(self, ctx, x, y):
        for key, (rx, ry, rw, rh) in self._regions(ctx).items():
            if key == 'divider' or key.endswith('_value'):
                continue
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return key
        return None

    # -------------------------------------------------------------- eingabe

    def on_mouse_move(self, ctx, x, y):
        self._hover_key = self._hit(ctx, x, y)
        return True

    def on_mouse_up(self, ctx, x, y, button):
        if button != 1:
            return True
        key = self._hit(ctx, x, y)
        if key is None:
            return True
        telemetry = self.telemetry

        if key.startswith('pip_'):
            telemetry.select_node(int(key.split('_')[1]))
            return True
        if key == 'add':
            telemetry.add_node()
            return True
        if key == 'delete':
            telemetry.delete_node()
            return True
        if key == 'execute':
            if self.execute_enabled():
                telemetry.toggle_execute()
            return True

        for prefix, axis in (('pro', 'prograde'), ('nrm', 'normal')):
            for name, sign, coarse, _glyph in _STEPPERS:
                if key == f'{prefix}_{name}':
                    step = (telemetry.maneuver_dv_step_coarse if coarse
                            else telemetry.maneuver_dv_step_fine)
                    telemetry.adjust_node_dv(axis, sign * step)
                    return True
        return True

    # -------------------------------------------------------------- zeichnen

    def draw(self, ctx):
        palette = ctx.theme.palette
        telemetry = self.telemetry
        regions = self._regions(ctx)
        active = getattr(telemetry, 'maneuver_state', 'idle') in ('armed', 'burning')

        chrome.frame(ctx, self.rect.x, self.rect.y, self.rect.w, self.rect.h,
                     cut=WIDTH * 0.13,
                     glow_role='node' if active else 'frame')

        self._draw_pips(ctx, regions)
        self._draw_axis(ctx, regions, 'pro', 'PRO',
                        telemetry.maneuver_dv_prograde, palette.snap)
        self._draw_axis(ctx, regions, 'nrm', 'NRM',
                        telemetry.maneuver_dv_normal, palette.normal)

        dx, dy, dw, _dh = regions['divider']
        ctx.draw.line(dx, dy, dx + dw, dy, palette.divider,
                      width=max(1.0, ctx.px(1.0)))

        self._draw_line(ctx, regions['dv_total'], 'DV',
                        units.delta_v(telemetry.maneuver_dv_total),
                        palette.node)
        self._draw_line(ctx, regions['burn'], 'BURN',
                        units.duration(telemetry.maneuver_burn_seconds),
                        palette.node)
        # Solange nichts scharf ist, zaehlt der countdown auf den KNOTEN;
        # scharf zaehlt er auf die ZUENDUNG. Das ist der zeitpunkt, auf den
        # es dann ankommt -- eine halbe brenndauer frueher.
        countdown = (telemetry.maneuver_time_to_ignition if active
                     else telemetry.maneuver_time_to_node)
        self._draw_line(ctx, regions['countdown'], 'IGN' if active else 'NODE',
                        units.countdown(countdown), palette.node)

        self._draw_execute(ctx, regions['execute'], active)
        self._draw_foot(ctx, regions)

        chrome.tab(ctx, chrome.tab_text('MANEUVER'),
                   self.rect.center_x, self.rect.bottom,
                   color=palette.node if active else palette.text_dim,
                   align='center', edge='bottom')

    def _draw_pips(self, ctx, regions):
        palette = ctx.theme.palette
        count = int(getattr(self.telemetry, 'maneuver_count', 0))
        selected = int(getattr(self.telemetry, 'maneuver_selected', 0))
        total = int(getattr(self.telemetry, 'maneuver_max', 5))
        for i in range(total):
            rect = regions.get(f'pip_{i}')
            if rect is None:
                continue
            x, y, w, h = rect
            filled = i < count
            is_selected = filled and i == selected
            hover = 1.0 if self._hover_key == f'pip_{i}' else 0.0
            if filled:
                fill, _text, border = _button_colors(
                    ctx, is_selected, palette.node, hover)
            else:
                fill, border = palette.disabled, palette.edge_inner
            chrome.plate(ctx, x, y, w, h, fill=fill, line=border, cut=3.0)

    def _draw_axis(self, ctx, regions, prefix, label, value, color):
        palette = ctx.theme.palette
        enabled = getattr(self.telemetry, 'maneuver_node', None) is not None
        for name, _sign, _coarse, glyph in _STEPPERS:
            rect = regions.get(f'{prefix}_{name}')
            if rect is None:
                continue
            x, y, w, h = rect
            hover = 1.0 if self._hover_key == f'{prefix}_{name}' else 0.0
            if enabled:
                fill, text_color, border = _button_colors(ctx, False, color, hover)
            else:
                fill, text_color, border = (
                    palette.disabled, palette.text_dimmer, palette.edge_inner)
            chrome.plate(ctx, x, y, w, h, fill=fill, line=border, cut=3.0)
            ctx.text.draw(glyph, x + w * 0.5, y + h * 0.5, role='button_sm',
                          color=text_color, align='center', valign='middle')

        x, y, w, h = regions[f'{prefix}_value']
        ctx.text.draw(label, x, y + h * 0.5, role='caption',
                      color=palette.text_dim, align='left', valign='middle')
        ctx.text.draw(
            units.delta_v(value if enabled else None),
            x + w, y + h * 0.5, role='value',
            color=color if enabled else palette.text_dimmer,
            align='right', valign='middle')

    def _draw_line(self, ctx, rect, key, value, color):
        palette = ctx.theme.palette
        x, y, w, h = rect
        ctx.text.draw(key, x, y + h * 0.5, role='caption',
                      color=palette.text_dim, align='left', valign='middle')
        ctx.text.draw(value, x + w, y + h * 0.5, role='value',
                      color=color, align='right', valign='middle')

    def _draw_execute(self, ctx, rect, active):
        palette = ctx.theme.palette
        x, y, w, h = rect
        enabled = self.execute_enabled()
        hover = 1.0 if self._hover_key == 'execute' else 0.0
        if not enabled:
            # DIE SICHTBARE HAELFTE DER SPERRE (siehe modulkopf).
            fill, text_color, border = (
                palette.disabled, palette.text_dimmer, palette.edge_inner)
        else:
            fill, text_color, border = _button_colors(
                ctx, active, palette.snap, hover)
        chrome.plate(ctx, x, y, w, h, fill=fill, line=border, cut=6.0)
        state = getattr(self.telemetry, 'maneuver_state', 'idle')
        label = {'armed': 'ABORT', 'burning': 'ABORT'}.get(state, 'EXECUTE')
        ctx.text.draw(label, x + w * 0.5, y + h * 0.5, role='button',
                      color=text_color, align='center', valign='middle')

    def _draw_foot(self, ctx, regions):
        palette = ctx.theme.palette
        telemetry = self.telemetry
        full = int(getattr(telemetry, 'maneuver_count', 0)) >= int(
            getattr(telemetry, 'maneuver_max', 5))
        has_node = getattr(telemetry, 'maneuver_node', None) is not None
        for key, label, usable in (('add', '+ NODE', not full),
                                   ('delete', 'DEL', has_node)):
            x, y, w, h = regions[key]
            hover = 1.0 if self._hover_key == key else 0.0
            if usable:
                fill, text_color, border = _button_colors(
                    ctx, False, palette.frame, hover)
            else:
                fill, text_color, border = (
                    palette.disabled, palette.text_dimmer, palette.edge_inner)
            chrome.plate(ctx, x, y, w, h, fill=fill, line=border, cut=4.0)
            ctx.text.draw(label, x + w * 0.5, y + h * 0.5, role='button_sm',
                          color=text_color, align='center', valign='middle')
```

- [ ] **Step 9: Dock it in `ui/hud/layout.py`**

Add the import beside the others:

```python
from .maneuver import ManeuverBlock
from .maneuver import WIDTH as MANEUVER_WIDTH
```

Extend `Hud.__init__`'s signature with the maneuver bindings (after `horizon_sweep_s=2.5`):

```python
                 maneuver_plan=None, maneuver_preview=None,
                 maneuver_executor=None, maneuver_selected_get=None,
                 maneuver_selected_set=None, maneuver_add=None,
                 maneuver_delete=None, maneuver_execute=None,
                 maneuver_dv_step_fine=1.0, maneuver_dv_step_coarse=10.0,
```

and forward them into the `Telemetry(...)` construction:

```python
        self.telemetry = Telemetry(
            world, ship, ship_control, camera, renderer, predictor, ui_state,
            tick_rate=tick_rate,
            maneuver_plan=maneuver_plan,
            maneuver_preview=maneuver_preview,
            maneuver_executor=maneuver_executor,
            maneuver_selected_get=maneuver_selected_get,
            maneuver_selected_set=maneuver_selected_set,
            maneuver_add=maneuver_add,
            maneuver_delete=maneuver_delete,
            maneuver_execute=maneuver_execute,
            maneuver_dv_step_fine=maneuver_dv_step_fine,
            maneuver_dv_step_coarse=maneuver_dv_step_coarse,
        )
```

In `_build`, directly after the two `SnapRosette` additions, add:

```python
        # Der MANEUVER-block spiegelt die rosette auf der LINKEN flanke:
        # dieselbe verankerung an der unteren bildmitte, derselbe
        # dock-abstand, nur nach links geschoben. So liest sich die untere
        # bildmitte als eine instrumentenreihe -- und die komposition, die
        # bisher nach rechts haengt, steht wieder gerade.
        maneuver_offset = -(NAVBALL_WIDTH * 0.5 + DOCK_GAP + MANEUVER_WIDTH * 0.5)
        self.maneuver = root.add(ManeuverBlock(
            telemetry, anchor=BOTTOM_CENTER,
            offset=(maneuver_offset, MARGIN + 22),
        ))
```

In `_apply_responsive`, add:

```python
        # Unter dem umbruch faellt der block weg -- er ist ein PLANUNGS-
        # werkzeug, kein fluginstrument, und in einem schmalen fenster
        # nimmt er den platz weg, den die bahn braucht. Die tasten N / X
        # bleiben in jeder groesse erreichbar.
        self.maneuver.visible = wide
```

- [ ] **Step 10: Update the HUD module docstring**

In `ui/hud/__init__.py`, add to the module list:

```
    maneuver.py      der MANEUVER-block links am navball -- knoten,
                     delta-v, brenndauer, EXECUTE
```

and **correct** the now-false note. Replace

```
- **Schub = schubstufe.** Es gibt keinen dauerschub, nur impulse pro frame.
```

with

```
- **Schub = schubstufe -- ausser beim manoever-autopiloten.** Von hand gibt
  es nur impulse je frame, und der bogen skaliert dafuer
  schiffcontrol.thrust_acc. Ein ausgefuehrter manoeverknoten ist der eine
  DAUERSCHUB in diesem spiel: `ship/maneuver/` faehrt ein rampenprofil ab
  und schreibt seine hebelstellung je frame in set_thrust_level, der bogen
  zeigt also die rampe. Im zeitraffer bleibt der schub gesperrt und der
  bogen beschriftet sich mit HOLD -- der autopilot zieht die raffung vor
  der zuendung selbst auf echtzeit herunter.
```

- [ ] **Step 11: Pass the bindings from `bootstrap.py`**

Extend the `Hud(...)` construction with:

```python
            maneuver_plan=app.maneuver_plan,
            maneuver_preview=app.maneuver_preview,
            maneuver_executor=app.maneuver_executor,
            maneuver_selected_get=lambda: app.selected_node_index,
            maneuver_selected_set=_set_selected_node,
            maneuver_add=lambda: _router_ref[0].add_node_at_cursor(),
            maneuver_delete=lambda: _router_ref[0].delete_selected_node(),
            maneuver_execute=lambda: _router_ref[0].toggle_execute(),
            maneuver_dv_step_fine=mc['dv_step_fine'],
            maneuver_dv_step_coarse=mc['dv_step_coarse'],
```

`App` has `__slots__`, so `app.selected_node_index` cannot be written from a lambda's closure directly — define the setter and the router holder just above the `Hud(...)` call:

```python
    def _set_selected_node(index):
        app.selected_node_index = max(0, int(index))

    # Die drei aktionen des blocks nehmen DENSELBEN weg wie die tasten
    # N / Shift+N / X -- sonst gaebe es zwei wege, einen knoten zu setzen,
    # und sie wuerden auseinanderlaufen. Der router entsteht erst in
    # runtime/loop.py::run(), deshalb eine box, die dort gefuellt wird.
    _router_ref = [None]
    app.maneuver_router_ref = _router_ref
```

Add `'maneuver_router_ref'` to `App.__slots__`, and in `runtime/loop.py::run()` fill it immediately after `router = InputRouter(app)`:

```python
    router = InputRouter(app)
    # Die HUD-knoepfe rufen ueber diese box denselben router wie die tasten.
    if getattr(app, 'maneuver_router_ref', None) is not None:
        app.maneuver_router_ref[0] = router
```

The HUD test constructs a `Hud` without those three callables; `Telemetry.add_node()` and friends return `False` when the binding is `None`, which is exactly what section 4 of the test relies on (it drives the steppers, not `+ NODE`).

- [ ] **Step 12: Run the tests**

```
python tests/maneuver_hud_test.py
python tests/ui_hud_test.py
python tests/ui_render_test.py
python tests/ui_horizon_slider_test.py
```
Expected: all pass. `ui_hud_test.py` is the guard on `layout.py` / `telemetry.py` / `controls.py` / `attitude.py` — all four are touched here, so a failure there is a real regression, not noise.

- [ ] **Step 13: Look at it**

```
python tools/game_shot.py 1920 1080 --frames 120
```
Check against `screenshots for debugging/`: the block should read as the left counterpart of `SNAP.FREE`, its `MANEUVER` tab on the bottom edge, `PRO` green, `NRM` magenta, `DV` / `BURN` / `NODE` amber, and `EXECUTE` grey until a node carries Δv.

- [ ] **Step 14: Commit**

```bash
cd spacesim
git add ui/hud/maneuver.py ui/theme.py ui/hud/attitude.py ui/hud/controls.py ui/hud/telemetry.py ui/hud/layout.py ui/hud/__init__.py config/config.json config/loader.py runtime/bootstrap.py runtime/loop.py tests/maneuver_hud_test.py
git commit -m "feat(maneuver): MANEUVER block docked to the navball's left flank

Mirrors the snap rosette: same anchor, same dock gap, notch tab on the
bottom edge. One self-drawing widget with _regions() as the single
geometry source. EXECUTE is greyed while the node carries no delta-v, and
the compass ring gains a fifth marker for the burn direction.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 9: The drag gizmo on the line

**Files:** Modify `spacesim/ui/hud/maneuver.py`, `spacesim/ui/hud/layout.py`; extend `spacesim/tests/maneuver_hud_test.py`.

**Interfaces:**
- Consumes: `renderer.maneuver_node_hits`, `renderer.maneuver_curve_screen`, `renderer.maneuver_drag_active` (Task 7); `Telemetry.maneuver_plan`.
- Produces: `ui.hud.maneuver.ManeuverGizmo(telemetry, dv_per_px=0.75, **kwargs)`; `Hud.gizmo`.

**One-frame lag, on purpose.** `maneuver_node_hits` is filled during `renderer.render()`, which runs *after* the event loop. A click therefore hit-tests the previous frame's positions — exactly the situation `ApsisTooltip` already lives with, and at 60 fps it is invisible. Do not "fix" it by recomputing screen positions in the widget; that reintroduces the second transform this whole publish/subscribe arrangement exists to avoid.

- [ ] **Step 1: Add the gizmo test sections**

Append to `spacesim/tests/maneuver_hud_test.py`, before the final `if FAILURES:` block:

```python
print("\n9) der ziehgriff faengt NUR seine eigenen griffe")
from ui.hud.maneuver import ManeuverGizmo

gizmo = hud.gizmo
check(gizmo is not None, "hud.gizmo existiert", "")
renderer.maneuver_node_hits = [{
    'index': 0, 'sx': 500.0, 'sy': 400.0, 'radius_px': 8.0,
    'handles': [
        {'kind': 'prograde', 'sx': 530.0, 'sy': 400.0, 'radius_px': 7.0,
         'dir_sx': 1.0, 'dir_sy': 0.0},
        {'kind': 'retrograde', 'sx': 470.0, 'sy': 400.0, 'radius_px': 7.0,
         'dir_sx': -1.0, 'dir_sy': 0.0},
        {'kind': 'normal', 'sx': 500.0, 'sy': 370.0, 'radius_px': 7.0,
         'dir_sx': 0.0, 'dir_sy': -1.0},
        {'kind': 'antinormal', 'sx': 500.0, 'sy': 430.0, 'radius_px': 7.0,
         'dir_sx': 0.0, 'dir_sy': 1.0},
    ],
}]
check(gizmo.hit_test(ui, 530.0, 400.0) is True, "der prograde-griff wird getroffen", "")
check(gizmo.hit_test(ui, 500.0, 400.0) is True, "der marker ebenso", "")
check(gizmo.hit_test(ui, 500.0, 200.0) is False,
      "eine leere stelle daneben NICHT (sonst blockiert er den kameraschwenk)", "")

print("\n10) ziehen am griff aendert das delta-v des knotens")
selected[0] = 0
frame()
node0 = plan.nodes[0]
start = float(node0.dv_prograde)
before = plan.version
gizmo.on_mouse_down(ui, 530.0, 400.0, 1)
check(renderer.maneuver_drag_active is True,
      "der zug meldet sich beim renderer an", "")
gizmo.on_mouse_move(ui, 570.0, 400.0)
moved = float(node0.dv_prograde) - start
check(abs(moved - 40.0 * mc['handle_dv_per_px']) < 1e-6,
      "40 px nach aussen = 40 * dv_per_px mehr prograde", f"{moved:.4f}")
check(plan.version > before, "und plan.version zaehlt hoch", "")
gizmo.on_mouse_up(ui, 570.0, 400.0, 1)
check(renderer.maneuver_drag_active is False, "loslassen meldet ab", "")

print("\n11) der retrograde-griff zieht dieselbe achse zurueck")
start = float(node0.dv_prograde)
gizmo.on_mouse_down(ui, 470.0, 400.0, 1)
gizmo.on_mouse_move(ui, 430.0, 400.0)
moved = float(node0.dv_prograde) - start
check(moved < 0.0 and abs(moved + 40.0 * mc['handle_dv_per_px']) < 1e-6,
      "nach aussen ziehen VERMINDERT prograde", f"{moved:.4f}")
gizmo.on_mouse_up(ui, 430.0, 400.0, 1)

print("\n12) den marker verschieben setzt die knotenzeit neu")
renderer.maneuver_curve_screen = [
    (500.0 + i * 4.0, 400.0, world.time + 100.0 * i) for i in range(20)
]
before_t = float(node0.t_node)
gizmo.on_mouse_down(ui, 500.0, 400.0, 1)
gizmo.on_mouse_move(ui, 540.0, 402.0)
check(abs(float(node0.t_node) - (world.time + 100.0 * 10)) < 1e-6,
      "der knoten springt auf die naechste stuetzstelle der linie",
      f"{before_t:.1f} -> {float(node0.t_node):.1f}")
gizmo.on_mouse_up(ui, 540.0, 402.0, 1)
renderer.maneuver_node_hits = []
renderer.maneuver_curve_screen = []
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python tests/maneuver_hud_test.py` — Expected: FAIL, `cannot import name 'ManeuverGizmo'`.

- [ ] **Step 3: Append `ManeuverGizmo` to `ui/hud/maneuver.py`**

```python
class ManeuverGizmo(Widget):
    """Die ziehgriffe AN DER LINIE -- kein rechteck, nur treffer.

    Er zeichnet nichts: marker, stiele und pfeilspitzen malt der renderer
    (`render/maneuver.py`), weil nur der die zeitabhaengige
    frame-transformation kennt, die sie auf der bahn haelt. Dieses widget
    ist ausschliesslich der EINGABEweg dazu und trifft gegen genau die
    schirmpositionen, die dort gezeichnet wurden
    (`renderer.maneuver_node_hits`) -- dieselbe arbeitsteilung wie beim
    schwebezettel an den Ap/Pe-rauten.

    ER FAENGT DIE MAUS NUR UEBER EINEM GRIFF. `hit_test` prueft radien, kein
    rechteck: das widget sitzt mitten im bild ueber der bahn, und eines,
    das dort flaechig klicks schluckt, blockierte koerperauswahl und
    kameraschwenk -- derselbe fehler, den `AttitudeRing.hit_test` fuer den
    kompassring behebt.

    EIN FRAME VERSATZ, UND ZWAR ABSICHTLICH. Die trefferliste entsteht in
    `renderer.render()`, also NACH der ereignisschleife; ein klick prueft
    damit gegen die positionen des vorbildes. Bei 60 bildern je sekunde ist
    das unsichtbar, und die alternative -- die schirmposition hier noch
    einmal auszurechnen -- waere genau die zweite transformation, die diese
    aufteilung vermeidet.
    """

    def __init__(self, telemetry, dv_per_px=0.75, **kwargs):
        kwargs.setdefault('size', (0.0, 0.0))
        kwargs.setdefault('z', 55)
        super().__init__(**kwargs)
        self.telemetry = telemetry
        self.dv_per_px = float(dv_per_px)
        self.blocks_mouse = True
        self._grab = None          # ('handle', index, kind) | ('marker', index)
        self._press = (0.0, 0.0)
        self._start_dv = 0.0

    # ------------------------------------------------------------- treffer

    def _renderer(self):
        return getattr(self.telemetry, 'renderer', None)

    def _hits(self):
        renderer = self._renderer()
        return list(getattr(renderer, 'maneuver_node_hits', ()) or ())

    def _pick(self, x, y):
        for hit in self._hits():
            for handle in hit['handles']:
                r = float(handle['radius_px']) + 6.0
                if math.hypot(x - handle['sx'], y - handle['sy']) <= r:
                    return ('handle', int(hit['index']), handle['kind'], handle)
            r = float(hit['radius_px']) + 6.0
            if math.hypot(x - hit['sx'], y - hit['sy']) <= r:
                return ('marker', int(hit['index']), None, hit)
        return None

    def hit_test(self, ctx, x, y):
        if not self.visible:
            return False
        return self._pick(float(x), float(y)) is not None

    # ------------------------------------------------------------- eingabe

    def _node(self, index):
        plan = getattr(self.telemetry, 'maneuver_plan', None)
        if plan is None or not (0 <= index < len(plan)):
            return None
        return plan.nodes[index]

    def on_mouse_down(self, ctx, x, y, button):
        if button != 1:
            return True
        picked = self._pick(float(x), float(y))
        if picked is None:
            return True
        kind, index, handle_kind, payload = picked
        node = self._node(index)
        if node is None:
            return True

        self.telemetry.select_node(index)
        self._press = (float(x), float(y))
        if kind == 'handle':
            axis = 'prograde' if handle_kind in ('prograde', 'retrograde') else 'normal'
            self._grab = ('handle', index, handle_kind, axis,
                          float(payload['dir_sx']), float(payload['dir_sy']))
            self._start_dv = (node.dv_prograde if axis == 'prograde'
                              else node.dv_normal)
        else:
            self._grab = ('marker', index, None, None, 0.0, 0.0)
            self._start_dv = 0.0

        renderer = self._renderer()
        if renderer is not None:
            # Erst dieses flag laesst den renderer die BASISlinie in
            # schirmkoordinaten ablegen -- sie kostet einen frame-transform
            # je punkt und wird deshalb nur waehrend eines zugs gebaut.
            renderer.maneuver_drag_active = True
        return True

    def on_mouse_move(self, ctx, x, y):
        if self._grab is None:
            return True
        kind, index, handle_kind, axis, dir_sx, dir_sy = self._grab
        node = self._node(index)
        plan = getattr(self.telemetry, 'maneuver_plan', None)
        if node is None or plan is None:
            return True

        if kind == 'handle':
            # Die zeigerbewegung auf die GRIFFRICHTUNG projizieren: nur der
            # anteil laengs des pfeils zaehlt, seitliches wackeln nicht.
            dx = float(x) - self._press[0]
            dy = float(y) - self._press[1]
            along = dx * dir_sx + dy * dir_sy
            # Nach aussen ziehen heisst immer MEHR in richtung des pfeils --
            # am retrograde-pfeil ist das weniger prograde.
            sign = -1.0 if handle_kind in ('retrograde', 'antinormal') else 1.0
            value = self._start_dv + sign * along * self.dv_per_px
            if axis == 'prograde':
                node.dv_prograde = value
            else:
                node.dv_normal = value
            plan.touch()
            return True

        # Marker: auf die naechste stuetzstelle der gezeichneten linie
        # rasten. Die zeit kommt damit VON DER LINIE und nicht aus einer
        # eigenen umrechnung -- der knoten kann gar nicht neben ihr landen.
        renderer = self._renderer()
        curve = list(getattr(renderer, 'maneuver_curve_screen', ()) or ())
        if len(curve) < 2:
            return True
        best_t = None
        best_d2 = None
        for point in curve:
            d2 = (float(x) - point[0]) ** 2 + (float(y) - point[1]) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_t = float(point[2])
        if best_t is not None:
            node.t_node = best_t
            plan.touch()
        return True

    def on_mouse_up(self, ctx, x, y, button):
        self._grab = None
        renderer = self._renderer()
        if renderer is not None:
            renderer.maneuver_drag_active = False
        return True
```

- [ ] **Step 4: Add it in `ui/hud/layout.py`**

Import `ManeuverGizmo` alongside `ManeuverBlock`, add `maneuver_dv_per_px=0.75` to `Hud.__init__`'s signature, and in `_build`, after the `ManeuverBlock`:

```python
        # Der ziehgriff steht AUSSERHALB jeder gruppe -- sein platz kommt aus
        # der weltposition des knotens, nicht aus der verankerung. Wie der
        # Ap/Pe-schwebezettel.
        self.gizmo = root.add(ManeuverGizmo(
            telemetry, dv_per_px=maneuver_dv_per_px))
```

`_apply_responsive` leaves the gizmo alone: it lives on the line, not in the chrome, and works at any window size.

In `runtime/bootstrap.py`, pass `maneuver_dv_per_px=mc['handle_dv_per_px']` to `Hud(...)`.

- [ ] **Step 5: Run the tests**

```
python tests/maneuver_hud_test.py
python tests/ui_hud_test.py
```
Expected: both pass.

- [ ] **Step 6: Fly it**

`python main.py` — press `N`, drag the green arrow outward and watch the green planned trajectory swing; drag the hexagon along the line to retime; press `X` and watch the warp drop, the nose swing onto the node marker, and the throttle arc ramp up and back down.

- [ ] **Step 7: Commit**

```bash
cd spacesim
git add ui/hud/maneuver.py ui/hud/layout.py runtime/bootstrap.py tests/maneuver_hud_test.py
git commit -m "feat(maneuver): drag handles on the trajectory

Radius hit-test against the renderer's published positions, so an empty
patch of sky still routes to body selection and camera pan. Handle drags
project onto the arrow direction; the marker drag snaps to the drawn line.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Task 10: Documentation

**Files:** Create `Werk/.claude/rules/maneuver.md`; modify `Werk/CLAUDE.md`, `Werk/.claude/rules/tests.md`, `Werk/.claude/rules/hud-ui.md`, `spacesim/README.md`.

None of these are in a git repo except `README.md` — edit the rest in place, commit only the README.

- [ ] **Step 1: Write `Werk/.claude/rules/maneuver.md`**

Frontmatter:

```
---
paths:
  - "spacesim/ship/maneuver/**"
  - "spacesim/physics/kernels/burn.py"
  - "spacesim/render/maneuver.py"
  - "spacesim/ui/hud/maneuver.py"
---
```

Then, one section each — state the rule, the measurement, and the counter-check that would fail without it:

1. **`profile.py` is the only place a burn duration is computed.** The ramp *rate* is conserved, not the ramp time; trapezoid and triangle meet continuously at `dv = a_max · ramp`. Half the Δv lands before `total_time/2`, which is where the ignition lead comes from. Counter-check: `tests/maneuver_profile_test.py` §3 and §5.
2. **The njit twin is duplicated on purpose.** `_profile_accel_numba` restates `BurnProfile.accel_at` because numba cannot call a Python method. §8 compares them at 2004 points for *exact* equality — without it, preview and execution could drift apart silently.
3. **`a_max` is a SIM-time acceleration.** `thrust_acc / realtime_warp_max` = 600 / 60 = 10 m/s². Using `thrust_acc` directly burns 60× as hard as the arrow key *and* previews that burn correctly, so nothing on screen would give it away. Counter-check: `tests/maneuver_execute_test.py` §1.
4. **The Δv direction is resolved once and held.** Fixed in world space at node time; that is what makes preview and execution the same integration. Normal is positive **inward**, the same sign rule as `apparent_orbital_directions`, so the rosette, the ring markers and the handles cannot disagree.
5. **The preview is a chain, and it rebuilds only on change.** Each node reads its state off the previous node's result (`state_on_curve`, cubic Hermite). Gated on `plan.version` and `predictor._trajectory_version` plus `preview_min_interval_s` — up to five integrations per frame would be the most expensive thing in the picture. Counter-check: `tests/maneuver_preview_test.py` §6 and §8.
6. **A node beyond the drawn horizon has no readable state.** The chain stops there rather than guessing.
7. **Kick-then-drift.** `update()` applies one step's Δv before the step; the preview integrates continuously. The step is capped at `burn_step_max_s` for exactly this reason. Measured residual: `tests/maneuver_execute_test.py` §8.
8. **Screen positions are published, not recomputed.** `renderer.maneuver_node_hits`, the `apsis_marker_hits` pattern, and the one-frame lag that comes with it.
9. **D9, verbatim:** node 5 sits on a trajectory four integrations deep; the tail of a five-node multi-year plan is approximate.

- [ ] **Step 2: `Werk/CLAUDE.md`**

- Module map: add a row — `ship/maneuver/` → "`plan` (knoten + plan, max 5), `profile` (das rampenprofil — DIE quelle für dauer und zündzeitpunkt), `preview` (die kette coast→burn→coast), `executor` (der autopilot)". Extend the `render/` row with `maneuver` and the `ui/` row with the MANEUVER block.
- Routing table: add `.claude/rules/maneuver.md` → "maneuver nodes: das rampenprofil, die vorschau-kette, der autopilot, die griffe".
- Controls table: `N` add node / `Shift+N` delete / `X` arm-or-abort; note that manual thrust or rotation aborts a running burn.
- Invariants: add **"There is exactly ONE burn-duration calculation, and it is `BurnProfile`."**
- Keep the file under 200 lines — trim if the additions push it over.

- [ ] **Step 3: `.claude/rules/tests.md`** — a row for each of `maneuver_profile_test.py`, `maneuver_plan_test.py`, `maneuver_burn_kernel_test.py`, `maneuver_preview_test.py`, `maneuver_execute_test.py`, `maneuver_render_test.py`, `maneuver_hud_test.py`, naming what each asserts.

- [ ] **Step 4: `.claude/rules/hud-ui.md`** — a note under the HUD-layout section: the block mirrors the snap rosette on the left flank, `_regions()` is the single geometry source, EXECUTE is greyed at zero Δv, and the palette gains no fifth colour.

- [ ] **Step 5: `spacesim/README.md`** — the controls list gains `N` / `Shift+N` / `X`, and a short paragraph on what a maneuver node is. No new dependency: the install line is unchanged.

- [ ] **Step 6: Full suite**

```
python tests/maneuver_profile_test.py
python tests/maneuver_plan_test.py
python tests/maneuver_burn_kernel_test.py
python tests/maneuver_preview_test.py
python tests/maneuver_execute_test.py
python tests/maneuver_render_test.py
python tests/maneuver_hud_test.py
python tests/ui_hud_test.py
python tests/ui_render_test.py
python tests/warp_predictor_test.py
python tests/apsis_stability_test.py
python tests/energy_test.py
```
Expected: everything passes except `warp_predictor_test.py`'s three known pre-existing failures. Report the actual output — do not claim a pass you have not seen.

- [ ] **Step 7: Commit**

```bash
cd spacesim
git add README.md
git commit -m "docs: maneuver nodes in the README controls list

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012yXkoZXryKwMbh5fA6dt8F"
```

---

## Self-review notes

- **Coverage.** D1→Tasks 1, D2→5, D3→2/4/5, D4→2/5, D5→2/8, D6→5/6, D7→8, D8→7/8, D9→10.
- **Type consistency.** `BurnProfile(dv, a_max, ramp_seconds)`, `orbital_basis(rel_px, rel_py, rel_vx, rel_vy)`, `burn_direction_world(basis, dv_prograde, dv_normal)`, `state_on_curve(points, t_abs)`, `_burn_arc_numba(...)`, `ManeuverExecutor.update(world, sim_seconds)` and `maneuver_node_hits`' dict shape are used identically wherever they appear.
- **The one thing to watch while executing:** Task 4's kernel call has 30 positional arguments. Check it against the live call site in `ship/predictor/compute.py` line ~654 rather than trusting the listing — if the predictor's signature has moved since this plan was written, that call is where it shows up first.
