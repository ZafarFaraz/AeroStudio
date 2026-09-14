# AeroStudio product context

AeroStudio is a classroom learning environment for CoDrone EDU. Students use ready-made checks and flights, a visual block builder, and teacher-unlocked manual controls. Its defining mechanism is a student-friendly interface over a real USB-connected drone, with obstacle braking and bounded programs built into every flight path.

The primary audience is school students using managed Windows or ChromeOS laptops. They must be able to open a URL and work without installing an executable. Teachers need a predictable setup, clear connection feedback, an emergency stop, and a practice mode when hardware is unavailable.

The browser app must preserve the 18 programs, safety behavior, visual block builder, hidden advanced controller, cyan-and-teal identity, and plain-language recovery messages. It uses Web Serial and the official `codrone-edu` Python package running locally in the browser through Pyodide. Student code and drone traffic stay on the device.
