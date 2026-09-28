# Task 7 review package

## diff: spacesim/predictor.py
```diff
--- .sdd-horizon-slider/snapshots/task-7-predictor.py.base	2026-09-02 22:54:43.746098400 +0200
+++ spacesim/predictor.py	2026-09-02 23:00:30.211844200 +0200
@@ -2900,6 +2900,13 @@
         # waehrend sie in echtzeit einen einzigen bogen zeigt.
         # None = alles zeichnen. Siehe set_display_length().
         self.display_length = None
+        # Die GEZEICHNETE punktzahl wird auf ein vielfaches hiervon gerundet,
+        # damit ein langsamer regler-zug nicht in JEDEM frame eine neue view
+        # (self.points[:count]) erzeugt -- der renderer-cache und
+        # get_apsis_markers() haengen an id(points). Aus config gesetzt
+        # (predictor.display_length_quantum_points), getattr-default weil eine
+        # vor __init__ gebaute (oder entpickelte) instanz sie nicht traegt.
+        self._display_quantum = 8
         self._display_view = None
         self._display_view_base = None
         self._display_view_limit = -1
@@ -6249,7 +6256,11 @@
         else:
             value = float(metres)
             self.display_length = value if value > 0.0 else None
-        self._clear_display_view()
+        # KEIN _clear_display_view() hier: der regler ruft diese methode jeden
+        # frame, und ein harter cache-reset erzwaenge trotz gerundetem count
+        # (siehe _display_point_count) je frame eine neue view. get_points()
+        # verwirft die view schon selbst, sobald sich der gerundete count,
+        # das zugrundeliegende array oder der zeichne-alles-fall aendert.
 
     def _clear_display_view(self):
         self._display_view = None
@@ -6296,6 +6307,8 @@
             if limit >= spacing * (n - 1):
                 return None
             count = int(math.ceil(limit / spacing)) + 1
+            q = max(1, int(getattr(self, '_display_quantum', 8)))
+            count = int(round(count / q)) * q
             return max(2, min(n, count))
 
         # Entartete kurve (stillstand, NaN) -- alter weg als rueckfall.
@@ -6305,6 +6318,8 @@
         if total <= 0.0 or limit >= total:
             return None
         count = int(math.ceil(n * (limit / total)))
+        q = max(1, int(getattr(self, '_display_quantum', 8)))
+        count = int(round(count / q)) * q
         return max(2, min(n, count))
 
     def get_points(self):
```

## diff: spacesim/test.py
```diff
--- .sdd-horizon-slider/snapshots/task-7-test.py.base	2026-09-02 22:54:43.802290400 +0200
+++ spacesim/test.py	2026-09-02 23:00:34.718736600 +0200
@@ -191,6 +191,9 @@
     predictor = Predictor(recompute_every_update=True, **predictor_kwargs)
     # Übrige Predictor-Parameter (Qualität, Toleranzen, Apsis-Marker) aus config.json
     config.apply_to_predictor(predictor)
+    # Auf wie viele punkte die GEZEICHNETE laenge gerundet wird -- haelt die
+    # view-identitaet (get_points()) waehrend eines langsamen regler-zugs stehen.
+    predictor._display_quantum = int(config.get('predictor.display_length_quantum_points', 8))
     # Look-ahead horizon (length) is the cost knob; point spacing (precision) is
     # cosmetic. Pin the horizon from startup so changing spacing ('9'/'0') no
     # longer moves the horizon (and thus no longer changes compute cost).
```

## diff: spacesim/config.json
```diff
--- .sdd-horizon-slider/snapshots/task-7-config.json.base	2026-09-02 22:54:43.764785300 +0200
+++ spacesim/config.json	2026-09-02 23:01:19.948889800 +0200
@@ -62,6 +62,7 @@
     "horizon_slider_min_mult": 0.25,
     "horizon_slider_max_mult": 4.0,
     "horizon_slider_sweep_seconds": 2.5,
+    "display_length_quantum_points": 8,
     "precision_step_factor": 2.0,
     "min_precision": 1.0,
     "auto_precision_from_zoom": true,
```

## diff: spacesim/tests/horizon_targets_test.py (section 5 added)
```diff
--- .sdd-horizon-slider/snapshots/task-7-horizon_targets_test.py.base	2026-09-02 22:54:43.784121400 +0200
+++ spacesim/tests/horizon_targets_test.py	2026-09-02 22:59:55.628672600 +0200
@@ -152,6 +152,30 @@
 
 pred.close()
 
+# --- 5. view-identitaet bleibt stehen innerhalb eines quantums --------
+# Der regler ruft set_display_length() JEDEN frame waehrend des ziehens.
+# get_points() gibt self.points[:count] heraus; aendert sich count je frame,
+# entsteht je frame eine neue view -- der renderer-cache und
+# get_apsis_markers() (beide auf id(points)) verfehlen dann jeden frame.
+# _display_quantum rundet count auf ein vielfaches, so bleibt die view-
+# identitaet ueber die meisten zug-frames stehen.
+print("5. get_points()-identitaet")
+pred2 = Predictor(async_compute=False, rolling_mode=False,
+                  num_points=2000, precision=1.0e6)
+pred2.initialize(ship, w)
+pred2.set_length(2000 * 1.0e6)
+pred2.update(ship, w)
+
+pred2.set_display_length(1.0e9)
+a = pred2.get_points()
+pred2.set_display_length(1.0e9 + 1.0e6)      # < 8 punkte weiter
+b = pred2.get_points()
+check(a is b, "identische view innerhalb eines quantums", f"{id(a)} vs {id(b)}")
+pred2.set_display_length(1.0e9 + 5.0e7)      # deutlich weiter
+c = pred2.get_points()
+check(c is not b, "quantum-grenze ueberschritten -> neue view", "")
+pred2.close()
+
 print()
 if FAILURES:
     print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
```

## loader.py — line 365 area (implementer registered display_length_quantum_points)
```python
            ('async_compute', None, None),
            ('rolling_mode', None, None),
            ('strict_snapshot_matching', 'strict_snapshot_matching', bool),
            ('use_time_dependent_bodies', 'use_time_dependent_bodies', bool),
            # laufzeit-regler
            ('min_precision', 'min_precision', float),
            ('auto_precision_from_zoom', 'auto_precision_from_zoom', bool),
            ('target_screen_step_px', 'target_screen_step_px', float),
            ('force_sync_on_stale', 'force_sync_on_stale', bool),
            ('use_reference_acceleration_correction', 'use_reference_acceleration_correction', bool),
            ('rkn_adaptive_far_maxdt', 'rkn_adaptive_far_maxdt', bool),
            ('rkn_far_field_target_steps', 'rkn_far_field_target_steps', float),
            ('rkn_max_dt_ceiling', 'rkn_max_dt_ceiling', float),
            ('apsis_markers_enabled', 'apsis_markers_enabled', bool),
            ('apsis_max_markers', 'apsis_max_markers', int),
            # Gleichzeitige vorhersagen unter schub. Eine rechnung dauert
            # laenger als ein bild, also gibt erst der DURCHSATZ mehrerer
            # zeitversetzter laeufe eine bildweise nachziehende linie.
            # 1 = wie vorher (eine nach der anderen).
            ('thrust_pipeline_depth', 'thrust_pipeline_depth', int),
            # Jitter-puffer fuer das einwechseln fertiger vorhersagen.
            # 0 = immer sofort das neueste (kuerzeste verzoegerung, aber
            # ruckartig), 2 = vollstaendig gleichmaessig, dafuer aeltere linie.
            ('swap_backlog_max', 'swap_backlog_max', int),
            # nur von test.py ausgewertet (tastenbelegung / ein-aus-verhalten)
            ('display_length_quantum_points', None, None),
            ('quality', None, None),
            ('enabled', None, None),
            ('toggle_num_points', None, None),
```

## CONTEXT: current get_points() and _clear_display_view() (unchanged by Task 7, needed to judge the set_display_length change)
```python
    def _clear_display_view(self):
        self._display_view = None
        self._display_view_base = None
        self._display_view_limit = -1

    def _display_point_count(self):
        """Zahl der zu zeichnenden fuehrenden punkte, oder None fuer alle.

        Ueber den INDEXANTEIL, nicht ueber die aufsummierte bogenlaenge: der
        kernel legt seine stuetzstellen auf festen abstand, der anteil ist
        also der laengenanteil -- und er kostet O(1) statt O(n) je frame.

        Der abstand wird an den GESPEICHERTEN punkten gemessen, nicht aus
        `self.length` erschlossen. Das ist derselbe O(1)-griff, aber er fragt
        die kurve, die wirklich da liegt, statt die zuletzt ANGEFORDERTE
        laenge fuer sie zu halten. Beim zeitraffer-stufenwechsel fallen die
        beiden fuer ein paar frames auseinander: `set_length()` stellt schon
        auf 4x, waehrend der halt noch die alte 1x-kurve zeigt (die neue
        entsteht im hintergrund, siehe _request_hold_recompute). Mit
        `self.length` als bezug waeren davon 1/4 gezeichnet worden -- die
        linie waere auf 25 % zusammengefallen und beim einwechseln wieder
        aufgesprungen. Gemessen: 25.0 % / 24.9 % / 24.8 % auf den drei
        aufwaerts-wechseln.

        Gemessen wird in der MITTE der kurve: points[0] ist im halt das
        schiff selbst und traegt ein absichtlich verkuerztes erstes
        teilstueck (siehe _hold_advance), waere als massstab also zu klein.
        """
        limit = self.display_length
        if limit is None:
            return None
        pts = self.points
        if np is None or not isinstance(pts, np.ndarray):
            return None
        n = int(pts.shape[0])
        if n <= 2:
            return None

        mid = n // 2
        spacing = math.hypot(float(pts[mid, 0]) - float(pts[mid - 1, 0]),
                             float(pts[mid, 1]) - float(pts[mid - 1, 1]))
        if spacing > 0.0 and math.isfinite(spacing):
            if limit >= spacing * (n - 1):
                return None
            count = int(math.ceil(limit / spacing)) + 1
            q = max(1, int(getattr(self, '_display_quantum', 8)))
            count = int(round(count / q)) * q
            return max(2, min(n, count))

        # Entartete kurve (stillstand, NaN) -- alter weg als rueckfall.
        total = self.length
        if total is None or total <= 0.0:
            total = float(self.num_points) * float(self.precision)
        if total <= 0.0 or limit >= total:
            return None
        count = int(math.ceil(n * (limit / total)))
        q = max(1, int(getattr(self, '_display_quantum', 8)))
        count = int(round(count / q)) * q
        return max(2, min(n, count))

    def get_points(self):
        """Die zu ZEICHNENDE kurve (siehe set_display_length).

        Der ausschnitt wird gemerkt und nur neu gebildet, wenn sich das
        zugrundeliegende array oder die zahl aendert. Das ist kein geiz:
        Renderer._make_prediction_line_cache_key nimmt `id(path_points)` in
        den schluessel auf, ein frisch erzeugter view je aufruf wuerde den
        cache also in JEDEM frame verfehlen.
        """
        count = self._display_point_count()
        if count is None:
            self._clear_display_view()
            return self.points
        # `is` statt id(): so haelt der vergleich eine referenz und kann nicht
        # auf eine wiederverwendete id hereinfallen.
        if (self._display_view_base is not self.points
                or self._display_view_limit != count
                or self._display_view is None):
            self._display_view = self.points[:count]
            self._display_view_base = self.points
            self._display_view_limit = count
        return self._display_view
```

## NOTE: predictor.md — Task 7 MERGED its quantisation paragraph into Task 6's existing 'HUD horizon slider' block (verified: grep -c = 1, no duplicate). tests.md got a 2-line addition at L84-85.
