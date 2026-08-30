# AeroStudio

AeroStudio is the desktop learning app for the Drone Incursions program and is
compatible with CoDrone EDU. It contains 18 ready-made programs, an advanced
manual controller, and a visual block-programming builder. Every ready-made
program lives in its own file under `programs/` and includes a short
description. The cyan-and-teal visual identity and app icon combine the
supplied Muslims in Tech geometric mark with a quadcopter influence.

The desktop interface follows the Apple design guidance stored in
`.design-rules/`: a persistent sidebar, clear content/action separation,
high-contrast layered surfaces, readable desktop typography, visible status
feedback, and keyboard navigation. Press `Command–1` through `Command–4` to
switch between the student sections on macOS. The unlocked Controller uses
`Command–5`.

The tabs are organised by difficulty:

- **Basic** contains six grounded battery, sensor, light, temperature,
  orientation, and colour checks.
- **Simple** contains six beginner flights, including a triangle, zigzag, and
  gentle light dance.
- **Advanced** contains six larger routines, including a figure eight,
  obstacle-aware scout, and rainbow square.
- **Controller** provides advanced takeoff, landing, movement, height, turn,
  and hover controls. It is hidden by default; pressing the
  **AeroStudio** title five times reveals it until the app closes.
- **Block Builder** groups 29 drone commands and seven control blocks into
  Flight, Movement, Lights, Sensors & timing, Tricks & paths, and Logic & loops
  palettes. The tricks palette includes four flip directions, a 360° turn,
  square, triangle, zigzag, circle, figure-eight, and rainbow-square paths.
  Logic blocks introduce Python-style `if` / `else`, `for`, and `while` structures.
  Opening blocks automatically add their matching end marker, and selected
  blocks become the insertion point for nested commands. The sequence view
  displays indentation and equivalent Python expressions. Inline checks catch
  malformed structures, movement before takeoff, and unsafe flight paths. For
  safety, `while` loops stop after at most five repeats and the app
  automatically lands if a valid sequence ends in the air.

## Start the app

1. Connect the CoDrone EDU controller to the computer with its USB data cable.
2. Turn on the controller and drone.
3. From this folder, run:

   ```bash
   source venv/bin/activate
   python main.py
   ```

4. Select **Connect** in the app. Once connected, choose one program.

Program cards, controller controls, and the block sequence stay disabled until
a drone is connected. Select anywhere on a ready-made program card to run it;
each card includes a small pictogram describing its check or flight path.
Connection and flight failures appear in a dismissible recovery banner and in
the student-friendly Flight updates panel.

## Build desktop apps

PyInstaller produces a native app for the operating system on which it runs, so
macOS and Windows must be built separately. The project uses an unpacked app
folder rather than a single-file executable for faster startup and more
reliable bundled USB/serial dependencies.

### One-click Windows build

Install Python 3.10–3.14 on the Windows computer (Python 3.12 is recommended),
copy or clone the complete project, then
double-click `build_windows.bat`. It creates an isolated Windows build
environment, installs the dependencies, builds `AeroStudio.exe`, and produces
the distributable `dist/AeroStudio-Windows.zip`. Send the ZIP, not the EXE by
itself, because the executable needs the adjacent `_internal` folder.

### Manual or macOS build

On either platform, create and activate a Python 3.10–3.14 virtual environment,
then
run:

```bash
python -m pip install -r requirements-build.txt
python tools/build_app.py
```

Build outputs appear in `dist/`:

- macOS: `AeroStudio.app`
- Windows: `AeroStudio/AeroStudio.exe`

The `.github/workflows/windows-build.yml` workflow builds Windows on a hosted
Windows runner when run manually or when a `v*` tag is pushed. Download its ZIP
from the workflow artifact. Public Windows distribution should use a trusted
code-signing certificate to avoid security warnings.

## Safety

All ready-made programs, controller moves, and Block Builder flights use the
same obstacle-braking layer. Before forward movement, AeroStudio checks that the
travel distance plus a 35 cm buffer is clear. If the path is blocked, the drone
hovers, stops the routine, lands when possible, and shows an obstacle warning.

The CoDrone EDU has one forward-facing obstacle sensor, so it cannot inspect
left, right, backward, or upward paths. These controls always retain their
literal movement behaviour and never rotate the drone for a hidden sensor check.
Always use a clear indoor flight area and keep the physical controller ready.

- Fly indoors in a clear area and keep people away from the propellers.
- Begin with **Battery Check**, **Sensor Check**, and **LED Colors**.
- Keep the controller accessible during every flight.
- Use the red **EMERGENCY STOP** button if the drone behaves unexpectedly.
- The flip program needs substantially more clear space than the other programs.

## Project layout

- `main.py` launches the dashboard.
- `app.py` contains the interface, connection management, and Flight updates UI.
- `safety.py` applies shared directional obstacle checks and braking.
- `block_actions.py` defines the visual programming blocks.
- `block_program.py` parses, validates, and safely executes nested control
  structures from the Block Builder.
- `assets/codrone_studio_icon.png` is the full-resolution app icon.
- `assets/codrone_studio_icon_96.png` is the toolbar-sized icon source.
- `assets/program_icons/` contains the 18 descriptive program-card PNGs.
- `programs/` contains one file for each of the 18 ready-made programs.
- `requirements.txt` records the tested CoDrone EDU library version.
- `requirements-build.txt`, `packaging/`, and `tools/build_app.py` define the
  reproducible Windows/macOS packaging process.
