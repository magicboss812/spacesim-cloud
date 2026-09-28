# Task 1 review package

## Files changed
- NEW spacesim/ui/widgets/rate_slider.py
- NEW spacesim/tests/ui_horizon_slider_test.py
- MOD spacesim/ui/widgets/__init__.py

## diff: spacesim/ui/widgets/__init__.py
```diff
--- .sdd-horizon-slider/snapshots/task-1__init__.py.orig	2026-09-02 21:54:25.687879200 +0200
+++ spacesim/ui/widgets/__init__.py	2026-09-02 21:56:18.804471700 +0200
@@ -1,16 +1,17 @@
-"""Wiederverwendbare bedienelemente des spieler-HUDs.
-
-Alle rechnen in top-down bildschirmpixeln und zeichnen ueber ctx.draw /
-ctx.text -- keines fasst moderngl direkt an.
-"""
-
-from .button import Button, SegmentedControl, Toggle
-from .dropdown import Dropdown
-from .label import Label, Readout
-from .panel import Group, Panel, Stack
-from .slider import Slider
-
-__all__ = [
-    'Button', 'Dropdown', 'Group', 'Label', 'Panel', 'Readout',
-    'SegmentedControl', 'Slider', 'Stack', 'Toggle',
-]
+"""Wiederverwendbare bedienelemente des spieler-HUDs.
+
+Alle rechnen in top-down bildschirmpixeln und zeichnen ueber ctx.draw /
+ctx.text -- keines fasst moderngl direkt an.
+"""
+
+from .button import Button, SegmentedControl, Toggle
+from .dropdown import Dropdown
+from .label import Label, Readout
+from .panel import Group, Panel, Stack
+from .rate_slider import HorizonSlider
+from .slider import Slider
+
+__all__ = [
+    'Button', 'Dropdown', 'Group', 'HorizonSlider', 'Label', 'Panel',
+    'Readout', 'SegmentedControl', 'Slider', 'Stack', 'Toggle',
+]
```

## NEW FILE: spacesim/ui/widgets/rate_slider.py
```python
"""Mittenzentrierter RATEN-regler.

Zieht man ihn aus der mitte, aendert sich die gesteuerte groesse WEITER,
solange man haelt -- die auslenkung ist die GESCHWINDIGKEIT der aenderung,
nicht ihr zielwert. Loslassen federt weich in die mitte zurueck.

Getrennt von ui/widgets/slider.py (das ist ein LAGE-regler), weil die
interaktion eine voellig andere ist -- ein `log=`-schalter reichte nicht.

Benutzt fuer den vorhersage-horizont: die gezeichnete linienlaenge folgt
der auslenkung jeden frame ueber predictor.set_display_length() (O(1), kein
neuaufbau). Siehe plans/predictor_horizon_slider_design.md.
"""

import math

from ..core import Rect, Widget, ease
from ..theme import mix

#: Totzone um die mitte. Darunter zaehlt die auslenkung als null -- sonst
#: zittert der federweg beim zuruecklaufen noch winzige aenderungen ein,
#: und ein regler, der im ruhezustand nicht ruht, ist unbrauchbar.
DEADZONE = 0.06


def _response(offset):
    """Auslenkung [-1, 1] -> raten-faktor [-1, 1].

    Null in der totzone, sonst `sign * ((|x| - dz) / (1 - dz)) ** 1.8`. Die
    potenz gibt feines gefuehl nahe der mitte und volle geschwindigkeit am
    anschlag; ohne sie ist der regler bei kleiner auslenkung schon zu schnell.
    """
    magnitude = abs(float(offset))
    if magnitude <= DEADZONE:
        return 0.0
    scaled = (magnitude - DEADZONE) / (1.0 - DEADZONE)
    return math.copysign(scaled ** 1.8, offset)


class HorizonSlider(Widget):
    """Waagerechter raten-regler mit federrueckstellung in die mitte."""

    def __init__(self, value, minimum, maximum, on_change, predictor=None,
                 sweep_seconds=2.5, wheel_step=2.0, role='frame',
                 size=(168.0, None), **kwargs):
        super().__init__(size=size, **kwargs)
        self.value = value              # callable -> aktueller multiplikator
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.on_change = on_change
        self.predictor = predictor
        self.sweep_seconds = max(float(sweep_seconds), 1e-3)
        self.wheel_step = float(wheel_step)
        self.role = role
        self.blocks_mouse = True
        self._offset = 0.0

    # ------------------------------------------------------------- werte
    def resolve_value(self):
        return float(self.value() if callable(self.value) else self.value)

    @property
    def is_grabbing(self):
        return bool(self.pressed) and abs(self._offset) > DEADZONE

    def _clamp_mult(self, mult):
        return max(self.minimum, min(self.maximum, float(mult)))

    # ------------------------------------------------------------ layout
    def _tab_h(self, ctx):
        return ctx.text.measure('X', 'tab')[1] + ctx.px(4.0)

    def _readout_h(self, ctx):
        return ctx.text.measure('X', 'mono_readout')[1] + ctx.px(4.0)

    def measure(self, ctx):
        track = ctx.px(5.0)
        knob = ctx.px(18.0)
        height = self._tab_h(ctx) + self._readout_h(ctx) + max(track, knob) + ctx.px(6.0)
        return (ctx.px(168.0), height)

    def _track_rect(self, ctx):
        h = ctx.px(5.0)
        top_band = self._tab_h(ctx) + self._readout_h(ctx)
        free = self.rect.h - top_band - h
        top = self.rect.y + top_band + max(0.0, free) * 0.5
        return Rect(self.rect.x, top, self.rect.w, h)

    # ------------------------------------------------------------ eingabe
    def _offset_from_x(self, ctx, x):
        track = self._track_rect(ctx)
        half = track.w * 0.5
        if half <= 0.0:
            return 0.0
        return max(-1.0, min(1.0, (float(x) - track.center_x) / half))

    def on_mouse_down(self, ctx, x, y, button):
        if button == 1 and self.enabled:
            self._offset = self._offset_from_x(ctx, x)
        return True

    def on_mouse_move(self, ctx, x, y):
        if self.pressed and self.enabled:
            self._offset = self._offset_from_x(ctx, x)
            return True
        return False

    def on_wheel(self, ctx, dx, dy):
        if not self.enabled or not dy:
            return False
        factor = self.wheel_step ** (1.0 if dy > 0 else -1.0)
        if self.on_change is not None:
            self.on_change(self._clamp_mult(self.resolve_value() * factor))
        return True

    # ------------------------------------------------------------ update
    def update(self, ctx, dt):
        super().update(ctx, dt)          # _hover_t / _press_t
        if self.predictor is not None:
            self.enabled = int(getattr(self.predictor, 'num_points', 1)) > 0
        if not self.pressed:
            self._offset = ease(self._offset, 0.0, ctx.theme.motion.fast, dt)
        f = _response(self._offset)
        if f != 0.0 and self.enabled and self.on_change is not None:
            # Exponentiell (linear im logarithmus): so fuehlt sich die
            # bewegung ueber die ganze spanne gleich an -- der horizont wird
            # in dekaden wahrgenommen, nicht in metern.
            k = math.log(self.maximum / self.minimum) / self.sweep_seconds
            new = self.resolve_value() * math.exp(k * f * float(dt))
            self.on_change(self._clamp_mult(new))

    # draw() kommt in Task 2.
```

## NEW FILE: spacesim/tests/ui_horizon_slider_test.py
```python
"""Kopftest fuer ui/widgets/rate_slider.py -- die federphysik und die
ratensteuerung. Laeuft ohne fenster, ohne GL: der widget-code fasst in
update()/on_*() nur ctx.px, ctx.theme und die callables an, alles davon
laesst sich stellen.

Aufruf: python tests/ui_horizon_slider_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ui.core import Rect
from ui.widgets.rate_slider import DEADZONE, HorizonSlider, _response

FAILURES = []


def check(condition, label, detail=''):
    if condition:
        print(f"  ok   {label}{(' -- ' + detail) if detail else ''}")
    else:
        FAILURES.append(f"{label}: {detail}")
        print(f"  FAIL {label} -- {detail}")


class _Motion:
    fast = 22.0
    normal = 14.0
    slow = 8.0


class _Theme:
    motion = _Motion()
    control_height = 24.0


class _Text:
    def measure(self, s, role):
        return (8.0 * len(str(s)), 12.0)


class _Ctx:
    """Das Nötigste, das der Widget-Code berührt."""
    def __init__(self):
        self.theme = _Theme()
        self.text = _Text()
        self.dt = 0.0

    def px(self, v):
        if isinstance(v, (tuple, list)):
            return tuple(float(x) for x in v)
        return float(v)


class _Predictor:
    def __init__(self, num_points=10000):
        self.num_points = num_points


def make(value_box, minimum=0.25, maximum=4.0, sweep=2.5, predictor=None):
    """value_box ist eine 1-elementige liste, damit on_change zurueckschreibt."""
    def getter():
        return value_box[0]

    def setter(m):
        value_box[0] = m

    w = HorizonSlider(getter, minimum, maximum, setter,
                      predictor=predictor, sweep_seconds=sweep)
    w.rect = Rect(0.0, 0.0, 168.0, 60.0)
    w.enabled = True
    return w


def drive(widget, ctx, seconds, dt=1.0 / 60.0):
    steps = int(round(seconds / dt))
    for _ in range(steps):
        widget.update(ctx, dt)


ctx = _Ctx()

# --- 1. Totzone: kleine auslenkung aendert nichts -----------------------
print("1. Totzone")
box = [1.0]
w = make(box)
w._offset = DEADZONE * 0.5
w.pressed = True
drive(w, ctx, 2.0)
check(box[0] == 1.0, "innerhalb der totzone bleibt der wert stehen",
      f"wert {box[0]}")
w._offset = 0.5
w.pressed = True
drive(w, ctx, 0.2)
check(box[0] > 1.0, "ausserhalb der totzone steigt der wert", f"wert {box[0]:.3f}")

# --- 2. Raten-proportionalitaet ---------------------------------------
print("2. Raten-proportionalitaet")
box = [0.25]
w = make(box)
w._offset = 1.0
w.pressed = True
drive(w, ctx, 2.5)            # sweep_seconds bei voller auslenkung
check(abs(box[0] - 4.0) <= 4.0 * 0.05,
      "volle auslenkung fuer sweep_seconds -> min..max", f"wert {box[0]:.3f}")

box = [0.25]
w = make(box)
w._offset = 0.5
w.pressed = True
drive(w, ctx, 2.5)
check(box[0] < 0.25 + (4.0 - 0.25) * 0.6,
      "halbe auslenkung ist deutlich langsamer", f"wert {box[0]:.3f}")

# --- 3. Rueckweg ----------------------------------------------------------
print("3. Rueckweg zur mitte")
box = [4.0]
w = make(box)
w._offset = -1.0
w.pressed = True
drive(w, ctx, 2.5)
check(abs(box[0] - 0.25) <= 0.25 * 0.10 + 0.02,
      "voll nach links -> zurueck auf min", f"wert {box[0]:.4f}")

# --- 4. Feder laeuft in die mitte, aenderung stoppt --------------------
print("4. Federweg")
box = [1.0]
w = make(box)
w._offset = 0.8
w.pressed = False
drive(w, ctx, 0.4)
check(abs(w._offset) < DEADZONE, "offset zerfaellt in die totzone",
      f"offset {w._offset:.4f}")
frozen = box[0]
drive(w, ctx, 2.0)
check(box[0] == frozen, "nach dem federweg keine weitere aenderung",
      f"{box[0]} == {frozen}")

# gedrueckt gehalten: offset bleibt stehen
w2 = make([1.0])
w2._offset = 0.7
w2.pressed = True
drive(w2, ctx, 0.5)
check(abs(w2._offset - 0.7) < 1e-9, "gedrueckt haelt der offset",
      f"offset {w2._offset}")

# --- 5. Klemmung --------------------------------------------------------
print("5. Klemmung auf [min, max]")
import random
random.seed(1)
box = [1.0]
w = make(box)
w.pressed = True
ok = True
for _ in range(600):
    w._offset = random.uniform(-1.0, 1.0)
    w.update(ctx, 1.0 / 60.0)
    if not (0.25 - 1e-9 <= box[0] <= 4.0 + 1e-9):
        ok = False
        break
check(ok, "der wert verlaesst [0.25, 4.0] nie", f"wert {box[0]:.4f}")

# --- 6. is_grabbing ---------------------------------------------------
print("6. is_grabbing")
w = make([1.0])
w.pressed = False
w._offset = 1.0
check(not w.is_grabbing, "nicht gedrueckt -> kein grabbing", "")
w.pressed = True
w._offset = 0.0
check(not w.is_grabbing, "gedrueckt in der mitte -> kein grabbing", "")
w._offset = 0.5
check(w.is_grabbing, "gedrueckt und ausgelenkt -> grabbing", "")

# --- 7. Mausrad -------------------------------------------------------
print("7. Mausrad-raste")
box = [1.0]
w = make(box)
w.on_wheel(ctx, 0, 1)
check(abs(box[0] - 2.0) < 1e-9, "eine raste hoch = x wheel_step", f"wert {box[0]}")
w.on_wheel(ctx, 0, -1)
check(abs(box[0] - 1.0) < 1e-9, "eine raste runter = / wheel_step", f"wert {box[0]}")
for _ in range(10):
    w.on_wheel(ctx, 0, 1)
check(box[0] == 4.0, "das rad klemmt auch", f"wert {box[0]}")

# --- 8. _response-kurve --------------------------------------------------
print("8. _response")
check(_response(0.0) == 0.0, "_response(0) == 0", "")
check(_response(DEADZONE * 0.9) == 0.0, "_response in der totzone == 0", "")
check(_response(1.0) == 1.0, "_response(1) == 1", f"{_response(1.0)}")
check(_response(-1.0) == -1.0, "_response(-1) == -1", f"{_response(-1.0)}")
check(0.0 < _response(0.5) < 0.5, "_response(0.5) unter der geraden",
      f"{_response(0.5):.3f}")

# --- 9. abgeschaltet bei predictor.num_points == 0 --------------------
print("9. Abgeschaltet ohne vorhersage")
box = [1.0]
pred = _Predictor(num_points=0)
w = make(box, predictor=pred)
w._offset = 1.0
w.pressed = True
w.update(ctx, 1.0 / 60.0)
check(w.enabled is False, "num_points == 0 -> enabled False", "")
check(box[0] == 1.0, "abgeschaltet aendert der regler nichts", f"wert {box[0]}")
w.on_mouse_down(ctx, 80.0, 30.0, 1)
check(box[0] == 1.0, "abgeschaltet ignoriert er klicks", f"wert {box[0]}")
pred.num_points = 10000
w.update(ctx, 1.0 / 60.0)
check(w.enabled is True, "num_points zurueck -> enabled True", "")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("ui/widgets/rate_slider.py: alle pruefungen bestanden")
```
