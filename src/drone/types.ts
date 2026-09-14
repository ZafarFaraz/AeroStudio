export interface DroneDriver {
  readonly mode: "hardware" | "practice";
  connect(onProgress?: (message: string) => void): Promise<void>;
  disconnect(): Promise<void>;
  invoke<T = unknown>(method: string, ...args: unknown[]): Promise<T>;
  isConnected(): boolean;
}

export type SerialPortLike = {
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
  getSignals(): Promise<unknown>;
  getInfo(): { usbVendorId?: number; usbProductId?: number };
};

export type SerialNavigator = Navigator & {
  serial?: {
    requestPort(options?: { filters?: Array<{ usbVendorId: number }> }): Promise<SerialPortLike>;
    getPorts(): Promise<SerialPortLike[]>;
  };
};

export type Pyodide = {
  loadPackage(packages: string[]): Promise<void>;
  registerJsModule(name: string, module: unknown): void;
  runPython(code: string): unknown;
  runPythonAsync(code: string): Promise<unknown>;
  globals: { get(name: string): ((...args: unknown[]) => unknown) & { destroy?: () => void } };
};

declare global {
  interface Window {
    loadPyodide?: (options: { indexURL: string }) => Promise<Pyodide>;
  }
}
