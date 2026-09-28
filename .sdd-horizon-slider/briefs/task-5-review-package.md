# Task 5 review package

## diff: spacesim/ui/hud/layout.py
```diff
--- .sdd-horizon-slider/snapshots/task-5-layout.py.base	2026-09-02 22:28:20.546931000 +0200
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

## diff: spacesim/test.py
```diff
--- .sdd-horizon-slider/snapshots/task-5-test.py.base	2026-09-02 22:28:20.578733600 +0200
+++ spacesim/test.py	2026-09-02 22:30:51.329421000 +0200
@@ -391,6 +391,11 @@
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
```

## diff: spacesim/tests/ui_hud_test.py
```diff
--- .sdd-horizon-slider/snapshots/task-5-ui_hud_test.py.base	2026-09-02 22:28:20.596605000 +0200
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

## rate_slider.py — current _track_rect + measure + _offset_from_x (only _track_rect changed this task, ruling-c inset)
```python
    def measure(self, ctx):
        track = ctx.px(5.0)
        knob = ctx.px(18.0)
        height = self._tab_h(ctx) + self._readout_h(ctx) + max(track, knob) + ctx.px(6.0)
        return (ctx.px(168.0), height)

    def _track_rect(self, ctx):
    def _track_rect(self, ctx):
        # Spur einwaerts gesetzt: die '-'/'+'-endglyphen sitzen px(9)+px(3)
        # Spur einwaerts gesetzt: die '-'/'+'-endglyphen sitzen px(9)+px(3)
        # AUSSERHALB der spur, und ohne diesen einzug ragte das minus ueber
        # AUSSERHALB der spur, und ohne diesen einzug ragte das minus ueber
        # die widget-kante hinaus fast bis an den bildschirmrand.
        # die widget-kante hinaus fast bis an den bildschirmrand.
        inset = ctx.px(12.0)
        inset = ctx.px(12.0)
        h = ctx.px(5.0)
        h = ctx.px(5.0)
        top_band = self._tab_h(ctx) + self._readout_h(ctx)
        top_band = self._tab_h(ctx) + self._readout_h(ctx)
        free = self.rect.h - top_band - h
        free = self.rect.h - top_band - h
        top = self.rect.y + top_band + max(0.0, free) * 0.5
        top = self.rect.y + top_band + max(0.0, free) * 0.5
        return Rect(self.rect.x + inset, top, self.rect.w - inset * 2.0, h)
        return Rect(self.rect.x + inset, top, self.rect.w - inset * 2.0, h)

    # ------------------------------------------------------------ eingabe
    def _offset_from_x(self, ctx, x):
    def _offset_from_x(self, ctx, x):
        track = self._track_rect(ctx)
        track = self._track_rect(ctx)
        half = track.w * 0.5
        half = track.w * 0.5
        if half <= 0.0:
        if half <= 0.0:
            return 0.0
            return 0.0
        return max(-1.0, min(1.0, (float(x) - track.center_x) / half))
        return max(-1.0, min(1.0, (float(x) - track.center_x) / half))
```

## diff: tools/hud_shot.py (NOT in brief file list — implementer added box closures for the visual check)
```diff
(no baseline snapshot — full current file below)
```
```python
"""Baut das HUD offscreen auf und legt einen PNG-abzug ab.

Zweck: waehrend der gestaltung sehen, was herauskommt, ohne das spiel zu
starten und ohne screenshots von hand zu machen. Der aufbau ist derselbe
wie in test.py -- welt, kamera, predictor, telemetrie -- nur ohne
hauptschleife und ohne weltrender.

    python tools/hud_shot.py [breite hoehe] [-o datei.png]
"""

import argparse
import math
import os
import sys

SPACESIM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spacesim'
)
sys.path.insert(0, SPACESIM)
os.chdir(SPACESIM)
os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS', 'permonitorv2')

import moderngl
import numpy as np
import pygame
from pygame.locals import DOUBLEBUF, OPENGL

parser = argparse.ArgumentParser()
parser.add_argument('width', nargs='?', type=int, default=1600)
parser.add_argument('height', nargs='?', type=int, default=900)
parser.add_argument('-o', '--out', default=None)
parser.add_argument('--scale', type=float, default=None)
parser.add_argument('--frames', type=int, default=8)
parser.add_argument('--radial', type=float, default=None,
                    help='radialen geschwindigkeitsanteil erzwingen (m/s)')
parser.add_argument('--open-browser', type=int, default=0,
                    help='koerperliste oeffnen und N frames der animation laufen lassen')
args = parser.parse_args()

W, H = args.width, args.height

# Nur display+font -- pygame.init() zaehlt mixer- und joystick-geraete auf
# und kostet dabei ~45 s (siehe CLAUDE.md).
pygame.display.init()
pygame.font.init()
pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
gl = moderngl.create_context()
gl.enable(moderngl.BLEND)
gl.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

from camera import Camera
from loader import ConfigLoader, SystemLoader
from predictor import Predictor
from rendering import Renderer
from schiff import schiffcontrol
from ui import UIContext, UIRoot
from ui.hud import Hud
from ui.state import UIState
from world import world as World

config = ConfigLoader()
bodies = SystemLoader(config.get('simulation.system_file', 'solar_system.json')).load()
w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
w.body = bodies
config.apply_to_world(w)
w.update_planets(0.0)

ship = next(b for b in w.body if b.is_ship)
ship_control = schiffcontrol(ship)
config.apply_to_ship_control(ship_control)

# Das schiff auf eine ansehnliche ellipse um die Erde setzen -- ein
# gestaltungsabzug soll plausible zahlen zeigen, keine platzhalter.
erde = next((b for b in w.body if b.name.lower().startswith('erde')), None)
if erde is not None:
    mu = w.G * erde.mass
    r = float(getattr(erde, 'radius', 6.371e6)) + 1.2e6
    ship.position.x = erde.position.x + r
    ship.position.y = erde.position.y
    # Zentrale differenz -- das velocity-feld skriptgefuehrter koerper ist 0.
    ahead = erde.position_at_time(1.0)
    behind = erde.position_at_time(-1.0)
    ship.velocity.x = (float(ahead.x) - float(behind.x)) / 2.0
    ship.velocity.y = (float(ahead.y) - float(behind.y)) / 2.0 + math.sqrt(mu / r) * 1.18

if args.radial is not None:
    # Radial nach aussen aufaddieren -- fuer den abzug der V/S-flanke.
    rx = float(ship.position.x) - float(erde.position.x)
    ry = float(ship.position.y) - float(erde.position.y)
    norm = math.hypot(rx, ry) or 1.0
    ship.velocity.x += args.radial * rx / norm
    ship.velocity.y += args.radial * ry / norm

camera = Camera(None, W, H)
config.apply_to_camera(camera)
camera.target = ship
# Echtzeit-stufe, sonst ist der schub gesperrt und beide bogen blass.
camera.sim_dt = 60.0 / 180.0
camera.snap_to_targets()

renderer = Renderer(W, H, enable_fxaa=False, ctx=gl)
config.apply_to_renderer(renderer)

predictor = Predictor(**config.predictor_kwargs())
config.apply_to_predictor(predictor)
predictor.initialize(ship, w)

ui_state = UIState(w.body)
try:
    ui_state.set_reference_index(w.body.index(erde))
except Exception:
    pass

scale = args.scale if args.scale is not None else renderer.ui_scale
ui_ctx = UIContext(gl, W, H, ui_scale=scale)
ui_root = UIRoot(ui_ctx)
# Der horizont-regler braucht ein paar closures ueber den manuellen
# multiplikator -- im spiel liegen die in test.py::main(), hier reicht eine box.
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

## hud_shot.py — ORIGINAL Hud construction (from controller's earlier full read of the file, pre-Task-5)

The original file built the HUD as (around line 117):
```python
hud = Hud(ui_root, w, ship, ship_control, camera, renderer, predictor, ui_state,
          tick_rate=180.0)
```
with no horizon closures. Everything else in hud_shot.py was as shown in the full current file above — compare to see exactly what the implementer added/changed.
