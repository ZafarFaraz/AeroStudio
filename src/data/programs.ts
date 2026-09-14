import type { DroneDriver } from "../drone/types";

export type ProgramLevel = "Basic" | "Simple" | "Advanced";
export type ProgramContext = {
  log(message: string): void;
  stopped(): boolean;
  safeForward(distanceCm: number, speed?: number): Promise<void>;
};

export type ProgramSpec = {
  name: string;
  description: string;
  icon: string;
  level: ProgramLevel;
  run(driver: DroneDriver, context: ProgramContext): Promise<void>;
};

async function flight(
  driver: DroneDriver,
  context: ProgramContext,
  body: () => Promise<void>,
): Promise<void> {
  let attempted = false;
  try {
    context.log("Taking off…");
    attempted = true;
    await driver.invoke("takeoff");
    if (!context.stopped()) await body();
  } finally {
    if (attempted && !context.stopped()) {
      context.log("Landing…");
      await driver.invoke("land");
    }
  }
}

const basic: ProgramSpec[] = [
  {
    name: "Battery Check",
    description: "Shows the drone battery level. The drone does not take off.",
    icon: "battery_check",
    level: "Basic",
    run: async (driver, { log }) => log(`Battery: ${await driver.invoke("get_battery")}%`),
  },
  {
    name: "Sensor Check",
    description: "Reads height and front distance sensors without taking off.",
    icon: "sensor_check",
    level: "Basic",
    run: async (driver, { log }) => {
      log(`Height: ${await driver.invoke("get_height", "cm")} cm`);
      log(`Front distance: ${await driver.invoke("get_front_range", "cm")} cm`);
    },
  },
  {
    name: "LED Colors",
    description: "Cycles red, green, blue, and white. The drone stays grounded.",
    icon: "led_colors",
    level: "Basic",
    run: async (driver, context) => {
      for (const [name, r, g, b] of [["Red", 255, 0, 0], ["Green", 0, 255, 0], ["Blue", 0, 0, 255], ["White", 255, 255, 255]] as const) {
        if (context.stopped()) return;
        context.log(name);
        await driver.invoke("set_drone_LED", r, g, b, 100);
        await driver.invoke("hover", 1);
      }
    },
  },
  {
    name: "Temperature Check",
    description: "Shows the drone temperature in Celsius without taking off.",
    icon: "temperature_check",
    level: "Basic",
    run: async (driver, { log }) => log(`Drone temperature: ${await driver.invoke("get_drone_temperature", "C")}°C`),
  },
  {
    name: "Orientation Check",
    description: "Reads the X, Y, and Z angles while the drone stays grounded.",
    icon: "orientation_check",
    level: "Basic",
    run: async (driver, { log }) => {
      log(`X angle: ${await driver.invoke("get_x_angle")}°`);
      log(`Y angle: ${await driver.invoke("get_y_angle")}°`);
      log(`Z angle: ${await driver.invoke("get_z_angle")}°`);
    },
  },
  {
    name: "Color Check",
    description: "Shows colours detected by both colour sensors. No flight.",
    icon: "color_check",
    level: "Basic",
    run: async (driver, { log }) => {
      log(`Front colour: ${await driver.invoke("get_front_color", "name")}`);
      log(`Bottom colour: ${await driver.invoke("get_back_color", "name")}`);
    },
  },
];

const simple: ProgramSpec[] = [
  {
    name: "Takeoff + Hover",
    description: "Takes off, hovers for 3 seconds, then lands.",
    icon: "hover", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      context.log("Hovering for 3 seconds…");
      await driver.invoke("hover", 3);
    }),
  },
  {
    name: "Forward + Back",
    description: "Takes off, flies forward 50 cm, returns 50 cm, and lands.",
    icon: "forward_back", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      context.log("Moving forward…");
      await context.safeForward(50, 0.5);
      if (!context.stopped()) {
        context.log("Moving back…");
        await driver.invoke("move_backward", 50, "cm", 0.5);
      }
    }),
  },
  {
    name: "Side to Side",
    description: "Takes off, moves left 40 cm, right 40 cm, and lands.",
    icon: "side_to_side", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      context.log("Moving left…"); await driver.invoke("move_left", 40, "cm", 0.5);
      if (!context.stopped()) { context.log("Moving right…"); await driver.invoke("move_right", 40, "cm", 0.5); }
    }),
  },
  {
    name: "Fly a Triangle",
    description: "Flies three 50 cm sides with 120° right turns, then lands.",
    icon: "triangle", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      for (let side = 1; side <= 3 && !context.stopped(); side += 1) {
        context.log(`Triangle side ${side}…`); await context.safeForward(50, 0.5);
        if (!context.stopped()) await driver.invoke("turn_right", 120);
      }
    }),
  },
  {
    name: "Zigzag Flight",
    description: "Flies a gentle four-leg zigzag, then lands.",
    icon: "zigzag", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      const turns = [45, -90, 90, -45];
      for (let index = 0; index < turns.length && !context.stopped(); index += 1) {
        context.log(`Zigzag leg ${index + 1}…`); await context.safeForward(35, 0.5);
        const turn = turns[index];
        await driver.invoke(turn > 0 ? "turn_right" : "turn_left", Math.abs(turn));
      }
    }),
  },
  {
    name: "Gentle Dance",
    description: "Performs small side moves and turns while changing LED colours.",
    icon: "gentle_dance", level: "Simple",
    run: (driver, context) => flight(driver, context, async () => {
      const moves = [["Blue left", [0, 80, 255], "move_left"], ["Pink right", [255, 20, 120], "move_right"], ["Green left", [20, 255, 80], "move_left"], ["Gold right", [255, 160, 0], "move_right"]] as const;
      for (const [label, color, method] of moves) {
        if (context.stopped()) return;
        context.log(label); await driver.invoke("set_drone_LED", ...color, 100);
        await driver.invoke(method, 25, "cm", 0.4); await driver.invoke("turn_right", 45);
      }
      await driver.invoke("set_drone_LED", 255, 255, 255, 100);
    }),
  },
];

const advanced: ProgramSpec[] = [
  {
    name: "Fly a Square", description: "Flies four 50 cm sides with right turns, then lands.", icon: "square", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => {
      for (let side = 1; side <= 4 && !context.stopped(); side += 1) {
        context.log(`Square side ${side}…`); await context.safeForward(50, 0.5); await driver.invoke("turn_right", 90);
      }
    }),
  },
  {
    name: "360° Turn", description: "Takes off, turns right 360 degrees, and lands.", icon: "full_turn", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => { context.log("Turning 360 degrees…"); await driver.invoke("turn_right", 360); }),
  },
  {
    name: "Backward Flip", description: "Takes off, performs one backward flip, then lands. Needs extra space.", icon: "flip", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => {
      const battery = await driver.invoke<number>("get_battery");
      if (battery < 50) throw new Error(`Flip needs at least 50% battery; current level is ${battery}%.`);
      context.log("Flipping backward…"); await driver.invoke("flip", "back"); await driver.invoke("hover", 2);
    }),
  },
  {
    name: "Figure Eight", description: "Traces two small opposite loops to form a figure eight.", icon: "figure_eight", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => {
      for (const [label, turn] of [["Right loop", "turn_right"], ["Left loop", "turn_left"]] as const) {
        context.log(label);
        for (let side = 0; side < 4 && !context.stopped(); side += 1) { await context.safeForward(35, 0.45); await driver.invoke(turn, 90); }
      }
    }),
  },
  {
    name: "Obstacle Scout", description: "Checks ahead, approaches open space or backs away from an obstacle.", icon: "obstacle_scout", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => {
      const distance = await driver.invoke<number>("get_front_range", "cm"); context.log(`Front distance: ${distance} cm`);
      if (distance > 100) { context.log("Path is clear. Moving forward…"); await context.safeForward(40, 0.35); }
      else { context.log("Obstacle nearby. Moving backward…"); await driver.invoke("move_backward", 30, "cm", 0.35); }
      if (!context.stopped()) await driver.invoke("turn_right", 180);
    }),
  },
  {
    name: "Rainbow Square", description: "Flies a colourful square, changing LED colour on every side.", icon: "rainbow_square", level: "Advanced",
    run: (driver, context) => flight(driver, context, async () => {
      const colors = [["Red", 255, 0, 0], ["Green", 0, 255, 0], ["Blue", 0, 80, 255], ["Purple", 170, 0, 255]] as const;
      for (let index = 0; index < colors.length && !context.stopped(); index += 1) {
        const [name, r, g, b] = colors[index]; context.log(`Side ${index + 1}: ${name}`);
        await driver.invoke("set_drone_LED", r, g, b, 100); await context.safeForward(45, 0.45); await driver.invoke("turn_right", 90);
      }
      await driver.invoke("set_drone_LED", 255, 255, 255, 100);
    }),
  },
];

export const programs: ProgramSpec[] = [...basic, ...simple, ...advanced];

export const programDescriptions: Record<ProgramLevel, string> = {
  Basic: "Grounded checks and lights — the safest place to begin.",
  Simple: "Short beginner flights with one easy movement.",
  Advanced: "Longer manoeuvres that need more clear flying space.",
};
