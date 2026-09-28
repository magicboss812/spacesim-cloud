# Predictor Horizon Slider — final whole-branch review package

Plan: plans/2026-09-02-predictor-horizon-slider.md   Spec: plans/predictor_horizon_slider_design.md
No git in this repo. Diffs are `diff -u` vs pre-plan snapshots. 7 tasks, each task-reviewed and approved.

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
        # Spur einwaerts gesetzt: die '-'/'+'-endglyphen sitzen px(9)+px(3)
        # AUSSERHALB der spur, und ohne diesen einzug ragte das minus ueber
        # die widget-kante hinaus fast bis an den bildschirmrand.
        inset = ctx.px(12.0)
        h = ctx.px(5.0)
        top_band = self._tab_h(ctx) + self._readout_h(ctx)
        free = self.rect.h - top_band - h
        top = self.rect.y + top_band + max(0.0, free) * 0.5
        return Rect(self.rect.x + inset, top, self.rect.w - inset * 2.0, h)

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

    # ------------------------------------------------------------ zeichnen
    def _horizon_metres(self):
        pred = self.predictor
        if pred is not None:
            try:
                length = pred.get_display_length()
            except Exception:
                length = None
            if length and math.isfinite(length):
                return float(length)
        return None

    def draw(self, ctx):
        # Lazy, sonst zieht ui/widgets/__init__ das ganze ui/hud-paket beim
        # import herein (layout.py importiert wiederum ui/widgets -> zyklus).
        from ..hud import chrome
        from .. import units

        palette = ctx.theme.palette
        color = palette.accent_for(self.role)          # cyan = daten/rahmen
        track = self._track_rect(ctx)
        enabled = self.enabled

        # Notch-tab auf der oberkante.
        chrome.tab(ctx, chrome.tab_text('PREDICT'),
                   track.x + ctx.px(12.0), self.rect.y + self._tab_h(ctx),
                   color=color if enabled else palette.text_dim, edge='top')

        # Ablesewert: die GEZEICHNETE horizontlaenge, aus dem predictor
        # zurueckgelesen -- nie lokal gehalten.
        metres = self._horizon_metres()
        ctx.text.draw(
            units.distance(metres) if metres is not None else '--',
            self.rect.right, self.rect.y + self._tab_h(ctx),
            role='mono_readout',
            color=palette.text if enabled else palette.text_dim,
            align='right',
        )

        # Spur.
        ctx.draw.rect(track.x, track.y, track.w, track.h,
                      fill=palette.panel_sunken, radius=track.h * 0.5)

        # Mittenkerbe.
        tick_w = max(1.0, ctx.px(2.0))
        ctx.draw.rect(track.center_x - tick_w * 0.5, track.y - ctx.px(2.0),
                      tick_w, track.h + ctx.px(4.0),
                      fill=palette.text if enabled else palette.text_dim)

        # Fuellbalken von der MITTE zum knauf -- richtung, nicht lage.
        knob_x = track.center_x + track.w * 0.5 * self._offset
        if enabled and abs(self._offset) > DEADZONE:
            lo, hi = sorted((track.center_x, knob_x))
            fill = color if self._offset > 0.0 else palette.text_dim
            ctx.draw.rect(lo, track.y, max(track.h, hi - lo), track.h,
                          fill=fill, radius=track.h * 0.5)

        # Endkappen-glyphen.
        gy = track.center_y
        gr = ctx.px(3.0)
        gcol = palette.text_muted if enabled else palette.text_dim
        gw = max(1.0, ctx.px(1.4))
        ctx.draw.line(track.x - ctx.px(9.0) - gr, gy, track.x - ctx.px(9.0) + gr,
                      gy, gcol, width=gw)                      # minus links
        ctx.draw.line(track.right + ctx.px(9.0) - gr, gy,
                      track.right + ctx.px(9.0) + gr, gy, gcol, width=gw)
        ctx.draw.line(track.right + ctx.px(9.0), gy - gr,
                      track.right + ctx.px(9.0), gy + gr, gcol, width=gw)  # plus

        # Knauf.
        knob_r = ctx.px(7.0) + ctx.px(1.5) * self._hover_t
        ctx.draw.circle(
            knob_x, track.center_y, knob_r,
            fill=mix(palette.text, palette.accent_strong, self._press_t)
            if enabled else palette.text_dim,
            border_color=palette.panel_sunken, border_width=ctx.theme.border_width,
        )
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

# --- 10. _horizon_metres liest aus dem predictor zurueck --------------
print("10. _horizon_metres")


class _PredLen:
    def __init__(self, length):
        self.num_points = 10000
        self._length = length

    def get_display_length(self):
        return self._length


w = make([1.0], predictor=_PredLen(2.4e10))
check(w._horizon_metres() == 2.4e10, "gibt die predictor-laenge zurueck",
      f"{w._horizon_metres()}")
w = make([1.0], predictor=_PredLen(None))
check(w._horizon_metres() is None, "None bleibt None", "")
w = make([1.0], predictor=_PredLen(float('inf')))
check(w._horizon_metres() is None, "inf wird zu None", "")

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("ui/widgets/rate_slider.py: alle pruefungen bestanden")
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

# --- 5. view-identitaet bleibt stehen innerhalb eines quantums --------
# Der regler ruft set_display_length() JEDEN frame waehrend des ziehens.
# get_points() gibt self.points[:count] heraus; aendert sich count je frame,
# entsteht je frame eine neue view -- der renderer-cache und
# get_apsis_markers() (beide auf id(points)) verfehlen dann jeden frame.
# _display_quantum rundet count auf ein vielfaches, so bleibt die view-
# identitaet ueber die meisten zug-frames stehen.
print("5. get_points()-identitaet")
pred2 = Predictor(async_compute=False, rolling_mode=False,
                  num_points=2000, precision=1.0e6)
pred2.initialize(ship, w)
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

print()
if FAILURES:
    print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("test.horizon_targets: alle pruefungen bestanden")
```

## diff: spacesim/ui/widgets/__init__.py
```diff
--- .sdd-horizon-slider/snapshots/task-1__init__.py.orig	2026-09-02 21:54:25.687879200 +0200
+++ spacesim/ui/widgets/__init__.py	2026-09-02 21:56:18.804471700 +0200
@@ -8,9 +8,10 @@
 from .dropdown import Dropdown
 from .label import Label, Readout
 from .panel import Group, Panel, Stack
+from .rate_slider import HorizonSlider
 from .slider import Slider
 
 __all__ = [
-    'Button', 'Dropdown', 'Group', 'Label', 'Panel', 'Readout',
-    'SegmentedControl', 'Slider', 'Stack', 'Toggle',
+    'Button', 'Dropdown', 'Group', 'HorizonSlider', 'Label', 'Panel',
+    'Readout', 'SegmentedControl', 'Slider', 'Stack', 'Toggle',
 ]
```

## diff: spacesim/test.py
```diff
--- .sdd-horizon-slider/snapshots/test.py.base	2026-09-02 21:55:20.777581700 +0200
+++ spacesim/test.py	2026-09-02 23:00:34.718736600 +0200
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
@@ -169,6 +191,9 @@
     predictor = Predictor(recompute_every_update=True, **predictor_kwargs)
     # Übrige Predictor-Parameter (Qualität, Toleranzen, Apsis-Marker) aus config.json
     config.apply_to_predictor(predictor)
+    # Auf wie viele punkte die GEZEICHNETE laenge gerundet wird -- haelt die
+    # view-identitaet (get_points()) waehrend eines langsamen regler-zugs stehen.
+    predictor._display_quantum = int(config.get('predictor.display_length_quantum_points', 8))
     # Look-ahead horizon (length) is the cost knob; point spacing (precision) is
     # cosmetic. Pin the horizon from startup so changing spacing ('9'/'0') no
     # longer moves the horizon (and thus no longer changes compute cost).
@@ -212,6 +237,9 @@
     precision_step = max(float(config.get('predictor.precision_step_factor', 2.0)), 1.0 + 1e-9)
     predictor_toggle_points = int(config.get('predictor.toggle_num_points', 30))
     predictor_min_precision = float(config.get('predictor.min_precision', 1.0))
+    HORIZON_MULT_MIN = float(config.get('predictor.horizon_slider_min_mult', 0.25))
+    HORIZON_MULT_MAX = float(config.get('predictor.horizon_slider_max_mult', 4.0))
+    HORIZON_SWEEP_S = float(config.get('predictor.horizon_slider_sweep_seconds', 2.5))
     if verbose:
         print(f"PREDICTOR DEBUG: async_compute = {predictor.async_compute}")
         print(f"PREDICTOR DEBUG: force_sync_on_stale = {predictor.force_sync_on_stale}")
@@ -345,6 +373,14 @@
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
@@ -358,6 +394,11 @@
             tick_rate=float(max(1, FPS)),
             realtime_warp_max=REALTIME_WARP_MAX,
             warp_timescale_divisor=WARP_TIMESCALE_DIVISOR,
+            horizon_mult_get=get_predictor_horizon_mult,
+            horizon_mult_set=set_predictor_horizon_mult,
+            horizon_mult_min=HORIZON_MULT_MIN,
+            horizon_mult_max=HORIZON_MULT_MAX,
+            horizon_sweep_s=HORIZON_SWEEP_S,
         )
 
     # Taste Home holt die ansicht zum schiff zurueck -- der weg heraus aus
@@ -561,10 +602,14 @@
         # Hat der spieler mit '+' bereits ueber das budget hinaus verlaengert,
         # faellt der raffungsfaktor auf 1: seine eigene vergroeberung bleibt
         # (die ist gewollt und dokumentiert), die der raffung kommt nicht dazu.
-        drawn, wanted = predictor_horizon_lengths(
+        grabbing = (hud is not None
+                    and getattr(hud, 'horizon', None) is not None
+                    and hud.horizon.is_grabbing)
+        drawn, wanted = horizon_targets(
             PREDICTOR_BASE_LENGTH, predictor_manual_mult,
             predictor_warp_length_mult(),
             PREDICTOR_MAX_POINTS, PREDICTOR_BASE_SPACING,
+            grabbing=grabbing, ceiling_mult=HORIZON_MULT_MAX,
         )
         # GEZEICHNET wird immer nur der un-geraffte horizont. Ohne das wickelt
         # sich die linie im zeitraffer mehrfach um die bahn, waehrend sie in
```

## diff: spacesim/config.json
```diff
--- .sdd-horizon-slider/snapshots/config.json.base	2026-09-02 21:55:20.798953700 +0200
+++ spacesim/config.json	2026-09-02 23:01:19.948889800 +0200
@@ -59,6 +59,10 @@
     "rolling_mode": false,
     "toggle_num_points": 30,
     "length_step_factor": 2.0,
+    "horizon_slider_min_mult": 0.25,
+    "horizon_slider_max_mult": 4.0,
+    "horizon_slider_sweep_seconds": 2.5,
+    "display_length_quantum_points": 8,
     "precision_step_factor": 2.0,
     "min_precision": 1.0,
     "auto_precision_from_zoom": true,
```

## diff: spacesim/ui/hud/layout.py
```diff
--- .sdd-horizon-slider/snapshots/layout.py.base	2026-09-02 21:55:20.814116300 +0200
+++ spacesim/ui/hud/layout.py	2026-09-02 22:30:45.846623900 +0200
@@ -32,6 +32,7 @@
     TOP_RIGHT,
 )
 from ..widgets import Stack
+from ..widgets.rate_slider import HorizonSlider
 from .apsis_tooltip import ApsisTooltip
 from .body_browser import BodyBrowser
 from .controls import SegmentBar, SnapRosette, WarpBar, ZoomButtons
@@ -89,7 +90,10 @@
 
     def __init__(self, ui_root, world, ship, ship_control, camera, renderer,
                  predictor, ui_state, tick_rate=60.0, realtime_warp_max=60.0,
-                 warp_timescale_divisor=3.0):
+                 warp_timescale_divisor=3.0,
+                 horizon_mult_get=None, horizon_mult_set=None,
+                 horizon_mult_min=0.25, horizon_mult_max=4.0,
+                 horizon_sweep_s=2.5):
         self.root = ui_root
         self.ctx = ui_root.ui
         self.camera = camera
@@ -104,6 +108,12 @@
         # Dieselbe zahl wie der riegel in test.py -- sonst blendet das HUD
         # andere stufen ab als die hauptschleife zulaesst.
         self.telemetry.warp_timescale_divisor = float(warp_timescale_divisor)
+        self._horizon_mult_get = horizon_mult_get
+        self._horizon_mult_set = horizon_mult_set
+        self._horizon_mult_min = float(horizon_mult_min)
+        self._horizon_mult_max = float(horizon_mult_max)
+        self._horizon_sweep_s = float(horizon_sweep_s)
+        self.horizon = None
         self._wide = None
         self._build(ship_control)
 
@@ -199,6 +209,21 @@
             ZoomButtons(telemetry, self.camera, compact=True)
         )
 
+        # Der vorhersage-horizont: ein mittenzentrierter raten-regler. Nach
+        # rechts ziehen verlaengert die gezeichnete linie, nach links
+        # verkuerzt sie -- die auslenkung ist die geschwindigkeit. Er
+        # aendert NUR predictor.set_display_length (O(1), kein neuaufbau);
+        # siehe plans/predictor_horizon_slider_design.md.
+        if self._horizon_mult_get is not None and self._horizon_mult_set is not None:
+            self.horizon = self.left_stack.add(HorizonSlider(
+                value=self._horizon_mult_get,
+                minimum=self._horizon_mult_min,
+                maximum=self._horizon_mult_max,
+                on_change=self._horizon_mult_set,
+                predictor=self.telemetry.predictor,
+                sweep_seconds=self._horizon_sweep_s,
+            ))
+
     # ----------------------------------------------------------------- ablauf
 
     def update(self):
```

## diff: spacesim/predictor.py
```diff
--- .sdd-horizon-slider/snapshots/predictor.py.base	2026-09-02 21:55:20.860114600 +0200
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

## diff: spacesim/tests/ui_hud_test.py
```diff
--- .sdd-horizon-slider/snapshots/ui_hud_test.py.base	2026-09-02 21:55:20.831361000 +0200
+++ spacesim/tests/ui_hud_test.py	2026-09-02 22:30:23.386961900 +0200
@@ -857,6 +857,54 @@
       f"{loose:.6f} gegen {tight:.6f}")
 frame()
 
+# ═══════════════════════════════════ 14. horizont-regler ist verdrahtet
+print()
+print("14. Horizont-Regler")
+
+# Eigener Hud mit ECHTEN closures ueber eine veraenderliche box -- so
+# schreibt ein simulierter griff den manuellen faktor wirklich zurueck.
+_hmult = [1.0]
+
+
+def predictor_manual_mult_getter():
+    return _hmult[0]
+
+
+def _hmult_set(m):
+    _hmult[0] = max(0.25, min(4.0, float(m)))
+
+
+hud_h = Hud(root, world, sim_ship, control, camera, renderer, predictor, state,
+            tick_rate=60.0,
+            horizon_mult_get=predictor_manual_mult_getter,
+            horizon_mult_set=_hmult_set,
+            horizon_mult_min=0.25, horizon_mult_max=4.0, horizon_sweep_s=2.5)
+
+check(getattr(hud_h, 'horizon', None) is not None,
+      "hud.horizon existiert", str(getattr(hud_h, 'horizon', None)))
+check(hud_h.horizon in hud_h.left_stack.children,
+      "sitzt im linken stapel (unter FRAME + zoom)", "")
+check(hud_h.horizon.is_grabbing is False,
+      "startet ungegriffen", "")
+
+# ein simulierter griff nach rechts hebt den manuellen faktor
+_start = predictor_manual_mult_getter()
+hud_h.horizon.pressed = True
+hud_h.horizon._offset = 1.0
+for _ in range(30):
+    hud_h.horizon.update(hud_h.ctx, 1.0 / 60.0)
+check(predictor_manual_mult_getter() > _start,
+      "griff nach rechts verlaengert den horizont",
+      f"{_start:.3f} -> {predictor_manual_mult_getter():.3f}")
+check(hud_h.horizon.is_grabbing is True, "waehrend des griffs: is_grabbing", "")
+
+hud_h.horizon.pressed = False
+for _ in range(30):
+    hud_h.horizon.update(hud_h.ctx, 1.0 / 60.0)
+check(abs(hud_h.horizon._offset) < 0.06,
+      "loslassen federt in die mitte zurueck",
+      f"offset {hud_h.horizon._offset:.4f}")
+
 print()
 if FAILURES:
     print(f"FEHLGESCHLAGEN: {len(FAILURES)}")
```

## diff: .claude/rules/hud-ui.md
```diff
--- .sdd-horizon-slider/snapshots/hud-ui.md.base	2026-09-02 21:55:20.880080200 +0200
+++ .claude/rules/hud-ui.md	2026-09-02 22:49:33.904136400 +0200
@@ -191,7 +191,8 @@
     cannot diverge. **Invariant: view state only, no physics** — the reference
     frame is a pure display transform.
   - `ui/widgets/` — Panel, Group, Label, Readout, Button, Toggle,
-    SegmentedControl, Slider (linear/log), Dropdown.
+    SegmentedControl, Slider (linear/log), HorizonSlider (centre-sprung rate),
+    Dropdown.
   - `ui/hud/` — the concrete HUD elements, restyled 2026-08-19 onto the KSP2
     instrument panel. `chrome.py` (**the form vocabulary — chamfer, double
     frame, notch tab, ruler, segmented arc; every surface goes through it**),
@@ -207,7 +208,7 @@
 > Top-left ship badge → reference selector → target block (one column, equal
 > widths, docked by sharp corners); top-right the warp bar with the UT clock;
 > bottom-centre the navball cluster with the snap rosette docked to its right;
-> bottom-left frame selector and zoom. The previous layout scattered eight
+> bottom-left frame selector, zoom and the predictor-horizon slider. The previous layout scattered eight
 > separate lozenges and built the bottom-centre column tall enough to sit on
 > top of the orbit — the one thing the screen exists to show.
 >
@@ -297,6 +298,26 @@
 > `UIState` cannot reach — `set_reference_index(None)` is a no-op — but
 > `Telemetry` accepts `ui_state=None`, so the test goes through that door).
 
+> **The horizon slider is a RATE control, not a position one**
+> (`ui/widgets/rate_slider.py::HorizonSlider`, bottom-left stack under FRAME +
+> the SYSTEM/LOCAL zoom buttons). The knob rests at centre and springs back
+> there (`ease` at `theme.motion.fast`); its displacement is the *speed* at
+> which the drawn prediction length changes, integrated in `update()` as
+> `mult *= exp(k·f(offset)·dt)`, `k = ln(max/min) / sweep` sized so a full
+> deflection sweeps `predictor.horizon_slider_min_mult` (0.25) → `_max_mult`
+> (4.0) in `_sweep_seconds` (2.5). A ±0.06 deadzone and an `x^1.8` response on
+> the deadzone-shifted magnitude keep it still at rest and fine near centre.
+>
+> It is smooth because moving the knob only writes a clamped multiplier
+> (`set_predictor_horizon_mult`); `apply_predictor_horizon()` in `test.py`
+> turns that into one `predictor.set_display_length()` per frame — an O(1)
+> clip of the already-computed curve. While the knob is held that function
+> reads `hud.horizon.is_grabbing` and, via `test.py::horizon_targets()`, pins
+> the *computed* horizon (`set_length`, async/soft) as if the manual factor
+> sat at the `_max_mult` ceiling, so the `1e-9` guard swallows every
+> `set_length` after the first — one recompute per drag, not per frame. The
+> `+` / `-` keys are unchanged (they still `predictor.reset()`).
+
 > **The reference list unfolds DOWNWARD out of its button.** `BodyBrowser`
 > keeps `open` as the *target* and `_open_t` as the drawn state, eased with
 > the project's usual framerate-independent `1 - exp(-rate·dt)` at
```

## diff: .claude/rules/predictor.md
```diff
--- .sdd-horizon-slider/snapshots/predictor.md.base	2026-09-02 21:55:20.898513300 +0200
+++ .claude/rules/predictor.md	2026-09-02 23:09:00.876063000 +0200
@@ -253,6 +253,34 @@
 >    O(1)), taken **mid-curve**, because `points[0]` is the ship and carries a
 >    deliberately short first chord.
 
+> **The HUD horizon slider rides `set_display_length` every frame.** It is a
+> rate control (`ui/widgets/rate_slider.py::HorizonSlider`): the drawn length
+> tracks the knob through `set_display_length` (O(1), no recompute,
+> independent of the hold / async swap / thrust), while the *computed* length
+> trails via the already-soft `set_length`. `test.py::horizon_targets()` pins
+> the computed target as if the manual factor sat at the config ceiling
+> `predictor.horizon_slider_max_mult` (4.0) while `hud.horizon.is_grabbing`,
+> so the `1e-9` guard in `apply_predictor_horizon()` trips once per drag and
+> the async pipeline is never thrashed. No `reset()` on this path — that
+> (still on `+` / `-`) is the synchronous `_compute_full` the slider exists to
+> avoid.
+>
+> **The drawn point count is quantised so a slow drag does not churn
+> `id(points)`.** `get_points()` returns `self.points[:count]`; every frame of a
+> drag `set_display_length` moves the raw metres a little, so an un-quantised
+> `count` shifts ~every frame → a fresh view object → the renderer's
+> line-subdivision cache and `get_apsis_markers()` (both keyed on `id(pts)`)
+> miss every frame. `_display_point_count` rounds `count` to a multiple of
+> `self._display_quantum` (`predictor.display_length_quantum_points`, default 8)
+> at **both** return sites, *after* the `limit is None` / `limit >= full` early
+> returns (those still mean "draw everything" and are untouched). Paired with
+> this, `set_display_length()` no longer calls `_clear_display_view()` — that
+> hard reset forced a rebuild every frame regardless of the rounded count;
+> `get_points()`'s own three-way check (base identity, `_display_view_limit`,
+> `None`) already invalidates correctly. Warp §18/§19/§21/§23 are unaffected
+> because none of them set a `display_length`, so `_display_point_count`
+> returns `None` before the quantiser runs.
+
 > **Real time now uses the hold's mechanism too — the Ap/Pe markers were
 > jittering because it did not.** Fixed 2026-08-25. Outside the warp hold
 > `_anchor_first_point` translated the whole curve rigidly so its head sat on
```

## diff: .claude/rules/camera-input.md
```diff
--- .sdd-horizon-slider/snapshots/camera-input.md.base	2026-09-02 21:55:20.914640600 +0200
+++ .claude/rules/camera-input.md	2026-09-02 22:49:47.119551500 +0200
@@ -299,8 +299,12 @@
 - `P` — toggle predictor. `E` — toggle epicycle (Ptolemaic) mode.
 - `R` — cycle reference body. `1` — non-rotating frame.
   `2` — body-direction frame. `T` — target overlay.
-- `+` / `-` — predictor length ×2 / ÷2. `9` / `0` — predictor precision
-  (finer / coarser).
+- `+` / `-` — predictor length ×2 / ÷2 (instant, full recompute). `9` / `0` —
+  predictor precision (finer / coarser). The **HUD horizon slider**
+  (bottom-left, under FRAME) is the smooth alternative to `+` / `-`: a
+  centre-sprung rate control that changes only the *drawn* length per frame
+  (`predictor.set_display_length`), with the computed horizon trailing
+  asynchronously. See `.claude/rules/hud-ui.md`.
 - `PageUp` / `PageDown` — sim_dt up / down. `Esc` — quit.
 - **Warp steps are `1m/s, 10m/s, 1h/s, 1d/s, 7d/s, 30d/s, 100d/s, 1y/s`**
   (`ui/hud/layout.py::WARP_STEPS`, sim-seconds per real second). The top
```

## small files without a pre-plan snapshot (each reviewed in-task):
### spacesim/loader.py — one line added at ~365:
```
            # ruckartig), 2 = vollstaendig gleichmaessig, dafuer aeltere linie.
            ('swap_backlog_max', 'swap_backlog_max', int),
            # nur von test.py ausgewertet (tastenbelegung / ein-aus-verhalten)
            ('display_length_quantum_points', None, None),
            ('quality', None, None),
```
### .claude/rules/tests.md — added at L83-85:
```
  slider: §1–3 `test.horizon_targets()` against `predictor_horizon_lengths`
  (grabbing pins the computed length at the ceiling, `drawn` follows the knob),
  §4 the `set_length`-once-per-grip contract against a real `Predictor`, and
  §5 (2026-09-02) that `get_points()` returns the **same array object** when
  `set_display_length` moves less than one `_display_quantum` (8 points) and a
  new one past that — the view-identity churn fix.

```
### tools/hud_shot.py — box closures added; ORIGINAL Hud call was:
```python
hud = Hud(ui_root, w, ship, ship_control, camera, renderer, predictor, ui_state,
          tick_rate=180.0)
```
current:
```python
_hmult = [1.0]
hud = Hud(ui_root, w, ship, ship_control, camera, renderer, predictor, ui_state,
          tick_rate=180.0,
          horizon_mult_get=lambda: _hmult[0],
          horizon_mult_set=lambda m: _hmult.__setitem__(0, max(0.25, min(4.0, float(m)))))
try:
    hud.telemetry.set_thrust_level(0.62)
except Exception:
    pass

if args.open_browser:
    hud.body_browser.open = True

# Ein paar frames laufen lassen: hover-/easing-zustaende starten auf null,
# und der erste frame zeigt deshalb einen ring, der noch auf kurs 0 steht.
for _ in range(max(1, args.open_browser or args.frames)):
    gl.screen.use()
    gl.viewport = (0, 0, W, H)
    gl.clear(*ui_ctx.theme.palette.ground[:3], 1.0)
    hud.update()
    ui_root.begin_frame(1.0 / 60.0)
    ui_root.render()

data = gl.screen.read(viewport=(0, 0, W, H), components=3, dtype='f1')
frame = np.frombuffer(data, dtype=np.uint8).reshape(H, W, 3)[::-1]
out = args.out or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'screenshots for debugging', 'hud_current.png',
)
pygame.image.save(pygame.surfarray.make_surface(frame.transpose(1, 0, 2)), out)
print('geschrieben:', out, f'({W}x{H}, ui_scale {scale:.2f})')
```
