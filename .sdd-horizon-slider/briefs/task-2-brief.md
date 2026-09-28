## Task 2: `HorizonSlider.draw()` — the KSP2 instrument look

**Files:**
- Modify: `spacesim/ui/widgets/rate_slider.py` (add `draw`)
- Test: manual — `python tools/hud_shot.py`

**Interfaces:**
- Consumes: `ctx.draw` (`rect`, `circle`, `line`), `ctx.text.draw(text, x, y, role=, color=, align=, valign=)`, `ctx.theme.palette` (`panel_sunken`, `text`, `text_dim`, `accent_strong`, `text_muted`, `accent_for(role)`), lazy `from ..hud import chrome` (`chrome.tab`, `chrome.tab_text`), `spacesim/ui/units.py` `distance(m)`. `self.predictor.get_display_length() -> float | None`.
- Produces: nothing new — `draw` is called by `UIRoot.render()`.

- [ ] **Step 1: Add `draw` to `HorizonSlider`**

Append to `spacesim/ui/widgets/rate_slider.py` (inside the class, after `update`):

```python
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

- [ ] **Step 2: Render the HUD offscreen**

Run: `cd .. && python tools/hud_shot.py 1600 900 -o "$(pwd)/screenshots for debugging/horizon_slider_check.png"`
(the tool `os.chdir`s into `spacesim/` itself; pass an absolute `-o`).
Expected: exits `geschrieben: ...horizon_slider_check.png (1600x900, ui_scale 1.00)` with **no traceback**. The widget is not wired into the HUD yet (Task 5), so it will not appear — this step only proves `draw` imports and the lazy `chrome` import works. If it raises `ImportError` on `from ..hud import chrome`, the lazy import is wrong.

- [ ] **Step 3: Unit-check the readout helper (headless)**

Add to `tests/ui_horizon_slider_test.py` before the final summary block:

```python
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
```

- [ ] **Step 4: Run the test**

Run: `cd spacesim && python tests/ui_horizon_slider_test.py`
Expected: PASS.

- [ ] **Step 5: Review checkpoint**

Summarise: `draw` added, `hud_shot.py` runs clean, readout helper tested. Note the widget still isn't visible in-HUD (Task 5). Wait for approval.

---

