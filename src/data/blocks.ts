import type { DroneDriver } from "../drone/types";

export type BlockCategory = "Flight" | "Movement" | "Lights" | "Sensors & timing" | "Tricks & paths" | "Logic & loops";
export type BlockKind = "command" | "if" | "else" | "end_if" | "repeat" | "end_repeat" | "while" | "end_while";

export type BlockSpec = {
  id: string;
  name: string;
  category: BlockCategory;
  code: string;
  kind?: BlockKind;
  command?: { method: string; args?: unknown[] };
};

const command = (id: string, name: string, category: BlockCategory, code: string, method: string, ...args: unknown[]): BlockSpec => ({ id, name, category, code, command: { method, args } });

export const blocks: BlockSpec[] = [
  command("takeoff", "Take off", "Flight", "drone.takeoff()", "takeoff"),
  command("land", "Land", "Flight", "drone.land()", "land"),
  command("hover", "Hover 1 second", "Flight", "drone.hover(1)", "hover", 1),
  command("forward", "Forward 30 cm", "Movement", "drone.move_forward(30)", "move_forward", 30, "cm", 0.5),
  command("backward", "Backward 30 cm", "Movement", "drone.move_backward(30)", "move_backward", 30, "cm", 0.5),
  command("left", "Left 30 cm", "Movement", "drone.move_left(30)", "move_left", 30, "cm", 0.5),
  command("right", "Right 30 cm", "Movement", "drone.move_right(30)", "move_right", 30, "cm", 0.5),
  command("up", "Up 30 cm", "Movement", "drone.move_distance(0, 0, 0.3)", "move_distance", 0, 0, 0.3, 0.5),
  command("down", "Down 30 cm", "Movement", "drone.move_distance(0, 0, -0.3)", "move_distance", 0, 0, -0.3, 0.5),
  command("turn-left", "Turn left 90°", "Movement", "drone.turn_left(90)", "turn_left", 90),
  command("turn-right", "Turn right 90°", "Movement", "drone.turn_right(90)", "turn_right", 90),
  command("led-red", "LED red", "Lights", "drone.set_drone_LED(255, 0, 0)", "set_drone_LED", 255, 0, 0, 100),
  command("led-green", "LED green", "Lights", "drone.set_drone_LED(0, 255, 0)", "set_drone_LED", 0, 255, 0, 100),
  command("led-blue", "LED blue", "Lights", "drone.set_drone_LED(0, 80, 255)", "set_drone_LED", 0, 80, 255, 100),
  command("led-white", "LED white", "Lights", "drone.set_drone_LED(255, 255, 255)", "set_drone_LED", 255, 255, 255, 100),
  command("wait", "Wait 1 second", "Sensors & timing", "await wait(1)", "hover", 1),
  command("battery", "Read battery", "Sensors & timing", "battery = drone.get_battery()", "get_battery"),
  command("front", "Read front sensor", "Sensors & timing", "distance = drone.get_front_range('cm')", "get_front_range", "cm"),
  command("flip-back", "Flip backward", "Tricks & paths", "drone.flip('back')", "flip", "back"),
  command("flip-front", "Flip forward", "Tricks & paths", "drone.flip('front')", "flip", "front"),
  command("turn-360", "Turn 360°", "Tricks & paths", "drone.turn_right(360)", "turn_right", 360),
  { id: "if-clear", name: "If path is clear", category: "Logic & loops", code: "if front_distance > 80:", kind: "if" },
  { id: "otherwise", name: "Otherwise", category: "Logic & loops", code: "else:", kind: "else" },
  { id: "end-if", name: "End if", category: "Logic & loops", code: "# end if", kind: "end_if" },
  { id: "repeat", name: "Repeat 3 times", category: "Logic & loops", code: "for _ in range(3):", kind: "repeat" },
  { id: "end-repeat", name: "End repeat", category: "Logic & loops", code: "# end repeat", kind: "end_repeat" },
  { id: "while-clear", name: "While path is clear", category: "Logic & loops", code: "while front_distance > 80:", kind: "while" },
  { id: "end-while", name: "End while", category: "Logic & loops", code: "# end while", kind: "end_while" },
];

export const blockCategories: BlockCategory[] = ["Flight", "Movement", "Lights", "Sensors & timing", "Tricks & paths", "Logic & loops"];

export function blockIndent(sequence: BlockSpec[]): number[] {
  let depth = 0;
  return sequence.map((block) => {
    if (["else", "end_if", "end_repeat", "end_while"].includes(block.kind ?? "")) depth = Math.max(0, depth - 1);
    const current = depth;
    if (["if", "else", "repeat", "while"].includes(block.kind ?? "")) depth += 1;
    return current;
  });
}

export function validateSequence(sequence: BlockSpec[]): { valid: boolean; message: string; autoLand: boolean } {
  if (!sequence.length) return { valid: false, message: "Add a command to begin", autoLand: false };
  const stack: BlockKind[] = [];
  let airborne = false;
  for (let index = 0; index < sequence.length; index += 1) {
    const block = sequence[index];
    const kind = block.kind ?? "command";
    if (["if", "repeat", "while"].includes(kind)) stack.push(kind);
    if (kind === "else" && stack.at(-1) !== "if") return { valid: false, message: `Block ${index + 1}: Otherwise needs If path is clear`, autoLand: false };
    if (kind === "end_if" && stack.pop() !== "if") return { valid: false, message: `Block ${index + 1}: End if has no matching start`, autoLand: false };
    if (kind === "end_repeat" && stack.pop() !== "repeat") return { valid: false, message: `Block ${index + 1}: End repeat has no matching start`, autoLand: false };
    if (kind === "end_while" && stack.pop() !== "while") return { valid: false, message: `Block ${index + 1}: End while has no matching start`, autoLand: false };
    if (block.id === "takeoff") {
      if (airborne) return { valid: false, message: `Block ${index + 1}: the drone may already be airborne`, autoLand: false };
      airborne = true;
    }
    if (block.id === "land") {
      if (!airborne) return { valid: false, message: `Block ${index + 1}: the drone may not have taken off`, autoLand: false };
      airborne = false;
    }
    if ((block.category === "Movement" || block.category === "Tricks & paths") && !airborne) {
      return { valid: false, message: `Block ${index + 1}: movement needs Take off first`, autoLand: false };
    }
  }
  if (stack.length) return { valid: false, message: "A control block is missing its matching end", autoLand: false };
  return { valid: true, message: airborne ? "Ready — automatic landing will be added" : "Ready to run", autoLand: airborne };
}

export async function runSequence(
  sequence: BlockSpec[],
  driver: DroneDriver,
  context: { log(message: string): void; stopped(): boolean; safeForward(distance: number, speed?: number): Promise<void> },
): Promise<void> {
  let airborne = false;
  let commandSteps = 0;

  type Node =
    | { type: "command"; block: BlockSpec; index: number }
    | { type: "if"; block: BlockSpec; index: number; whenTrue: Node[]; whenFalse: Node[] }
    | { type: "loop"; block: BlockSpec; index: number; body: Node[] };

  const parseBody = (start: number, endings: Set<BlockKind>): [Node[], number, BlockKind | null] => {
    const nodes: Node[] = [];
    let position = start;
    while (position < sequence.length) {
      const block = sequence[position];
      const kind = block.kind ?? "command";
      if (endings.has(kind)) return [nodes, position, kind];
      if (kind === "command") { nodes.push({ type: "command", block, index: position }); position += 1; continue; }
      if (kind === "if") {
        const [whenTrue, marker, markerKind] = parseBody(position + 1, new Set(["else", "end_if"]));
        let whenFalse: Node[] = [];
        let end = marker;
        if (markerKind === "else") [whenFalse, end] = parseBody(marker + 1, new Set(["end_if"]));
        nodes.push({ type: "if", block, index: position, whenTrue, whenFalse }); position = end + 1; continue;
      }
      if (kind === "repeat" || kind === "while") {
        const expected = kind === "repeat" ? "end_repeat" : "end_while";
        const [body, end] = parseBody(position + 1, new Set([expected]));
        nodes.push({ type: "loop", block, index: position, body }); position = end + 1; continue;
      }
      position += 1;
    }
    return [nodes, position, null];
  };

  const executeCommand = async (block: BlockSpec, index: number) => {
    if (!block.command) return;
    commandSteps += 1;
    if (commandSteps > 100) throw new Error("Stopped after 100 commands for safety.");
    context.log(`Block ${index + 1}: ${block.name}`);
    if (block.id === "forward") await context.safeForward(30, 0.5);
    else {
      if (block.id.startsWith("flip")) {
        const battery = await driver.invoke<number>("get_battery");
        if (battery < 50) throw new Error(`Flip needs at least 50% battery; current level is ${battery}%.`);
      }
      const result = await driver.invoke(block.command.method, ...(block.command.args ?? []));
      if (block.id === "battery") context.log(`Battery: ${result}%`);
      if (block.id === "front") context.log(`Front distance: ${result} cm`);
    }
    if (block.id === "takeoff") airborne = true;
    if (block.id === "land") airborne = false;
  };

  const executeNodes = async (nodes: Node[]): Promise<void> => {
    for (const node of nodes) {
      if (context.stopped()) return;
      if (node.type === "command") { await executeCommand(node.block, node.index); continue; }
      if (node.type === "if") {
        const distance = await driver.invoke<number>("get_front_range", "cm");
        const clear = distance > 80;
        context.log(`Condition: front distance ${Math.round(distance)} cm → ${String(clear)}`);
        await executeNodes(clear ? node.whenTrue : node.whenFalse);
        continue;
      }
      if (node.block.kind === "repeat") {
        for (let repeat = 0; repeat < 3 && !context.stopped(); repeat += 1) await executeNodes(node.body);
      } else {
        for (let repeat = 0; repeat < 5 && !context.stopped(); repeat += 1) {
          const distance = await driver.invoke<number>("get_front_range", "cm");
          context.log(`While check ${repeat + 1}: ${Math.round(distance)} cm ahead`);
          if (distance <= 80) break;
          await executeNodes(node.body);
        }
      }
    }
  };

  try {
    const [nodes] = parseBody(0, new Set());
    await executeNodes(nodes);
  } finally {
    if (airborne && !context.stopped()) {
      context.log("Sequence complete — landing automatically…");
      await driver.invoke("land");
    }
  }
}
