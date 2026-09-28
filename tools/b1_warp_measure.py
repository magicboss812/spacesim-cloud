"""B1 -- warp-ceiling messung (phase 5, plan B1).

Misst pro raffungsstufe: weltschritt-kosten, integrator-teilschritte,
volle predictor-neuberechnungen und ob der warp-hold ueberlebt.

KEIN pygame.init() -- es wird ueberhaupt kein fenster gebraucht, weil
weder world noch predictor GL beruehren.
"""
import os
import sys
import time
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SPACESIM = r"C:\Users\Martin\Desktop\Bahnmechanik Seminararbeit - Astronomie\Werk\spacesim"
sys.path.insert(0, SPACESIM)
os.chdir(SPACESIM)

from loader import ConfigLoader, SystemLoader
from world import world as World
from predictor import Predictor

TICK_RATE = 180.0
FRAME_DT = 1.0 / TICK_RATE

DAY = 86400.0
STEPS = [
    ("7 d/s",   7.0 * DAY),
    ("30 d/s",  30.0 * DAY),
    ("100 d/s", 100.0 * DAY),
    ("365 d/s", 365.0 * DAY),
]


def build():
    config = ConfigLoader()
    bodies = SystemLoader(config.get('simulation.system_file', "solar_system.json")).load()
    w = World(float(config.get('physics.gravitational_constant', 6.6730831e-11)))
    w.body = bodies
    config.apply_to_world(w)

    predictor = Predictor(recompute_every_update=True, **config.predictor_kwargs())
    config.apply_to_predictor(predictor)
    predictor.set_length(predictor.num_points * predictor.precision)

    ship = next(b for b in w.body if b.is_ship)
    return config, w, predictor, ship


MAX_SUBSTEP = 1000.0


def step_simulation(w, sim_seconds):
    import math
    if sim_seconds <= 0.0:
        return 0
    if sim_seconds <= MAX_SUBSTEP:
        w.update_dynamics(sim_seconds)
        w.update_planets(sim_seconds)
        return w.integrator_last_substeps
    steps = int(math.ceil(sim_seconds / MAX_SUBSTEP))
    sub_dt = sim_seconds / steps
    total = 0
    for _ in range(steps):
        w.update_dynamics(sub_dt)
        w.update_planets(sub_dt)
        total += w.integrator_last_substeps
    return total


def horizon_span(points):
    if points is None or len(points) < 2:
        return 0.0
    return float(points[-1, 2] - points[0, 2])


def run(label, rate, frames=180, warmup=20):
    config, w, predictor, ship = build()

    full_calls = [0]
    orig_full = predictor._compute_full

    def counting_full(s, wd):
        full_calls[0] += 1
        return orig_full(s, wd)

    predictor._compute_full = counting_full

    predictor.initialize(ship, w)
    predictor.set_hold(True)

    # aufwaermen: numba-JIT und der erste volle lauf duerfen nicht in die
    # messung fallen.
    for _ in range(warmup):
        step_simulation(w, rate * FRAME_DT)
        predictor.update(ship, w)
    full_calls[0] = 0

    world_ms = []
    substeps = []
    pred_ms = []
    npoints = []
    spans = []

    for _ in range(frames):
        t0 = time.perf_counter()
        subs = step_simulation(w, rate * FRAME_DT)
        t1 = time.perf_counter()
        predictor.update(ship, w)
        t2 = time.perf_counter()

        world_ms.append((t1 - t0) * 1000.0)
        pred_ms.append((t2 - t1) * 1000.0)
        substeps.append(subs)
        pts = predictor.get_points()
        npoints.append(0 if pts is None else len(pts))
        spans.append(horizon_span(pts))

    hold_ok = predictor._hold_active() and min(npoints) > 2

    predictor.close()

    return {
        'label': label,
        'rate': rate,
        'sim_s_per_frame': rate * FRAME_DT,
        'world_ms_med': statistics.median(world_ms),
        'world_ms_max': max(world_ms),
        'pred_ms_med': statistics.median(pred_ms),
        'pred_ms_max': max(pred_ms),
        'substeps_med': statistics.median(substeps),
        'full_per_frame': full_calls[0] / frames,
        'points_min': min(npoints),
        'points_med': statistics.median(npoints),
        'span_med_days': statistics.median(spans) / DAY,
        'hold_ok': hold_ok,
    }


def main():
    print(f"tick rate {TICK_RATE:.0f} fps, frame_dt {FRAME_DT*1000:.2f} ms\n")
    rows = []
    for label, rate in STEPS:
        print(f"  ... {label}", flush=True)
        rows.append(run(label, rate))

    hdr = (f"{'warp':>8} | {'sim-s/frame':>12} | {'world ms':>16} | {'substeps':>9} | "
           f"{'pred ms':>16} | {'full/frame':>10} | {'points':>12} | {'span d':>8} | hold")
    print("\n" + hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['label']:>8} | {r['sim_s_per_frame']:>12.0f} | "
              f"{r['world_ms_med']:>7.2f}/{r['world_ms_max']:>7.2f} | "
              f"{r['substeps_med']:>9.0f} | "
              f"{r['pred_ms_med']:>7.2f}/{r['pred_ms_max']:>7.2f} | "
              f"{r['full_per_frame']:>10.3f} | "
              f"{r['points_min']:>5.0f}/{r['points_med']:>6.0f} | "
              f"{r['span_med_days']:>8.1f} | {'yes' if r['hold_ok'] else 'NO'}")
    print("\n(world ms and pred ms shown as median/max; points as min/median)")
    budget = 1000.0 / TICK_RATE
    print(f"frame budget at {TICK_RATE:.0f} fps = {budget:.2f} ms\n")
    for r in rows:
        total = r['world_ms_med'] + r['pred_ms_med']
        verdict = "OK" if total < budget else "OVER BUDGET"
        print(f"  {r['label']:>8}: world+pred median {total:6.2f} ms  -> {verdict}")


if __name__ == '__main__':
    main()
