# Task 6 report — documentation for the predictor horizon slider

Docs only. Three `.claude/rules/*.md` files edited. No code touched, no git, no pytest.

## Verification pass (code read before writing)

| fact | source | result |
|---|---|---|
| widget class `HorizonSlider` | `spacesim/ui/widgets/rate_slider.py:40` | ✓ |
| spring-back uses `motion.fast` | `rate_slider.py:126` `ease(self._offset, 0.0, ctx.theme.motion.fast, dt)` | ✓ |
| rate integration `mult *= exp(k·f·dt)` | `rate_slider.py:133` `new = self.resolve_value() * math.exp(k * f * float(dt))` | ✓ |
| `k = ln(max/min) / sweep` | `rate_slider.py:132` `k = math.log(self.maximum / self.minimum) / self.sweep_seconds` | ✓ |
| deadzone `0.06` | `rate_slider.py:23` `DEADZONE = 0.06` | ✓ |
| response exponent `1.8` on deadzone-shifted magnitude | `rate_slider.py:37` `math.copysign(scaled ** 1.8, offset)`, `scaled = (magnitude - DEADZONE) / (1.0 - DEADZONE)` | ✓ (not raw `x^1.8` — noted as "on the deadzone-shifted magnitude") |
| `_track_rect` inset `ctx.px(12.0)` per side | `rate_slider.py:86` `inset = ctx.px(12.0)` … `Rect(self.rect.x + inset, top, self.rect.w - inset * 2.0, h)` | ✓ present (brief's section text never claimed otherwise, so nothing to correct) |
| `is_grabbing` = pressed AND `|offset| > DEADZONE` | `rate_slider.py:63-64` | ✓ |
| config keys `horizon_slider_min_mult` 0.25 / `_max_mult` 4.0 / `_sweep_seconds` 2.5 | `spacesim/config.json:62-64` | ✓ |
| `horizon_targets()` pins computed length to `ceiling_mult` while `grabbing` | `spacesim/test.py:39-58` | ✓ |
| `apply_predictor_horizon()` reads `hud.horizon.is_grabbing`, passes `ceiling_mult=HORIZON_MULT_MAX` | `test.py:602-610` | ✓ |
| `1e-9` guard skips redundant `set_length` | `test.py:630` `if current is not None and abs(current - wanted) <= wanted * 1e-9: return` | ✓ |
| `set_display_length` called once per frame with the drawn length | `test.py:616-617`; `apply_predictor_horizon()` runs every frame at `test.py:858` | ✓ |
| `+` / `-` still call `predictor.reset()` | `test.py:775, 783` | ✓ |
| `+` / `-` = "full recompute" | `predictor.reset()` → synchronous `_compute_full` (existing predictor.md note at line ~348) | ✓ |

### Corrections made to the brief's prose

1. **`predictor.horizon_slider_max_mult` is a config key, not a predictor attribute.**
   `grep` over `spacesim/predictor.py` shows no such attribute; the value is
   `config.get('predictor.horizon_slider_max_mult', 4.0)` read into the
   `HORIZON_MULT_MAX` local in `test.py::main()` and passed to `horizon_targets()`
   as `ceiling_mult`. Both notes now name it as the **config ceiling**
   `predictor.horizon_slider_max_mult` (the dotted `section.key` form the rule
   files already use for config, e.g. `camera.max_scale`), not as an object
   attribute.

2. **The knob's `on_change` does not itself call `set_display_length`.**
   The brief's hud-ui text said the slider "only ever calls
   `predictor.set_display_length()`". Actual wiring: `HorizonSlider.on_change`
   is `set_predictor_horizon_mult` (`test.py:376-379`), which only writes the
   clamped `predictor_manual_mult` nonlocal. The per-frame
   `apply_predictor_horizon()` reads that multiplier and issues the single
   `predictor.set_display_length()` call. The hud-ui note now states this
   two-step path explicitly ("moving the knob only writes a clamped
   multiplier … `apply_predictor_horizon()` … turns that into one
   `predictor.set_display_length()` per frame"). The predictor.md note keeps
   the shorter "rides `set_display_length` every frame" framing, which is
   accurate at that file's altitude.

3. **Response curve** — written as "`x^1.8` response on the deadzone-shifted
   magnitude" rather than a bare `x^1.8`, since the code raises
   `((|x|−dz)/(1−dz))` to 1.8, not `x`.

---

## Edit 1 — `.claude/rules/hud-ui.md`

### 1a. widgets bullet (list of widget classes)

```
  - `ui/widgets/` — Panel, Group, Label, Readout, Button, Toggle,
    SegmentedControl, Slider (linear/log), HorizonSlider (centre-sprung rate),
    Dropdown.
```

(was: `… Slider (linear/log), Dropdown.`)

### 1b. new section, inserted after the navball notes (immediately before `> **The reference list unfolds DOWNWARD out of its button.**`)

```
`Telemetry` accepts `ui_state=None`, so the test goes through that door).

> **The horizon slider is a RATE control, not a position one**
> (`ui/widgets/rate_slider.py::HorizonSlider`, bottom-left stack under FRAME +
> the SYSTEM/LOCAL zoom buttons). The knob rests at centre and springs back
> there (`ease` at `theme.motion.fast`); its displacement is the *speed* at
> which the drawn prediction length changes, integrated in `update()` as
> `mult *= exp(k·f(offset)·dt)`, `k = ln(max/min) / sweep` sized so a full
> deflection sweeps `predictor.horizon_slider_min_mult` (0.25) → `_max_mult`
> (4.0) in `_sweep_seconds` (2.5). A ±0.06 deadzone and an `x^1.8` response on
> the deadzone-shifted magnitude keep it still at rest and fine near centre.
>
> It is smooth because moving the knob only writes a clamped multiplier
> (`set_predictor_horizon_mult`); `apply_predictor_horizon()` in `test.py`
> turns that into one `predictor.set_display_length()` per frame — an O(1)
> clip of the already-computed curve. While the knob is held that function
> reads `hud.horizon.is_grabbing` and, via `test.py::horizon_targets()`, pins
> the *computed* horizon (`set_length`, async/soft) as if the manual factor
> sat at the `_max_mult` ceiling, so the `1e-9` guard swallows every
> `set_length` after the first — one recompute per drag, not per frame. The
> `+` / `-` keys are unchanged (they still `predictor.reset()`).

> **The reference list unfolds DOWNWARD out of its button.**
```

### 1c. layout blockquote ("The HUD is four blocks in four corners")

```
bottom-centre the navball cluster with the snap rosette docked to its right;
> bottom-left frame selector, zoom and the predictor-horizon slider.
```

(was: `> bottom-left frame selector and zoom.`)

---

## Edit 2 — `.claude/rules/predictor.md`

New blockquote inserted after the warp-STEP `set_length(soft)` note (the block
ending "… `points[0]` is the ship and carries a deliberately short first
chord."), before `> **Real time now uses the hold's mechanism too …`:

```
>    O(1)), taken **mid-curve**, because `points[0]` is the ship and carries a
>    deliberately short first chord.

> **The HUD horizon slider rides `set_display_length` every frame.** It is a
> rate control (`ui/widgets/rate_slider.py::HorizonSlider`): the drawn length
> tracks the knob through `set_display_length` (O(1), no recompute,
> independent of the hold / async swap / thrust), while the *computed* length
> trails via the already-soft `set_length`. `test.py::horizon_targets()` pins
> the computed target as if the manual factor sat at the config ceiling
> `predictor.horizon_slider_max_mult` (4.0) while `hud.horizon.is_grabbing`,
> so the `1e-9` guard in `apply_predictor_horizon()` trips once per drag and
> the async pipeline is never thrashed. No `reset()` on this path — that
> (still on `+` / `-`) is the synchronous `_compute_full` the slider exists to
> avoid.

> **Real time now uses the hold's mechanism too — the Ap/Pe markers were
```

---

## Edit 3 — `.claude/rules/camera-input.md`

Controls list, the `+` / `-` row:

```
- `+` / `-` — predictor length ×2 / ÷2 (instant, full recompute). `9` / `0` —
  predictor precision (finer / coarser). The **HUD horizon slider**
  (bottom-left, under FRAME) is the smooth alternative to `+` / `-`: a
  centre-sprung rate control that changes only the *drawn* length per frame
  (`predictor.set_display_length`), with the computed horizon trailing
  asynchronously. See `.claude/rules/hud-ui.md`.
```

(was: `- `+` / `-` — predictor length ×2 / ÷2. `9` / `0` — predictor precision
  (finer / coarser).`)

---

## Self-review

- **Tight?** hud-ui section is 20 lines (2 short paragraphs) — same order as the
  brief's draft and in line with neighbouring navball blockquotes. predictor.md
  note is 11 lines, one paragraph, matching the surrounding soft-invalidation
  notes. camera-input.md is a 6-line list item. No changelog-style prose; each
  note states the rule + the mechanism that enforces it.
- **Style match?** All three files are English-leaning; kept English. Used the
  files' existing conventions: `` `file::symbol` `` refs, `> **Bold lead.**`
  blockquotes, dotted config-key names.
- **Facts unverified?** None load-bearing. Not independently re-derived: the
  measured `+`/`-` = `_compute_full` cost (taken from the existing predictor.md
  `reset()` note, not re-measured) and `theme.motion.fast`'s numeric rate
  (named, not quoted). The claim "one recompute per drag" is the design intent
  encoded by `horizon_targets` + the `1e-9` guard, read from the code, not
  timed in a running session.
- **Cross-references** are explicit paths (`.claude/rules/hud-ui.md`), per the
  project CLAUDE.md rule.
