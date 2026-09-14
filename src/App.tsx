import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BatteryCharging,
  Blocks,
  Bot,
  Check,
  ChevronDown,
  CircleStop,
  Code2,
  Gamepad2,
  Gauge,
  GripVertical,
  Lightbulb,
  LoaderCircle,
  Play,
  Power,
  RotateCcw,
  RotateCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Unplug,
  Usb,
  WifiOff,
  X,
} from "lucide-react";
import logo from "../assets/codrone_studio_icon_96.png";
import batteryIcon from "../assets/program_icons/battery_check.png";
import colorIcon from "../assets/program_icons/color_check.png";
import figureEightIcon from "../assets/program_icons/figure_eight.png";
import flipIcon from "../assets/program_icons/flip.png";
import forwardBackIcon from "../assets/program_icons/forward_back.png";
import fullTurnIcon from "../assets/program_icons/full_turn.png";
import danceIcon from "../assets/program_icons/gentle_dance.png";
import hoverIcon from "../assets/program_icons/hover.png";
import ledIcon from "../assets/program_icons/led_colors.png";
import obstacleIcon from "../assets/program_icons/obstacle_scout.png";
import orientationIcon from "../assets/program_icons/orientation_check.png";
import rainbowIcon from "../assets/program_icons/rainbow_square.png";
import sensorIcon from "../assets/program_icons/sensor_check.png";
import sideIcon from "../assets/program_icons/side_to_side.png";
import squareIcon from "../assets/program_icons/square.png";
import temperatureIcon from "../assets/program_icons/temperature_check.png";
import triangleIcon from "../assets/program_icons/triangle.png";
import zigzagIcon from "../assets/program_icons/zigzag.png";
import { blockCategories, blockIndent, blocks, runSequence, validateSequence, type BlockCategory, type BlockSpec } from "./data/blocks";
import { programDescriptions, programs, type ProgramLevel, type ProgramSpec } from "./data/programs";
import { MockDroneDriver } from "./drone/mock-driver";
import { PyodideDroneDriver } from "./drone/pyodide-driver";
import type { DroneDriver, SerialNavigator } from "./drone/types";

type Page = ProgramLevel | "Controller" | "Block Builder";
type Tone = "info" | "success" | "warning" | "error";
type LogItem = { id: number; message: string; tone: Tone; time: string };

const iconMap: Record<string, string> = {
  battery_check: batteryIcon, color_check: colorIcon, figure_eight: figureEightIcon,
  flip: flipIcon, forward_back: forwardBackIcon, full_turn: fullTurnIcon,
  gentle_dance: danceIcon, hover: hoverIcon, led_colors: ledIcon,
  obstacle_scout: obstacleIcon, orientation_check: orientationIcon,
  rainbow_square: rainbowIcon, sensor_check: sensorIcon, side_to_side: sideIcon,
  square: squareIcon, temperature_check: temperatureIcon, triangle: triangleIcon,
  zigzag: zigzagIcon,
};

const navItems: Array<{ name: Page; icon: typeof Gauge; detail?: string }> = [
  { name: "Basic", icon: Gauge },
  { name: "Simple", icon: Play },
  { name: "Advanced", icon: Sparkles },
  { name: "Block Builder", icon: Blocks },
];

function friendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (/user gesture|user activation|permission request/i.test(message)) return "Chrome could not show the controller chooser. Refresh this page, then click Connect again.";
  if (/No port selected|NotFoundError/i.test(message)) return "No controller was selected. Plug it in and choose Connect when you are ready.";
  if (/NetworkError|Failed to open|already open|already in use/i.test(message)) return "Chrome found the controller but could not open it. Close other drone apps, reconnect the USB cable, and try again.";
  if (/download|fetch|micropip/i.test(message)) return "The flight engine could not download. Check the school network allows cdn.jsdelivr.net and pypi.org, then try again.";
  return message || "Something went wrong. Check the controller and try again.";
}

function App() {
  const [page, setPage] = useState<Page>("Basic");
  const [driver, setDriver] = useState<DroneDriver | null>(null);
  const [connection, setConnection] = useState<"disconnected" | "connecting" | "connected">("disconnected");
  const [connectionDetail, setConnectionDetail] = useState("Connect a controller or start practice mode");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogItem[]>([{ id: 1, message: "Ready to begin", tone: "info", time: "Now" }]);
  const [controllerUnlocked, setControllerUnlocked] = useState(false);
  const [brandPresses, setBrandPresses] = useState(0);
  const runToken = useRef(0);
  const logId = useRef(1);

  const connected = connection === "connected" && Boolean(driver?.isConnected());
  const serialSupported = "serial" in (navigator as SerialNavigator);

  const log = useCallback((message: string, tone: Tone = "info") => {
    logId.current += 1;
    const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date());
    setLogs((current) => [{ id: logId.current, message, tone, time }, ...current].slice(0, 8));
  }, []);

  const connect = async (mode: "hardware" | "practice") => {
    if (connection === "connecting") return;
    setNotice(null);
    setConnection("connecting");
    const nextDriver = mode === "hardware" ? new PyodideDroneDriver() : new MockDroneDriver();
    try {
      await nextDriver.connect((message) => setConnectionDetail(message));
      setDriver(nextDriver);
      setConnection("connected");
      const label = mode === "hardware" ? "CoDrone EDU connected" : "Practice mode ready";
      setConnectionDetail(label);
      log(`${label}.`, "success");
    } catch (error) {
      const message = friendlyError(error);
      setConnection("disconnected");
      setConnectionDetail("Connect a controller or start practice mode");
      setNotice(message);
      log(message, "error");
    }
  };

  const disconnect = async () => {
    runToken.current += 1;
    setBusy(false);
    await driver?.disconnect();
    setDriver(null);
    setConnection("disconnected");
    setConnectionDetail("Connect a controller or start practice mode");
    log("Disconnected.");
  };

  const emergencyStop = async () => {
    if (!driver || !connected) return;
    runToken.current += 1;
    setBusy(false);
    log("Emergency stop sent.", "warning");
    try {
      await Promise.race([
        driver.invoke("emergency_stop"),
        new Promise((resolve) => window.setTimeout(resolve, 1200)),
      ]);
      log("Motors stopped. Keep the controller nearby.", "success");
    } catch (error) {
      const message = `Stop may not have reached the drone: ${friendlyError(error)}`;
      setNotice(message);
      log(message, "error");
    }
  };

  const makeContext = (token: number) => ({
    log,
    stopped: () => runToken.current !== token,
    safeForward: async (distanceCm: number, speed = 0.5) => {
      if (!driver) throw new Error("Connect the controller first.");
      const distance = await driver.invoke<number>("get_front_range", "cm");
      const required = Math.max(55, distanceCm + 35);
      log(`Safety check: ${Math.round(distance)} cm clear ahead`);
      if (distance <= required) {
        await driver.invoke("hover", 0.5).catch(() => undefined);
        throw new Error(`Obstacle detected ${Math.round(distance)} cm away. The drone braked and the flight was stopped.`);
      }
      await driver.invoke("move_forward", distanceCm, "cm", speed);
    },
  });

  const runProgram = async (program: ProgramSpec) => {
    if (!driver || !connected || busy) return;
    const token = ++runToken.current;
    setBusy(true);
    setNotice(null);
    log(`Starting ${program.name}…`, "info");
    try {
      await program.run(driver, makeContext(token));
      if (runToken.current === token) log(`${program.name} complete.`, "success");
    } catch (error) {
      const message = friendlyError(error);
      setNotice(message);
      log(`${program.name} stopped: ${message}`, "error");
      if (driver.isConnected()) await driver.invoke("land").catch(() => undefined);
    } finally {
      if (runToken.current === token) setBusy(false);
    }
  };

  const pressBrand = () => {
    if (controllerUnlocked) return;
    const next = brandPresses + 1;
    setBrandPresses(next);
    if (next >= 5) {
      setControllerUnlocked(true);
      setBrandPresses(0);
      log("Advanced controller unlocked.", "success");
    }
  };

  useEffect(() => {
    const shortcuts = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey)) return;
      const pages: Page[] = ["Basic", "Simple", "Advanced", "Block Builder", "Controller"];
      const target = pages[Number(event.key) - 1];
      if (target && (target !== "Controller" || controllerUnlocked)) {
        event.preventDefault(); setPage(target);
      }
      if (event.key === "Enter" && page === "Block Builder") event.preventDefault();
    };
    window.addEventListener("keydown", shortcuts);
    return () => window.removeEventListener("keydown", shortcuts);
  }, [controllerUnlocked, page]);

  const statusLabel = connection === "connecting" ? "Connecting" : connected ? (driver?.mode === "practice" ? "Practice" : "Connected") : "Disconnected";
  const latest = logs[0];

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={pressBrand} aria-label="AeroStudio" title="AeroStudio">
          <img src={logo} alt="" />
          <span><strong>AeroStudio</strong><small>Learn, build, and fly with CoDrone EDU</small></span>
        </button>
        <div className="connection-actions">
          <div className={`status-badge ${connection}`} aria-live="polite">
            <span className="status-dot" />
            <span><strong>{statusLabel}</strong><small>{connectionDetail}</small></span>
          </div>
          {connected ? (
            <button className="button secondary" onClick={disconnect}><Unplug size={17} /> Disconnect</button>
          ) : (
            <>
              <button className="button quiet practice-button" onClick={() => connect("practice")} disabled={connection === "connecting"}><Bot size={17} /> Practice</button>
              <button className="button primary" onClick={() => connect("hardware")} disabled={connection === "connecting" || !serialSupported}>
                {connection === "connecting" ? <LoaderCircle className="spin" size={17} /> : <Usb size={17} />} Connect
              </button>
            </>
          )}
          <button className="button emergency" onClick={emergencyStop} disabled={!connected}><CircleStop size={18} /> Stop now</button>
        </div>
      </header>

      {!serialSupported && !connected && (
        <div className="browser-warning" role="status">
          <WifiOff size={18} /><span><strong>USB connection is unavailable in this browser.</strong> Open AeroStudio in Chrome or Edge, or use Practice.</span>
        </div>
      )}
      {notice && (
        <div className="notice" role="alert"><AlertTriangle size={19} /><span>{notice}</span><button onClick={() => setNotice(null)} aria-label="Dismiss message"><X size={17} /></button></div>
      )}

      <div className="workspace">
        <aside className="sidebar" aria-label="AeroStudio sections">
          <span className="nav-label">Explore</span>
          <nav>
            {[...navItems, ...(controllerUnlocked ? [{ name: "Controller" as Page, icon: Gamepad2, detail: "Advanced" }] : [])].map((item, index) => {
              const Icon = item.icon;
              return <button key={item.name} className={page === item.name ? "active" : ""} onClick={() => setPage(item.name)}><Icon size={18} /><span>{item.name}</span><kbd>{index + 1}</kbd></button>;
            })}
          </nav>
          <div className="sidebar-tip"><Lightbulb size={17} /><p><strong>Start safely</strong>Begin with Basic checks before your first flight.</p></div>
        </aside>

        <main className="main-surface">
          {(["Basic", "Simple", "Advanced"] as Page[]).includes(page) && (
            <ProgramPage level={page as ProgramLevel} connected={connected} busy={busy} onRun={runProgram} />
          )}
          {page === "Controller" && <Controller driver={driver} connected={connected} busy={busy} log={log} setBusy={setBusy} setNotice={setNotice} />}
          {page === "Block Builder" && <BlockBuilder driver={driver} connected={connected} busy={busy} setBusy={setBusy} setNotice={setNotice} log={log} makeContext={makeContext} runToken={runToken} />}
        </main>
      </div>

      <section className="flight-updates" aria-label="Flight updates" aria-live="polite">
        <div className="updates-header"><span><strong>Flight updates</strong><em><ShieldCheck size={15} /> Forward obstacle braking on</em></span><button onClick={() => setLogs([])}>Clear</button></div>
        {latest ? <div className={`latest-update ${latest.tone}`}><span className="update-symbol">{latest.tone === "success" ? <Check /> : latest.tone === "error" || latest.tone === "warning" ? <AlertTriangle /> : <span>●</span>}</span><strong>{latest.message}</strong><time>{latest.time}</time></div> : <div className="latest-update info"><span className="update-symbol">●</span><strong>No flight updates yet</strong></div>}
        {logs.length > 1 && <p className="earlier-update">Earlier: {logs.slice(1, 4).map((item) => item.message).join(" · ")}</p>}
      </section>
    </div>
  );
}

function ProgramPage({ level, connected, busy, onRun }: { level: ProgramLevel; connected: boolean; busy: boolean; onRun(program: ProgramSpec): void }) {
  const visible = programs.filter((program) => program.level === level);
  return (
    <section className="page-section">
      <div className="page-heading"><div><span className="eyebrow">{level === "Basic" ? "Start here" : level === "Simple" ? "Build confidence" : "More room required"}</span><h1>{level}</h1><p>{programDescriptions[level]}</p></div><span className="program-count">{visible.length} programs</span></div>
      <div className="program-grid">
        {visible.map((program, index) => (
          <button className="program-card" key={program.name} disabled={!connected || busy} onClick={() => onRun(program)}>
            <span className="program-number">{String(index + 1).padStart(2, "0")}</span>
            <img src={iconMap[program.icon]} alt="" />
            <span className="card-copy"><strong>{program.name}</strong><small>{program.description}</small></span>
            <span className="run-label"><Play size={14} fill="currentColor" /> Run</span>
          </button>
        ))}
      </div>
      {!connected && <div className="locked-hint"><Power size={18} /><span><strong>Programs unlock after connection.</strong> Use a real controller or choose Practice in the top bar.</span></div>}
    </section>
  );
}

type ControllerProps = { driver: DroneDriver | null; connected: boolean; busy: boolean; log(message: string, tone?: Tone): void; setBusy(value: boolean): void; setNotice(value: string | null): void };

function Controller({ driver, connected, busy, log, setBusy, setNotice }: ControllerProps) {
  const action = async (label: string, method: string, ...args: unknown[]) => {
    if (!driver || !connected || busy) return;
    setBusy(true); log(`${label}…`);
    try { await driver.invoke(method, ...args); log(`${label} complete.`, "success"); }
    catch (error) { const message = friendlyError(error); setNotice(message); log(message, "error"); }
    finally { setBusy(false); }
  };
  const controls = [
    ["Forward 30 cm", ArrowUp, "move_forward", 30, "cm", 0.5], ["Left 30 cm", ArrowLeft, "move_left", 30, "cm", 0.5],
    ["Right 30 cm", ArrowRight, "move_right", 30, "cm", 0.5], ["Backward 30 cm", ArrowDown, "move_backward", 30, "cm", 0.5],
    ["Turn left 90°", RotateCcw, "turn_left", 90], ["Turn right 90°", RotateCw, "turn_right", 90],
  ] as const;
  return <section className="page-section controller-page"><div className="page-heading"><div><span className="eyebrow">Teacher-unlocked controls</span><h1>Controller</h1><p>Send one deliberate movement at a time. Keep the physical controller within reach.</p></div><Gamepad2 className="heading-icon" /></div>
    <div className="controller-layout"><div className="control-panel"><h2>Movement pad</h2><div className="control-grid">{controls.map(([label, Icon, method, ...args]) => <button key={label} disabled={!connected || busy} onClick={() => action(label, method, ...args)}><Icon /><span>{label}</span></button>)}</div></div>
      <div className="control-panel flight-panel"><h2>Flight</h2><button className="takeoff" disabled={!connected || busy} onClick={() => action("Take off", "takeoff")}><ArrowUp />Take off</button><button disabled={!connected || busy} onClick={() => action("Hover", "hover", 1)}><Bot />Hover 1 second</button><button className="land" disabled={!connected || busy} onClick={() => action("Land", "land")}><ChevronDown />Land</button><p><ShieldCheck /> Forward program paths include obstacle braking. Manual directional controls preserve the movement you select.</p></div>
    </div></section>;
}

type BlockBuilderProps = {
  driver: DroneDriver | null; connected: boolean; busy: boolean;
  setBusy(value: boolean): void; setNotice(value: string | null): void;
  log(message: string, tone?: Tone): void;
  makeContext(token: number): {
    log(message: string, tone?: Tone): void;
    stopped(): boolean;
    safeForward(distance: number, speed?: number): Promise<void>;
  };
  runToken: React.MutableRefObject<number>;
};

function BlockBuilder({ driver, connected, busy, setBusy, setNotice, log, makeContext, runToken }: BlockBuilderProps) {
  const [category, setCategory] = useState<BlockCategory>("Flight");
  const [sequence, setSequence] = useState<BlockSpec[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const validation = useMemo(() => validateSequence(sequence), [sequence]);
  const indents = useMemo(() => blockIndent(sequence), [sequence]);
  const palette = blocks.filter((block) => block.category === category);

  const addBlock = (block: BlockSpec) => {
    const insertion = selected === null ? sequence.length : selected + 1;
    const additions = [block];
    const ending: Record<string, string> = { if: "end-if", repeat: "end-repeat", while: "end-while" };
    const endId = ending[block.kind ?? ""];
    if (endId) additions.push(blocks.find((candidate) => candidate.id === endId)!);
    setSequence((current) => [...current.slice(0, insertion), ...additions, ...current.slice(insertion)]);
    setSelected(insertion);
  };

  const remove = () => {
    if (selected === null) return;
    setSequence((current) => current.filter((_, index) => index !== selected));
    setSelected(sequence.length <= 1 ? null : Math.min(selected, sequence.length - 2));
  };
  const move = (direction: -1 | 1) => {
    if (selected === null) return;
    const target = selected + direction;
    if (target < 0 || target >= sequence.length) return;
    const next = [...sequence]; [next[selected], next[target]] = [next[target], next[selected]]; setSequence(next); setSelected(target);
  };
  const run = async () => {
    if (!driver || !connected || busy || !validation.valid) return;
    const token = ++runToken.current; setBusy(true); setNotice(null); log("Starting block sequence…");
    try { await runSequence(sequence, driver, makeContext(token)); if (runToken.current === token) log("Block sequence complete.", "success"); }
    catch (error) { const message = friendlyError(error); setNotice(message); log(`Sequence stopped: ${message}`, "error"); await driver.invoke("land").catch(() => undefined); }
    finally { if (runToken.current === token) setBusy(false); }
  };

  return <section className="page-section builder-page"><div className="page-heading"><div><span className="eyebrow">Visual programming</span><h1>Block Builder</h1><p>Build a safe sequence. Control blocks add their matching end automatically.</p></div><Code2 className="heading-icon" /></div>
    <div className="builder-layout"><div className="palette-panel"><div className="panel-title"><h2>Command palette</h2><span>{palette.length} blocks</span></div><div className="category-tabs">{blockCategories.map((name) => <button className={category === name ? "active" : ""} key={name} onClick={() => setCategory(name)}>{name}</button>)}</div><div className="palette-list">{palette.map((block) => <article className={`palette-item category-${block.category.toLowerCase().replaceAll(" ", "-").replaceAll("&", "and")}`} key={block.id}><span className="block-glyph"><Blocks size={18} /></span><div><strong>{block.name}</strong><code>{block.code}</code></div><button onClick={() => addBlock(block)} disabled={busy} aria-label={`Add ${block.name}`}>Add <span>+</span></button></article>)}</div></div>
      <div className="sequence-panel"><div className="panel-title"><h2>Flight sequence</h2><span>{sequence.length} {sequence.length === 1 ? "block" : "blocks"}</span></div><p className={`validation ${validation.valid ? "valid" : sequence.length ? "invalid" : ""}`}>{validation.valid ? <Check size={15} /> : sequence.length ? <AlertTriangle size={15} /> : <Code2 size={15} />}{validation.message}</p>
        <div className="sequence-list">{sequence.length ? sequence.map((block, index) => <button key={`${block.id}-${index}`} className={selected === index ? "selected" : ""} style={{ paddingLeft: `${16 + indents[index] * 22}px` }} onClick={() => setSelected(index)}><GripVertical size={15} /><span>{String(index + 1).padStart(2, "0")}</span><code>{block.code}</code></button>) : <div className="empty-sequence"><Blocks size={30} /><strong>Your sequence is empty</strong><span>Choose a command on the left to begin.</span></div>}</div>
        <div className="sequence-tools"><button onClick={remove} disabled={selected === null || busy}><Trash2 /> Remove</button><button onClick={() => move(-1)} disabled={selected === null || selected === 0 || busy}><ArrowUp /> Up</button><button onClick={() => move(1)} disabled={selected === null || selected === sequence.length - 1 || busy}><ArrowDown /> Down</button><button onClick={() => { setSequence([]); setSelected(null); }} disabled={!sequence.length || busy}><RotateCcw /> Clear</button></div>
        <button className="run-sequence" onClick={run} disabled={!connected || busy || !validation.valid}><Play fill="currentColor" /> Run sequence</button>
      </div></div>
  </section>;
}

export default App;
