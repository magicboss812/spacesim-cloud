# Task 7 report — quantise `_display_point_count()` to stabilise the drawn-view identity

**Status: DONE_WITH_CONCERNS** (one necessary deviation from the brief; see §Deviation).

Date 2026-09-02. Controller ruled the gate satisfied by code reading; implemented with the
warp-hold revert gate (§18/§19/§21/§23) as the safety net. All four gate sections PASS.

---

## What changed — every edit

### 1. `spacesim/predictor.py`

| line(s) | change |
|---|---|
| **2909** | `Predictor.__init__`: added `self._display_quantum = 8` immediately after `self.display_length = None`, with a German comment explaining it is set from config (`predictor.display_length_quantum_points`) and read via `getattr(..., 8)` so a pre-`__init__` / unpickled instance still works. |
| **6309–6312** | `_display_point_count()` primary (spacing-based) return site: after `count = int(math.ceil(limit / spacing)) + 1` added `q = max(1, int(getattr(self, '_display_quantum', 8)))` / `count = int(round(count / q)) * q`, then the unchanged `return max(2, min(n, count))`. |
| **6320–6323** | `_display_point_count()` degenerate/fallback return site: same two lines before the unchanged `return max(2, min(n, count))`. |
| **6259–6263** | `set_display_length()`: **removed** the unconditional `self._clear_display_view()` call, replaced by a German comment. **This is the deviation** — see §Deviation. The method still writes `self.display_length` exactly as before. |

The `limit is None` early return (line ~6294) and the `limit >= spacing * (n - 1)` early
return (line ~6307) are **untouched** — both still mean "draw everything" and return
`None` before the quantiser runs. No `@njit` function was touched.

### 2. `spacesim/test.py`

| line | change |
|---|---|
| **196** | Right after `config.apply_to_predictor(predictor)` (line 193): `predictor._display_quantum = int(config.get('predictor.display_length_quantum_points', 8))` with a two-line German comment. |

### 3. `spacesim/config.json`

| line | change |
|---|---|
| **65** | Added `"display_length_quantum_points": 8,` to the `predictor` section, right after `"horizon_slider_sweep_seconds": 2.5,`. JSON validated (game loads it, `python -c json.load` clean). |

### 4. `spacesim/loader.py`

| line | change |
|---|---|
| **365** | Added `('display_length_quantum_points', None, None),` to the `apply_to_predictor` `_assign` spec (the `attr=None` "known, evaluated in test.py" pattern, same as `quality` / `enabled` / `toggle_num_points`). Without this the key prints as an unknown key at startup. |

*Note:* the sibling keys `horizon_slider_{min,max}_mult` / `horizon_slider_sweep_seconds`
(added in Task 4) are **not** in that spec and still print as unknown keys — pre-existing,
not touched here. My key does **not** appear in that warning (verified in the smoke run).

### 5. `spacesim/tests/horizon_targets_test.py` — new section 5 (lines 155–176)

Added after section 4's `pred.close()`. Builds a fresh `Predictor(async_compute=False,
rolling_mode=False, num_points=2000, precision=1.0e6)`, `initialize` + `set_length(2e9)` +
`update`, then:

```
set_display_length(1.0e9)          -> a = get_points()
set_display_length(1.0e9 + 1.0e6)  -> b = get_points()   check(a is b)      # < 1 quantum
set_display_length(1.0e9 + 5.0e7)  -> c = get_points()   check(c is not b)  # past the quantum
```

**Test-harness adaptation (test setup only, per the brief's licence):** the brief's line
`pred2._compute_full(pred2._make_snapshot(ship, w), w) if hasattr(...)` does not match the
real API — `_make_snapshot(self, ship, world, max_points)` takes 3 args and `_compute_full`
takes `(ship, world)`, not a snapshot. Replaced with the section-4 idiom
`initialize` → `set_length` → `update`, which populates a real `self.points (2000, 5)` at
1e6 m spacing. Also pinned `rolling_mode=False` (bare `async_compute=False` defaults
`rolling_mode` to `True`, per `predictor.py:2774`) so the section exercises the RKN
`self.points` path the game and renderer actually use. `_display_point_count` itself was
**not** changed to fit the test.

### 6. `.claude/rules/predictor.md` (+ a paragraph in the HUD-slider note, ~line 267)

One paragraph: the quantiser, both return sites, the `set_display_length` clear removal
and why `get_points()`'s own three-way check is sufficient, and why §18/§19/§21/§23 are
unaffected (none set a `display_length`).

### 7. `.claude/rules/tests.md` (+ one bullet, ~line 79)

Added `horizon_targets_test.py` to the "Predictor and time warp" list (it was absent),
including the new §5.

---

## Deviation from the brief — `set_display_length` no longer calls `_clear_display_view()`

**The brief's Step 3 ("touch ONLY `_display_point_count` and `__init__`") is insufficient
for its own Step 1 test to pass.** Traced:

1. `set_display_length(x)` calls `_clear_display_view()` → `self._display_view = None`.
2. Next `get_points()` hits `if ... or self._display_view is None:` → **always rebuilds**
   `self.points[:count]`, a fresh object, regardless of whether the quantised `count`
   changed.

So quantising `count` alone cannot make `a is b` true — `set_display_length` blows the
cache away every frame. Confirmed empirically: with the quantiser in place but the clear
still present, `_display_point_count()` returns `992, 992, 1040` for the three test values
(stable across the sub-quantum step) yet `a is b` is **False**.

The minimal correct fix is to stop `set_display_length` from hard-resetting the view.
`get_points()` already invalidates on all real triggers:
`self._display_view_base is not self.points` (array swapped by async / hold),
`self._display_view_limit != count` (rounded count changed), `self._display_view is None`
(first call), and the `count is None` branch calls `_clear_display_view()` itself. Nothing
else in the file references `_display_view*` (grep: only `__init__`, `set_display_length`,
`get_points`, `_clear_display_view`). Removing the call is safe and is precisely the churn
fix the task asks for.

This is one extra line beyond the brief, in `set_display_length` (adjacent to
`_display_point_count`), fully in service of the stated goal. Flagged as a concern below.

---

## TDD — section 5 RED → GREEN

**RED** (quantiser in `_display_point_count`, `set_display_length` clear still present):

```
5. get_points()-identitaet
  FAIL identische view innerhalb eines quantums -- 1502970836240 vs 1502500953168
  ok   quantum-grenze ueberschritten -> neue view
FEHLGESCHLAGEN: 1
```

**GREEN** (after removing the `_clear_display_view()` call from `set_display_length`):

```
5. get_points()-identitaet
  ok   identische view innerhalb eines quantums -- 3076083201488 vs 3076083201488
  ok   quantum-grenze ueberschritten -> neue view

test.horizon_targets: alle pruefungen bestanden
```

All of sections 1–4 remained green throughout.

Underlying numbers (diagnostic run): `n = (2000, 5)`, mid-curve spacing 1e6 m.
`_display_point_count()` → raw 1001 / 1002 / 1051 → quantised **992 / 992 / 1040**.
992 == 992 → same cached view; 1040 ≠ 992 → new view.

---

## Warp-hold regression — `python tests/warp_predictor_test.py`, run ALONE

Exit code 0. `FEHLGESCHLAGEN: 2` — **identical to the baseline**
`.sdd-horizon-slider/snapshots/warp_predictor_test.SERIAL-after-task4.txt`
(which is also `FEHLGESCHLAGEN: 2`).

### The two FAILs — both pre-existing, classified

| fail | this run | baseline (after-task4) | verdict |
|---|---|---|---|
| `jede neue linie gehoert zu einem NEUEREN schiffszustand` | `358 schnappschuesse, kleinste zunahme -0.035 m/s` (a 2nd full run: `359 ... -0.035 m/s`) | `359 schnappschuesse ... -0.035 m/s` | **pre-existing** — documented in `MEMORY.md` (warp-test-preexisting-failures) and `.claude/rules/tests.md` ("one snapshot in ~359 goes backwards by 0.035 m/s"). Same `-0.035 m/s`. Snapshot count varies run-to-run by scheduling (§12 is a real-time burn loop). Not a regression. |
| `die decke senkt die teilschritte bei 1 y/s um mehr als das 20-fache` | `ohne decke 1408, mit decke 1280 (faktor 1)` | `ohne decke 1408, mit decke 1280 (faktor 1)` | **pre-existing** — documented identically ("measured factor 1"). Byte-identical to baseline. Not a regression. |

### The flaky sections — clean this run

- §14 (`puffer` / double-step): all 4 checks `ok` (`0 von 240 bildern`, `0 doppelschritte`).
- §17 (`wechsel-frame billig`): all 28 checks `ok` across the 7 transitions.

Not re-run needed.

### The four gate sections — QUOTED, all PASS

**§18 "Welt und vorhersage rechnen dieselbe bahn" — PASS (8/8):**
```
  ok   das schiff bleibt auf der vorhergesagten linie, bei jeder chunk-groesse -- 5s: 5.198e+01 m  300s: 5.196e+01 m  1000s: 5.192e+01 m
  ok   und die bahn haengt nicht davon ab, wie fein man sie zerlegt -- 1000 s gegen 5 s: 6.784e-02 m
  ok   vertauschte reihenfolge (planets vor dynamics) faellt durch -- 9.382e+06 m gegen 5.192e+01 m
  ok   im zeitraffer bleibt das schiff auf der gehaltenen linie -- groesster seitlicher versatz 1.571e+03 m = 0.016 px ueber 1200 frames (1.5 umlaeufe)
  ok   und keine Ap/Pe-fahne sitzt auf dem schiff, wo es gar kein extremum gibt -- 0 von 1200 frames
  ok   die schranke rechnet pixel in meter um -- 0.5 px bei 1e-5 px/m = 50000.0 m
  ok   und zwar mit dem zoom, nicht fest -- 0.5 px bei 1e-3 px/m = 500.0 m
  ok   0 px heisst AUS, nicht 'null meter erlaubt' -- inf
```

**§19 "Der selbst vorangestellte kopf faelscht die apsis-suche nicht" — PASS (4/4):**
```
  ok   ohne die absicherung erzeugt der versetzte kopf eine fahne am schiff -- erste fahne bei 1.50 punkten (unversetzt 849.0)
  ok   mit skip_head bleibt die fahne dort, wo sie ohne versatz war -- erste fahne bei 849.02 punkten (unversetzt 849.02)
  ok   und sie meldet dieselben fahnen wie die ungestoerte kurve -- 13 gegen 13 fahnen
  ok   ohne halt (skip_head = 0) ist die suche bit-identisch -- gleicher aufruf, gleiches ergebnis
```

**§21 "bahn-zeitskala auf einer mondtransferbahn" — PASS (5/5):**
```
  ok   genug messpunkte fern der koerper (sonst prueft (a) nichts) -- 65 von 84 paaren
  ok   t_char ist fern der koerper stetig (2-%-radiusschritt) -- groesster sprung 1.19x bei r = 4.416e+08 m
  ok   erlaubter frame-schritt bleibt unter einem viertel der umlaufzeit -- groesster anteil 0.218 T bei r = 5.277e+08 m (T = 9.3059e+05 s)
  ok   fernfeld unveraendert: 1 AU ergibt jahr/2pi -- 5.0225e+06 s gegen 5.0225e+06 s
  ok   nahfeld unveraendert: LEO ergibt T/2pi -- 8.8258e+02 s gegen 8.8258e+02 s
```

**§23 "der zeitraffer aendert die gezeichnete linie nicht" — PASS (5/5):**
```
  ok   manuell 1x: raffung x16 laesst die gezeichnete linie stehen -- groesste abweichung 0.0000e+00 m ueber 3.8 tage, 10000 gegen 10000 punkte
  ok   manuell 1x: raffung x64 laesst die gezeichnete linie stehen -- groesste abweichung 0.0000e+00 m ueber 3.8 tage, 10000 gegen 10000 punkte
  ok   manuell 8x: raffung x16 laesst die gezeichnete linie stehen -- groesste abweichung 0.0000e+00 m ueber 31.3 tage, 40000 gegen 40000 punkte
  ok   manuell 8x: raffung x64 laesst die gezeichnete linie stehen -- groesste abweichung 0.0000e+00 m ueber 31.3 tage, 40000 gegen 40000 punkte
  ok   gegenprobe: ohne deckel wandert dieselbe linie um megameter -- groesste abweichung 2.2731e+06 m, nur noch 626 punkte
```

Also §24 (local step ceiling) PASS 13/13; §20 PASS 3/3; §22 PASS 4/4; §11 PASS 4/4;
§9/§10/§12(1 pre-existing FAIL)/§13/§15/§16(1 pre-existing FAIL) as baseline.

**No REVERT triggered.** Why the gate sections are immune: §18, §19, §21, §23 never call
`set_display_length`, so `self.display_length` stays `None`, so `_display_point_count()`
returns `None` at its first line — the quantiser and the `set_display_length` change are
both dead code on those paths.

Full tail is in `.sdd-horizon-slider/snapshots/` was not overwritten; the raw run output
was captured to a scratch file during the session.

---

## Other suites — no new failures

```
python tests/prediction_detail_test.py      -> "vorhersage-detail: alle pruefungen bestanden"   (EXIT 0)
python tests/apsis_stability_test.py         -> "Alle pruefungen bestanden."                     (EXIT 0)
python tests/prediction_projection_test.py   -> "prediction-projektion: alle pruefungen bestanden" (EXIT 0)
python tests/horizon_targets_test.py         -> "test.horizon_targets: alle pruefungen bestanden" (EXIT 0)
```

`apsis_stability_test` is the most relevant cross-check (it drives `get_points()` /
`get_apsis_markers()` under warp): `streuung 0.000e+00 m ueber 200 frames`,
`kleinste punktzahl 10000` — unchanged.

---

## Game smoke — `SPACESIM_MAX_FRAMES=180 python test.py`

Exit code 0. 180 `TIMING:` lines emitted (all 180 frames ran). No traceback / exception.
Frame time ~6.6 ms nominal with occasional 12–14 ms GC/spike frames — matches the
`perf-full-solar-system` memory note, nothing new.
Startup config warning lists only the pre-existing `horizon_slider_*` keys —
`predictor.display_length_quantum_points` is **not** flagged (loader.py registration works).

---

## Self-review

- **Both return sites quantised** — yes, identical two lines, verified by grep (6310–6311,
  6321–6322).
- **`getattr` default** — both sites use `getattr(self, '_display_quantum', 8)`; a
  Predictor built before `__init__` runs, or unpickled, still works.
- **Early returns preserved** — `limit is None` → `None`; `limit >= spacing*(n-1)` → `None`;
  degenerate `total <= 0 or limit >= total` → `None`. Quantiser runs only when a real
  clipped count is produced.
- **Clamp order** — `max(2, min(n, count))` after rounding, so a rounded 0 → 2 and a
  rounded value > n → n. `q = max(1, ...)` guards against a config 0.
- **Numba** — no `@njit` function touched.
- **`set_display_length` semantics** — still writes `self.display_length` byte-for-byte as
  before; only the cache-reset side effect removed.
- **Config valid JSON** — game loads it; key registered in loader so no unknown-key noise.
- **German comments** — all added comments are German, matching `predictor.py`'s older
  style and the brief's verbatim German test comments.

## Concerns

1. **Deviation:** `set_display_length` no longer calls `_clear_display_view()`. Necessary
   for the churn fix (see §Deviation) and safe (`get_points()` fully self-invalidates), but
   it is one line outside the brief's "only `_display_point_count` + `__init__`" scope. If
   the controller wants strict scope, the alternative is to also change `get_points()` to
   not treat `_display_view is None` as forcing a rebuild when count matches — more code,
   same effect. I chose the smaller change.
2. **Not verified interactively.** The gate was ruled satisfied by code reading; smoothness
   during an actual slow drag is asserted by section 5's object-identity check plus the
   `apsis_stability` / warp suites, not by eye. No interactive session available.
3. **`_display_quantum = 8` on a ~10 000-point curve** shifts the drawn end by at most
   ~4 points ≈ 0.04 % of the horizon. Below the renderer's 0.3 px budget and well inside
   §17's `>= 0.95` drawn-fraction check (measured 98.7 %). No visible end-step.
4. The two pre-existing warp FAILs remain; this task does not address them and the brief
   does not ask it to.
