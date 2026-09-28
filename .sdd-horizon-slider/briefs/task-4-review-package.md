# Task 4 review package

## diff: spacesim/config.json
```diff
--- .sdd-horizon-slider/snapshots/task-4-config.json.base	2026-09-02 22:16:59.133559700 +0200
+++ spacesim/config.json	2026-09-02 22:18:11.369307500 +0200
@@ -59,6 +59,9 @@
     "rolling_mode": false,
     "toggle_num_points": 30,
     "length_step_factor": 2.0,
+    "horizon_slider_min_mult": 0.25,
+    "horizon_slider_max_mult": 4.0,
+    "horizon_slider_sweep_seconds": 2.5,
     "precision_step_factor": 2.0,
     "min_precision": 1.0,
     "auto_precision_from_zoom": true,
```

## diff: spacesim/test.py
```diff
--- .sdd-horizon-slider/snapshots/task-4-test.py.base	2026-09-02 22:16:59.115042400 +0200
+++ spacesim/test.py	2026-09-02 22:18:28.702639200 +0200
@@ -234,6 +234,9 @@
     precision_step = max(float(config.get('predictor.precision_step_factor', 2.0)), 1.0 + 1e-9)
     predictor_toggle_points = int(config.get('predictor.toggle_num_points', 30))
     predictor_min_precision = float(config.get('predictor.min_precision', 1.0))
+    HORIZON_MULT_MIN = float(config.get('predictor.horizon_slider_min_mult', 0.25))
+    HORIZON_MULT_MAX = float(config.get('predictor.horizon_slider_max_mult', 4.0))
+    HORIZON_SWEEP_S = float(config.get('predictor.horizon_slider_sweep_seconds', 2.5))
     if verbose:
         print(f"PREDICTOR DEBUG: async_compute = {predictor.async_compute}")
         print(f"PREDICTOR DEBUG: force_sync_on_stale = {predictor.force_sync_on_stale}")
@@ -367,6 +370,14 @@
     ui_state.on_change = apply_frame_selection
     apply_frame_selection()
 
+    def get_predictor_horizon_mult():
+        return predictor_manual_mult
+
+    def set_predictor_horizon_mult(mult):
+        nonlocal predictor_manual_mult
+        predictor_manual_mult = max(HORIZON_MULT_MIN,
+                                    min(HORIZON_MULT_MAX, float(mult)))
+
     # Spieler-HUD aufbauen. Muss NACH ui_state und dem frame-selector
     # entstehen: die rahmenwahl im HUD schreibt in ui_state, und dessen
     # aenderungs-benachrichtigung ist erst jetzt verdrahtet.
@@ -583,10 +594,14 @@
         # Hat der spieler mit '+' bereits ueber das budget hinaus verlaengert,
         # faellt der raffungsfaktor auf 1: seine eigene vergroeberung bleibt
         # (die ist gewollt und dokumentiert), die der raffung kommt nicht dazu.
+        grabbing = (hud is not None
+                    and getattr(hud, 'horizon', None) is not None
+                    and hud.horizon.is_grabbing)
         drawn, wanted = horizon_targets(
             PREDICTOR_BASE_LENGTH, predictor_manual_mult,
             predictor_warp_length_mult(),
             PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
+            grabbing=grabbing, ceiling_mult=HORIZON_MULT_MAX,
         )
         # GEZEICHNET wird immer nur der un-geraffte horizont. Ohne das wickelt
         # sich die linie im zeitraffer mehrfach um die bahn, waehrend sie in
```

## diff: spacesim/tests/horizon_targets_test.py
```diff
--- .sdd-horizon-slider/snapshots/task-4-horizon_targets_test.py.base	2026-09-02 22:16:59.152114200 +0200
+++ spacesim/tests/horizon_targets_test.py	2026-09-02 22:18:43.652989900 +0200
@@ -65,6 +65,93 @@
 b = predictor_horizon_lengths(BASE, 2.0, 1.0, MAXP, SPACING)
 check(a == b, "kein ceiling_mult -> unveraendert", f"{a} vs {b}")
 
+# --- 4. mit realem Predictor: set_length genau einmal je griff -------
+print("4. griff-kontrakt gegen einen echten Predictor")
+import numpy as np
+from predictor import Predictor
+from vec import G
+
+
+class _Body:
+    def __init__(self, x, y, mass, radius):
+        self.position = type('P', (), {'x': x, 'y': y})()
+        self.velocity = type('V', (), {'x': 0.0, 'y': 0.0})()
+        self.mass = mass
+        self.radius = radius
+        self.is_ship = False
+        self.name = 'Erde'
+        self.fixed = True
+        self.is_moon_of = None
+
+
+class _World:
+    def __init__(self):
+        self.G = G
+        self.time = 0.0
+        m = 5.9722e24
+        self.erde = _Body(0.0, 0.0, m, 6.371e6)
+        self.body = [self.erde]
+
+    def update_planets(self, dt):
+        pass
+
+
+w = _World()
+mu = G * w.erde.mass
+r = 6.371e6 + 4.0e5
+ship = _Body(r, 0.0, 0.0, 0.0)
+ship.is_ship = True
+ship.name = 'Schiff'
+ship.fixed = False
+import math as _m
+ship.velocity = type('V', (), {'x': 0.0, 'y': _m.sqrt(mu / r) * 1.2})()
+
+pred = Predictor(async_compute=False, num_points=2000, precision=1.0e6)
+pred.initialize(ship, w)
+
+calls = {'set_length': 0, 'set_display_length': 0}
+_orig_sl, _orig_sdl = pred.set_length, pred.set_display_length
+pred.set_length = lambda m, _o=_orig_sl, _c=calls: (_c.__setitem__('set_length', _c['set_length'] + 1), _o(m))[1]
+pred.set_display_length = lambda m, _o=_orig_sdl, _c=calls: (_c.__setitem__('set_display_length', _c['set_display_length'] + 1), _o(m))[1]
+
+BASE = pred.num_points * pred.precision
+CEIL = 4.0
+
+
+def apply(mult, grabbing):
+    """Der schwanz von test.apply_predictor_horizon, nachgebaut."""
+    drawn, wanted = horizon_targets(BASE, mult, 1.0, 40000, 1.0e6,
+                                    grabbing=grabbing, ceiling_mult=CEIL)
+    pred.set_display_length(drawn if wanted > drawn else None)
+    pw = int(min(40000, max(1, _m.ceil(wanted / 1.0e6))))
+    if pw != int(pred.num_points):
+        pred.set_num_points(pw, soft=True)
+    cur = pred.length
+    if cur is not None and abs(cur - wanted) <= wanted * 1e-9:
+        return
+    pred.set_length(wanted)
+
+
+apply(1.0, grabbing=False)                       # ausgangslage
+calls['set_length'] = 0
+calls['set_display_length'] = 0
+
+# 30 frames "ziehen": mult waechst, griff gehalten
+for i in range(30):
+    apply(1.0 + i * 0.1, grabbing=True)
+check(calls['set_length'] <= 1, "set_length hoechstens 1x waehrend des griffs",
+      f"{calls['set_length']}x")
+check(calls['set_display_length'] == 30, "set_display_length jeden frame",
+      f"{calls['set_display_length']}x")
+
+# loslassen: ein weiterer set_length auf den settled-wert
+before = calls['set_length']
+apply(3.9, grabbing=False)
+check(calls['set_length'] == before + 1, "beim loslassen genau ein set_length",
+      f"{calls['set_length']} (war {before})")
+
+pred.close()
+
 print()
 if FAILURES:
     print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
```

## Context: current apply_predictor_horizon full function
```python
        rate = warp_rate()
        ratio = rate / 604800.0          # ab 7 d/s waechst der horizont mit
        if ratio <= 1.0:
            return 1.0
        # RUNDEN, nicht abschneiden: abgeschnitten faellt 1 y/s auf 32x, und
        # das ist gemessen die schlechtere stufe (max 14.7 ms gegen 4.8 ms bei
        # 64x). Gerundet ergibt die reihe genau die gemessenen guten werte
        # 7d/s->1, 30d/s->4, 100d/s->16, 1y/s->64.
        exp = min(6, max(0, int(round(math.log2(ratio)))))
        return float(1 << exp)

    def apply_predictor_horizon():
        """Horizont neu setzen, wenn sich basis*manuell*raffung geaendert hat."""
        if predictor.num_points <= 0:
            return
        # DIE RAFFUNGS-VERLAENGERUNG IST EIN VORRAT, KEIN BILD -- UND SIE DARF
        # DIE GEZEICHNETE LINIE NICHT ANFASSEN.
        #
        # `wanted` geht an zwei stellen weiter, die beide auf die SICHTBARE
        # kurve durchschlagen, obwohl der verlaengerte teil gar nicht
        # gezeichnet wird (set_display_length unten):
        #
        # 1. `points_wanted` ist bei `PREDICTOR_MAX_POINTS` gedeckelt. Ist der
        #    deckel erreicht, vergroebert jede weitere verlaengerung den
        #    PUNKTABSTAND -- gemessen bei manuell 8x und 64x raffung: 40000
        #    punkte auf dem gezeichneten stueck werden zu **626**, und die
        #    gezeichnete kurve weicht dann selbst mit der kubischen
        #    Hermite-auswertung um **2.3e6 m** von derselben bahn ab (linear
        #    waeren es 6.8e6 m). Auf einer bahn mit perigaeum 1e7 m ist das
        #    eine sichtbar andere linie.
        # 2. `horizon_arc` in `Predictor._make_snapshot` ist `punkte x abstand`
        #    und hebt damit die fernfeld-schrittdecke an. Gemessen dieselbe
        #    lage: decke 2163 -> 8676 s, und die INTEGRIERTE bahn verschiebt
        #    sich um **2.3e6 m** (mit fester decke: 8.4e4 m).
        #
        # Beides zusammen ist der bericht "die vorhersage sieht im zeitraffer
        # ganz anders aus" -- rund 4.6e6 m auf einer linie, deren perigaeum
        # 1e7 m misst, allein vom druck auf die raffungstaste.
        #
        # Der vorrat wird deshalb auf das begrenzt, was das PUNKTBUDGET beim
        # basis-abstand noch traegt. Dann ist `wanted` nie groesser als
        # `PREDICTOR_MAX_POINTS x PREDICTOR_BASE_SPACING`, der abstand bleibt
        # exakt der der echtzeit -- und mit ihm `horizon_arc` und die decke.
        # Hat der spieler mit '+' bereits ueber das budget hinaus verlaengert,
        # faellt der raffungsfaktor auf 1: seine eigene vergroeberung bleibt
        # (die ist gewollt und dokumentiert), die der raffung kommt nicht dazu.
        grabbing = (hud is not None
                    and getattr(hud, 'horizon', None) is not None
                    and hud.horizon.is_grabbing)
        drawn, wanted = horizon_targets(
            PREDICTOR_BASE_LENGTH, predictor_manual_mult,
            predictor_warp_length_mult(),
            PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
            grabbing=grabbing, ceiling_mult=HORIZON_MULT_MAX,
        )
        # GEZEICHNET wird immer nur der un-geraffte horizont. Ohne das wickelt
        # sich die linie im zeitraffer mehrfach um die bahn, waehrend sie in
        # echtzeit einen einzigen bogen zeigt -- und die Ap/Pe-fahnen stapeln
        # sich uebereinander. GERECHNET wird trotzdem die volle laenge, weil
        # genau die den halt am leben haelt (siehe predictor_warp_length_mult).
        if hasattr(predictor, 'set_display_length'):
            predictor.set_display_length(drawn if wanted > drawn else None)
        # Punktbudget zuerst, damit `set_length` gleich darauf arbeitet.
        # WEICH: der zeitraffer-schritt verstellt den horizont bei jedem
        # stufenwechsel und damit auch das budget -- ein harter reset waere
        # genau der ruckler, den set_length(soft) schon einmal beseitigt hat
        # (34-82 ms im hauptthread, siehe §17).
        points_wanted = int(min(
            PREDICTOR_MAX_POINTS,
            max(1, math.ceil(wanted / max(PREDICTOR_BASE_SPACING, 1e-9))),
        ))
        if points_wanted != int(predictor.num_points):
            predictor.set_num_points(points_wanted, soft=True)
        current = predictor.length
        if current is not None and abs(current - wanted) <= wanted * 1e-9:
```
