## Task 4: Wire `grabbing` + config into `apply_predictor_horizon`

**Files:**
- Modify: `spacesim/test.py` (config reads, continuous mult clamp helpers, `grabbing` in `apply_predictor_horizon`)
- Modify: `spacesim/config.json`
- Test: `spacesim/tests/horizon_targets_test.py` (add the guard-interaction section)

**Interfaces:**
- Consumes: `horizon_targets(...)` (Task 3); `Predictor.set_display_length(m)`, `Predictor.set_num_points(n, soft=)`, `Predictor.set_length(m)`, `Predictor.length` (all exist).
- Produces:
  - `test.py` module-level constant default lookups: `predictor.horizon_slider_min_mult` (0.25), `predictor.horizon_slider_max_mult` (4.0), `predictor.horizon_slider_sweep_seconds` (2.5).
  - closures `get_predictor_horizon_mult() -> float` and `set_predictor_horizon_mult(mult: float)` (clamps to `[MIN, MAX]`, writes `predictor_manual_mult`).
  - `Hud` receives `horizon_mult_get`, `horizon_mult_set`, `horizon_mult_min`, `horizon_mult_max`, `horizon_sweep_s` — consumed in Task 5.

- [ ] **Step 1: Add the config keys**

In `spacesim/config.json`, inside the `"predictor"` object, after `"length_step_factor": 2.0,` add:

```json
    "horizon_slider_min_mult": 0.25,
    "horizon_slider_max_mult": 4.0,
    "horizon_slider_sweep_seconds": 2.5,
```

(Trailing comma correctness: ensure the object still parses — these go between existing keys, not at the end.)

Verify: `cd spacesim && python -c "import json; json.load(open('config.json')); print('ok')"`

- [ ] **Step 2: Write the failing test (guard interaction)**

Add to `spacesim/tests/horizon_targets_test.py`, before the final summary:

```python
# --- 4. mit realem Predictor: set_length genau einmal je griff -------
print("4. griff-kontrakt gegen einen echten Predictor")
import numpy as np
from predictor import Predictor
from vec import G


class _Body:
    def __init__(self, x, y, mass, radius):
        self.position = type('P', (), {'x': x, 'y': y})()
        self.velocity = type('V', (), {'x': 0.0, 'y': 0.0})()
        self.mass = mass
        self.radius = radius
        self.is_ship = False
        self.name = 'Erde'
        self.fixed = True
        self.is_moon_of = None


class _World:
    def __init__(self):
        self.G = G
        self.time = 0.0
        m = 5.9722e24
        self.erde = _Body(0.0, 0.0, m, 6.371e6)
        self.body = [self.erde]

    def update_planets(self, dt):
        pass


w = _World()
mu = G * w.erde.mass
r = 6.371e6 + 4.0e5
ship = _Body(r, 0.0, 0.0, 0.0)
ship.is_ship = True
ship.name = 'Schiff'
ship.fixed = False
import math as _m
ship.velocity = type('V', (), {'x': 0.0, 'y': _m.sqrt(mu / r) * 1.2})()

pred = Predictor(async_compute=False, num_points=2000, precision=1.0e6)
pred.initialize(ship, w)

calls = {'set_length': 0, 'set_display_length': 0}
_orig_sl, _orig_sdl = pred.set_length, pred.set_display_length
pred.set_length = lambda m, _o=_orig_sl, _c=calls: (_c.__setitem__('set_length', _c['set_length'] + 1), _o(m))[1]
pred.set_display_length = lambda m, _o=_orig_sdl, _c=calls: (_c.__setitem__('set_display_length', _c['set_display_length'] + 1), _o(m))[1]

BASE = pred.num_points * pred.precision
CEIL = 4.0


def apply(mult, grabbing):
    """Der schwanz von test.apply_predictor_horizon, nachgebaut."""
    drawn, wanted = horizon_targets(BASE, mult, 1.0, 40000, 1.0e6,
                                    grabbing=grabbing, ceiling_mult=CEIL)
    pred.set_display_length(drawn if wanted > drawn else None)
    pw = int(min(40000, max(1, _m.ceil(wanted / 1.0e6))))
    if pw != int(pred.num_points):
        pred.set_num_points(pw, soft=True)
    cur = pred.length
    if cur is not None and abs(cur - wanted) <= wanted * 1e-9:
        return
    pred.set_length(wanted)


apply(1.0, grabbing=False)                       # ausgangslage
calls['set_length'] = 0
calls['set_display_length'] = 0

# 30 frames "ziehen": mult waechst, griff gehalten
for i in range(30):
    apply(1.0 + i * 0.1, grabbing=True)
check(calls['set_length'] <= 1, "set_length hoechstens 1x waehrend des griffs",
      f"{calls['set_length']}x")
check(calls['set_display_length'] == 30, "set_display_length jeden frame",
      f"{calls['set_display_length']}x")

# loslassen: ein weiterer set_length auf den settled-wert
before = calls['set_length']
apply(3.9, grabbing=False)
check(calls['set_length'] == before + 1, "beim loslassen genau ein set_length",
      f"{calls['set_length']} (war {before})")

pred.close()
```

- [ ] **Step 3: Run it, verify the new section fails**

Run: `cd spacesim && python tests/horizon_targets_test.py`
Expected: section 4 currently **passes already** (the test replicates the tail itself and calls `horizon_targets` with `grabbing`/`ceiling_mult`, which Task 3 already supports). If section 4 passes, that is fine — it locks the contract. Proceed. (If `Predictor(async_compute=False, ...)` construction fails, fix the stub bodies until `pred.initialize` succeeds — the predictor only needs `position`, `velocity`, `mass`, `radius`, `is_ship`, `fixed`, `is_moon_of`, `name` on each body and `G`, `time`, `body`, `update_planets` on the world.)

- [ ] **Step 4: Add the config reads and closures in `test.py`**

In `spacesim/test.py`, near the other predictor knobs (after line ~214, `predictor_min_precision = ...`), add:

```python
    HORIZON_MULT_MIN = float(config.get('predictor.horizon_slider_min_mult', 0.25))
    HORIZON_MULT_MAX = float(config.get('predictor.horizon_slider_max_mult', 4.0))
    HORIZON_SWEEP_S = float(config.get('predictor.horizon_slider_sweep_seconds', 2.5))
```

Then, immediately after `apply_predictor_horizon` is defined (after line ~590), add:

```python
    def get_predictor_horizon_mult():
        return predictor_manual_mult

    def set_predictor_horizon_mult(mult):
        nonlocal predictor_manual_mult
        predictor_manual_mult = max(HORIZON_MULT_MIN,
                                    min(HORIZON_MULT_MAX, float(mult)))
```

- [ ] **Step 5: Wire `grabbing` into `apply_predictor_horizon`**

In `spacesim/test.py`, change the `horizon_targets` call inside `apply_predictor_horizon()` (edited in Task 3 Step 4) to:

```python
        grabbing = (hud is not None
                    and getattr(hud, 'horizon', None) is not None
                    and hud.horizon.is_grabbing)
        drawn, wanted = horizon_targets(
            PREDICTOR_BASE_LENGTH, predictor_manual_mult,
            predictor_warp_length_mult(),
            PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
            grabbing=grabbing, ceiling_mult=HORIZON_MULT_MAX,
        )
```

`hud` is `None` until it is built (line ~356) and `hud.horizon` is `None` unless the slider is wired (Task 5) — both guarded above, so this is safe to land now.

- [ ] **Step 6: Run tests + game smoke**

Run: `cd spacesim && python tests/horizon_targets_test.py && python tests/ui_horizon_slider_test.py`
Expected: both PASS.

Run: `cd spacesim && python tests/warp_predictor_test.py 2>&1 | tail -40`
Expected: no **new** failures vs. the Task 3 baseline.

Run: `cd spacesim && SPACESIM_MAX_FRAMES=120 python test.py 2>&1 | tail -20`
Expected: clean exit.

- [ ] **Step 7: Review checkpoint**

Summarise: config keys added, closures added, `grabbing` branch live but dormant (no widget yet). Tests green. Wait for approval.

---

