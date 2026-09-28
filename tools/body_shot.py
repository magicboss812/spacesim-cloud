"""Zeichnet einen (oder mehrere) koerper offscreen und legt einen PNG-abzug ab.

Gegenstueck zu ``hud_shot.py``, aber fuer die prozedurale koerper-optik: es
laeuft der ECHTE renderer-pfad (``Renderer.render``), damit der abzug zeigt,
was das spiel zeigt, und nicht eine nachgebaute vorschau.

    python tools/body_shot.py --body Erde --radius 260
    python tools/body_shot.py --contact          # kontaktabzug aller koerper
    python tools/body_shot.py --body Erde --phases 6
"""

import argparse
import math
import os
import sys
import time

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
parser.add_argument('width', nargs='?', type=int, default=1280)
parser.add_argument('height', nargs='?', type=int, default=800)
parser.add_argument('-o', '--out', default=None)
parser.add_argument('--body', default='Erde')
parser.add_argument('--radius', type=float, default=260.0,
                    help='gewuenschter bildschirmradius in pixeln')
parser.add_argument('--contact', action='store_true',
                    help='alle koerper nebeneinander statt eines einzelnen')
parser.add_argument('--phases', type=int, default=0,
                    help='N beleuchtungsphasen desselben koerpers nebeneinander')
parser.add_argument('--ladder', action='store_true',
                    help='derselbe koerper ueber die detailschwelle hinweg')
args = parser.parse_args()

W, H = args.width, args.height

pygame.display.init()
pygame.font.init()
pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
gl = moderngl.create_context()

from camera import Camera
from loader import ConfigLoader, SystemLoader
from rendering import Renderer
from vec import Vec2

config = ConfigLoader()
bodies = SystemLoader(config.get('simulation.system_file', 'solar_system.json')).load()
from world import world as World

w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
w.body = bodies
config.apply_to_world(w)
w.update_planets(0.0)

renderer = Renderer(W, H, enable_fxaa=True, ctx=gl)
config.apply_to_renderer(renderer)
camera = Camera(None, W, H)
config.apply_to_camera(camera)


def pick(name):
    lowered = str(name).lower()
    for body in w.body:
        if str(body.name).lower().startswith(lowered):
            return body
    raise SystemExit(f'kein koerper {name!r}')


def frame_for(subject, radius_px, light_angle_deg=None):
    """Kamera so setzen, dass `subject` mit `radius_px` in der mitte steht."""
    camera.scale = radius_px / float(subject.radius)
    camera.target_scale = camera.scale
    camera.target = None
    camera.position = Vec2(float(subject.position.x), float(subject.position.y))
    camera.target_position = Vec2(float(subject.position.x), float(subject.position.y))
    if light_angle_deg is not None:
        # Den stern kuenstlich umsetzen -- der einzige weg, in einem
        # standbild verschiedene phasen nebeneinander zu zeigen.
        star = renderer._find_light_source(w.body)
        distance = 2.0e11
        angle = math.radians(light_angle_deg)
        star.position = Vec2(
            float(subject.position.x) + distance * math.cos(angle),
            float(subject.position.y) + distance * math.sin(angle),
        )


def shoot(label):
    renderer.render(w.body, camera, sim_time=0.0)
    renderer.ctx.screen.use()


tiles = []
if args.contact:
    names = [b.name for b in w.body if not getattr(b, 'is_ship', False)]
elif args.phases:
    names = [args.body] * args.phases
elif args.ladder:
    names = [args.body] * 6
else:
    names = [args.body]

cols = int(math.ceil(math.sqrt(len(names)))) if len(names) > 1 else 1
rows = int(math.ceil(len(names) / cols))
tile_w, tile_h = W // cols, H // rows
# 0.30, nicht mehr: der halo eines sterns reicht bis 3x radius und
# wuerde sonst am kachelrand hart abgeschnitten.
tile_radius = min(tile_w, tile_h) * 0.30

sheet = np.zeros((H, W, 3), dtype=np.uint8)
ladder_radii = [8.0, 22.0, 48.0, 95.0, 150.0, 230.0]

for index, name in enumerate(names):
    subject = pick(name)
    radius = args.radius if len(names) == 1 else tile_radius
    if args.ladder:
        radius = ladder_radii[index % len(ladder_radii)]
    angle = None
    if args.phases:
        angle = 360.0 * index / float(args.phases)
    frame_for(subject, radius, angle)
    # Der bau laeuft nebenlaeufig -- warten, bis die zeichnung wirklich
    # steht, sonst zeigt der abzug die flache scheibe davor.
    for _ in range(600):
        renderer.render(w.body, camera, sim_time=0.0)
        if not renderer._body_style_jobs and renderer.debug_info.get('bodies_vector'):
            break
        time.sleep(0.002)
    renderer.render(w.body, camera, sim_time=0.0)
    data = gl.screen.read(viewport=(0, 0, W, H), components=3, dtype='f1')
    frame = np.frombuffer(data, dtype=np.uint8).reshape(H, W, 3)[::-1]
    if len(names) == 1:
        sheet = frame
        break
    row, col = divmod(index, cols)
    crop = frame[H // 2 - tile_h // 2: H // 2 - tile_h // 2 + tile_h,
                 W // 2 - tile_w // 2: W // 2 - tile_w // 2 + tile_w]
    sheet[row * tile_h:(row + 1) * tile_h, col * tile_w:(col + 1) * tile_w] = crop

out = args.out or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'screenshots for debugging', 'body_current.png',
)
pygame.image.save(pygame.surfarray.make_surface(sheet.transpose(1, 0, 2)), out)
print('geschrieben:', out, f'({W}x{H})',
      'vektor-koerper:', renderer.debug_info.get('bodies_vector'),
      'fehler:', renderer.debug_info.get('body_style_error'),
      renderer.debug_info.get('shader_error'))
