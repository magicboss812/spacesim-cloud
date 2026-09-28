# Task 3 review package

## Files changed
- MOD spacesim/test.py (added horizon_targets fn ~L39-62; routed 1 call in apply_predictor_horizon)
- NEW spacesim/tests/horizon_targets_test.py

## diff: spacesim/test.py
```diff
--- .sdd-horizon-slider/snapshots/task-3-test.py.base	2026-09-02 22:05:22.210701300 +0200
+++ spacesim/test.py	2026-09-02 22:08:29.262703600 +0200
@@ -36,6 +36,28 @@
     return drawn, drawn * warp_mult
 
 
+def horizon_targets(base_length, manual_mult, warp_mult, max_points,
+                    base_spacing, *, grabbing=False, ceiling_mult=None):
+    """Wie `predictor_horizon_lengths`, aber mit dem slider-griff.
+
+    Solange der spieler den horizont-regler HAELT (`grabbing`), wird die
+    GERECHNETE laenge so bestimmt, als staende der manuelle faktor auf
+    `ceiling_mult` -- sie aendert sich dann nicht, waehrend der knauf
+    wandert, also greift die 1e-9-schranke in `apply_predictor_horizon`
+    genau einmal und der einzige aufruf pro frame ist das O(1)
+    `set_display_length`. Die GEZEICHNETE laenge folgt weiter dem echten
+    faktor. Siehe plans/predictor_horizon_slider_design.md.
+    """
+    drawn, wanted = predictor_horizon_lengths(
+        base_length, manual_mult, warp_mult, max_points, base_spacing,
+    )
+    if grabbing and ceiling_mult is not None:
+        _, wanted = predictor_horizon_lengths(
+            base_length, float(ceiling_mult), warp_mult, max_points, base_spacing,
+        )
+    return drawn, wanted
+
+
 def main():
     import os
     import time
@@ -561,7 +583,7 @@
         # Hat der spieler mit '+' bereits ueber das budget hinaus verlaengert,
         # faellt der raffungsfaktor auf 1: seine eigene vergroeberung bleibt
         # (die ist gewollt und dokumentiert), die der raffung kommt nicht dazu.
-        drawn, wanted = predictor_horizon_lengths(
+        drawn, wanted = horizon_targets(
             PREDICTOR_BASE_LENGTH, predictor_manual_mult,
             predictor_warp_length_mult(),
             PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
```

## NEW FILE: spacesim/tests/horizon_targets_test.py
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

## BASELINE warp_predictor_test.py FAIL lines (pre-change, machine quiet):
```
114:  FAIL jede neue linie gehoert zu einem NEUEREN schiffszustand -- 359 schnappschuesse, kleinste zunahme -0.035 m/s
153:  FAIL die decke senkt die teilschritte bei 1 y/s um mehr als das 20-fache -- ohne decke 1408, mit decke 1280 (faktor 1)
290:FEHLGESCHLAGEN: 2
```
