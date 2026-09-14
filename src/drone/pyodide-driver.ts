import { serialPortManager } from "./serial-manager";
import type { DroneDriver, Pyodide, SerialNavigator } from "./types";

const PYODIDE_VERSION = "0.27.7";
const PYODIDE_ROOT = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let runtimePromise: Promise<Pyodide> | null = null;

function loadScript(source: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${source}"]`);
    if (existing) {
      if (window.loadPyodide) resolve();
      else existing.addEventListener("load", () => resolve(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = source;
    script.async = true;
    script.addEventListener("load", () => resolve(), { once: true });
    script.addEventListener("error", () => reject(new Error("Could not download the browser Python runtime.")), { once: true });
    document.head.append(script);
  });
}

async function loadRuntime(onProgress?: (message: string) => void): Promise<Pyodide> {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      onProgress?.("Loading the flight engine for the first time…");
      await loadScript(`${PYODIDE_ROOT}pyodide.js`);
      if (!window.loadPyodide) throw new Error("The browser Python runtime did not start.");
      const pyodide = await window.loadPyodide({ indexURL: PYODIDE_ROOT });
      pyodide.registerJsModule("serialPortModule", { SerialPortManager: serialPortManager });
      onProgress?.("Loading the CoDrone EDU library…");
      await pyodide.loadPackage(["micropip", "numpy", "pillow"]);
      await pyodide.runPythonAsync(`
import micropip
await micropip.install("colorama==0.4.6", deps=False)
await micropip.install("codrone-edu==2.8", deps=False)
      `);
      pyodide.runPython(`
import asyncio
import builtins
import inspect
from codrone_edu.drone import Drone
from codrone_edu.system import ModeFlight

_aerostudio_original_print = builtins.print
def _aerostudio_web_print(*args, color=None, **kwargs):
    _aerostudio_original_print(*args, **kwargs)
builtins.print = _aerostudio_web_print

_aerostudio_drone = Drone()
_aerostudio_receive_task = None

# codrone-edu 2.8 invokes this optional Emscripten callback unconditionally
# when it sets the initial speed during connection. The teaching UI does not
# need a speed slider callback, so install a harmless one.
def _aerostudio_speed_changed(_speed):
    pass

_aerostudio_drone.add_callback("speed", _aerostudio_speed_changed)

async def aerostudio_connect():
    global _aerostudio_receive_task
    _aerostudio_drone._flagThreadRun = True
    _aerostudio_receive_task = asyncio.create_task(_aerostudio_drone._receiving_emscripten())
    await _aerostudio_drone._open_success_emscripten()
    if await _aerostudio_drone.get_flight_state() != ModeFlight.Ready:
        raise RuntimeError("The controller is connected, but the drone is not paired and ready.")
    return True

async def aerostudio_invoke(name, *args):
    result = getattr(_aerostudio_drone, name)(*args)
    if inspect.isawaitable(result):
        result = await result
    return result

async def aerostudio_stop_receiver():
    _aerostudio_drone._flagThreadRun = False
    await asyncio.sleep(0)
      `);
      return pyodide;
    })();
  }
  try {
    return await runtimePromise;
  } catch (error) {
    runtimePromise = null;
    throw error;
  }
}

export class PyodideDroneDriver implements DroneDriver {
  readonly mode = "hardware" as const;
  private runtime: Pyodide | null = null;
  private connected = false;

  async connect(onProgress?: (message: string) => void): Promise<void> {
    if (!(navigator as SerialNavigator).serial) {
      throw new Error("This browser cannot connect to USB serial devices. Open AeroStudio in Chrome or Edge.");
    }

    // Chrome only permits requestPort() while the Connect click still has user
    // activation. Ask for the controller before any runtime downloads/awaits.
    onProgress?.("Choose the CoDrone EDU controller in the browser prompt…");
    await serialPortManager.connect();
    try {
      this.runtime = await loadRuntime(onProgress);
      onProgress?.("Checking the controller and drone…");
      await this.runtime.runPythonAsync("await aerostudio_connect()");
      this.connected = true;
    } catch (error) {
      await this.runtime?.runPythonAsync("await aerostudio_stop_receiver()").catch(() => undefined);
      this.runtime = null;
      await serialPortManager.disconnectAsync();
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    if (this.runtime) {
      await this.runtime.runPythonAsync("await aerostudio_stop_receiver()").catch(() => undefined);
    }
    await serialPortManager.disconnectAsync();
  }

  async invoke<T = unknown>(method: string, ...args: unknown[]): Promise<T> {
    if (!this.runtime || !this.connected) throw new Error("Connect the controller first.");
    const invoke = this.runtime.globals.get("aerostudio_invoke");
    try {
      return (await invoke(method, ...args)) as T;
    } finally {
      invoke.destroy?.();
    }
  }

  isConnected(): boolean {
    return this.connected;
  }
}
