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
