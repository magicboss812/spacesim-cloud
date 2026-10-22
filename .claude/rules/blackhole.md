---
paths:
  - "spacesim/render/blackhole.py"
  - "spacesim/render/blackhole_tables.py"
  - "spacesim/render/gl/blackhole*"
  - "spacesim/render/gl/body_cell_hole.frag"
  - "spacesim/render/gl/blackhole_glow.frag"
  - "spacesim/config/schlund_system.json"
  - "spacesim/tests/blackhole_test.py"
---

# Black holes — pixel body, lens, inset

A body with `is_black_hole: true` (its `radius` is r_s = 2GM/c²) is not drawn
as a disc. The physics treats it as any other mass (Newtonian, no
Paczyński–Wiita: that would have to go into both kernels at once).
`blackhole.style` picks how it looks: **`"pixel"`** (default) or `"lens"`.

## `"pixel"`: a body in the cell grid, seen at a slant (2026-10-20)

The hole goes through the **same pipeline as the planets**
(`render/body_pixel.py`, `.claude/rules/body-art.md` → "Pixel bodies"), as
`u_kind = 3`: its own cell pass, then the unchanged clean pass and compose.
The first, face-on lens version was rejected in play: too sharp next to the
pixel bodies, and flat. Rules:

- **One light ray per CELL, not per pixel** (`body_cell_hole.frag`, on
  `body.vert`). Parallel rays (the game camera is "infinitely" far) start
  40 r_s in front, at inclination `view_inclination_deg` (82°), and the
  whole picture is turned by `view_roll_deg` (14°, counter-clockwise), so
  the disk is not parallel to the screen edge. Same leapfrog geodesic and
  Doppler g as the inset. The quad is the disk's circumscribed circle,
  `apparent_radius(disk_outer_rs) · 1.06 · r_s_px`.
- **Each cell is disk, shadow or nothing.** Disk: light tone-mapped
  (`cell_gain`), then quantised to the four `ramp()` steps of the planets
  (dithered ±0.04), halftone size from brightness, hue = blackbody mixed
  `cell_hue_mix` (0.35) toward the body colour. Region id = radius band of
  the first hit (inner / middle / outer), so the compose draws 1-px strokes
  between the bands, like ring divisions. Shadow: black, its own region; the
  stroke where it meets the disk is the bright edge around the hole.
  Escaped rays leave no cell.
- **`disk_outer_rs` is 9, not 18.** At 82° the projected disk is thinner
  than the hole is tall, so the shadow and the arched back side stand out
  above and below the band.
- **The glow is one blurred field, read twice** (2026-10-20). After the
  clean pass, `blackhole_glow.frag` runs a separable Gauss
  (`glow_sigma_cells`, 2.2) over the lit cells (colour × halftone) into two
  float16 targets at cell resolution. The compose (`body_pixel.frag`, kind 3,
  outside the cells) samples it **linearly** for a soft glow
  (`glow_smooth`) and thresholds it per **screen pixel** against Bayer 4×4
  for dithered glow pixels (`glow_dither`). Both hang on the body's grid,
  so nothing crawls while panning. The cell buffer and the compose rect reach
  `_blackhole_glow_reach_cells()` (2.5 σ + 1) beyond the circle. Earlier
  versions failed: the planets' radius-based dot matrix drew a dotted
  circle round the flat disk, and neighbour-cell dots had no gradient.
- **The background lens bends only the STARS** (`pixel_lens`). Deflection
  depends only on the distance to the hole, not on the disk's tilt, so the
  face-on table is valid here too. When a lens is on screen
  (`_black_hole_lens_in_view`) the background splits (`_bg_defer_ink`,
  `u_pass` in `background.frag`): black → stars → lens → ground, grid and
  vignette **added** on top. Bending the grid turned the node under the
  reference body, which sits exactly behind a focused hole, into a full
  cyan Einstein ring that read as an orbit line. The lens snaps its sample to
  a pixel centre on a NEAREST copy, so stars become stretched hard pixels.
  Its disk and shadow are off (`u_draw_disk = 0`); the cells draw both.
  `einstein_radius_rs` is 14 (32 filled the whole screen at close zoom).
- **The lens shift is a WORLD length, the star field a screen pattern**
  (`_black_hole_lens_gain`, both styles). `D·α` is ~6 r_s at the
  Kundschafter's 26 r_s orbit, which lies inside the 35 r_s quad: at
  1e-4 px/m that is 1.8 million px, so each frame sampled the mirrored scene
  copy somewhere else and the stars jumped wildly while following the ship.
  Two rules: the shift fades out between 1.0 and 2.5 screen diagonals from
  the hole to the screen centre (beyond, the lens on screen is only a
  featureless stretch turning with the orbit; `_black_hole_lens_in_view`
  then returns False and the background is not split), and from 0.6 to 1.2
  diagonals the shift of the screen centre is subtracted (`u_ref`,
  `u_ref_w`, faded to 0 at the quad edge or it leaves a seam). A constant
  shift is invisible on a random field, so the still picture is unchanged;
  only the racing goes. With the hole on screen nothing changes: there the
  bent field moves with the hole, and that is right. Measured following
  the Kundschafter (changed px per frame in a star-only band, grid off):
  old lens 2800–3200 at 1e-7…1e-4 px/m, now 360–560 = no lens.
- **No dust in this style**: sparkles on top of the cells.
- Below `body_icon_min_radius_px` (circumscribed circle) the normal icon
  takes over.

Cost (llvmpipe, 1280×800, Schlund system, median of 30): +6–7 ms at a
149-px circle (old lens +15), +11–22 ms at 356 px. The steps per ray are a
real part of it (60 steps instead of 240: −3 to −12 ms, noisy); on a GPU
it is ~14k cells × 240 steps, negligible.

## `"lens"`: the smooth face-on view

`BlackHoleDrawMixin` draws it in three GPU parts:

| part | shader | when |
| --- | --- | --- |
| lens + disk + shadow | `blackhole.vert/.frag` | right after `_draw_background`, into the FXAA target |
| gas clumps | `blackhole_dust.vert/.frag` | same place, additive, instanced quads |
| tilted inset | `blackhole_inset.frag` | in the shared preview box (`render/inset.py`, `.claude/rules/body-art.md` → "The preview box") when the hole is selected — in both styles |

`blackhole_common.glsl` (disk flux, blackbody, noise, tone curve) has no
`#version`; `_compile_blackhole_program` pastes it at `//@common`.
All settings: `config.json` → `blackhole`, read by
`ConfigLoader.apply_to_blackhole` into `renderer.blackhole_*`.

## The lens runs BEFORE orbits, bodies and ship — on purpose

Only what lies BEHIND the disk plane is bent: the star field and the grid.
Planets, orbit lines, the prediction line and the ship lie IN the plane and are
drawn afterwards, unbent. Lensing the finished frame would bend the HUD-like
lines too and was not done. The pass copies the target into
`_bh_scene_tex` (`ctx.copy_framebuffer`), then draws its quad over the same
target with blending off. Beyond the quad not one pixel changes
(`tests/blackhole_test.py` §7 measures 0).

A grid node sitting right behind the hole becomes a full **Einstein ring** at
`einstein_radius_rs` — a bright cyan circle that looks like an orbit line.
That is the lens, not a bug.

## The face-on picture is exact; only temperature and turbulence are chosen

`face_on_table()` integrates u'' + u = 3/2 u² (RK4, dψ = 2e-3, numba,
~0.3 s, once, only when a hole is on screen) for 2048 impact parameters on
`b = B_CRIT / (1 - s²)`: deflection α and the crossing radii r1..r3 (primary
image, n=1 and n=2 rings, the n-th rotated (n-1)·180°). Face-on photons have
L_z = 0, so the only frequency shift is g = sqrt(1 - 1.5/r); the inset, which
is tilted, adds the Doppler term g = sqrt(1-1.5/r) / (1 - Ω λ).

- **A missing crossing is stored as 1e6, not 0.** Linear interpolation between
  r2 ≈ 1e3 and 0 at the ring's edge invented a ring at mid radii.
- **The background shift is `src = b - D·α`, D = R_E²/2.** A top-down camera has
  no observer distance, so the Einstein radius is a choice
  (`einstein_radius_rs`, 32). With the first value (9) the ring sat under the
  disk (apparent radius 18.5 r_s) and no lensing was visible at all.
- **The shader's weak-field branch (s > S_MAX, b > 1300 r_s) is third order:**
  2/b + 15π/16b² + 16/3b³. The first version had 15π/48 in the second term;
  the test caught it.
- **`disk_peak_temperature_k` is an art choice, 6500 K.** A real 10^6 M☉ disk
  peaks in the UV/X-ray and is white-blue everywhere visible; 14 000 K already
  rendered as flat white. The colour comes from the CIE-1931 blackbody table
  normalised to Y = 1; the flux r^-3 (1 - sqrt(3/r)) and g⁴ set brightness.

## Disk time: sim time, capped, wrapped

`_blackhole_phase` advances `t·c/r_s` with SIM time — at 1× the inner edge
turns with its real period (7.7 min for Schlund) — but at most
`disk_max_turn_per_frame` (0.04 rad at the ISCO) per frame, else at warp it
spins hundreds of turns per frame and only flickers. The phase wraps every
1000 ISCO orbits (float32 in the shader). The turbulence is a flow map: two
noise copies each sheared for one local orbit, cross-faded, so the shear never
winds into hair-thin stripes after long times.

## Cost (llvmpipe, 1280×800, `render()` + `gl.finish()`, median of 35)

Off 13.3 ms; lens + disk + dust 21–23 ms; plus inset 24.6 ms. The cost is the
quad's **pixel area** (a quarter of the area: 18.0 ms); turbulence is not
measurable, dust ~1 ms. On a real GPU all of it is well under a millisecond;
these numbers are only for before/after inside the container.
