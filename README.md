# AeroStudio Web

AeroStudio is a browser-based CoDrone EDU learning environment for managed
classroom laptops. Students open one HTTPS URL, connect the controller through
the browser, and use 18 ready-made programs, a visual Block Builder, and
teacher-unlocked manual controls without installing an executable.

The web application preserves AeroStudio's safety model:

- forward movement checks the front range sensor before moving;
- the required clearance includes a 35 cm braking buffer;
- block programs are capped at 100 command steps;
- `while` blocks stop after five repeats;
- flights and valid block sequences land automatically; and
- **Stop now** remains available whenever a controller is connected.

## Student requirements

- Google Chrome or Microsoft Edge on Windows, macOS, Linux, or ChromeOS.
- A CoDrone EDU controller connected with a USB data cable.
- Browser permission to access the controller's serial port.
- Access to the hosted AeroStudio URL, `cdn.jsdelivr.net`, and `pypi.org`.

On the first hardware connection, the browser downloads Pyodide and
`codrone-edu==2.8`, then asks the student to select the CoDrone controller.
Drone commands and sensor data stay between the browser and the attached USB
controller. **Practice** runs a local simulator when hardware is unavailable.

Safari and Firefox do not currently provide the Web Serial API required by the
controller.

## School IT setup

The hosted site must be served over HTTPS. Allow the Firebase origin and USB
serial access in the managed browser. Chrome administrators may use
`SerialAllowAllPortsForUrls` for the exact AeroStudio origin; otherwise each
student chooses the controller in Chrome's permission prompt.

Before a class, verify this path on one managed student device:

1. Open AeroStudio in Chrome.
2. Connect the controller and powered-on drone.
3. Choose **Connect**, then select the CoDrone EDU controller.
4. Run **Battery Check**.
5. Run **LED Colors**.
6. Verify **Stop now** sends an emergency stop.

## Local development

Requires Node.js 20 or newer.

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:4173`. Localhost is treated as a secure browser context,
so Web Serial can be tested locally in Chrome.

Build the production assets with:

```bash
npm run build
```

## Firebase Hosting

This branch includes `firebase.json` with SPA routing, security headers,
long-lived hashed-asset caching, and a same-origin Web Serial permissions
policy. It intentionally does not include `.firebaserc`; select the correct
school or personal Firebase project explicitly.

```bash
npx firebase login
npx firebase use --add
npm run build
npx firebase deploy --only hosting
```

Firebase publishes the app to `https://PROJECT_ID.web.app` and
`https://PROJECT_ID.firebaseapp.com`. Add a custom domain from the Firebase
console if the school prefers an allow-listed institutional address.

## Project layout

- `src/App.tsx` contains the classroom interface and connection lifecycle.
- `src/drone/serial-manager.ts` provides Web Serial at 57,600 baud.
- `src/drone/pyodide-driver.ts` loads the official CoDrone Python package.
- `src/drone/mock-driver.ts` powers local Practice mode.
- `src/data/programs.ts` defines the 18 ready-made student programs.
- `src/data/blocks.ts` defines, validates, and executes Block Builder programs.
- `firebase.json` configures production hosting.
- `assets/` contains the existing identity and program illustrations.

The former Python desktop sources remain as implementation and safety
references while the browser port is validated with classroom hardware.

## Safety

Fly indoors in a clear area and keep people away from propellers. Keep the
physical controller accessible during every flight. The CoDrone EDU has one
forward-facing obstacle sensor, so AeroStudio cannot inspect left, right,
backward, or upward paths without changing the requested movement. Those
directions therefore retain their literal behavior.

The backward-flip program requires at least 50% battery and substantially more
clear space than other programs. Always test hardware behavior with an adult
supervising the first flight after a deployment.
