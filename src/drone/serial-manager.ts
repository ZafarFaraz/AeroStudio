import type { SerialNavigator, SerialPortLike } from "./types";

const CODRONE_VENDOR_ID = 1155;
const BAUD_RATE = 57_600;

export class SerialPortManager {
  port: SerialPortLike | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  private writeQueue: Promise<void> = Promise.resolve();

  async connect(): Promise<void> {
    const serial = (navigator as SerialNavigator).serial;
    if (!serial) {
      throw new Error("Web Serial is not available. Use Chrome or Edge on a school-approved laptop.");
    }
    const selectedPort = await serial.requestPort({
      filters: [{ usbVendorId: CODRONE_VENDOR_ID }],
    });
    this.port = selectedPort;
    try {
      await this.openSelectedPort();
    } catch (error) {
      this.port = null;
      throw error;
    }
  }

  async reconnectToPort(): Promise<boolean> {
    const serial = (navigator as SerialNavigator).serial;
    if (!serial) return false;
    const ports = await serial.getPorts();
    this.port = ports.find((port) => port.getInfo().usbVendorId === CODRONE_VENDOR_ID) ?? null;
    if (!this.port) return false;
    await this.openSelectedPort();
    return true;
  }

  async read(): Promise<Uint8Array | null> {
    if (!this.port?.readable) return null;
    if (!this.reader) this.reader = this.port.readable.getReader();
    try {
      const { value, done } = await this.reader.read();
      return done ? null : value ?? null;
    } catch (error) {
      if (this.port) throw error;
      return null;
    }
  }

  write(data: ArrayLike<number>): void {
    const bytes = Uint8Array.from(data);
    this.writeQueue = this.writeQueue.catch(() => undefined).then(async () => {
      if (!this.writer) {
        if (!this.port?.writable) throw new Error("The controller serial port is not writable.");
        this.writer = this.port.writable.getWriter();
      }
      await this.writer.write(bytes);
    });
  }

  async disconnectAsync(): Promise<void> {
    const port = this.port;
    this.port = null;
    try {
      await this.reader?.cancel();
    } catch {
      // The cable may already be unplugged.
    }
    this.reader?.releaseLock();
    this.reader = null;
    await this.writeQueue.catch(() => undefined);
    this.writer?.releaseLock();
    this.writer = null;
    if (port) await port.close().catch(() => undefined);
  }

  disconnect(): void {
    void this.disconnectAsync();
  }

  private async openSelectedPort(): Promise<void> {
    if (!this.port) throw new Error("No CoDrone EDU controller was selected.");
    await this.port.open({ baudRate: BAUD_RATE });
  }
}

export const serialPortManager = new SerialPortManager();
