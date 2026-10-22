---
paths:
  - "spacesim/physics/surface.py"
  - "spacesim/bodies/terrain.py"
  - "spacesim/render/surface.py"
  - "spacesim/render/ship_close.py"
  - "spacesim/render/view_rotation.py"
  - "spacesim/render/gl/surface.frag"
  - "spacesim/render/gl/ship_close.*"
  - "spacesim/tests/landing_test.py"
  - "spacesim/bodies/spaceport.py"
  - "spacesim/render/spaceport.py"
  - "spacesim/render/gl/spaceport.frag"
  - "spacesim/runtime/spawn.py"
---

# Oberflaeche, atmosphaere, landung -- und die nahansicht

| datei | rolle |
|---|---|
| `bodies/terrain.py` | festes gelaende `h(lam)` je koerper, reines numpy; EINE funktion fuer physik und bild |
| `physics/surface.py` | `SurfaceSystem` an `world.surface`: widerstand, aufsetzen, gelandet halten, abheben, absturz, raffungsgrenze, linienschnitt |
| `render/surface.py` | `SurfaceViewMixin`: boden, luft, wolken, tag/nacht, staub (+ `render/gl/surface.frag`) |
| `render/view_rotation.py` | `ViewRotationMixin` + `ViewRotatedFrame`: nahe am koerper rollt das bild, boden unten |
| `render/ship_close.py` | `ShipCloseMixin`: schiff in echter groesse (100 m), 3D-licht, plasma (+ `render/gl/ship_close.{vert,frag}`) |
| `bodies/spaceport.py` | der startplatz auf der Erde: plateau, rampe, plattform als teil von `h(lam)`; bauten als grundformen |
| `render/spaceport.py` | `SpaceportViewMixin`: die bauten in der nahansicht (+ `render/gl/spaceport.frag`) |
| `runtime/spawn.py` | start auf der plattform (`spaceport.spawn_on_pad`) |

Tunables: `config.json` → `surface` (`ConfigLoader.apply_to_surface`, physik
direkt, ansicht als `renderer.surface_*`). Je koerper in der systemdatei:
`rotation_period` (s, negativ = rueckwaertig), optional `rotation_phase`,
`atmos_scale_height` (m), `terrain_relief_m`, `ground_color`.

## Drehung ist exakt aus der zeit

`body.rotation_angle(t) = phase + 2pi t / P` -- nie aufsummiert, aus
demselben grund wie das Kepler-modell (`physics-world.md`): ein schritt oder
hundert geben denselben winkel. Koerperfeste laenge = weltwinkel −
`rotation_angle(t)`. Die physik bleibt baryzentrisch; koerperfest ist nur die
GESPEICHERTE landestelle (`landed_lam`, `landed_r`).

## Gelaende: oktaven mit GAIN > 0.5

`BASE_CELLS · 2^k` zellen um den umfang, periodisch gehasht (schliesst bei
2pi, `landing_test` §1). Amplitude `A·GAIN^k`, `GAIN = 0.72` bis
`FINE_OCTAVE` (14, ~400 m an der Erde), danach 0.45. Bei 0.5 waere die
steigung auf jeder skala gleich -- nah heran eine flache linie. Gemessen an
der Erde (fenster → hub): 20 km → ~540 m, 2 km → ~60 m. Krater auf koerpern
mit `atmos_density < 2`. `A = 3·sqrt(R)` (Erde 7.6 km gesamt).

> **Das bild zeichnet nie feiner als die physik** (`terrain_min_wavelength_m`,
> 4 m). Feinere oktaven im bild stellten das gelandete schiff sichtbar neben
> den boden: bei 100 px/m ist 1 m schon 100 px.

## Widerstand: Strang-split um den schritt, nicht im integrator

`world.step` ruft `before_step` (halber kick) und `after_step` (halber kick,
aufsetzen). Der RKN4 rechnet `a(r, t)` und ist bit-gleich mit seinem
numba-zwilling -- ein geschwindigkeitsabhaengiger term haette beide brechen
muessen. Bei festem rho ist der quadratische widerstand exakt:
`v(dt) = v0 / (1 + k v0 dt)`, `k = rho/2 · Cd·A/m` (`landing_test` §3:
2857.568354 m/s gegen 2857.568354 erwartet). Die luft dreht mit
(`omega × r`). Dichte `rho0·exp(-h/H)`, `rho0 = atmos_density ·
atmos_density_per_unit` (20 → 1.225 kg/m³), obergrenze bei `rho0 ·
atmos_top_density_ratio` (Erde ~117 km).

> **In der atmosphaere ist die raffung echtzeit** (`world.warp_timescale`
> gibt 1e-9 zurueck). Ein kick je frame ist nur bei ~1/3 s je frame
> genau. `warp_timescale` ist eine EIGENE methode neben
> `characteristic_timescale`: loop, HUD und WARP TO lesen sie, der predictor
> nicht (seine schrittdecke ist eine frage der bahn). Gelandet: keine
> grenze (1e30). Im anflug: ein frame rueckt hoechstens 1/`approach_frames`
> der zeit bis zum eintritt vor -- nur wenn die oskulierende bahn die schale
> trifft, sonst bliebe jede ellipse ueber der atmosphaere gebremst.

`world.step` ohne `surface` (oder ein schiff weit weg) ist bit-gleich zu
vorher (`landing_test` §3, parkbahn mit/ohne).

## Gelandet = aus der dynamik genommen

`ship.landed` laesst `update_dynamics` das schiff ueberspringen; `_pin`
setzt es nach jedem schritt auf `koerper(t) + r·(cos phi, sin phi)`, `v =
v_koerper + omega × r`, nase radial. Darum laeuft jede raffung am boden, und
nach 6 h im zeitraffer steht es auf 1e-6 grad an der mitgedrehten stelle
(`landing_test` §4). Schwerpunkt = boden + halbe schiffslaenge (die duesen
sitzen bei −115 von 230 einheiten).

- **Abheben**: radialer schub dieses schritts > `g·dt`. Darunter schluckt der
  boden jeden schub (§5).
- **Absturz**: aufprall gegen die mitdrehende luft > `crash_speed_m_s`
  (12), neigung > `max_landing_tilt_deg` (35°, umkippen) oder ein koerper
  ohne festen boden. Das wrack BLEIBT LIEGEN, wie es aufschlug: lage zum
  boden fest (`landed_rel_theta`, dreht mit), tiefster rumpfpunkt am boden;
  abheben geht weiter. `crash_respawn_s > 0` schaltet das alte zuruecksetzen
  in die startbahn wieder ein (vorgabe 0: es riss die ganze landung ab).
- **Der rumpf ist eine ellipse** (`ship_extent`: halbe laenge 0.5 L, halbe
  breite 0.25 L): aufsetzen, sobald der schwerpunkt `extent(neigung)` ueber
  dem gelaende ist. Mit der festen halben laenge setzte ein quer
  anfliegendes schiff 25 m UEBER dem boden auf (§6 misst 25.0 m).
- **Aufsetzen prueft die STRECKE des schritts** (bis 96 punkte in einem
  numpy-aufruf, dann halbieren), nicht nur den endpunkt: im zeitraffer
  sprang ein schiff sonst durch kleine monde.
- **`_prev_rel` ueber `position_at_time`, bis der erste schritt lief**: beim
  aufbau stehen alle geskripteten koerper auf (0, 0). Mit `body.position`
  zog die strecke im ersten bild quer durch die Sonne -- „ABSTURZ auf Sonne"
  beim start.

`ambient_density` / `ambient_air_rel` (am ende jedes `after_step`, auch
gelandet) sind NUR fuer die abgasfahne: `_drag_kick` laeuft am boden nicht
und nullt seine felder, auf der rampe stuende die fahne sonst im vakuum
(`.claude/rules/body-art.md`). Landen ohne eindringen aus dem dev-panel:
`.claude/rules/devui.md`.

## Die vorhersage endet am boden

`prediction_cut` schneidet die linie am ersten punkt unter dem gelaende des
naechsten koerpers (64 Kepler-stuetzstellen, linear dazwischen). Ohne
schnitt zog eine suborbitale ellipse durch den planeten und lag bei 3 px/m
als buendel paralleler striche im bild (45 000 magenta-pixel gegen 377
danach). Rechnet nur, wenn die oskulierende bahn die schale trifft. Der
predictor selbst kennt keinen widerstand: in der luft zeigt die linie die
vakuumbahn.

## Nahansicht: um einen ANKER, in double vorbereitet

Einblendung ueber `view_start_radius_screens .. view_full_radius_screens`
(radius / bilddiagonale); voll eingeblendet ersetzt sie die pixel-scheibe
(`_surface_hides_body`). Der anker ist der punkt der kugel unter der
bildmitte; der shader rechnet `alt = (2 r0 w + w² + u²)/(r + r0)` -- `r − r0`
loeschte in float32 aus (Erde: 0.2 m fehler, bei 100 px/m 20 px).

- **Die gelaende-textur kommt aus python** (`view_samples` stuetzstellen,
  double), nicht aus einem shader-rauschen: die laenge `lam·R` ist an der
  Erde 4e7 m, float32 haette dort 4 m spiel.
- **Muster haengen am koerper**: zellraster am gerundeten mittelpunkt,
  wolken und koernung ueber versaetze modulo 256 musterzellen (`_wrap_cells`;
  die periode ist ein vielfaches der zelle, sonst ein saum beim
  ueberlauf). Die koernung hat vier oktaven (4 m × 37^k); genommen wird die
  erste, deren zelle ≥ 3 bildzellen ist -- sonst flirrt sie.
- **Helligkeit faellt in BILDzellen**, nicht in metern: rand (1 zelle, vom
  hang und der sonne beleuchtet), krume (3), schichten nach log-tiefe, ab
  ~48 zellen der koerper VON OBEN (flecken der stufenfarben, tageslicht) --
  so passt das innere zur pixel-scheibe, in die es ueberblendet. Mit
  metern war bei 0.02 px/m alles unter 1 km schwarz.
- **Tag/nacht**: `cos(phi − phi_sonne)` je pixel; der koerper dreht sich,
  die daemmerung wandert ueber das gelaende. Himmel `atmosphere_color`,
  daemmerung orange, nachts durchsichtig (sterne).
- **Boden-farbe**: `ground_color` wenn gesetzt (Erde `#6f8a4a` -- ihre
  stufen sind vier blautoene), sonst die stufen von `build_planet_style`.
- **Teilchen** (`SurfaceParticles`, koerperfest): staub, sobald das heck
  < 2.5 schiffslaengen ueber grund ist und die duesen zum boden zeigen; er
  setzt auf der bodenhoehe seines ausstosses auf. Schwebeteilchen in der
  luft nahe am boden.

## Das bild rollt: boden unten (`render/view_rotation.py`)

Das bild dreht sich, bis die oertliche senkrechte AM SCHIFF nach oben
zeigt, nur wenn alle drei gelten: die kamera folgt dem schiff, das schiff
ist hoechstens `view_rotate_altitude_m` (10 km) ueber dem gelaende, und die
laengere bildkante zeigt hoechstens `view_rotate_span_m` (1000 km). Austritt
mit hysterese (12.5 km, 1250 km), dann zurueck auf 0. Nachgefuehrt wird nur
der ABSTAND zum ziel (`view_rotate_rate` 1.0/s, kuerzester weg), das ziel
selbst exakt -- sonst kam der winkel ab 1 d/s der erddrehung nicht nach.

> **Nie an der kamera-position messen.** Die erste fassung nahm die
> bildmitte gegen den naechsten koerper (1.6 radien). Ein klick auf einen
> koerper fliegt die kamera zu seiner MITTE; dort hat die senkrechte keine
> richtung, und das bild drehte sich im anflug einmal ganz herum. Ausserdem
> drehte es schon beim eintritt in die atmosphaere.

- **Eine huelle um den plot-frame, keine zweite projektion.**
  `_active_frame()` gibt `ViewRotatedFrame(inner, angle)` zurueck; jede
  projektion des renderers laeuft schon ueber `_active_frame()`, also dreht
  sich linie, bahnlinien, picking, kurs und orientierungs-rast ohne eigenen
  weg. Was die huelle nicht selbst kann, reicht `__getattr__` durch.
- **`theta` ist im uhrzeigersinn**: `transform_heading` zieht den winkel
  ab, `heading_from_this_frame` addiert ihn -- mit `+` drehte die nase
  gegen das bild.
- **Caches haengen an `id(frame)`**: die huelle wird nur bei geaendertem
  winkel (gerundet auf 1e-4 rad = 0.13 px am rand) neu gebaut, die letzten
  64 bleiben referenziert, damit keine id wiederverwendet wird.
- **Schwenken** (WASD, ziehen, nachlauf) dreht sein delta um
  `camera.view_rotation` zurueck in die welt (`Camera._shift_target_position`),
  sonst liefe das bild schraeg.

## Abgas am boden

Der boden unter dem schiff ist eine halbebene im schiffsraum
(`_ship_ground_plane`: `n.p + d < 0` ist erde, `d` = GEZEICHNETER abstand
zum boden in bauform-einheiten -- als sprite ist das schiff groesser als in
echt, der boden nicht). Partikel (`ship/plume.py::_bounce`) werden auf die
flaeche gesetzt, senkrecht mit 25 % zurueckgeworfen, quer gestreut; der
heisse kern endet am boden. Im 3D-schiff (`ship_close.frag`) endet der
strahl am aufschlagpunkt und laeuft als flache schicht nach beiden seiten
weiter (zweiter durchgang je duese mit `s = s_aufschlag + |quer|`). In die
erde reicht keins von beiden.

**Das 3D-schiff und der einschub tragen die PARTIKEL-fahne des icons**,
nicht mehr die shader-fahne. Voll eingeblendet zeichnet
`_draw_ship_pixel(..., plume_only=True)` nur fahne, schein und hitze (die
rumpfzellen bleiben leer), darueber das 3D-schiff mit `u_plume_on = 0`
(die shader-fahne bleibt nur fuer `ship_pixel_style = vector`). Der
zellpuffer ist dafuer 384 statt 160 zellen gross: bei 1000 px schiffslaenge
blieben die zellen sonst 19 px. Der einschub dreht dieselben partikel in den
schiffsraum, rastert sie in einen 224×120-puffer (`_inset_heat_pass`) und
liest ihn beim strahlengang als schicht mit gauss-dicke ueber z (breiter mit
dem abstand zur duese), verstaerkung 0.35. Im leerlauf (spool ≤ 0.02) keine
fahne im kasten, wie vorher (`inset_test` §9).

## Hoehenzuege und horizontschein

Ueber dem boden drei hoehenzuege (`surface.ridges`): fern hoeher und
dunstiger. Ihre hoehe ist ein BILDanteil, weit draussen auf echte meter
begrenzt -- als kulisse sollen sie nicht mit dem zoom wachsen. Beleuchtet
aus sonnenstand plus hangneigung.

> **Der zoom darf die kulisse nicht verschieben, die bewegung schon.**
> Waagerecht ist die rauschkoordinate `bildpixel ab mitte / zelle + off_k`,
> und `off_k` wird AUFSUMMIERT (`_ridge_parallax`): je bild
> `k · Δs · scale / zelle` mit `k` = 0.12 / 0.25 / 0.45 (fern -> nah), also
> ein bruchteil der bodenbewegung auf dem schirm. Zwei fehlversuche davor:
> `lam·R·scale` als absolute groesse sprang bei jedem zoom um millionen
> zellen (flackern); feste 300 / 120 / 45 km je zelle bewegten die zuege
> bei start und landung gar nicht. Gefaltet wird modulo 2560 zellen -- der
> shader liest x, 2.3 x und 5.1 x, nur 2560 macht alle drei zu
> vielfachen der 256er-hash-periode.

- **Mit luft**: 12 / 8 / 5 % der bildhoehe, hoechstens 0.16 / 0.11 / 0.07
  skalenhoehen (Erde 1.3 km: unter der wolkenbasis 0.18 H), deckend, dunst
  62 / 40 / 18 % zum himmel. Mit 22 % und 1.2 H standen sie nah heran gross
  ueber den wolken und schrumpften erst unter 0.018 px/m.
- **Ohne luft**: 9 / 6.5 / 4 %, hoechstens 2 / 1.4 / 0.8 km, eine
  tonstufe dunkler und zu 78 / 68 / 58 % in den schwarzen himmel gedrueckt.
  Mit den werten der luftkoerper standen sie hoch und hell ueber dem rand
  und lasen sich als der eigentliche boden.

Am rand ein gedithertes flimmern in der BODENfarbe (hellste stufe, mit luft
25 % atmosphaerenfarbe): dichte `(1 − h/3 zellen)² × 0.38` (mit luft
0.55) gegen die Bayer-schwelle. Ein flaechiger schein in atmosphaerenfarbe
liess luftlose koerper aussehen, als haetten sie eine atmosphaere.

## Schiff in echter groesse

`_ship_length_px = max(sprite, ship_length_m · scale)`; zwischen 1× und
`ship_close_fade`× (echt/sprite) blendet der pixel-sprite in das 3D-schiff:
die karten des einschubs (`ship/inset_model.py`) von OBEN, normalen aus dem
hoehenfeld, licht = `_body_light_dir` in den schiffsraum gedreht, z ≥ 0.6.
**Materialien statt einer rampe**: lack (gesaettigt), blankes metall
(ungesaettigt und holme: diffus schwach, spiegelt in eigener farbe), glas
(cyan-blau: starke Fresnel-spiegelung, scharfes glanzlicht). Diffus +
Schlick-Fresnel gegen eine umgebung (himmel zur oertlichen senkrechten,
boden davon weg; im all dunkles HUD-blau) + Blinn-Phong, verdeckung aus dem
hoehenfeld. ERST das ergebnis wird gerastert: sechs stufen je kanal, dither
nur ±0.15 stufe -- ein voller Bayer-dither machte jede flaeche zu
salz-und-pfeffer. Glanzlichter als harte helle pixel. Der umriss ist nur
noch auf der schattenseite und nur ×0.72 (vorher immer, zwei stufen dunkler:
die linie trug die form statt des lichts).
Es dreht sich nur in der ebene. Schatten nur vom NAECHSTEN koerper (seine
nachtseite): eine finsternis durch einen anderen koerper machte das schiff
dunkel auf taghellem boden -- beim ersten mond-bild stand die Erde genau
zwischen Mond und Sonne. Plasma aus `SurfaceSystem.ship_heating`
(`sqrt(rho) v³`, log-skaliert zwischen 3e9 und 2.5e10; beginn ~85 km an der Erde -- mit 4e8 gluehte es bis zur luftobergrenze, unter schwarzem himmel), stosshaube auf der
luvseite, schweif im lee, auch hinter dem kleinen sprite (`u_mode 1`).

## Der himmel dithert BILDFEST

Boden, wolken und schein rastern auf einem am koerper verankerten
zellgitter (sie sollen mit der welt wandern). Der himmelsverlauf nicht: ein
50-%-schachbrett, um eine zelle verschoben, ist sein eigenes negativ --
gemessen 20-27 % aller pixel je bild im horizontalflug, ein flimmern.
Bildfest (eigenes gitter `floor(frag / cell)`, hoehe an dessen
zellmitte) wandert nur die stufenkante: 3-4 %, und das ist die welt.

## Wolken: haufen, nicht streifen

**Dynamisch wie im gasriesen** (2026-10-20): `vnoise3` mit `u_time`,
gruppen entstehen und vergehen, ein zeitabhaengiges wirbelfeld verdreht die
form; deckkraft aus der dichte (`smoothstep(TH − 0.08, TH + 0.20)`, vier
stufen gedithert), UEBER den himmel gelegt statt ihn zu ersetzen (vorher
0.96 deckend mit harter kante). Dazu **ferne wolkenbaenke um die
hoehenzuege**: in bildeinheiten wie die zuege (zoomfest), mit der
parallaxe des mittleren zugs, 45 % in den himmel gedrueckt, vor dem fernen
zug, hinter den naeheren (`ridge_k`).

- **Formwandel 0.6× langsamer, wind 40 m/s** (war 12): die wolken ziehen
  sichtbar, ohne zu brodeln.
- **Fuenf oktaven bis 1/12 der zelle** und eine vierte probe FEIN zur
  sonne (0.07 zellen): jede kleine quellung hat ihre helle und dunkle
  seite. Die feinen oktaven blenden aus, sobald ihre zelle unter ~5
  bildzellen faellt (sonst flirren sie weit draussen).
- **Die fernen baenke sind ISOTROP** (beide achsen `cellp / 3.2`). Vorher
  x in `cellp / 0.7`, y in `cellp · 0.32`: 4.4-fach in die breite gezogen,
  sie lasen sich als ein weiterer hoehenzug. 3.2, weil `u_ridge_off`
  modulo 2560 laeuft und 2560 × 3.2 = 8192 ein vielfaches der 256er
  hash-periode ist. Vier oktaven, eigener sonnenschatten.
- **Zwei wolkenfelder** (vorn, knapp dahinter mit eigenem muster, 85 %
  deckend, 25 % im dunst), jede wolke mit eigenem hoehenversatz (langsame
  noise ueber x, ±0.15 band; das hintere feld +0.10 band): sie
  ueberlappen, statt alle auf EINEM band zu liegen.
- **Weniger weiss**: der grobe schatten ist gestaucht (±0.45) und die feine
  struktur geht VOR der klemme hinein -- danach addiert blieb das helle
  innere (grober wert weit unter 0) reinweiss. Dazu fugen zwischen den
  ballen (`|2n − 1|` klein), kuehle schatten, warme lichter, ein grauer
  mittelton. Gegenprobe mit falschfarben je tonstufe: vorher fast nur
  stufe 3 und 1.


Isotrope zellen (`0.18 H`, Erde 1.5 km, in beide richtungen GLEICH -- die
alte 2.4 H × 0.32 H zelle zog jede wolke zum streifen), flache basis bei
0.18 H, kuppen bis 0.8 H, bedeckung in gruppen (zelle 7×) mit klarem himmel
dazwischen. Licht: weniger dichte UEBER der zelle (zur sonne versetzt) =
helle kuppe; freie zelle darunter = schattige basis.

> **Keine gezeichneten wolken-objekte.** Ein versuch mit pixel-art-haufen
> (runde ballen auf flacher basis, kugel-schattierung, 9a5499b) wurde als
> klobig und kindlich verworfen und zurueckgenommen: kein ausblenden, kein
> realismus. Das rauschfeld mit dichte-deckkraft bleibt der weg.

## Wolken v2 (`surface.cloud_style` 1..6, `render/gl/surface_clouds.glsl`)

0 ist der alte haufen-rauschweg oben. 1 kumulus, 2 + altokumulus/zirrus,
3 gewitter, 4 decke, 5 = 2 je bildpixel ohne stufen, **6 wetter** (1-4
gemischt). Die datei wird an `//@clouds` in `surface.frag` gesetzt
(`SurfaceViewMixin._compile_surface_program`). Je koerper eigenfarbe,
bedeckung, deckkraft in `render/surface.py::_CLOUD_LOOKS`.

- **Jeder haufen ist ein kandidat je 4 zellen** (`cl_env`: mitte, breite,
  hoehe, lebenslauf); die huelle ist ein vorzeichenbehafteter abstand in
  ZELLEN (gesaettigt bei 1.5), das rauschen (1 − F1-blasen) setzt den rand.
  Relativ gemessen waren kleine haufen glatte halbkugeln.
- **Die basis ist ein abstand, kein schnitt**: das feld steigt ueber 0.16
  zellen (Erde 250 m) ab dem kondensationsniveau an (fluessigwasser
  waechst adiabatisch linear mit der hoehe), darunter negativ, das
  rauschen franst die unterseite aus. Basis je wolke +-0.03 zellen, unter
  tuermen 0.06 tiefer; breiteste stelle bei ~0.28 der hoehe (unten 62 %),
  unterseite bis 30 % dunkler nach hoehe ueber der basis in zellen (nicht
  `hn`: das springt zwischen nachbarwolken). Vorher: unter der basis hart
  −1 und die verbiegung schob ganze basisstuecke -- jede wolke endete auf
  einem lineal wie eine abgeschnittene kugel.
- **Gesucht werden +-2 plaetze**, die breite ist auf 3 zellen begrenzt
  (amboss 2.7 hw): ein haufen reicht <= 8.5 zellen, der naechste nicht
  gepruefte platz liegt >= 8.8 weg. Mit +-1 schnitten tuerme und ambosse
  senkrecht ab.
- **Stil 6: `cl_regime`** (gewitter, decke, schichten, bedeckung) ueber 32
  haufenzellen, entschieden an der MITTE jeder wolke (nie halb turm).
  Decke nie im gewitter, keine haufen unter der decke, kein altokumulus
  ueber dem gewitter; das hintere feld rechnet dasselbe wetter in seine
  zellen um -- sonst stand ein hinterer turm in einer vorderen decke.
- **Wolkenbasis ab grobem gelaende**: zweiter kanal der profiltextur
  (wellen >= 20 wolkenzellen), sonst sassen die basen auf hohem gelaende.
- **Licht**: Beer-weg zur sonne (5 schritte), boden 0.30 (daemmerung 0.10)
  fuer das streulicht zum betrachter, himmelslicht nie unter 45 %, glatte
  blasen (`bubbles`, keine F1-knicke) fuer licht/schatten je quellung.
  Stufen: 12 je kanal, dither nur +-0.15 stufe -- voller Bayer machte ein
  farbiges schachbrett.
- **Schatten** auf boden und luft (`cl_shadow`) ab dem pixel aufwaerts;
  ab der basis gerechnet stand unter jeder decke eine dunkle "bergkette".
- **Ferne reihen** (`cl_rows`): vier reihen in bildeinheiten wie die
  hoehenzuege, 2/3 hinter dem fernen zug.
- Faktoren auf x sind vielfache von 1/256 (periode der versaetze).
- **Ein texel je bildzelle** (`_surface_cloud_pass`, `CLOUD_PASS` in
  `surface.frag`): nahe wolken, ferne reihen 2/3 und 0/1, schatten (luft,
  boden) in vier RGBA8-ziele der groesse `w/zelle + 2`; der hauptpass
  liest sie mit `texelFetch(gq + 1)`. Alles haengt nur an der zellmitte,
  vorher rechnete jedes bildpixel sein volumen neu (9x bei 1280x800,
  ~25x bei 1440p): RTX bei stil 6 auf 80 % last und 12 fps. Bild gleich
  (groesste abweichung 4/765 je pixel). Stil 5 bleibt je pixel (vergleich).
  Uniform-reihungen kuerzt der treiber im pass (`array_length`), `put`
  schneidet mit.
- Kosten (llvmpipe, ganzes bild): 1280x800 stil 0 104 ms, 1 55, 3 65,
  4 48, 6 62 (vorher 196); 2560x1440 nah an der wolke (0.4 px/m) stil 0
  497, 6 202, ohne wolken 104.

## Lesbarkeit ueber dem himmel

`theme.idle_fill` ist deckend (`#0d1a27`, 0.90; war 0.045): ueber einem
hellen taghimmel verschwanden ruhende knoepfe (SYSTEM, SRF, TGT) samt
schrift. Der PREDICT-regler hat eine grundplatte. Weltbeschriftungen
(`_blit_text_topdown`: Ap/Pe, koerpernamen) bekommen eine dunkle platte,
aber nur solange die nahansicht eingeblendet ist -- im all bleibt das bild
bit-gleich.

## Pruefen

`tests/landing_test.py` (rein, ohne GL). Bilder: `tools/game_shot.py`
`--land KOERPER`, `--fly KOERPER,HOEHE,V_HOR,V_RAD`, `--sun GRAD`
(0 mittag, 90 untergang, 180 mitternacht), `--thrust 0..1`. game_shot
klemmt die raffung wie das spiel (`_clamp_warp`); ohne das fiel ein schiff
in 55 km in fuenf bildern zu 18 s auf den boden.

Kosten (orbit, 28 koerper, ohne bild): `world.step` + 3× `warp_timescale` +
`prediction_cut` 0.22 → 0.50 ms je frame. `warp_timescale` ist je
(zeit, zustand) gemerkt, `params_for` vergleicht rohe felder statt den
namens-hash neu zu rechnen (vorher 0.69 ms).


## Rigid-body contact (`SurfaceSystem._rigid_step`, 2026-10-20)

At real-time steps (`dt <= rigid_max_dt`, 0.25 s) the ship touches ground as a
rigid body: the hull from `ship/hull.py` (convex hull of the build, <= 14
corners, plus a flat stern as wide as the hindmost tenth of the hull: the
nozzle bell alone is ONE point and the ship balanced on it), contacts at
every corner below ground, slope normals from the terrain, sequential
impulses with restitution 0.25 (only above 1.5 m/s, else a resting ship
jitters) and friction 0.7, then the penetration pushed out radially.

- **Speculative contacts** (corners up to 0.3 m above ground) stay in the
  solve; without them the push-out lifted the second foot out of the set and
  the ship rocked through upright and fell asleep on one foot. A gap the
  corner closes within this step counts as an impact, not as a brake, or a
  30 m/s crash lost its bounce.
- **Damping only while two corners touch** (`contact_damping` 8/s): a slender
  body loses ~4 % per corner change (Housner) and rocked for minutes on the
  Moon; on one corner (tipping) it stays free.
- **Sleep** after `rest_time_s` calm AND the centre of mass between two
  touching corners; then `landed`, pinned body-fixed in the pose it lies in
  (`landed_rel_theta`, 0 = upright). Tilt > `max_landing_tilt_deg` = tipped,
  `crashed`. A requested spin or thrust wakes it.
- **Crash = sink rate of the CENTRE OF MASS** > `crash_speed_m_s`, not the
  fastest corner (a turning ship moves its nose 50 m x rate).
- Warp: real time while in contact or below `warp_block_altitude_m` (500 m);
  only a sleeping ship warps (pinned, no clipping).
- Measured on flat ground (Moon): upright and 5° settle upright, 25° tips
  to 90°, 30 m/s bounces 17 m, a held rotate key tilts about the foot with
  no hull point deeper than 1 cm. `tests/landing_test.py` §8.
- The 16 m base tips past ~9° of slope. Rough terrain (the shipped octaves)
  is therefore often not landable; pick flat ground. Smoothing the terrain to
  fix this made the planets look flat and was reverted.

## Re-entry (`ship_close.frag`)

Shock layer (white-hot, flickering) on the windward side, a trail that fans
out (three rays), flaps and pulses, coloured hot -> orange -> pink -> violet
(`trail_col`), embers on a grid that travels DOWNSTREAM (`- u_time`; with
`+` they flew into the ship) and is fixed in SHIP units (20 x 10; sized in
screen cells it changed with every zoom step and every ember jumped; only
the ember's thickness widens to stay one cell), the trail's flap wave also
in ship units, a dithered glow halo, plasma light on the hull,
and a whole-pixel shake of up to 3 px (`ShipCloseMixin._reentry_shake`).
The clock (`_ship_close_time`) advances once per frame in `_ship_close_draw`;
counted only in the 3D pass, trail and embers froze behind the small sprite.
`u_flow` points from nose to tail (the air past the ship).

## Gasriesen: kein boden (2026-10-20)

`terrain.body_kind == 'gas'` (Jupiter, Saturn, Uranus, Neptun) hat keinen
kontakt: der 1-bar-radius ist eine konvention. `_rigid_step` und
`_check_contact` setzen dort nie auf; die dichte waechst unter 1 bar weiter
(`density_at` klemmt erst bei `gas_crush_depth_scale_heights`, 5 H, Jupiter
135 km, ~150 bar), und darunter zerdrueckt `_check_crush` das schiff
(wrack, koerperfest festgehalten). `prediction_cut` und `impact_arc` nehmen
fuer gasriesen den zerdrueck-radius statt der oberflaeche.

- **Raffung in der gasluft nicht echtzeit**: kein boden, an dem ein schritt
  vorbeischiessen koennte, der kick ist exakt. Begrenzt auf
  `min(gas_warp_step_s, 0.3 v_term / g)` je tick: mit festen 4 s sank das
  schiff bei 270 kg/m³ mit ~50 statt ~8 m/s (der split ueberrannte die
  sinkgeschwindigkeit). Mit der grenze: 98494 gegen 98418 m tiefe nach
  600 s, gegen 0.05-s-schritte.
- **Bild** (`surface.frag::gas_giant`, `u_kind 1`): alles ist luft. Dunst
  `1 − exp(−2.5 e^{−z})` (z = hoehe / H; oben durchsichtig, sterne
  scheinen durch, unter 1 bar deckend), bildfest gedithert wie der himmel.
  Ein deck ist KEIN festes band (`gas_deck`): basis und dicke wogen mit
  zwei grossraeumigen wellen (±0.8 / ±0.25 dicke), haufen wachsen in den
  gruppen zu tuermen (bis 1.4 dicken hoch), der rand ist domain-gewarpt,
  und die hintergrund-ebenen sitzen ±0.55 dicken versetzt zwischen den
  decks. Mit fester basis/kuppe je deck lagen alle wolken eines decks als
  gerader balken auf einer hoehe.
  Die wolken sind VOLUMEN, nicht flaechen: deckkraft aus der dichte
  (`smoothstep(0.16, 0.42, d)`, vier stufen, an den stufen gedithert),
  vorn nach hinten zusammengesetzt bis 95 % deckung, der dunst fuellt den
  rest. Als deckende erste wolke lasen sie sich wie scharfe, schwebende
  landschaften. Sie LEBEN (`u_time`, echtzeit): gruppen entstehen und
  vergehen (`vnoise3` mit zeit), zwei verschachtelte zeitabhaengige
  verzerrungen verwirbeln die form, die feinen oktaven ziehen schneller als
  die groben (gemessen 16 % der pixel anders nach 1 s). Farbton je stelle
  aus zwei koerperstufen und koerper-/luftfarbe gemischt, gerastert.
  Selbstschatten nur in der vorderen ebene (kosten).
  **Blenden geht vor form**: die hintergrund-ebenen decken nur 38 / 24 %
  (waren 85 % -- zwei fast feste flaechen hinter jedem deck, das bild las
  sich als gestapelte schwebende landschaften), jede wolke nimmt die
  dunstfarbe ihrer hoehe an (vorn 18-48 %, fern 55 / 72 %), deckkraft
  laeuft ueber `smoothstep(0.12, 0.55, d)` breit aus. Dazwischen
  FUELLWOLKEN unabhaengig von den decks (kleine haufen 0.6 H, baenke 3 H,
  hoechstens 55 / 40 %, unter z 2) und STAUB: festes gitter in metern je
  oktave (60 m … 60 km), gezeichnet die oktave mit 3-60 bildzellen, ein
  teilchen = eine bildzelle, HINTER der vorderen wolkenebene (plane 0) und
  vor den hintergrund-ebenen und fuellwolken (`gas_dust`, eingesetzt beim
  uebergang plane 0 → 1): ganz vorn wirkte er wie auf das bild geklebt. Drei schwaerme je oktave
  mit eigener drift (zellen/s: +0.35/−0.05, −0.22/−0.14, +0.12/−0.38 --
  seitwaerts beide richtungen, verschieden schnell fallend); das GITTER
  zieht mit (`g − v t`), ein teilchen gleitet und kreuzt nie eine
  zellgrenze. Vorher: 30 m/s in 600-m-zellen stand auf dem schirm still,
  und ein sinus-schaukeln liess es auf der stelle zucken. Mit
  den deckenden hintergrund-ebenen kam kein staubkorn durch (0.2 % statt
  6 % der pixel bei wahrscheinlichkeit 1). GLSL: `smoothstep(a, b, x)` mit
  a > b ist undefiniert -- `1 − smoothstep(b, a, x)` schreiben.
  Bis zu 24 wolkendecks (`SurfaceViewMixin._gas_layers`): neun obere
  (`GAS_LAYERS`, z +2.6 eis-schleier bis −3.7), darunter geometrisch je
  1.45-mal tiefer und dicker bis `GAS_DEPTH_FRACTION` (R/3, Jupiter 22 decks
  bis ~16 000 km). Wind abwechselnd ±120 … ±1 m/s, die baender ziehen
  gegeneinander. Zwischen den wolken eines decks zwei HINTERGRUND-ebenen
  (zellen 1.35× / 1.8×, in den dunst gedrueckt 45 / 68 %, parallaxe 0.65 /
  0.35 der bodenbewegung -- in METERN gerechnet, also zoomfest ohne
  aufsummieren) statt eines leeren himmels. Licht
  `gas_light(z) = exp(−max(0, 1 − z)/2.2)` in stufen; darunter haelt eine
  warme glut von innen (`gas_glow`, 0.06 → 0.18 bis R/3) die tiefen decks
  schwach sichtbar. Dieselbe sonnenkurve daempft sonne, grundlicht und
  umgebung des 3D-schiffs (`gas_light_at`). Die zerdrueck-tiefe (5 H)
  bleibt; die tiefen decks sieht man im herausgezoomten schnitt.
- **Ein texel je bildzelle, wie wolken v2**: `gas_clouds` (decks,
  fuellwolken, staub) laeuft im `CLOUD_PASS` nach `u_cl_t0`, der hauptpass
  setzt nur den dunst dazu (`gas_compose`, bayer am bildschirm wie vorher).
  Das ziel ist RGBA8, also farbe NICHT vormultipliziert ablegen -- geteilt
  durch kleine deckkraft verstaerkte sich sonst der rundungsfehler. Vorher
  rechnete jedes bildpixel bis zu 3 ebenen × 24 decks × 2 (selbstschatten)
  `gas_deck` mit je ~14 `vnoise3` neu, 9× je zelle bei 1280x800, ~25× bei
  1440p. Gemessen (llvmpipe, 1280x800, Saturn −20 km, `_draw_surface_view`
  mit `ctx.finish`): 0.02 px/m 254 → 33 ms, 0.002 px/m 233 → 31 ms.
  Gegenprobe mit staub wieder ganz vorn: groesste abweichung 5/765 je
  pixel zum alten bild.
- `landing_test` §9: sinkt unter 1 bar ohne aufsetzen, raffung begrenzt,
  wrack bei −135 001 m.


## Der startplatz (`bodies/spaceport.py`, 2026-10-22)

Fest an `spaceport.longitude_deg` (168.349 = 2.93826 rad: dort liegen 4 km
mit nur 13 m natuerlichem relief, und bei t = 0 steht die sonne 11.7° vom
zenit). Ortsfeste meter: `x` entlang der oberflaeche (+ = steigende laenge,
im bild NACH LINKS), `y` ueber dem plateau `h0` (mittel des natuerlichen
gelaendes, Erde 127.8 m). Masse echt: schiff 100 m, turm 118 m ueber dem
deck, halle 160 m; die abstaende eines echten komplexes (rampe -> halle
5.5 km) sind auf 1.7 km geschoben, damit bei 0.35 px/m alles im bild ist.

> **Rampe und deck SIND gelaende.** `terrain.heights` rechnet `site.apply`
> ein (plateau ueber `X_MIN..X_MAX`, smoothstep-blende 1500 m, dazu
> `solid_height`: huegel 15 m, deck 30 m). So steht, landet und startet das
> schiff auf dem deck ohne eigenen kontaktweg (`landing_test` §10: deck
> 30.000 m, abheben, geregelt mit 3 m/s zurueck auf 30.00 m). Turm,
> masten, hallen sind KEIN gelaende -- kein kontakt. `site=False` gibt das
> natuerliche gelaende; fern vom platz ist `heights` bit-gleich.

- **Die bodenschichten zaehlen ab dem natuerlichen boden**: dritter kanal
  der profiltextur (`heights − site.solid`), `surface.frag` zieht
  `hgt − prof.b` von der tiefe ab. Ohne das stand unter dem deck eine
  saeule verschobener schichten und der "von oben"-fleck.
- **Ein texel je bildzelle** wie wolken v2 (`_spaceport_targets`), dann
  `texelFetch(gq + 1)` auf den schirm; dasselbe zellraster, derselbe
  anker, dieselbe `ramp()`. Vor dem schleifenlauf ein huellen-test
  (`u_bounds`): himmel und tiefer boden kosten nichts. Python schneidet die
  formen auf den sichtbaren bereich (plus schattenreichweite zur sonne).
  Kosten (llvmpipe, 1600x900, 241 formen im bild): ~16 ms.
- **Duennes haelt eine zelle, unter 1/4 zelle faellt es weg** (`widen`);
  gittermasten unter 3 zellen je feld werden durchbrochene flaeche
  (bayer < 0.48), muster (fenster, rippen, baender) erst ab 2 zellen.
- **Licht**: grundstufe nach tageszeit, die kante zur sonne +1, die andere
  −1; kugeln aus der lage im umriss. Nachts leuchten fenster (`F_GLOW`,
  58 % der fenster) und flutlicht, rote warnlichter blinken (0.5 Hz) mit
  einer zelle schein.
- **Schatten nur auf den BODEN** (oberste 3 zellen unter dem gelaende,
  auch deck und wege), und nur von koerpern mit tiefe (kasten >= 6 m,
  gitter >= 10 m, ellipse >= 3 m; huegel nie). In der seitenansicht liegt
  alles in einer ebene: auf fassaden lag sonst ein schraeger keil unter
  jedem dachrand, und hinter jedem mast ein schattenband ueber 360 m.
- **Start**: `spawn_on_pad` = `land_at` an der platzmitte +
  `clear_center_radius` + `_pin`, kamera `spawn_view_m` (320 m) um das
  schiff, `renderer.view_rotation_snap`: das erste bild steht schon boden
  unten. `tools/game_shot.py --orbit` (und `--dv`/`--node`) startet wie
  frueher in der parkbahn, `tools/transfer_bench.py` immer.
