## Task 3: `horizon_targets()` — the pure length rule (no behaviour change yet)

**Files:**
- Modify: `spacesim/test.py` (add module-level `horizon_targets`; call it from `apply_predictor_horizon`)
- Test: `spacesim/tests/horizon_targets_test.py` (new)

**Interfaces:**
- Consumes: `spacesim/test.py` module-level `predictor_horizon_lengths(base_length, manual_mult, warp_mult, max_points, base_spacing) -> (drawn, wanted)` (already exists).
- Produces:
  - `horizon_targets(base_length, manual_mult, warp_mult, max_points, base_spacing, *, grabbing=False, ceiling_mult=None) -> (drawn, wanted)`
    - identical to `predictor_horizon_lengths` when `grabbing` is `False`;
    - when `grabbing` is `True` and `ceiling_mult` is a number, `wanted` is computed as if `manual_mult == ceiling_mult` (so it does **not** vary while the knob moves), while `drawn` still follows the real `manual_mult`.

- [ ] **Step 1: Write the failing test**

Create `spacesim/tests/horizon_targets_test.py`:

```python
"""Kopftest fuer test.horizon_targets -- die reine laengen-regel des
vorhersage-horizonts. Modulebene, damit sie hier messbar ist statt
nachgebaut (dieselbe begruendung wie bei predictor_horizon_lengths).

Aufruf: python tests/horizon_targets_test.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from test import horizon_targets, predictor_horizon_lengths

FAILURES = []


def check(condition, label, detail=''):
    if condition:
        print(f"  ok   {label}{(' -- ' + detail) if detail else ''}")
    else:
        FAILURES.append(f"{label}: {detail}")
        print(f"  FAIL {label} -- {detail}")


BASE = 1.0e10          # 10000 punkte x 1e6 m abstand
MAXP = 40000
SPACING = 1.0e6
CEIL = 4.0

# --- 1. ohne grabbing exakt wie predictor_horizon_lengths -------------
print("1. deckungsgleich ohne grabbing")
for mult in (0.25, 1.0, 2.0, 4.0):
    for warp in (1.0, 4.0, 64.0):
        a = horizon_targets(BASE, mult, warp, MAXP, SPACING)
        b = predictor_horizon_lengths(BASE, mult, warp, MAXP, SPACING)
        check(a == b, f"mult={mult} warp={warp}", f"{a} vs {b}")

# --- 2. beim grabbing ist `wanted` konstant, `drawn` folgt der auslenkung
print("2. grabbing pinnt die gerechnete laenge an die decke")
prev_wanted = None
for mult in (0.5, 1.0, 2.0, 3.7):
    drawn, wanted = horizon_targets(BASE, mult, 1.0, MAXP, SPACING,
                                    grabbing=True, ceiling_mult=CEIL)
    exp_drawn, _ = predictor_horizon_lengths(BASE, mult, 1.0, MAXP, SPACING)
    check(abs(drawn - exp_drawn) < 1.0, f"drawn folgt mult={mult}",
          f"{drawn} vs {exp_drawn}")
    if prev_wanted is not None:
        check(wanted == prev_wanted, f"wanted konstant bei mult={mult}",
              f"{wanted} vs {prev_wanted}")
    prev_wanted = wanted

_, ceil_wanted = predictor_horizon_lengths(BASE, CEIL, 1.0, MAXP, SPACING)
check(prev_wanted == ceil_wanted, "wanted == die decken-laenge",
      f"{prev_wanted} vs {ceil_wanted}")

# --- 3. grabbing ohne ceiling_mult faellt auf das alte verhalten -----
print("3. grabbing ohne decke = normalverhalten")
a = horizon_targets(BASE, 2.0, 1.0, MAXP, SPACING, grabbing=True,
                    ceiling_mult=None)
b = predictor_horizon_lengths(BASE, 2.0, 1.0, MAXP, SPACING)
check(a == b, "kein ceiling_mult -> unveraendert", f"{a} vs {b}")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("test.horizon_targets: alle pruefungen bestanden")
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `cd spacesim && python tests/horizon_targets_test.py`
Expected: FAIL — `ImportError: cannot import name 'horizon_targets' from 'test'`

- [ ] **Step 3: Add `horizon_targets` beside `predictor_horizon_lengths`**

In `spacesim/test.py`, immediately after the `predictor_horizon_lengths` function (currently ends at line ~36), add:

```python
def horizon_targets(base_length, manual_mult, warp_mult, max_points,
                    base_spacing, *, grabbing=False, ceiling_mult=None):
    """Wie `predictor_horizon_lengths`, aber mit dem slider-griff.

    Solange der spieler den horizont-regler HAELT (`grabbing`), wird die
    GERECHNETE laenge so bestimmt, als staende der manuelle faktor auf
    `ceiling_mult` -- sie aendert sich dann nicht, waehrend der knauf
    wandert, also greift die 1e-9-schranke in `apply_predictor_horizon`
    genau einmal und der einzige aufruf pro frame ist das O(1)
    `set_display_length`. Die GEZEICHNETE laenge folgt weiter dem echten
    faktor. Siehe plans/predictor_horizon_slider_design.md.
    """
    drawn, wanted = predictor_horizon_lengths(
        base_length, manual_mult, warp_mult, max_points, base_spacing,
    )
    if grabbing and ceiling_mult is not None:
        _, wanted = predictor_horizon_lengths(
            base_length, float(ceiling_mult), warp_mult, max_points, base_spacing,
        )
    return drawn, wanted
```

- [ ] **Step 4: Route `apply_predictor_horizon` through it (still a no-op — `grabbing` is always False here)**

In `spacesim/test.py`, in `apply_predictor_horizon()` (line ~564), replace:

```python
        drawn, wanted = predictor_horizon_lengths(
            PREDICTOR_BASE_LENGTH, predictor_manual_mult,
            predictor_warp_length_mult(),
            PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
        )
```

with:

```python
        drawn, wanted = horizon_targets(
            PREDICTOR_BASE_LENGTH, predictor_manual_mult,
            predictor_warp_length_mult(),
            PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
        )
```

(No `grabbing` / `ceiling_mult` yet — added in Task 4. `horizon_targets` with the defaults returns exactly what `predictor_horizon_lengths` returned.)

- [ ] **Step 5: Run the new test and the horizon regression**

Run: `cd spacesim && python tests/horizon_targets_test.py`
Expected: PASS.

Run: `cd spacesim && python tests/warp_predictor_test.py 2>&1 | tail -40`
Expected: same pass/fail sheet as before this task. The three known pre-existing failures (`.claude/rules/tests.md` "Known pre-existing failures") may still show — that is fine. **Nothing new may fail.** In particular §23 (`predictor_horizon_lengths`) must still pass.

- [ ] **Step 6: Smoke-run the game**

Run: `cd spacesim && SPACESIM_MAX_FRAMES=120 python test.py 2>&1 | tail -20`
Expected: runs 120 frames and exits cleanly, no traceback.

- [ ] **Step 7: Review checkpoint**

Summarise: `horizon_targets` added, `apply_predictor_horizon` routed through it, behaviour identical (`grabbing` unused). Tests green, game runs. Wait for approval.

---

