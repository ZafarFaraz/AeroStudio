import type { DroneDriver } from "./types";

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export class MockDroneDriver implements DroneDriver {
  readonly mode = "practice" as const;
  private connected = false;
  private airborne = false;

  async connect(onProgress?: (message: string) => void): Promise<void> {
    onProgress?.("Starting practice mode…");
    await delay(350);
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    this.airborne = false;
  }

  async invoke<T = unknown>(method: string, ...args: unknown[]): Promise<T> {
    if (!this.connected) throw new Error("Start practice mode first.");
    await delay(method.startsWith("move_") || method === "hover" ? 450 : 180);
    const values: Record<string, unknown> = {
      get_battery: 84,
      get_height: this.airborne ? 62 : 0,
      get_front_range: 186,
      get_drone_temperature: 24.6,
      get_x_angle: 1,
      get_y_angle: -2,
      get_z_angle: 92,
      get_front_color: "blue",
      get_back_color: "white",
    };
    if (method === "takeoff") this.airborne = true;
    if (method === "land" || method === "emergency_stop") this.airborne = false;
    void args;
    return values[method] as T;
  }

  isConnected(): boolean {
    return this.connected;
  }
}
