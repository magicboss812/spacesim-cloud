# Graph Report - spacesim  (2026-09-08)

## Corpus Check
- 129 files · ~237,072 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2664 nodes · 4830 edges · 158 communities (122 shown, 36 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 140 edges (avg confidence: 0.86)
- Token cost: 319,765 input · 0 output

## Community Hubs (Navigation)
- Predictor Numba Kernels
- Core Physics & Config Bootstrapping
- UI Theme & Palette
- Maneuver HUD Panel
- Maneuver Planning
- Seminararbeit Draft & Outline
- Body Rendering
- Camera
- Vec2 Math
- Config Loader
- GitHub Update Logs
- Unit Formatting
- Body Browser Widget
- UI Core Framework
- Navball Cluster
- System Map Widget
- Starfield & Grid Background
- Shader Pipelines
- Attitude Ring
- Predictor View / Display Line
- Maneuver HUD Panel (2)
- N-Body World Integrator
- Ship Rendering
- Bootstrap & Frame Controller
- Draw Primitives & Clipping
- Renderer Text & Labels
- UI Draw Batch
- Maneuver Autopilot Executor
- Predictor Warp Hold
- Ship Geometry & Art
- Maneuver Preview Chain
- UI View State
- Frame Loop & Timing
- Tests: Orbit Lines
- Renderer Core
- Ship Control & Autopilot
- Predictor Core
- ImGui Dev Tools
- Tests: Ui Horizon
- Telemetry Readouts
- UI Theme & Palette (2)
- Planet Style Generation
- Tests: Selection Camera
- ImGui Dev Tools (2)
- Predictor Async Jobs
- Horizon Rate Slider
- Reference Frames (Principia-style)
- Predictor Horizon Policy
- Reference Frames (Principia-style) (2)
- Reference Frames (Principia-style) (3)
- Prediction Line Drawing
- Prediction Line Drawing (2)
- Input Router
- UI Text Renderer
- OpenGL Device & FXAA
- Button & Segmented Control
- Reference Frames (Principia-style) (4)
- Maneuver Rendering
- Maneuver Plan & Nodes
- Apsis Tooltip
- Dropdown Widget
- Panel & Stack Layout
- Body Icon Generation
- Reference Frames (Principia-style) (5)
- Orbit Line Rendering
- Tests: Ui Hud
- ImGui Dev Tools (3)
- HUD Control Bars
- Tests: Background Test
- Tests: Body Icon
- UI Core Framework (2)
- HUD Panels & Ship Badge
- UI Text Renderer (2)
- Label & Readout Widgets
- Orbit Lines (Bahnlinien)
- Reference Frames (Principia-style) (6)
- Starfield & Grid Background (2)
- Predictor Horizon Policy (2)
- Tests: Ship Scale
- UI Theme & Palette (3)
- Tests: Warp Predictor
- HUD Layout
- HUD Panels & Ship Badge (2)
- Telemetry Readouts (2)
- Slider Widget
- Orbit Lines (Bahnlinien) (2)
- Prediction Line Drawing (3)
- Tests: Warp Predictor (2)
- Orbit Lines (Bahnlinien) (3)
- Apollo 11 Mission Phases
- Orbital Mechanics Theory (Curtis)
- Orbital Mechanics Theory (Curtis) (2)
- Tests: Devui Timing
- HUD Control Bars (2)
- HUD Control Bars (3)
- Tests: Frame Origin
- Starfield & Grid Background (3)
- Starfield & Grid Background (4)
- Body Icon Generation (2)
- Orbit Lines (Bahnlinien) (4)
- Apollo 11 Mission Phases (2)
- Orbital Mechanics Theory (Curtis) (3)
- Reference Frames (Principia-style) (7)
- Tests: Warp Predictor (3)
- Window & Clock
- UI Core Framework (3)
- HUD Control Bars (4)
- Planet Style Generation (2)
- Apollo 11 Mission Phases (3)
- Apollo 11 Mission Phases (4)
- Attitude Ring (2)
- HUD Panels & Ship Badge (3)
- Button & Segmented Control (2)
- Planet Style Generation (3)
- Orbit Lines (Bahnlinien) (5)
- Orbit Lines (Bahnlinien) (6)
- Orbital Mechanics Theory (Curtis) (4)
- Orbital Mechanics Theory (Curtis) (5)
- Reference Frames (Principia-style) (8)
- Telemetry Readouts (3)
- UI Text Renderer (3)
- UI Text Renderer (4)
- Telemetry Readouts (4)
- UI Theme & Palette (4)
- Orbit Lines (Bahnlinien) (7)
- N-Body World Integrator (2)
- Starfield & Grid Background (5)
- Tests: Warp Predictor (4)
- ImGui Dev Tools (4)
- HUD Chrome & Frames
- HUD Chrome & Frames (2)
- UI Core Framework (4)
- Orbital Mechanics Theory (Curtis) (6)
- Starfield & Grid Background (6)
- Tests: Warp Predictor (5)
- Tests: Warp Predictor (6)
- Tests: Warp Predictor (7)
- Render Init
- Tests: Background Test (2)
- Tests: Background Test (3)
- Tests: Warp Predictor (8)
- Tests: Warp Predictor (9)
- Tests: Warp Predictor (10)
- Tests: Warp Predictor (11)
- Tests: Warp Predictor (12)
- Tests: Warp Predictor (13)
- Tests: Warp Predictor (14)
- HUD Chrome & Frames (3)
- Telemetry Readouts (5)
- Telemetry Readouts (6)
- Telemetry Readouts (7)
- Telemetry Readouts (8)
- Telemetry Readouts (9)
- Telemetry Readouts (10)
- Telemetry Readouts (11)
- Telemetry Readouts (12)
- Telemetry Readouts (13)
- Ui Assets

## God Nodes (most connected - your core abstractions)
1. `Vec2` - 88 edges
2. `Widget` - 65 edges
3. `Telemetry` - 48 edges
4. `ConfigLoader` - 47 edges
5. `world` - 46 edges
6. `Camera` - 46 edges
7. `Rect` - 46 edges
8. `Renderer` - 43 edges
9. `with_alpha()` - 42 edges
10. `Predictor` - 40 edges

## Surprising Connections (you probably didn't know these)
- `body` --uses--> `Vec2`  [INFERRED]
  bodies/body.py → physics/vec.py
- `world` --uses--> `body`  [INFERRED]
  physics/world.py → bodies/body.py
- `orbital_period()` --indirect_call--> `mass()`  [INFERRED]
  bodies/orbit_lines.py → ui/units.py
- `soi_radius()` --indirect_call--> `mass()`  [INFERRED]
  bodies/orbit_lines.py → ui/units.py
- `Renderer` --uses--> `IdentityReferenceFrame`  [INFERRED]
  render/renderer.py → physics/reference_frames.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Integratorwahl: Euler/Verlet verworfen, RKN4 gewaehlt** — obsidian_vault_evaluation_integrator_euler, obsidian_vault_evaluation_integrator_verlet, obsidian_vault_evaluation_integrator_rk4, obsidian_vault_evaluation_integrator_rkn4, obsidian_vault_evaluation_integrator_symplektik, obsidian_vault_evaluation_integrator_energiedrift_messung [EXTRACTED 0.90]
- **Kapitel 4: Bahnmanoever - Transfers und Swing-by** — obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__hohmann_transfer, obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__bi_elliptischer_transfer, obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__gravity_assist, obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__delta_v, obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__bezugssystem [EXTRACTED 0.90]
- **Validierung: Pruefgroessen und Messwerte** — obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__validierung, obsidian_vault_evaluation_integrator_energiedrift_messung, obsidian_vault_evaluation_integrator_phasendrift, obsidian_vault_evaluation__arbeit_00_gliederung__ki_ansatz__irrelevant__zweikoerperproblem, obsidian_vault_evaluation_integrator_rkn4 [EXTRACTED 0.85]
- **Predictor integrator evolution (RK4 to RK45 to RKN, via ASPI)** — obsidian_vault_readme_s_github_11_04_2026_osterupdate_rk4_integrator, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_aspi_integrator, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_rk45_integrator, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_rkn_integrator, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_predictor [EXTRACTED 0.75]
- **Predictor-line rendering pipeline (culling, RDP, densify, clipping)** — obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_screen_culling, obsidian_vault_readme_s_github_31_05_2026_readme_juni_rdp, obsidian_vault_readme_s_github_31_05_2026_readme_juni_densify, obsidian_vault_readme_s_github_31_05_2026_readme_juni_liang_barsky [EXTRACTED 0.75]
- **Reference-frame display transform (time-tagged points, moving bodies, epicycles)** — obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_reference_frame_system, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_time_tagged_points, obsidian_vault_readme_s_github_09_05_2026_april_mai_vergleich_time_dependent_body_positions, obsidian_vault_readme_s_github_11_04_2026_osterupdate_epicycle_mode [EXTRACTED 0.75]
- **The Two-Body Problem Toolkit (orbit equation, energy, position vs time)** — obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_two_body_problem, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_orbit_equation, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_vis_viva_energy_equation, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_keplers_equation [INFERRED 0.85]
- **Patched-Conic Interplanetary/Lunar Trajectory Design** — obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_patched_conic_method, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_sphere_of_influence, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_hyperbolic_excess_velocity, obsidian_vault_evaluation__arbeit_quellen_literatur_orbital_mechanics_for_engineering_students_fourth_edition_9780081021330_008102133x_compress_lunar_trajectories [EXTRACTED 0.75]
- **The Apollo 11 Translunar Trajectory** — obsidian_vault_evaluation__arbeit_quellen_literatur_nasa_apollo_11_flight_report_translunar_injection, obsidian_vault_evaluation__arbeit_quellen_literatur_nasa_apollo_11_flight_report_translunar_coast, obsidian_vault_evaluation__arbeit_quellen_literatur_nasa_apollo_11_flight_report_free_return_trajectory, obsidian_vault_evaluation__arbeit_quellen_literatur_nasa_apollo_11_flight_report_lunar_orbit_insertion, obsidian_vault_evaluation__arbeit_quellen_literatur_nasa_apollo_11_flight_report_midcourse_correction [EXTRACTED 0.75]

## Communities (158 total, 36 thin omitted)

### Community 0 - "Predictor Numba Kernels"
Cohesion: 0.05
Nodes (67): _find_apsis_markers_numba(), Ap/Pe-suche auf einer fertigen punktreihe. Die marker sitzen auf den EXTREMA…, _refine_apsis_numba(), _burn_arc_numba(), _profile_accel_numba(), Der brennbogen: schwerkraft plus konstant gerichteter schub.…, RK4 ueber den brennbogen: schwerkraft plus konstant gerichteter schub. FESTE…, _empty_points() (+59 more)

### Community 1 - "Core Physics & Config Bootstrapping"
Cohesion: 0.04
Nodes (56): body, schiff, ConfigLoader, Zentrale konfiguration: `config.json` ->…, Laedt `config.json` und verteilt die parameter auf die einzelnen module. die…, Path, bequemlichkeitsfunktion zum erstellen von Vec2., vec() (+48 more)

### Community 2 - "UI Theme & Palette"
Cohesion: 0.06
Nodes (50): ease(), Kern der UI-schicht: rechtecke, verankerung, widget-basis, eingabe-routing.…, Framerate-unabhaengiges exponentielles easing -- dieselbe formel wie das…, Der schwebezettel an einer Ap/Pe-raute auf der bahnlinie. Die raute selbst und…, Ausklappbare koerperliste zur wahl des BEZUGSKOERPERS. Bisher liess sich der…, frame(), plate(), Die formsprache der instrumententafel -- an EINER stelle. Vier bauteile, aus… (+42 more)

### Community 3 - "Maneuver HUD Panel"
Cohesion: 0.05
Nodes (23): setter, _edit_text(), ManeuverAxesBlock, ManeuverGizmo, ManeuverPlanBlock, Die ziehgriffe AN DER LINIE -- kein rechteck, nur treffer. Er zeichnet nichts:…, Auslenkung [-1, 1] -> ratenfaktor [-1, 1]. Null in der totzone, sonst `sign *…, Den knueppel INTEGRIEREN -- hier laeuft der wert, nicht im ereignis. Deshalb… (+15 more)

### Community 4 - "Maneuver Planning"
Cohesion: 0.05
Nodes (39): Der autopilot, der einen knoten wirklich fliegt. IDLE --arm()--> ARMED…, Manoeverknoten: planen, vorschau zeichnen, automatisch brennen. profile.py das…, burn_direction_world(), ManeuverNode, orbital_basis(), Manoeverknoten und der plan, der sie haelt. EIN KNOTEN SPEICHERT ZWEI ZAHLEN…, Das schubprofil dieses knotens -- IMMER frisch gerechnet., Prograde und einwaerts-normal am ort des knotens, in WELTkoordinaten. `rel_*`… (+31 more)

### Community 5 - "Seminararbeit Draft & Outline"
Cohesion: 0.07
Nodes (55): Gliederung der Seminararbeit, Apollo-Navigation, Wechselbares Bezugssystem, Bi-elliptischer Transfer, Delta-v / impulsive Manoever, Gravity Assist / Swing-by, Hohmann-Transfer, Fachliche Korrekturen an Integrator.md / Physik.md (+47 more)

### Community 6 - "Body Rendering"
Cohesion: 0.06
Nodes (26): BodyDrawMixin, Positions-marke eines körpers, konstanter bildschirmgröße. `radius` ist der…, Die koerper: scheibe, prozedurale marke, vektor-look, beschriftung,…, Die spanne der PHYSISCHEN koerper-radien im geladenen system. Einmal je frame…, 0..1: wo dieser koerper-radius innerhalb der GELADENEN spanne liegt. LOG-…, Der GEZEICHNETE radius der marke -- ein je koerper KONSTANTER wert aus seinem…, Deckkraft der marke bei diesem echten bildschirmradius. 1.0 unterhalb der…, Zeichnet einen körper als shader-gesteuertes quad (scheibe + optional… (+18 more)

### Community 7 - "Camera"
Cohesion: 0.06
Nodes (23): Camera, Wandelt Bildschirmkoordinaten in Weltkoordinaten um., screen->welt gegen eine BELIEBIGE position/skala. Wird für das zoom-ankern…, Setzt ein Objekt zur Verfolgung (SOFORT, ohne anflug)., Körper, auf den `Home` die ansicht zurückholt (das schiff). Die kamera kennt…, Fährt die ansicht GEGLÄTTET auf `body` und heftet sie dort an. Der trick ist,…, Taste Home: geglättet zurück zum heimatkörper (dem schiff)., Beendet die Objektverfolgung. Die aktuelle ansicht wird als freies ziel… (+15 more)

### Community 8 - "Vec2 Math"
Cohesion: 0.05
Nodes (23): kepler_relative_xy(), Return this body's Kepler position at simulation time t without modifying…, Position nach `dt` auf der eigenen bahn -- exakt, siehe kepler_relative_xy().…, Bahnposition relativ zum mutterkoerper nach `dt`, EXAKT geloest. Rueckgabe `(x,…, erstellt eine kopie dieses vektors., in (x, y)-tuple umwandeln., erstellt Vec2 aus tuple oder liste., quadratische distanz zu einem anderen vektor. (+15 more)

### Community 9 - "Config Loader"
Cohesion: 0.08
Nodes (24): Any, _float_list(), Liest die konfiguration ein und gibt sie zurueck. `utf-8-sig` statt `utf-8`:…, Gibt einen abschnitt (z. B. 'camera') als dict zurueck, notfalls leer., Liest einen wert ueber einen punkt-pfad, z. B. get('camera.zoom_factor').…, Wandelt `value` mit `caster` um; bei unpassendem wert warnung + default. so…, Liest einen kommazahl-parameter., Liest einen ganzzahl-parameter. (+16 more)

### Community 10 - "GitHub Update Logs"
Cohesion: 0.07
Nodes (42): Argument of periapsis (orbit orientation), ASPI (Adaptive Symplectic Predictor Integrator), April-Mai Vergleich (09.05.2026), Predictor (trajectory prediction), Principia (KSP mod, inspiration), Reference-Frame-System (Plotting-Frame), RK45 adaptive integrator, Runge-Kutta-Nystrom (RKN) integrator (+34 more)

### Community 11 - "Unit Formatting"
Cohesion: 0.07
Nodes (37): Koerperzustand in flache arrays. None = fuer den kernel ungeeignet. Abgelehnt…, Der koerper, der das system beleuchtet. `light_intensity > 0` gewinnt; sonst…, Regressionstest fuer ui/units.py. Reine funktionen -- laeuft ohne fenster, ohne…, altitude(), angle(), countdown(), countdown_compact(), delta_v() (+29 more)

### Community 12 - "Body Browser Widget"
Cohesion: 0.07
Nodes (16): Sich selbst und alle nachkommen, eltern zuerst., Wurzel des widget-baums. Verteilt eingaben und meldet, ob sie verbraucht…, Solange ein widget gedrueckt wird, gehoert die maus ihm -- auch wenn der zeiger…, Alle sichtbaren widgets in ZEICHENREIHENFOLGE, hinten zuerst. Sortiert nach…, Oberstes widget unter dem zeiger, das die maus beansprucht. Genau die…, True = das ereignis gehoert der UI und darf NICHT weitergereicht werden., UIRoot, _body_dot_color() (+8 more)

### Community 13 - "UI Core Framework"
Cohesion: 0.06
Nodes (14): Basisklasse. Haelt verankerung, groesse, kinder und hover-zustand. Groessen und…, Eigengroesse in PIXELN fuer size-komponenten, die None sind. Ueberschreiben, wo…, Loest die groessen-angabe auf. Pro achse sind drei angaben erlaubt: eine zahl…, Effektive groesse in pixeln: explizite vorgabe, sonst measure(). Container…, Berechnet self.rect aus anker, abstand und groesse., Flaeche, in der kinder verankert werden. Panels ziehen hier ihr padding ab., Eigene darstellung. Basisklasse zeichnet nichts., Trefferflaeche. Bekommt ctx, weil sie nicht immer gleich self.rect ist -- ein… (+6 more)

### Community 14 - "Navball Cluster"
Cohesion: 0.09
Nodes (15): NavballCluster, Punkt auf dem linken bogen -> schubstufe, oder None. Getroffen wird ein RING-…, Das rad stellt den schub -- aber NUR ueber dem bogen und dem streifen. Ueberall…, Das ORB- (links) bzw. ALT-kaestchen (rechts)., Der THR- (links) bzw. V/S-streifen (rechts) darunter., Der ORBITAL.INFO-block am unteren rand. Er ist nur um eine halbe flankenbreite…, Eine der beiden messwert-flanken. Aufbau der vorlage: winzige gesperrte…, Der schmale streifen unter einer flanke. (+7 more)

### Community 15 - "System Map Widget"
Cohesion: 0.09
Nodes (20): _body_color(), _log_spread(), ``body.color`` (0..255 aus dem JSON) -> zeichenfarbe. Unveraendert uebernommen,…, Werte auf [low, high] verteilen -- logarithmisch, optional nach rang.…, Der ECHTE bahnwinkel des koerpers um seinen mutterkoerper. Aus den momentanen…, Die karte als widget: kachel, ausfahren, treffer, mond-ansicht., (zentralkoerper, planeten, monde je planet), einmal aufgebaut. Die koerperliste…, Groesse aus dem ausfahr-fortschritt, nicht aus dem schalter. Zwischen kachel… (+12 more)

### Community 16 - "Starfield & Grid Background"
Cohesion: 0.07
Nodes (24): Das zeichnen der hintergrund-ebene. Die geometrie (sterne, gitter) rechnet…, family_normals(), lattice_vertices(), Hintergrund-ebene -- sternenfeld und rekursives Dreiecksgitter. Zwei schichten,…, Die knoten des dreiecksgitters als `(n, 2)`-array in weltkoordinaten. `x =…, Die drei linien-normalen., Das zeichnen der himmelskoerper. Die detail-leiter (`_body_detail_levels`)…, Die fuenfte zeichen-domaene: der manoeverplan. Sie zeichnet drei dinge und… (+16 more)

### Community 17 - "Shader Pipelines"
Cohesion: 0.10
Nodes (16): Die OpenGL-pipelines des Renderers und der GL-zustandscache. Die GLSL-quellen…, Programm der positions-marke. Teilt sich das statische einheits-quad mit der…, Shader uebersetzen, VAOs/VBOs anlegen, GL-zustand cachen. Die…, Programme fuer die vektor-zeichnung der koerper. Anders als die uebrigen…, Texturierte quads (labels, HUD) in der ortho-konvention (y nach oben)., Hintergrund-ebene: vollbild-quad (gitter) + punkt-sprites (sterne). Beide…, Erstellt wiederverwendbare puffer, programme und VAOs für kritische render-…, Geteilter dynamischer vertex-puffer für polylines und ortho-geometrie. (+8 more)

### Community 18 - "Attitude Ring"
Cohesion: 0.11
Nodes (16): AttitudeRing, _polar(), Der Attitude-Ring -- das Herzstueck des HUDs. Ein 2D-lagemesser statt einer…, RUND, nicht quadratisch. Das widget ist ein quadrat, der ring darin ein kreis…, Loslassen gibt das schiff SOFORT wieder frei. Ohne das blieb _manual_heading…, Das schwache polargitter auf der ringflaeche. Es macht die flaeche zu einem…, Die vier himmelsrichtungen, immer aufrecht. Eine richtung wird WEGGELASSEN,…, Die vier bahnsymbole als VEKTOREN, nicht als schriftzeichen. Der entwurf setzt… (+8 more)

### Community 19 - "Predictor View / Display Line"
Cohesion: 0.09
Nodes (11): Von der punkteliste abgeleitete zwischenergebnisse verwerfen. soft=True heisst:…, Feinste punktdichte, die den HORIZONT noch traegt -- oder None. Die kernel…, Was HERAUSKOMMT: punkte, Ap/Pe-marker, laenge, abstand, zoom. Horizont…, Wie viel von der gerechneten kurve GEZEICHNET wird, in metern. None oder >= der…, Zahl der zu zeichnenden fuehrenden punkte, oder None fuer alle. Ueber den…, Die zu ZEICHNENDE kurve (siehe set_display_length). Der ausschnitt wird gemerkt…, Traegt diese punkteliste brauchbare geschwindigkeits-spalten? Alles oder…, Apoapsis/Periapsis-Marker der aktuellen Prädiktionslinie. Rückgabe: ndarray (m,… (+3 more)

### Community 20 - "Maneuver HUD Panel (2)"
Cohesion: 0.09
Nodes (15): _button_colors(), Die gemeinsame zustandsregel. Siehe modul-docstring., ManeuverBurnBlock, ManeuverNodesBar, _ManeuverPlate, Ein plaettchen im navball-raster. `SIDE` waehlt die flanke, `PLACE` das feld…, Die zur kugel zeigende seite bleibt SCHARF -- wie bei den flanken., Eine zeile: beschriftung links, wert rechts. DREI STUFEN, genau wie… (+7 more)

### Community 21 - "N-Body World Integrator"
Cohesion: 0.10
Nodes (13): Decke fuer die integrator-schrittweite aus der raffung ableiten. Die kosten von…, Tatsaechlich benutzte decke -- nie kleiner als die konfigurierte., Rueckt die welt um `sim_seconds` vor, aufgeteilt in stuecke. Stand frueher als…, Return the body's world position at a given simulation time. For now: - if the…, One explicit RKN4-style step for r'' = a(r, t). p0: initial position v0:…, Störmer-Verlet (KDK leapfrog) — 2nd-order symplectic RKN., Adaptive embedded RKN-style step by step-doubling. Compares: - one full step h…, konvertiert position/geschwindigkeit (relativ zum parent) in orbitale… (+5 more)

### Community 22 - "Ship Rendering"
Cohesion: 0.08
Nodes (15): Tie the ship nose to the drawn orbital vector for the latched snap. Computes…, Debug overlay: always draws prograde (green) + normal-inward (magenta).…, Env-guarded (SPACESIM_DEBUG_ORIENT=1) screen-space angle report. Prints, in one…, Das schiff: sprite, pfeil, fahne, schubvektor und die orientierung.…, Returns the ship's apparent speed in the active plotting frame. This respects…, Massstabs-faktor des schiffs fuer die aktuelle zoomstufe. 1.0 bei…, Gezeichnete schiffslaenge in echten bildschirm-pixeln. Basislaenge (design-…, Halbe hoehe der gezeichneten schiffs-grafik in bildschirm-pixeln. Bezugsgroesse… (+7 more)

### Community 23 - "Bootstrap & Frame Controller"
Cohesion: 0.08
Nodes (16): PlottingFrameAdapter, App, build_app(), FrameController, Den ganzen apparat zusammenbauen: welt, kamera, predictor, renderer, UI. Das…, Alles, was die hauptschleife braucht -- ein sack voll verweise. Bewusst keine…, Bezugsrahmen und bezugskoerper anwenden. Haengt an `UIState.on_change`, wird…, _empty() (+8 more)

### Community 24 - "Draw Primitives & Clipping"
Cohesion: 0.09
Nodes (16): DrawMixin, Zeichen-primitive: polylinien, ortho-formen, texturen, clipping. Die clipping-…, Liang-Barsky clipping for screen-space line segments. Returns (cx0, cy0, cx1,…, Die zeichen-primitive: linien, ortho-formen, texturen, clipping. Alles hier…, Converts one logical predictor polyline into multiple visible screen-space…, Lädt ein (N,2)-float32-array in den geteilten dynamischen VBO. orphan()…, Kernel-weg von `_build_clipped_polyline_runs`. Ein numba-aufruf statt einer…, Zeichnet eine textur als quad in der ortho-konvention (y nach oben). Ersatz für… (+8 more)

### Community 25 - "Renderer Text & Labels"
Cohesion: 0.11
Nodes (13): Schriften und der label-textur-cache des Renderers. Das spieler-HUD hat mit…, Setzt die DESIGN-schriftgrößen und baut die fonts neu auf., Benutzer-skalenfaktor (multiplikativ auf die automatische skala)., Beschriftungs-textur besorgen -- moeglichst eine wiederverwendete. Wie in…, Schriften, der label-textur-cache und getoentes blitten. UI-groessen sind…, Rastert eine beschriftung -- bei bedarf HART und GESPERRT. Zwei zugestaendnisse…, Leitet ui_scale aus der fensterhöhe ab. Gibt True bei änderung zurück. Skaliert…, Text an TOP-DOWN koordinaten zeichnen (x = links, y = oberkante). Nimmt dem… (+5 more)

### Community 26 - "UI Draw Batch"
Cohesion: 0.10
Nodes (12): Zeichen-primitive der UI-schicht, alle auf EINEM SDF-shader.…, Abgerundetes rechteck. (x, y) = obere linke ecke, top-down. radius: skalar oder…, Kreis um (cx, cy), top-down., Kreisring. Umgesetzt als kreis OHNE fuellung mit rahmen der gewuenschten…, Kreisbogen. Winkel gegen den uhrzeigersinn, 0 = nach rechts., Beliebig gedrehte linie -- ein um ihre achse rotiertes rechteck. cap='round'…, Trennlinie. Achsenparallel, deshalb ohne rotation und damit ohne rasterungs-…, Instanz in den stapel legen -- gezeichnet wird erst in flush(). Frueher war… (+4 more)

### Community 27 - "Maneuver Autopilot Executor"
Cohesion: 0.10
Nodes (9): ManeuverExecutor, Den naechsten knoten scharfschalten. False, wenn das nicht geht., Von der hauptschleife gerufen, sobald der spieler selbst steuert. Handeingabe…, Die schrittklemme fuer eine gegebene sim-zeit (testbar ohne welt)., Wie weit die welt in DIESEM frame hoechstens vorruecken darf. Scharf:…, Muss die raffung jetzt auf echtzeit herunter? Ja, sobald die zuendung naeher…, VOR `world.step(sim_seconds)` aufrufen. Legt das delta-v des bevorstehenden…, Scharfschalten, ausrichten, zuenden, brennen, aufraeumen. (+1 more)

### Community 28 - "Predictor Warp Hold"
Cohesion: 0.10
Nodes (11): HoldMixin, Der halt, das verbrauchen der kurve und das umschalten auf einen neuen bahnast.…, Kurve VERBRAUCHEN statt starr verschieben. Rueckgabe: die zahl der vorn…, Setzt den kurvenanfang auf das schiff. DER REGELFALL IST DAS VERBRAUCHEN, NICHT…, Gibt die Anzahl der Einträge in `new_points` zurück, die sich von `old_points`…, Zeitraffer-halt ein/aus. Ausschalten erzwingt eine neuberechnung. Die beiden…, Die gehaltene kurve ist ueberholt (schub, rahmenwechsel, ...). `soft=True`…, Kurve VERBRAUCHEN statt neu rechnen. True = frame ist erledigt. WARUM. Ohne… (+3 more)

### Community 29 - "Ship Geometry & Art"
Cohesion: 0.13
Nodes (23): _arc_half(), build(), _circle(), _cross3(), _dash(), _hex_rgb(), _in_triangle(), _plume_polygons() (+15 more)

### Community 30 - "Maneuver Preview Chain"
Cohesion: 0.11
Nodes (10): _Done, ManeuverPreview, Die kette, ihre marker, und der weg, auf dem sie NEBENHER laeuft. NEBENLAEUFIG,…, Reichweite setzen. Der naechste neuaufbau uebernimmt sie., Ein fertiges ergebnis einwechseln. True, wenn eines kam., Auf einen laufenden auftrag warten und ihn einwechseln. Nur fuer tests und…, Nur rechnen, wenn sich etwas bewegt hat. True, wenn gerechnet wurde.…, SYNCHRON rechnen und sofort einwechseln (tests, screenshots). (+2 more)

### Community 31 - "UI View State"
Cohesion: 0.11
Nodes (8): Setzt die auswahl. Gibt True zurueck, wenn sie sich geaendert hat. LOEST…, Overlay direkt setzen (HUD-knopf), statt zu kippen (taste T)., Die drei modi der HUD-rahmenwahl in einem schritt. 'surface' -> mitrotierender…, Aktueller modus als index fuer die HUD-rahmenwahl., Erzwingt ein neuanwenden ohne aenderung (start, system-neuladen)., Bezugsrahmen-auswahl, referenzkoerper und overlay-schalter., Zweiter koerper fuer den body-direction-rahmen. Bevorzugt den mutterkoerper des…, UIState

### Community 32 - "Frame Loop & Timing"
Cohesion: 0.12
Nodes (20): main(), spacesim -- 2D-N-Koerper-Bahnmechanik mit spielbarem raumschiff. DAS IST DER…, load_config(), Zentrale Konfiguration laden. ALLE spielbaren parameter stehen in config.json;…, _apply_horizon(), _apply_maneuver(), _clamp_warp(), FrameTimingPrinter (+12 more)

### Community 33 - "Tests: Orbit Lines"
Cohesion: 0.09
Nodes (14): check(), close(), _constant_rate_position_at_time(), CountingFrame, _drawn_step_deg(), line_missing_moon_by(), make_body(), Regressionstest fuer orbit_lines.py -- die bahn-linien der koerper. Reine… (+6 more)

### Community 34 - "Renderer Core"
Cohesion: 0.16
Nodes (8): BackgroundDrawMixin, Sternenfeld und dekaden-gitter. NICHTS HIER SKALIERT MIT camera.scale -- der…, Laedt die sterntabelle in den instanz-VBO, wenn die dichte wechselt. Der puffer…, Zeichnet sternenfeld und gitter -- die unterste schicht. Laeuft VOR allem…, Die alte debug-textwand unten links. Seit Phase 4 standardmaessig AUS: ihre…, Der Renderer -- zusammengesetzt aus mixins, ein zustand. Die klasse war 5900…, Konvertiert einen Welt-Punkt zu einer bestimmten Sim-Zeit in…, Renderer

### Community 35 - "Ship Control & Autopilot"
Cohesion: 0.15
Nodes (6): Latch/unlatch an orientation-hold. Tapping the active mode clears it., Hold the ship nose on a world-space heading supplied by the renderer. The…, Smoothly rotate toward a world-space direction vector (see above)., rotation mit echtem (wanduhr-)delta behandeln damit das drehen sich glatt…, Manual nose thrust as acceleration per real frame. dies stellt sicher, dass der…, schiffcontrol

### Community 36 - "Predictor Core"
Cohesion: 0.12
Nodes (8): Predictor, Die vorausberechnete bahnlinie -- zusammengesetzt aus mixins. Die klasse war…, build(), Welt + schiff auf einer kreisbahn um die Erde + predictor., _earth_orbit_scene(), Schiff auf eine bekannte bahn um die Erde setzen., Mondtransferbahn -- lang, exzentrisch, das gemeldete szenario., _scene23()

### Community 37 - "ImGui Dev Tools"
Cohesion: 0.11
Nodes (10): Ringpuffer der per-frame zeitmessung, direkt fuer imgui.plot_lines. Ein…, Eine probe. Heisser pfad -- keine allokation, kein dict, kein try. `ui_calc`…, Laenge umstellen und dabei die JUENGSTEN proben behalten., `(feld, offset)` fuer plot_lines. Offset = aelteste probe., Kopie in chronologischer reihenfolge (alt -> neu). Nur fuer tests und ausgaben…, `(cur, avg, max)` ueber den GEFUELLTEN teil des puffers. Der ungefuellte rest…, Zerfallender spitzenwert der serie. Nicht gerastert. Je frame HOECHSTENS EINMAL…, Gerasterter achsen-maximalwert einer serie. (+2 more)

### Community 38 - "Tests: Ui Horizon"
Cohesion: 0.10
Nodes (11): _Ctx, _Dummy, make(), _Motion, _Predictor, _PredLen, Kopftest fuer ui/widgets/rate_slider.py -- die federphysik und die…, Das Nötigste, das der Widget-Code berührt. (+3 more)

### Community 40 - "UI Theme & Palette (2)"
Cohesion: 0.10
Nodes (8): Palette, Die vier bedeutungsfarben plus die feste, dunkle grundierung. Der grund (panel,…, Setzt die vier farben und leitet alle rollen neu ab., Ungehellte farbe -- fuer flaechen, nie fuer schrift., Der farbige schein hinter einem block -- ein schlagschatten mit versatz null…, Buendelt die stufen. Erreichbar ueber UIContext.theme., Nur noch der EINE satz -- der wechselknopf ist entfallen., Theme

### Community 41 - "Planet Style Generation"
Cohesion: 0.16
Nodes (20): build_planet_style(), _color_basis(), _emit_ring(), _euler_matrix(), expand_segments(), _fbm(), _hash3(), _hsl() (+12 more)

### Community 42 - "Tests: Selection Camera"
Cohesion: 0.11
Nodes (14): blob_centroid(), draw(), FakeBody, look_at(), make_camera(), Regressionstest fuer auswahl per mausklick und den kamera-anflug. Geprueft…, Schnelles rein/raus-zoomen ueber 240 frames, koerper faehrt mit. Gibt die…, Einen frame zeichnen. Die koerper-optik wird NEBENLAEUFIG gebaut, ein einzelner… (+6 more)

### Community 43 - "ImGui Dev Tools (2)"
Cohesion: 0.14
Nodes (4): ImguiLayer, ImGui-overlay auf dem geteilten moderngl-context., pygame-ereignis nach imgui uebersetzen., imgui-frame abschliessen und ueber moderngl zeichnen.

### Community 44 - "Predictor Async Jobs"
Cohesion: 0.16
Nodes (8): JobsMixin, Rechnet ueberhaupt ein auftrag? (bequemlichkeit fuer altes verhalten), Obergrenze: konfiguration und verfuegbare kerne., So viele gleichzeitige laeufe, dass je BILD eines fertig wird. Die dauer einer…, Schub-neuberechnung ANFORDERN statt sie im hauptthread zu erzwingen. Waehrend…, Die asynchrone rechen-pipeline. Mehrere rechnungen laufen VERSETZT…, Neue horizont-/abstands-kurve ANFORDERN, ohne den halt aufzugeben. Dasselbe…, Wie viele auftraege rechnen gerade? `_pending_futures` enthaelt auch bereits…

### Community 45 - "Horizon Rate Slider"
Cohesion: 0.17
Nodes (5): HorizonSlider, Die GEZEICHNETE horizontlaenge, aus dem predictor zurueckgelesen.…, Auslenkung [-1, 1] -> raten-faktor [-1, 1]. Null in der totzone, sonst `sign *…, Waagerechter raten-regler mit federrueckstellung in die mitte., _response()

### Community 46 - "Reference Frames (Principia-style)"
Cohesion: 0.13
Nodes (8): _BodyEphemerisMixin, _kepler_true_anomaly_from_mean(), Wie _prepare_cache + to_this_frame_xy, nur fuer ein ganzes feld. Winkel und…, Wie _prepare_cache + to_this_frame_xy, nur fuer ein ganzes feld. Winkel und…, Kuerzeste umlaufzeit in der elternkette von `body`, oder None. Die WELT-…, Kubik DURCH ALLE VIER knoten (Lagrange), ausgewertet auf [p1, p2]. Rein…, Stapelfassung von _body_world_position_at_time. None = nicht moeglich. Nutzt…, _solve_eccentric_anomaly()

### Community 47 - "Predictor Horizon Policy"
Cohesion: 0.15
Nodes (13): horizon_compute_rung(), horizon_targets(), predictor_horizon_lengths(), Die laengenregel des vorhersage-horizonts. Lag als lose funktionen und closures…, (gezeichnete laenge, gerechnete laenge) fuer den vorhersage-horizont.…, Naechsthoehere sprosse einer groben leiter ueber `wanted`. Die leiter haengt an…, Wie `predictor_horizon_lengths`, aber mit dem slider-griff. DIE GERECHNETE…, apply() (+5 more)

### Community 48 - "Reference Frames (Principia-style) (2)"
Cohesion: 0.20
Nodes (12): _body_arg_periapsis(), _body_true_anomaly(), _build_kepler_elements(), _has_scripted_orbit_data(), _mean_anomaly_from_true(), _orbit_model_from_body(), Vektorisierte fassung von _relative_position_to_parent_at_time., Visual-only propagation for parentless scripted bodies around world origin.… (+4 more)

### Community 50 - "Prediction Line Drawing"
Cohesion: 0.16
Nodes (11): _compact_min_step_numba(), _densify_numba(), _max_gap_refine_numba(), Die Numba-fassungen der reinen zahlenschleifen im linien-zeichenweg. Min-step-…, Zu weit auseinanderliegende RDP-punkte wieder auffuellen. Dieselbe schleife wie…, Segmente laenger als `max_segment` linear unterteilen. Zwei durchgaenge…, _rdp_keep_numba(), Das zeichnen der vorhersagelinie. Der teure teil ist nicht das zeichnen,… (+3 more)

### Community 51 - "Prediction Line Drawing (2)"
Cohesion: 0.19
Nodes (4): PredictionDrawMixin, Erlaubte abweichung der gezeichneten linie -- in metern und pixeln. Der…, Die vorhersagelinie: abtastung, Hermite-verfeinerung, Ap/Pe-marker. EINE…, Zeichnet apoapsis/periapsis-marker des predictors auf die linie. Marker kommen…

### Community 52 - "Input Router"
Cohesion: 0.16
Nodes (7): InputRouter, Zeit auf der vorhersagelinie, die dem mauszeiger am naechsten liegt. Der…, +'/'-' verstellen den MANUELLEN faktor, nicht die laenge direkt. Sonst wuerde…, Uebersetzt ereignisse in aenderungen an welt, kamera und predictor., Auswahl / anflug. Aendert WEDER bezugskoerper NOCH bezugsrahmen., Linke maustaste: koerper auswaehlen / anfliegen. Die kamera zieht mit der…, Eine taste anwenden. Liefert False, wenn das spiel enden soll.

### Community 53 - "UI Text Renderer"
Cohesion: 0.14
Nodes (7): Rollengroesse -> pixelgroesse, fuer die pixelschrift GERASTET. SB Liquid ist…, Die pixelschrift wird OHNE kantenglaettung gerastert. Gemessen ueber…, Die instrumentenschrift setzt ZIFFERN AUF FESTER BREITE. SB Liquid ist nicht…, Laufweite dieser rolle in pixeln (em-wert * schriftgroesse)., Textur dieser groesse besorgen -- moeglichst eine wiederverwendete. Der teure…, Verdraengte textur einsammeln statt freigeben (bis zum deckel)., Groesse des gerenderten textes in pixeln, ohne zu zeichnen.

### Community 54 - "OpenGL Device & FXAA"
Cohesion: 0.15
Nodes (8): GLDeviceMixin, Die GL-geraeteschicht des Renderers. War teil der 5900-zeiligen…, Wendet FXAA Post-Processing an. Erwartet, dass der ziel-framebuffer (screen)…, Context, FXAA-ziele, present und resize -- die geraeteschicht. Liegt in…, Fuehrt den buffer-swap aus und schreibt die swap-zeit in die timings. Von der…, Initialisiert OpenGL-Einstellungen (moderngl-state)., Erstellt FBO-textur und framebuffer in aktueller fenstergröße., Initialisiert FXAA Framebuffer und Shader.

### Community 55 - "Button & Segmented Control"
Cohesion: 0.17
Nodes (4): Mehrere sich gegenseitig ausschliessende optionen in einer leiste. Die form…, Rastender schalter mit schiebeknopf. value darf ein aufrufbares objekt sein…, SegmentedControl, Toggle

### Community 56 - "Reference Frames (Principia-style) (4)"
Cohesion: 0.23
Nodes (7): FrameChangeCallback, describe_plotting_frame(), _fallback_secondary_index(), new_plotting_frame(), PlottingFrameParameters, ReferenceFrameSelector, _resolve_body()

### Community 57 - "Maneuver Rendering"
Cohesion: 0.17
Nodes (9): ManeuverDrawMixin, Eine (n,5)-linie in schirmpunkte -- grob abgetastet, dann VERFEINERT. NUR…, Den plan zeichnen und seine schirmpositionen melden. Die trefferliste wird bei…, Wo die koerper stehen, wenn das schiff am ENDE DES PLANS ankommt. Dieselbe…, Ein sechseck -- die form, die sonst nichts im bild traegt. Die raute gehoert…, Ein stiel vom marker weg und eine pfeilspitze am ende. `deflection` ist der…, Geplante bahn, knotenmarker und ziehgriffe., Weltrichtung -> SCHIRMrichtung (einheitsvektor), oder None. Zwei schritte: der… (+1 more)

### Community 58 - "Maneuver Plan & Nodes"
Cohesion: 0.17
Nodes (4): ManeuverPlan, Bis zu `max_nodes` knoten, nach zeit sortiert., Der zeitlich naechste knoten -- den fliegt EXECUTE., Nach einer direkten feldaenderung aufrufen. Sortiert nach (ein ziehgriff darf…

### Community 59 - "Apsis Tooltip"
Cohesion: 0.19
Nodes (6): ApsisTooltip, Die beiden zeilen als (schluessel, wert). ETA ist SIMULATIONSZEIT bis zur…, Hoehe der abstands-fahne, die der renderer unter die raute setzt., Zwei zeilen -- ankunftszeit und bahntempo -- unter der raute., Trefferkreis um die raute, in echten pixeln. Grosszuegiger als die raute…, Der marker unter dem zeiger, oder None. Bei zwei dicht beieinander liegenden…

### Community 61 - "Panel & Stack Layout"
Cohesion: 0.15
Nodes (6): Group, Panel, Unsichtbarer container. Nur zum verankern -- verbraucht keine maus., Unsichtbarer container, der seine kinder aneinanderreiht. Die verankerung aus…, Abgerundete flaeche mit rahmen, schatten und innenabstand. blocks_mouse ist…, Stack

### Community 62 - "Body Icon Generation"
Cohesion: 0.17
Nodes (14): cells_array(), icon_palette(), _mix(), Entwurf A -- die Scheibe wird durchgehend gewuerfelt, radial gewichtet. Kein…, Entwurf D -- Kern plus 2-4 gesaete Zacken. Die Zacken sitzen auf DEMSELBEN…, Die POSITIONS-MARKE eines koerpers -- das icon beim herauszoomen. Nicht zu…, Die drei stufen-farben aus `body.color` (RGB 0..255). Der farbton bleibt…, Das feld als `(grid, grid)` int8 -- fuer tests und fehlersuche. Zeile 0 ist die… (+6 more)

### Community 63 - "Reference Frames (Principia-style) (5)"
Cohesion: 0.19
Nodes (13): apparent_orbital_directions(), _prograde_from_line(), reference-frame-primitiven und selector/adapter-verkabelung für spacesim. dies…, Bestimmt, welchem körper die kamera für den ausgewählten plotting-frame folgen…, Frame-space tangent of the *actual* predictor polyline at its start. ``points``…, Orbital orientation targets as they *appear* in the given plotting frame. Tied…, Vektorisierte fassung von _kepler_true_anomaly_from_mean. Newton-iteration wie…, Frame-raum-tangente aus der GESPEICHERTEN geschwindigkeit des kopfes. Die… (+5 more)

### Community 64 - "Orbit Line Rendering"
Cohesion: 0.17
Nodes (7): OrbitDrawMixin, Der zustandsbehaftete teil, ueber frames hinweg gehalten. Die konfiguration…, Die bahnlinien der koerper und die aufgezeichneten referenzspuren., Fertig projizierte bildschirmpunkte als polylinie, mit culling., Kleine raute auf dem endpunkt einer linie. Die endkappen sind der eigentliche…, Kreis-umriss mit dem ECHTEN radius des koerpers auf dem linienende. Das ist der…, Wo jeder koerper waehrend des VORHERSAGE-FENSTERS entlanglaeuft. Dieselbe…

### Community 65 - "Tests: Ui Hud"
Cohesion: 0.14
Nodes (8): cursor_at(), Cyc, frame(), _open_progress(), Regressionstest des spieler-HUDs (Phase 4). Drei ebenen, bewusst getrennt: 1.…, Ganzzahlige fensterkoordinate auf einem kompasswinkel am ring. GANZZAHLIG, weil…, Bildet NavballCluster._strip nach: drei stufen, wert gewinnt., _strip_width()

### Community 66 - "ImGui Dev Tools (3)"
Cohesion: 0.18
Nodes (13): _checkbox(), draw_dev_panels(), _draw_timing_graphs(), _fmt_si(), _nice_ceiling(), Dear ImGui entwickler-oberflaeche (moderngl-nativ). Bewusst NUR fuer…, Zeichnet die entwickler-panels. `ctxobj` ist ein DevContext., Kompakte SI-darstellung fuer die readouts. (+5 more)

### Community 67 - "HUD Control Bars"
Cohesion: 0.25
Nodes (4): Platz, den der notch-tab AUSSERHALB des rahmens braucht. Er wird in measure()…, Die flaeche des eigentlichen rahmens, ohne das tab-band., Waagerechte zellenleiste mit sich ausschliessenden optionen. Traegt den…, SegmentBar

### Community 68 - "Tests: Background Test"
Cohesion: 0.18
Nodes (9): jump(), pattern_origin_px(), Regressionstest fuer background.py -- sternenfeld und dreiecksgitter. Reine…, `path` abfahren, jeweils die anker zurueckgeben., run(), _ss(), tracked(), visible() (+1 more)

### Community 69 - "Tests: Body Icon"
Cohesion: 0.16
Nodes (11): edge_count(), FakeBody, ink(), line_dips(), object, Die POSITIONS-MARKE der koerper -- rechnung und echte pixel. Das icon hatte…, Ein koerper, wie er aus solar_system.json faellt., Gesamte helligkeit -- das mass, an dem sich kriechen zeigt. (+3 more)

### Community 71 - "HUD Panels & Ship Badge"
Cohesion: 0.16
Nodes (4): Die gesperrte versal-ueberschrift eines panels., Die pille oben links: leuchtpunkt, schiffsname, bezugskoerper. Im entwurf steht…, SectionLabel, ShipBadge

### Community 72 - "UI Text Renderer (2)"
Cohesion: 0.21
Nodes (6): Sucht die schriftdateien EINMAL, je familie und strichstaerke. Reihenfolge:…, Rastert alle rollen in der aktuellen skalierten pixelgroesse NEU. Fertige…, Font-verwaltung, label-textur-cache und texturiertes blitten., Wie draw(), aber erst beim naechsten flush() ausgefuehrt. Der einzige zweck:…, Eigene texquad-pipeline. Bewusst NICHT die des Renderers geteilt: die UI-…, TextRenderer

### Community 73 - "Label & Readout Widgets"
Cohesion: 0.20
Nodes (5): Label, Text-widgets: einfaches label und die zweispaltige messwert-zeile., Beschriftung links, wert rechts -- die standardzeile der info-panels. Der wert…, Text. Die groesse folgt standardmaessig dem inhalt (size=(None, None)). text…, Readout

### Community 74 - "Orbit Lines (Bahnlinien)"
Cohesion: 0.18
Nodes (12): _constant_track(), frame_origin_body(), future_track(), future_tracks(), polyline_stride(), Bahn-linien der himmelskoerper -- reine geometrie, kein GL. Zwei kurven je…, Der koerper, der im ursprung dieses plot-frames sitzt, oder None. Er bekommt…, Wo `body` zu den zeiten `times` stehen wird, (k, 2) in weltkoordinaten. Duenner… (+4 more)

### Community 75 - "Reference Frames (Principia-style) (6)"
Cohesion: 0.15
Nodes (3): IdentityReferenceFrame, Stapelfassung von to_this_frame_xy. None = nicht moeglich. Der renderer…, ReferenceFrame

### Community 76 - "Starfield & Grid Background (2)"
Cohesion: 0.15
Nodes (8): BackgroundLayer, Zustand und rechnung der hintergrund-ebene. Kein GL. `update()` einmal je bild…, True (einmalig), wenn der VBO neu geschrieben werden muss., Staerke des atmenden feldes, auf [0, 1] geklemmt., Der WAHRE gitteranker -- wo das lattice stehen muesste. "frame" (Vorgabe): die…, Der GEZEIGTE anker -- was `levels()` als phase bekommt., pan_drift(), Sterndrift, wenn die kamera um `screens` bildbreiten schwenkt.

### Community 77 - "Predictor Horizon Policy (2)"
Cohesion: 0.15
Nodes (7): Tastenbelegung und die klick-geste. Stand als eine 100-zeilige if/elif-kette…, HorizonPolicy, Horizont-faktor aus der raffung -- zweierpotenz, gedeckelt. `rate` ist die…, Haelt den horizont-zustand und setzt ihn am predictor durch. Der manuelle…, +' / '-': den MANUELLEN faktor verstellen, nicht die laenge direkt. Sonst…, Horizont neu setzen, wenn sich basis*manuell*raffung geaendert hat., warp_length_mult()

### Community 78 - "Tests: Ship Scale"
Cohesion: 0.15
Nodes (9): draw_at(), hull_bbox(), ink_extent(), Knobs, Regressionstest fuer die zoom-abhaengige groesse des schiffs. Das schiff wird…, Einen frame mit dem schiff in der bildmitte zeichnen., Breite der schiffs-silhouette in pixeln. Zwei dinge muessen dabei draussen…, (breite, hoehe) der wenig gesaettigten pixel im ganzen bild. Die orientierungs-… (+1 more)

### Community 79 - "UI Theme & Palette (3)"
Cohesion: 0.19
Nodes (10): corner_probe(), draw_frame(), Regressionstest der UI-zeichenschicht -- gegen echte PIXEL. Die lehre aus Phase…, Zeichnet ein rechteck bei (100, 100) und tastet seine linke obere ecke ab., Framebuffer als (h, w, 3) uint8 in TOP-DOWN reihenfolge. viewport= wird…, read_pixels(), cut_corners(), Eckwert-tupel, bei dem NUR die gewaehlten ecken gefast sind. Die vorlage fast… (+2 more)

### Community 80 - "Tests: Warp Predictor"
Cohesion: 0.17
Nodes (4): _advance_pattern(), _at_periapsis(), _long_horizon_points(), Regressionen fuer horizont, welt-integrator und zeitraffer-halt. Alle drei…

### Community 81 - "HUD Layout"
Cohesion: 0.19
Nodes (5): Hud, Einmal pro frame VOR ui_root.begin_frame() aufrufen. Erst abtasten, dann…, Naechstliegende zeitraffer-stufe zum AKTUELLEN sim_dt. Zurueckgelesen statt…, Ist diese stufe momentan erlaubt? (bahn-zeitskala, siehe…, Baut den widget-baum und haelt ihn pro frame aktuell. Besitzt die telemetrie…

### Community 82 - "HUD Panels & Ship Badge (2)"
Cohesion: 0.26
Nodes (5): HudPanel, Gefaster doppelrahmen mit notch-tab auf der unterkante. Stapelt seine kinder…, Platz fuer den notch-tab UNTERHALB des rahmens. Er sitzt ausserhalb der kante,…, Fiktive inhaltsflaeche fuer die messung. Die zeilen sind (FILL, None) breit --…, Hoehe aus den kindern, breite aus der vorgabe. Haengt bewusst NICHT von…

### Community 83 - "Telemetry Readouts (2)"
Cohesion: 0.17
Nodes (6): compass_from_frame_direction(), Alles, was der MANEUVER-block je frame zeigt -- einmal gelesen. Brenndauer und…, Frame-raum-richtung -> kompasskurs. atan2(-d.y, d.x) ist genau die groesse, die…, mu und spezifische bahnenergie -- die grundlage von vis-viva., Geschwindigkeit eines koerpers -- auch eines skriptgefuehrten. ACHTUNG, das ist…, v . r_dach gegen den bezugskoerper -- steig- bzw. sinkrate. Die geschwindigkeit…

### Community 86 - "Prediction Line Drawing (3)"
Cohesion: 0.17
Nodes (4): Alle stichproben-punkte in EINEM rutsch projizieren. Gibt ``(None,…, Kubische zwischenpunkte setzen -- nur sichtbar, nur so fein wie noetig.…, Das ROH-scan-budget dorthin legen, wo die linie im BILD liegt.…, Gleichmaessige stichprobe der rohpunkte -- GEMERKT, nicht neu gebaut. Das…

### Community 87 - "Tests: Warp Predictor (2)"
Cohesion: 0.20
Nodes (12): advance(), build(), _burn(), _leo_world(), _line(), _measure(), probe(), Kurvenpunkt zur ABSOLUTEN sim-zeit t (linear interpoliert). (+4 more)

### Community 88 - "Orbit Lines (Bahnlinien) (3)"
Cohesion: 0.22
Nodes (8): _cubic_4pt(), frame_affine_at(), FrameAffineTable, Kubik DURCH ALLE VIER knoten (Lagrange), ausgewertet auf [p1, p2]. Wortgleich…, Die starre transformation eines plot-frames ueber ein ZEITFENSTER. Alle koerper…, Knotenzahl aus dem, was sich im fenster WIRKLICH dreht. Zwei winkel, und beide…, (fx, fy) fuer beliebige zeiten im fenster, vollstaendig in numpy. Das gitter…, Die starre transformation des frames zur zeit `t`. Gibt `(r00, r01, r10, r11,…

### Community 89 - "Apollo 11 Mission Phases"
Cohesion: 0.20
Nodes (11): Coelliptic Sequence Initiation (CSI), Constant Differential Height Maneuver (CDH), LM Descent and Ascent Propulsion Systems, Guidance, Navigation, and Control, Lunar Landing and Landing Dynamics, Lunar Module Ascent (Powered Ascent), Lunar Module Powered Descent Trajectory, Lunar Orbit Rendezvous (+3 more)

### Community 90 - "Orbital Mechanics Theory (Curtis)"
Cohesion: 0.20
Nodes (11): Mean, Eccentric and True Anomaly (Position vs Time), Classical Orbital Elements, Orbital Mechanics for Engineering Students (Curtis, 4th ed.), Euler Elementary Rotation Sequences, J2 Oblateness Perturbation (Nodal Regression), Kepler's Equation, Lagrange f and g Functions, Rocket Equation (Tsiolkovsky) (+3 more)

### Community 91 - "Orbital Mechanics Theory (Curtis) (2)"
Cohesion: 0.18
Nodes (11): Elliptical Orbits, Gauss Method of Orbit Determination, Gibbs Method of Orbit Determination, Planetary Flyby / Gravity Assist, Hyperbolic Excess Velocity (C3), Hyperbolic Trajectories, Interplanetary Trajectories, Julian Day Numbering and Sidereal Time (+3 more)

### Community 92 - "Tests: Devui Timing"
Cohesion: 0.18
Nodes (5): FakePredictor, FakeRenderer, push_ramp(), Regressionstest fuer die timing-ringpuffer der entwickler-oberflaeche. Prueft…, n proben, in denen jede serie einen eindeutigen wert bekommt.

### Community 93 - "HUD Control Bars (2)"
Cohesion: 0.20
Nodes (3): Der zeitraffer -- die zellenleiste plus die laufende missionszeit. Die uhr…, Der rahmen endet ueber dem uhrstreifen., WarpBar

### Community 94 - "HUD Control Bars (3)"
Cohesion: 0.33
Nodes (3): Der orientierungs-autopilot als rosette -- vier knoepfe um das schiff. Bildet…, Ein schlanker pfeil nach oben -- dieselbe silhouette wie die schiffsnase am…, SnapRosette

### Community 95 - "Tests: Frame Origin"
Cohesion: 0.22
Nodes (7): BodyCentredNonRotatingReferenceFrame, linear_reference(), make_frame(), _origin_run(), Der ursprung eines plot-rahmens wird KUBISCH interpoliert, nicht linear.…, (groesster abstand zum exakten wert, groesste bewegung je frame) in m., Der ALTE weg: sehne zwischen den beiden umgebenden knoten.

### Community 96 - "Starfield & Grid Background (3)"
Cohesion: 0.22
Nodes (8): fold(), fold_spans(), Die kleinste GITTERTRANSLATION, in der `(x, y)` gefaltet werden darf. Der anker…, `value` in `(-span/2, +span/2]` zurueckholen., Die geschwindigkeit des verfolgten koerpers, aus seiner POSITION. > **Ein…, Einen bildschritt weiterdrehen. `cam_world_xy` ist die kameraposition in…, Geradeausflug; gibt (layer, ZURUECKGELEGTE strecke in px) zurueck. ACHTUNG:…, slide()

### Community 97 - "Starfield & Grid Background (4)"
Cohesion: 0.20
Nodes (6): Level, Wie GLSL `smoothstep` -- C1-stetig, damit nichts poppt., Eine sichtbare gitter-dekade., Die sichtbaren dekaden, hellste zuerst, hoechstens `MAX_LEVELS`. Eine dekade…, Gitterphase in `(a, b)`-koordinaten, modulo 2. `a = x*sqrt(3)/ws`, `b = y/ws`;…, _smoothstep()

### Community 98 - "Body Icon Generation (2)"
Cohesion: 0.22
Nodes (7): build_icon(), IconCells, object, Das gepackte zellfeld einer marke., Eine marke aus einem seed. Rein rechnerisch, kein GL, kein pygame., Der `rng`-generator des mockups (xorshift-multiply, 32 bit)., _Rng

### Community 99 - "Orbit Lines (Bahnlinien) (4)"
Cohesion: 0.25
Nodes (7): approach_alpha(), Radius der einflusssphaere, `a * (m / m_elter)^0.4`, oder None. Der massstab,…, Deckkraft aus der dichtesten annaeherung, in SOI-vielfachen. `miss <= soi_full…, Das gitter, auf dem die spur GEZEICHNET wird. Standardfall ist das gemeinsame:…, Wie VIEL der linie gezeichnet wird, 0..1 -- neben der deckkraft. Zweites,…, reveal_fraction(), soi_radius()

### Community 100 - "Apollo 11 Mission Phases (2)"
Cohesion: 0.22
Nodes (9): Apollo 11 Mission Report (NASA), Earth Parking Orbit, Free-Return Trajectory, Launch Phase (Saturn V Ascent), Trajectory Maneuver Analysis, S-IVB Stage, Mission Sequence of Events, Translunar Injection (TLI) (+1 more)

### Community 101 - "Orbital Mechanics Theory (Curtis) (3)"
Cohesion: 0.28
Nodes (9): Conservation of Angular Momentum, Cowell's Method, Lagrange Points, Lunar Trajectories, N-Body Equations of Motion, Newton's Law of Universal Gravitation, Numerical Integration of the Equations of Motion (Runge-Kutta / RKF45), Restricted Three-Body Problem (+1 more)

### Community 103 - "Tests: Warp Predictor (3)"
Cohesion: 0.22
Nodes (9): arc_length(), predictor_warp_length_mult() aus test.py., step_simulation() aus test.py., Ein frame der hauptschleife -- nur der zeitraffer-relevante teil., Auf from_rate einschwingen, dann auf to_rate wechseln. Rueckgabe: (ms auf dem…, _w17_frame(), _w17_mult(), _w17_step() (+1 more)

### Community 104 - "Window & Clock"
Cohesion: 0.25
Nodes (4): Fenster, GL-context und der frame-takt. Stand als erste 70 zeilen von `main()`…, Das SDL/OpenGL-fenster und die uhr, die den frame-takt vorgibt., Einen frame abwarten und das ECHTE delta in sekunden liefern., Window

### Community 105 - "UI Core Framework (3)"
Cohesion: 0.25
Nodes (3): Alles, was widgets zum zeichnen und messen brauchen. Bewusst ein explizites…, Design-einheiten -> pixel. Das gegenstueck zu Renderer.ui_px(). Nimmt auch eine…, UIContext

### Community 107 - "Planet Style Generation (2)"
Cohesion: 0.29
Nodes (3): PlanetStyle, object, Fertige zeichnung eines koerpers im einheitskreis. `tri` sind die flaechen…

### Community 108 - "Apollo 11 Mission Phases (3)"
Cohesion: 0.29
Nodes (7): Cislunar Midcourse Navigation, Midcourse Correction, Service Propulsion System, Transearth Coast, Transearth Injection (TEI), Translunar Coast, Transposition, Docking and Extraction

### Community 109 - "Apollo 11 Mission Phases (4)"
Cohesion: 0.29
Nodes (7): Descent Orbit Insertion (DOI), Lunar Orbit Circularization, Lunar Orbit Insertion (LOI), Powered Descent Initiation (PDI), Undocking and Separation Maneuver, Method of Patched Conics, Sphere of Influence

### Community 113 - "Planet Style Generation (3)"
Cohesion: 0.40
Nodes (5): Der seed einer marke: `style_seed`, sonst der name -- plus ein globaler…, seed_for(), _imul(), Stabiler 32-bit-seed aus dem koerpernamen. Damit bekommt jeder koerper ohne…, seed_from_name()

### Community 114 - "Orbit Lines (Bahnlinien) (5)"
Cohesion: 0.33
Nodes (6): chain_periods(), orbital_period(), Umlaufzeit des koerpers um seinen elter, `2*pi*sqrt(a^3/mu)`, oder None. Fuer…, `{id(glied): umlaufzeit}` fuer jedes glied der elternkette von `body`. Ein…, Schnellste umlaufzeit, die in `koerper(t) - ursprung(t)` steckt. DIE UMLAUFZEIT…, relative_min_period()

### Community 115 - "Orbit Lines (Bahnlinien) (6)"
Cohesion: 0.33
Nodes (4): closest_approach(), OrbitLineEntry, Kleinster abstand zwischen schiff und koerper ZUR GLEICHEN ZEIT. Alle drei…, Was zu EINEM koerper je bild bekannt ist.

### Community 116 - "Orbital Mechanics Theory (Curtis) (4)"
Cohesion: 0.33
Nodes (6): Command Module Atmospheric Entry, Recovery, Atmospheric Drag Perturbation, Encke's Method, Orbital Perturbations, Variation of Parameters / Gauss Variational Equations

### Community 117 - "Orbital Mechanics Theory (Curtis) (5)"
Cohesion: 0.40
Nodes (6): Bi-Elliptic Transfer, Hohmann Transfer, Impulsive Orbital Maneuvers (Delta-v), Phasing Maneuvers, Orbital Plane Change Maneuver, Vis-Viva / Orbital Energy Equation

### Community 118 - "Reference Frames (Principia-style) (8)"
Cohesion: 0.47
Nodes (3): KeplerScriptedOrbit, Hilfs-Kepler-Orbit, nur für die Visualisierungs-Frame-Logik., _rotate_xy()

### Community 119 - "Telemetry Readouts (3)"
Cohesion: 0.33
Nodes (3): (bahntempo, kreisbahn-tempo, fluchttempo) am aktuellen ort. Der MASSSTAB der…, Nadellaenge auf [0, 1]: 0 = ruhe, ~0.71 = kreisbahn, 1 = flucht., Wo auf derselben skala die kreisbahn liegt -- immer 1/sqrt(2). Steht hier…

### Community 120 - "UI Text Renderer (3)"
Cohesion: 0.33
Nodes (3): Breite der breitesten ziffer dieser schrift, einmal gemessen., Rastert text, bei bedarf mit LAUFWEITE (letter-spacing). Die oberflaeche sperrt…, Ein render-aufruf, mit alphakanal auch im hart gerasterten fall. Ohne…

### Community 121 - "UI Text Renderer (4)"
Cohesion: 0.33
Nodes (3): Zeichnet text an TOP-DOWN koordinaten. align: 'left' | 'center' | 'right' --…, Zeichnet und leert die aufgeschobene warteschlange., Top-down -> ortho und auf das pixelraster rasten.

### Community 123 - "UI Theme & Palette (4)"
Cohesion: 0.40
Nodes (3): Eine typo-rolle: groesse, laufweite, strichstaerke, schriftfamilie. FAMILIE ist…, Rueckwaertskompatibler alias -- die pixelschrift IST dicktengleich., Role

### Community 124 - "Orbit Lines (Bahnlinien) (7)"
Cohesion: 0.50
Nodes (4): frame_project(), _frame_project_scalar(), Weltpunkte in den plot-frame, je ZEIT statt je PUNKT. Die ellipse besteht aus…, Punktweise rueckfallebene -- langsam, aber immer richtig.

### Community 126 - "Starfield & Grid Background (5)"
Cohesion: 0.50
Nodes (3): build_star_table(), `(n, 7)`-float32: x, y, radius, alpha, parallaxe, funkelphase, zoomphase.…, Die sterntabelle, bei bedarf neu erzeugt.

### Community 127 - "Tests: Warp Predictor (4)"
Cohesion: 0.50
Nodes (4): _bvel24(), _departure24(), _orbit24(), Bahngeschwindigkeit eines geskripteten koerpers. `body.velocity` ist bei allen…

### Community 128 - "ImGui Dev Tools (4)"
Cohesion: 0.50
Nodes (3): _ms(), Robuste ms-zahl. Fehlende/kaputte werte werden zu 0, nicht zu NaN. Ein NaN in…, Eine probe der vier zeitreihen. Je frame einmal, aus test.py. BEWUSST…

### Community 129 - "HUD Chrome & Frames"
Cohesion: 0.50
Nodes (4): arc_ruler(), polar(), Teilung entlang eines kreisbogens, in kompassgrad. inward=True zieht die…, Kompasswinkel -> punkt in TOP-DOWN pixeln (0 = oben, im uhrzeigersinn).

### Community 130 - "HUD Chrome & Frames (2)"
Cohesion: 0.50
Nodes (4): compass_to_screen(), Ein bogen aus EINZELNEN zellen -- die anzeigeform der vorlage. Ein…, Kompasswinkel -> der winkel, den UIDraw.arc erwartet. UIDraw rechnet…, segment_arc()

### Community 132 - "Orbital Mechanics Theory (Curtis) (6)"
Cohesion: 0.67
Nodes (3): Quaternions for Attitude Representation, Rigid Body Dynamics / Euler's Equations of Rotational Motion, Satellite Attitude Dynamics and Control

### Community 134 - "Tests: Warp Predictor (5)"
Cohesion: 0.67
Nodes (3): _clear_of_bodies21(), t_char, wenn das schiff bei diesem Erd-abstand auf der transferbahn steht., _tchar_at()

### Community 135 - "Tests: Warp Predictor (6)"
Cohesion: 0.67
Nodes (3): _fires(), _place_on_ellipse(), Wie oft fordert die schub-erkennung in `frames` bildern eine neuberechnung an?…

### Community 136 - "Tests: Warp Predictor (7)"
Cohesion: 0.67
Nodes (3): _hermite_at(), Die linie KUBISCH auswerten -- so zeichnet der renderer sie auch. Linear…, _walk18()

## Knowledge Gaps
- **33 isolated node(s):** `_Motion`, `Anfangswertproblem`, `KI-Nutzung (Tabelle)`, `Superposition der Beschleunigungen`, `Wechsel PyOpenGL -> moderngl` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1132 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Rect` connect `UI Core Framework (2)` to `Core Physics & Config Bootstrapping`, `UI Theme & Palette`, `UI Core Framework (4)`, `Tests: Background Test`, `Tests: Ui Horizon`, `UI Core Framework (3)`, `UI Core Framework`, `Horizon Rate Slider`, `System Map Widget`, `HUD Panels & Ship Badge (2)`, `Maneuver HUD Panel (2)`, `Slider Widget`, `Dropdown Widget`, `Panel & Stack Layout`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `Predictor` connect `Predictor Core` to `Predictor Numba Kernels`, `Core Physics & Config Bootstrapping`, `Tests: Ui Hud`, `Maneuver Planning`, `Predictor Async Jobs`, `Predictor Horizon Policy`, `Tests: Warp Predictor`, `Predictor View / Display Line`, `Tests: Warp Predictor (2)`, `Bootstrap & Frame Controller`, `Predictor Warp Hold`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Renderer Core` to `Orbit Line Rendering`, `Core Physics & Config Bootstrapping`, `Tests: Ui Hud`, `Tests: Body Icon`, `Body Rendering`, `Tests: Selection Camera`, `Reference Frames (Principia-style) (6)`, `Starfield & Grid Background (2)`, `Tests: Ship Scale`, `Starfield & Grid Background`, `Shader Pipelines`, `Prediction Line Drawing (2)`, `Bootstrap & Frame Controller`, `Ship Rendering`, `OpenGL Device & FXAA`, `Draw Primitives & Clipping`, `Maneuver Rendering`, `Renderer Text & Labels`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `Vec2` (e.g. with `body` and `ReferenceFrame`) actually correct?**
  _`Vec2` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `world` (e.g. with `body` and `Vec2`) actually correct?**
  _`world` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `_Motion`, `Anfangswertproblem`, `KI-Nutzung (Tabelle)` to the rest of the system?**
  _33 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Predictor Numba Kernels` be split into smaller, more focused modules?**
  _Cohesion score 0.051717699775952204 - nodes in this community are weakly interconnected._