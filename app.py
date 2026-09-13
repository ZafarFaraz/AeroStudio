"""Tkinter user interface for running the CoDrone EDU example programs."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

from codrone_edu.drone import Drone
from codrone_edu.system import ModeFlight

from block_actions import BLOCK_ACTIONS, BLOCKS_BY_KIND, BlockAction
from block_program import (
    BlockProgramError,
    ExecutionResult,
    execute_program,
    parse_program,
    sequence_indents,
    validate_flight_safety,
)
from drone_runtime import (
    DroneConnectionError,
    connect_ready_drone,
    send_emergency_stop,
)
from programs import ADVANCED_PROGRAMS, BASIC_PROGRAMS, SIMPLE_PROGRAMS, Program
from safety import ObstacleDetected, SafetySensorError, protect


CLICKABLE_CURSOR = "pointinghand" if sys.platform == "darwin" else "hand2"
SHORTCUT_MODIFIER = "Command" if sys.platform == "darwin" else "Control"
SHORTCUT_LABEL = "⌘" if sys.platform == "darwin" else "Ctrl+"


class DarkButton(tk.Label):
    """A dark, keyboard-accessible button that macOS Aqua cannot recolour."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        command: Callable[[], object] | None = None,
        **options: object,
    ) -> None:
        self.command = command
        options.setdefault("takefocus", 1)
        options.setdefault("cursor", CLICKABLE_CURSOR)
        options.setdefault("relief", "flat")
        options.setdefault("highlightthickness", 1)
        options.setdefault("highlightcolor", "#35d2e8")
        super().__init__(parent, **options)
        self._resting_relief = str(self.cget("relief"))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Key-Return>", self._keyboard_invoke)
        self.bind("<Key-space>", self._keyboard_invoke)

    def _enabled(self) -> bool:
        return str(self.cget("state")) != "disabled"

    def _press(self, event: tk.Event) -> None:
        if self._enabled():
            self.focus_set()
            self.configure(relief="sunken")

    def _release(self, event: tk.Event) -> None:
        self.configure(relief=self._resting_relief)
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if inside:
            self.invoke()

    def _keyboard_invoke(self, event: tk.Event) -> str:
        self.invoke()
        return "break"

    def invoke(self) -> None:
        if self._enabled() and self.command is not None:
            self.command()


class ProgramCard(tk.Frame):
    """A full-card, keyboard-accessible action for a ready-made program."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        command: Callable[[], object],
        background: str,
        hover_background: str,
        pressed_background: str,
        disabled_background: str,
        border: str,
        focus_border: str,
        **options: object,
    ) -> None:
        self.command = command
        self.resting_background = background
        self.hover_background = hover_background
        self.pressed_background = pressed_background
        self.disabled_background = disabled_background
        self.border = border
        self.focus_border = focus_border
        self.enabled = False
        self.bound_widgets: list[tk.Widget] = []
        options.setdefault("bg", disabled_background)
        options.setdefault("takefocus", 1)
        options.setdefault("cursor", "arrow")
        options.setdefault("highlightthickness", 1)
        options.setdefault("highlightbackground", border)
        options.setdefault("highlightcolor", focus_border)
        super().__init__(parent, **options)
        self.register_widgets(self)

    def register_widgets(self, *widgets: tk.Widget) -> None:
        """Make every visible part of the card share one interaction target."""
        for widget in widgets:
            if widget not in self.bound_widgets:
                self.bound_widgets.append(widget)
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
            widget.bind("<ButtonPress-1>", self._press, add="+")
            widget.bind("<ButtonRelease-1>", self._release, add="+")
            widget.bind("<Key-Return>", self._keyboard_invoke, add="+")
            widget.bind("<Key-space>", self._keyboard_invoke, add="+")
        self._paint(self.resting_background if self.enabled else self.disabled_background)

    def set_state(self, state: str) -> None:
        self.enabled = state != "disabled"
        cursor = CLICKABLE_CURSOR if self.enabled else "arrow"
        for widget in self.bound_widgets:
            try:
                widget.configure(cursor=cursor)
            except tk.TclError:
                pass
        self._paint(self.resting_background if self.enabled else self.disabled_background)

    def _paint(self, color: str) -> None:
        for widget in self.bound_widgets:
            try:
                widget.configure(bg=color)
            except tk.TclError:
                pass

    def _enter(self, event: tk.Event) -> None:
        if self.enabled:
            self._paint(self.hover_background)

    def _leave(self, event: tk.Event) -> None:
        if self.enabled:
            self._paint(self.resting_background)

    def _press(self, event: tk.Event) -> None:
        if self.enabled:
            self.focus_set()
            self._paint(self.pressed_background)

    def _release(self, event: tk.Event) -> None:
        if not self.enabled:
            return
        pointer_x, pointer_y = self.winfo_pointerxy()
        inside = (
            self.winfo_rootx() <= pointer_x < self.winfo_rootx() + self.winfo_width()
            and self.winfo_rooty() <= pointer_y < self.winfo_rooty() + self.winfo_height()
        )
        self._paint(self.hover_background if inside else self.resting_background)
        if inside:
            self.command()

    def _keyboard_invoke(self, event: tk.Event) -> str:
        if self.enabled:
            self.command()
        return "break"


class AeroStudioApp:
    """A small, thread-safe flight-learning dashboard."""

    CONTROLLER_UNLOCK_CLICKS = 5
    BACKGROUND = "#061016"
    SIDEBAR = "#0b171d"
    PANEL = "#101b22"
    CARD = "#17242c"
    PROGRAM_CARD = "#1d4b56"
    PROGRAM_CARD_HOVER = "#286571"
    PROGRAM_CARD_PRESSED = "#173a43"
    PROGRAM_CARD_DISABLED = "#1a3b45"
    PROGRAM_CARD_BORDER = "#477783"
    BORDER = "#2d3d46"
    CONTROL = "#24343c"
    CONTROL_HOVER = "#304751"
    SELECTED = "#17383e"
    CONSOLE = "#040a0d"
    TEXT = "#f5f8f9"
    MUTED_TEXT = "#b7c4c9"
    TERTIARY_TEXT = "#91a3aa"
    BLUE = "#087f8c"
    BLUE_HOVER = "#0a98a7"
    ACCENT = "#35d2e8"
    RED = "#ff453a"
    RED_HOVER = "#ff6961"
    GREEN = "#30d158"
    WARNING = "#ffd60a"
    WARNING_SURFACE = "#332b12"
    INFO_SURFACE = "#102d35"
    SUCCESS_SURFACE = "#12301e"
    ERROR_SURFACE = "#35181d"
    DISABLED_TEXT = "#a8adb7"
    FONT = "SF Pro Text"
    DISPLAY_FONT = FONT
    MONO_FONT = "SF Mono"
    ICON_PATH = Path(__file__).resolve().parent / "assets" / "codrone_studio_icon.png"
    TOOLBAR_ICON_PATH = (
        Path(__file__).resolve().parent / "assets" / "codrone_studio_icon_96.png"
    )
    PROGRAM_ICON_DIR = Path(__file__).resolve().parent / "assets" / "program_icons"

    BLOCK_CATEGORY_COLORS = {
        "Flight": "#64a8ff",
        "Movement": "#b99cff",
        "Lights": "#ff8fab",
        "Utility": "#ffbf69",
        "Tricks": "#fb923c",
        "Logic": "#5eead4",
    }
    BLOCK_CATEGORY_SYMBOLS = {
        "Flight": "↥",
        "Movement": "↔",
        "Lights": "◆",
        "Utility": "◎",
        "Tricks": "★",
        "Logic": "◇",
    }

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AeroStudio")
        self.root.geometry("1180x820")
        self.root.minsize(820, 650)
        self.root.configure(bg=self.BACKGROUND)
        self.app_icon: tk.PhotoImage | None = None
        self.toolbar_icon: tk.PhotoImage | None = None
        self._load_app_icon()

        self.drone: Drone | None = None
        self.connected = False
        self.busy = False
        self.stop_requested = threading.Event()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.program_buttons: list[ProgramCard] = []
        self.program_images: dict[str, tk.PhotoImage] = {}
        self.controller_buttons: list[DarkButton] = []
        self.block_edit_buttons: list[DarkButton] = []
        self.block_palette_buttons: list[DarkButton] = []
        self.block_sequence_buttons: list[DarkButton] = []
        self.block_sequence: list[BlockAction] = []
        self.block_category = "Flight"
        self.current_tab = "Basic"
        self.controller_unlocked = False
        self.brand_click_count = 0
        self.activity_history: list[tuple[str, str]] = []
        self.tab_buttons: dict[str, DarkButton] = {}
        self.tab_frames: dict[str, tk.Frame] = {}

        self._build_ui()
        self._refresh_controls()
        self.root.after(100, self._process_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_app_icon(self) -> None:
        """Load the project icon for the Dock/window and a compact toolbar mark."""
        if not self.ICON_PATH.exists():
            return
        try:
            self.app_icon = tk.PhotoImage(file=str(self.ICON_PATH))
            self.root.iconphoto(True, self.app_icon)
            toolbar_source = tk.PhotoImage(file=str(self.TOOLBAR_ICON_PATH))
            self.toolbar_icon = toolbar_source.subsample(2, 2)
        except tk.TclError:
            self.app_icon = None
            self.toolbar_icon = None

    def _program_image(self, icon_name: str) -> tk.PhotoImage | None:
        """Load and retain one descriptive PNG for a program card."""
        if icon_name in self.program_images:
            return self.program_images[icon_name]
        path = self.PROGRAM_ICON_DIR / f"{icon_name}.png"
        if not path.exists():
            return None
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None
        self.program_images[icon_name] = image
        return image

    def _build_ui(self) -> None:
        toolbar = tk.Frame(self.root, bg=self.BACKGROUND, padx=22, pady=14)
        toolbar.pack(fill="x")
        self.toolbar = toolbar

        brand = tk.Frame(toolbar, bg=self.BACKGROUND)
        brand.pack(side="left")
        if self.toolbar_icon is not None:
            tk.Label(
                brand,
                image=self.toolbar_icon,
                bg=self.BACKGROUND,
                bd=0,
            ).pack(side="left", padx=(0, 11))
        identity = tk.Frame(brand, bg=self.BACKGROUND)
        identity.pack(side="left")
        self.brand_title_label = tk.Label(
            identity,
            text="AeroStudio",
            font=(self.DISPLAY_FONT, 22, "bold"),
            bg=self.BACKGROUND,
            fg=self.TEXT,
            takefocus=1,
            highlightthickness=1,
            highlightbackground=self.BACKGROUND,
            highlightcolor=self.ACCENT,
        )
        self.brand_title_label.pack(anchor="w")
        self.brand_title_label.bind("<Button-1>", self._brand_unlock_click)
        self.brand_title_label.bind("<Key-Return>", self._brand_unlock_key)
        self.brand_title_label.bind("<Key-space>", self._brand_unlock_key)
        self.brand_subtitle_label = tk.Label(
            identity,
            text="Learn, build, and fly with CoDrone EDU",
            font=(self.FONT, 12),
            bg=self.BACKGROUND,
            fg=self.MUTED_TEXT,
        )
        self.brand_subtitle_label.pack(anchor="w", pady=(2, 0))

        self.emergency_button = DarkButton(
            toolbar,
            text="■  Stop now",
            command=self._emergency_stop,
            bg=self.RED,
            fg="#ffffff",
            activebackground=self.RED_HOVER,
            activeforeground="#ffffff",
            disabledforeground="#d3a3a0",
            highlightbackground=self.BACKGROUND,
            font=(self.FONT, 13, "bold"),
            padx=14,
            pady=7,
        )
        self.emergency_button.pack(side="right", padx=(10, 0))
        self._add_hover(self.emergency_button, self.RED, self.RED_HOVER)

        self.connection_button = DarkButton(
            toolbar,
            text="Connect",
            command=self._toggle_connection,
            font=(self.FONT, 13, "bold"),
            bg=self.BLUE,
            fg="#ffffff",
            activebackground=self.BLUE_HOVER,
            activeforeground="#ffffff",
            disabledforeground="#c7d8f7",
            highlightbackground=self.BACKGROUND,
            padx=18,
            pady=7,
        )
        self.connection_button.pack(side="right")
        self._add_hover(self.connection_button, self.BLUE, self.BLUE_HOVER)

        status = tk.Frame(
            toolbar,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            padx=12,
            pady=7,
        )
        status.pack(side="right", padx=(0, 12))
        self.status_dot = tk.Label(
            status,
            text="●",
            bg=self.CARD,
            fg=self.RED,
            font=(self.FONT, 12, "bold"),
        )
        self.status_dot.pack(side="left", padx=(0, 7))
        self.status_label = tk.Label(
            status,
            text="Disconnected",
            fg=self.TEXT,
            bg=self.CARD,
            font=(self.FONT, 12, "bold"),
        )
        self.status_label.pack(side="left")

        self.notice_frame = tk.Frame(
            self.root,
            bg="#35181d",
            highlightbackground="#7f3038",
            highlightthickness=1,
            padx=13,
            pady=9,
        )
        self.notice_icon = tk.Label(
            self.notice_frame,
            text="⚠",
            bg="#35181d",
            fg="#ff8a84",
            font=(self.FONT, 13, "bold"),
        )
        self.notice_icon.pack(side="left", padx=(0, 9))
        self.notice_label = tk.Label(
            self.notice_frame,
            text="",
            bg="#35181d",
            fg=self.TEXT,
            font=(self.FONT, 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self.notice_label.pack(side="left", fill="x", expand=True)
        DarkButton(
            self.notice_frame,
            text="Dismiss",
            command=self._hide_notice,
            bg="#4b2228",
            fg=self.TEXT,
            highlightbackground="#35181d",
            font=(self.FONT, 11, "bold"),
            padx=10,
            pady=4,
        ).pack(side="right", padx=(10, 0))

        activity_frame = tk.Frame(
            self.root,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        activity_frame.pack(side="bottom", fill="x", padx=18, pady=(10, 16))
        activity_header = tk.Frame(activity_frame, bg=self.PANEL)
        activity_header.pack(fill="x", pady=(0, 8))
        tk.Label(
            activity_header,
            text="Flight updates",
            bg=self.PANEL,
            fg=self.TEXT,
            font=(self.FONT, 13, "bold"),
        ).pack(side="left")
        tk.Label(
            activity_header,
            text="●  Forward obstacle braking on",
            bg=self.PANEL,
            fg=self.GREEN,
            font=(self.FONT, 11, "bold"),
        ).pack(side="left", padx=(10, 0))
        DarkButton(
            activity_header,
            text="Clear",
            command=self._clear_log,
            bg=self.CARD,
            fg=self.TEXT,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            highlightbackground=self.PANEL,
            font=(self.FONT, 11),
            padx=12,
            pady=3,
        ).pack(side="right")

        self.activity_latest = tk.Frame(
            activity_frame,
            bg=self.INFO_SURFACE,
            padx=13,
            pady=9,
            highlightbackground="#28505b",
            highlightthickness=1,
        )
        self.activity_latest.pack(fill="x")
        self.activity_icon = tk.Label(
            self.activity_latest,
            text="●",
            bg=self.INFO_SURFACE,
            fg=self.ACCENT,
            font=(self.FONT, 14, "bold"),
            width=2,
        )
        self.activity_icon.pack(side="left", padx=(0, 8))
        self.activity_message = tk.Label(
            self.activity_latest,
            text="Ready to begin",
            bg=self.INFO_SURFACE,
            fg=self.TEXT,
            font=(self.FONT, 12, "bold"),
            anchor="w",
            justify="left",
        )
        self.activity_message.pack(side="left", fill="x", expand=True)

        self.activity_earlier = tk.Label(
            activity_frame,
            text="",
            bg=self.PANEL,
            fg=self.MUTED_TEXT,
            font=(self.FONT, 10),
            anchor="w",
            justify="left",
        )
        self.activity_earlier.pack(fill="x", padx=4, pady=(7, 0))

        workspace = tk.Frame(self.root, bg=self.BACKGROUND)
        workspace.pack(fill="both", expand=True, padx=18)

        sidebar = tk.Frame(
            workspace,
            bg=self.SIDEBAR,
            width=205,
            padx=10,
            pady=14,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        self.sidebar = sidebar
        tk.Label(
            sidebar,
            text="Explore",
            bg=self.SIDEBAR,
            fg=self.MUTED_TEXT,
            font=(self.FONT, 11, "bold"),
        ).pack(anchor="w", padx=10, pady=(0, 8))

        navigation = ("Basic", "Simple", "Advanced", "Block Builder")
        for shortcut, tab_name in enumerate(navigation, start=1):
            self._create_navigation_button(tab_name, shortcut=shortcut)

        tk.Label(
            sidebar,
            text="Tip\nStart with Basic checks before your first flight.",
            justify="left",
            wraplength=165,
            bg=self.SIDEBAR,
            fg=self.TERTIARY_TEXT,
            font=(self.FONT, 11),
        ).pack(side="bottom", anchor="w", padx=10, pady=6)

        tab_container = tk.Frame(
            workspace,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        tab_container.pack(side="left", fill="both", expand=True)
        tab_container.grid_rowconfigure(0, weight=1)
        tab_container.grid_columnconfigure(0, weight=1)

        categories = (
            (
                "Basic",
                "Grounded checks and lights — the safest place to begin.",
                BASIC_PROGRAMS,
            ),
            (
                "Simple",
                "Short beginner flights with one easy movement.",
                SIMPLE_PROGRAMS,
            ),
            (
                "Advanced",
                "Longer manoeuvres that need more clear flying space.",
                ADVANCED_PROGRAMS,
            ),
        )
        for name, description, programs in categories:
            frame = self._create_program_tab(tab_container, name, description, programs)
            self.tab_frames[name] = frame

        self.tab_frames["Controller"] = self._create_controller_tab(tab_container)
        self.tab_frames["Block Builder"] = self._create_block_tab(tab_container)
        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")
        self._show_tab("Basic")
        self.root.bind("<Configure>", self._adapt_shell, add="+")

    def _create_navigation_button(
        self,
        tab_name: str,
        *,
        shortcut: int | None = None,
        before: tk.Widget | None = None,
    ) -> DarkButton:
        """Add one sidebar destination with the app's standard interaction style."""
        label = "Controller  ·  Advanced" if tab_name == "Controller" else tab_name
        tab_button = DarkButton(
            self.sidebar,
            text=label,
            command=lambda selected=tab_name: self._show_tab(selected),
            font=(self.FONT, 12, "bold"),
            bg=self.SIDEBAR,
            fg=self.MUTED_TEXT,
            activebackground=self.CARD,
            activeforeground=self.TEXT,
            highlightbackground=self.SIDEBAR,
            relief="flat",
            anchor="w",
            padx=10,
            pady=9,
        )
        if before is None:
            tab_button.pack(fill="x", pady=2)
        else:
            tab_button.pack(fill="x", pady=2, before=before)
        self.tab_buttons[tab_name] = tab_button
        if shortcut is not None:
            self.root.bind(
                f"<{SHORTCUT_MODIFIER}-Key-{shortcut}>",
                lambda event, selected=tab_name: self._show_tab(selected),
            )
        return tab_button

    def _brand_unlock_click(self, event: tk.Event) -> None:
        self.brand_title_label.focus_set()
        self._count_brand_unlock()

    def _brand_unlock_key(self, event: tk.Event) -> str:
        self._count_brand_unlock()
        return "break"

    def _count_brand_unlock(self) -> None:
        """Reveal teacher-oriented controls after five deliberate title presses."""
        if self.controller_unlocked:
            return
        self.brand_click_count += 1
        if self.brand_click_count >= self.CONTROLLER_UNLOCK_CLICKS:
            self._unlock_controller()

    def _unlock_controller(self) -> None:
        if self.controller_unlocked:
            return
        self.controller_unlocked = True
        self.brand_click_count = 0
        before = self.tab_buttons.get("Block Builder")
        self._create_navigation_button("Controller", shortcut=5, before=before)
        self._write_log("Advanced controller unlocked.", "success")

    def _adapt_shell(self, event: tk.Event) -> None:
        """Keep the app chrome comfortable when the window becomes compact."""
        if event.widget is not self.root:
            return
        compact = event.width < 1000
        self.sidebar.configure(width=170 if compact else 205)
        self.toolbar.configure(padx=14 if compact else 22)
        self.brand_title_label.configure(
            font=(self.DISPLAY_FONT, 19 if compact else 22, "bold")
        )
        self.brand_subtitle_label.configure(font=(self.FONT, 11 if compact else 12))
        self.notice_label.configure(wraplength=max(420, event.width - 170))
        self.activity_message.configure(wraplength=max(420, event.width - 170))
        self.activity_earlier.configure(wraplength=max(420, event.width - 70))

    @staticmethod
    def _program_column_count(width: int) -> int:
        """Choose columns from available content width, not screen width."""
        if width >= 1200:
            return 4
        if width >= 760:
            return 3
        if width >= 520:
            return 2
        return 1

    def _create_program_tab(
        self,
        parent: tk.Frame,
        title: str,
        description: str,
        programs: tuple[Program, ...],
    ) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.PANEL, padx=18, pady=16)
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            frame,
            text=title,
            bg=self.PANEL,
            fg=self.TEXT,
            anchor="w",
            font=(self.DISPLAY_FONT, 24, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=4)
        heading = tk.Label(
            frame,
            text=description,
            bg=self.PANEL,
            fg=self.MUTED_TEXT,
            anchor="w",
            justify="left",
            font=(self.FONT, 13),
        )
        heading.grid(row=1, column=0, sticky="ew", padx=4, pady=(3, 12))

        program_grid = tk.Frame(frame, bg=self.PANEL)
        program_grid.grid(row=2, column=0, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)
        blocks: list[ProgramCard] = []
        title_labels: list[tk.Label] = []
        description_labels: list[tk.Label] = []

        for offset, program in enumerate(programs):
            block = ProgramCard(
                program_grid,
                command=lambda selected=program: self._start_program(selected),
                background=self.PROGRAM_CARD,
                hover_background=self.PROGRAM_CARD_HOVER,
                pressed_background=self.PROGRAM_CARD_PRESSED,
                disabled_background=self.PROGRAM_CARD_DISABLED,
                border=self.PROGRAM_CARD_BORDER,
                focus_border=self.ACCENT,
                padx=16,
                pady=14,
            )
            block.grid_columnconfigure(1, weight=1)
            block.grid_rowconfigure(1, weight=1)
            program_image = self._program_image(program.icon_name)
            icon_label = tk.Label(
                block,
                image=program_image,
                bg=self.PROGRAM_CARD_DISABLED,
                bd=0,
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 11))
            title_label = tk.Label(
                block,
                text=program.name,
                bg=self.PROGRAM_CARD_DISABLED,
                fg=self.TEXT,
                font=(self.FONT, 15, "bold"),
                anchor="w",
                justify="left",
            )
            title_label.grid(row=0, column=1, sticky="ew")
            chevron_label = tk.Label(
                block,
                text="›",
                bg=self.PROGRAM_CARD_DISABLED,
                fg=self.ACCENT,
                font=(self.FONT, 18, "bold"),
                anchor="e",
            )
            chevron_label.grid(row=0, column=2, sticky="ne", padx=(8, 0))
            description_label = tk.Label(
                block,
                text=program.description,
                bg=self.PROGRAM_CARD_DISABLED,
                fg=self.MUTED_TEXT,
                font=(self.FONT, 12),
                justify="left",
                anchor="nw",
                wraplength=350,
            )
            description_label.grid(
                row=1, column=0, columnspan=3, sticky="nsew", pady=(10, 0)
            )
            block.register_widgets(
                icon_label, title_label, chevron_label, description_label
            )
            self.program_buttons.append(block)
            blocks.append(block)
            title_labels.append(title_label)
            description_labels.append(description_label)

        layout_state = {"columns": 0, "width": 0, "job": None}

        def reflow() -> None:
            layout_state["job"] = None
            width = max(program_grid.winfo_width(), 1)
            columns = self._program_column_count(width)
            if columns == layout_state["columns"] and abs(width - layout_state["width"]) < 12:
                return
            layout_state["columns"] = columns
            layout_state["width"] = width

            for index in range(4):
                program_grid.grid_columnconfigure(index, weight=0, uniform="")
            for index in range(len(blocks)):
                program_grid.grid_rowconfigure(index, weight=0, uniform="")
            for index in range(columns):
                program_grid.grid_columnconfigure(
                    index, weight=1, uniform="program_block"
                )
            rows = (len(blocks) + columns - 1) // columns
            for index in range(rows):
                program_grid.grid_rowconfigure(index, weight=1, uniform="program_block")

            card_width = max(180, width // columns)
            if columns == 4:
                title_size, body_size, inset = 13, 11, 11
            elif columns == 3:
                title_size, body_size, inset = 14, 11, 13
            else:
                title_size, body_size, inset = 15, 12, 16

            for index, block in enumerate(blocks):
                column = index % columns
                block.grid(
                    row=index // columns,
                    column=column,
                    sticky="nsew",
                    padx=(4, 4),
                    pady=5,
                )
                block.configure(padx=inset, pady=max(11, inset - 2))
                title_labels[index].configure(
                    font=(self.FONT, title_size, "bold"),
                    wraplength=max(110, card_width - (inset * 2) - 96),
                )
                description_labels[index].configure(
                    font=(self.FONT, body_size),
                    wraplength=max(150, card_width - (inset * 2) - 12),
                )
            heading.configure(wraplength=max(280, width - 8))

        def schedule_reflow(event: tk.Event | None = None) -> None:
            if layout_state["job"] is not None:
                program_grid.after_cancel(layout_state["job"])
            layout_state["job"] = program_grid.after_idle(reflow)

        program_grid.bind("<Configure>", schedule_reflow)
        program_grid.after_idle(reflow)
        return frame

    def _create_controller_tab(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.PANEL, padx=20, pady=16)
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=2)
        frame.grid_rowconfigure(2, weight=1)

        tk.Label(
            frame,
            text="Controller",
            bg=self.PANEL,
            fg=self.TEXT,
            anchor="w",
            font=(self.DISPLAY_FONT, 24, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        controller_description = tk.Label(
            frame,
            text=(
                "Manual controls — each movement travels 30 cm and each turn rotates 90°. "
                "Forward obstacle braking is active; side and rear paths are not visible "
                "to the drone's sensor."
            ),
            bg=self.PANEL,
            fg=self.MUTED_TEXT,
            anchor="w",
            justify="left",
            font=(self.FONT, 13),
        )
        controller_description.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(3, 12)
        )

        direction_pad = tk.LabelFrame(
            frame,
            text="Direction pad",
            bg=self.PANEL,
            fg=self.TEXT,
            font=(self.FONT, 13, "bold"),
            padx=16,
            pady=16,
        )
        direction_pad.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        for index in range(3):
            direction_pad.grid_columnconfigure(index, weight=1, uniform="direction")
            direction_pad.grid_rowconfigure(index, weight=1, uniform="direction")

        self._controller_button(
            direction_pad, "▲\nForward", 0, 1,
            lambda drone: drone.move_forward(30, "cm", 0.5),
        )
        self._controller_button(
            direction_pad, "◀\nLeft", 1, 0,
            lambda drone: drone.move_left(30, "cm", 0.5),
        )
        self._controller_button(
            direction_pad, "Hover", 1, 1,
            lambda drone: drone.hover(1),
        )
        self._controller_button(
            direction_pad, "▶\nRight", 1, 2,
            lambda drone: drone.move_right(30, "cm", 0.5),
        )
        self._controller_button(
            direction_pad, "▼\nBackward", 2, 1,
            lambda drone: drone.move_backward(30, "cm", 0.5),
        )

        flight_pad = tk.LabelFrame(
            frame,
            text="Flight controls",
            bg=self.PANEL,
            fg=self.TEXT,
            font=(self.FONT, 13, "bold"),
            padx=12,
            pady=12,
        )
        flight_pad.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        for column in range(2):
            flight_pad.grid_columnconfigure(column, weight=1, uniform="flight")
        for row in range(3):
            flight_pad.grid_rowconfigure(row, weight=1, uniform="flight")

        self._controller_button(flight_pad, "Take off", 0, 0, lambda drone: drone.takeoff())
        self._controller_button(flight_pad, "Land", 0, 1, lambda drone: drone.land())
        self._controller_button(
            flight_pad, "↺ Turn left", 1, 0, lambda drone: drone.turn_left(90)
        )
        self._controller_button(
            flight_pad, "Turn right ↻", 1, 1, lambda drone: drone.turn_right(90)
        )
        self._controller_button(
            flight_pad, "Up 30 cm", 2, 0,
            lambda drone: drone.move_distance(0, 0, 0.3, 0.5),
        )
        self._controller_button(
            flight_pad, "Down 30 cm", 2, 1,
            lambda drone: drone.move_distance(0, 0, -0.3, 0.5),
        )

        controller_layout = {"stacked": None}

        def adapt_controller(event: tk.Event) -> None:
            stacked = event.width < 700
            controller_description.configure(wraplength=max(300, event.width - 40))
            if stacked == controller_layout["stacked"]:
                return
            controller_layout["stacked"] = stacked
            if stacked:
                frame.grid_columnconfigure(0, weight=1)
                frame.grid_columnconfigure(1, weight=0)
                frame.grid_rowconfigure(2, weight=1)
                frame.grid_rowconfigure(3, weight=1)
                direction_pad.grid_configure(
                    row=2, column=0, columnspan=2, padx=0, pady=(0, 8)
                )
                flight_pad.grid_configure(
                    row=3, column=0, columnspan=2, padx=0, pady=(8, 0)
                )
            else:
                frame.grid_columnconfigure(0, weight=3)
                frame.grid_columnconfigure(1, weight=2)
                frame.grid_rowconfigure(2, weight=1)
                frame.grid_rowconfigure(3, weight=0)
                direction_pad.grid_configure(
                    row=2, column=0, columnspan=1, padx=(0, 8), pady=0
                )
                flight_pad.grid_configure(
                    row=2, column=1, columnspan=1, padx=(8, 0), pady=0
                )

        frame.bind("<Configure>", adapt_controller)
        return frame

    def _create_block_tab(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.PANEL, padx=20, pady=16)
        frame.grid_columnconfigure(0, weight=5)
        frame.grid_columnconfigure(1, weight=4)
        frame.grid_rowconfigure(2, weight=1)

        tk.Label(
            frame,
            text="Block Builder",
            bg=self.PANEL,
            fg=self.TEXT,
            anchor="w",
            font=(self.DISPLAY_FONT, 24, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        builder_description = tk.Label(
            frame,
            text=(
                "Build with actions, if/else decisions, and safe for and while loops. "
                "Select a sequence block to insert after it; control blocks add their "
                "matching end automatically."
            ),
            bg=self.PANEL,
            fg=self.MUTED_TEXT,
            anchor="w",
            justify="left",
            font=(self.FONT, 13),
        )
        builder_description.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(3, 14)
        )

        palette = tk.Frame(
            frame,
            bg=self.PANEL,
        )
        palette.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        palette.grid_columnconfigure(0, weight=1)
        palette.grid_rowconfigure(2, weight=1)

        tk.Label(
            palette,
            text="Command palette",
            bg=self.PANEL,
            fg=self.TEXT,
            font=(self.FONT, 13, "bold"),
        ).grid(row=0, column=0, sticky="w")

        category_bar = tk.Frame(palette, bg=self.PANEL)
        category_bar.grid(row=1, column=0, sticky="ew", pady=(9, 10))
        self.block_category_buttons: dict[str, DarkButton] = {}
        categories = (
            ("Flight", "Flight"),
            ("Movement", "Movement"),
            ("Lights", "Lights"),
            ("Utility", "Sensors & timing"),
            ("Tricks", "Tricks & paths"),
            ("Logic", "Logic & loops"),
        )
        for index, (category, category_label) in enumerate(categories):
            button = DarkButton(
                category_bar,
                text=category_label,
                command=lambda selected=category: self._select_block_category(selected),
                bg=self.CARD,
                fg=self.MUTED_TEXT,
                disabledforeground=self.DISABLED_TEXT,
                highlightbackground=self.PANEL,
                font=(self.FONT, 11, "bold"),
                padx=11,
                pady=6,
            )
            button.grid(
                row=index // 3,
                column=index % 3,
                sticky="ew",
                padx=(0, 5),
                pady=(0, 5),
            )
            category_bar.grid_columnconfigure(index % 3, weight=1, uniform="category")
            self.block_category_buttons[category] = button
            self.block_edit_buttons.append(button)

        self.block_palette_frame = tk.Frame(
            palette,
            bg=self.BORDER,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        self.block_palette_frame.grid(row=2, column=0, sticky="nsew")
        self._render_block_palette()

        stack = tk.Frame(
            frame,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            padx=12,
            pady=12,
        )
        stack.grid(row=2, column=1, sticky="nsew", padx=(10, 0))
        stack.grid_rowconfigure(3, weight=1)
        stack.grid_columnconfigure(0, weight=1)

        sequence_header = tk.Frame(stack, bg=self.CARD)
        sequence_header.grid(row=0, column=0, sticky="ew")
        sequence_header.grid_columnconfigure(0, weight=1)
        tk.Label(
            sequence_header,
            text="Flight sequence",
            bg=self.CARD,
            fg=self.TEXT,
            font=(self.FONT, 13, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.block_count_label = tk.Label(
            sequence_header,
            text="0 blocks",
            bg=self.CARD,
            fg=self.TERTIARY_TEXT,
            font=(self.FONT, 11),
        )
        self.block_count_label.grid(row=0, column=1, sticky="e")

        tk.Label(
            stack,
            text=(
                "Loops are bounded and forward paths are checked for obstacles. "
                "The drone lands automatically if a valid sequence ends in the air."
            ),
            bg=self.CARD,
            fg=self.MUTED_TEXT,
            font=(self.FONT, 11),
            anchor="w",
            wraplength=380,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 10))

        self.block_validation_label = tk.Label(
            stack,
            text="Add a command to begin",
            bg=self.CARD,
            fg=self.TERTIARY_TEXT,
            font=(self.FONT, 11, "bold"),
            anchor="w",
            justify="left",
            wraplength=400,
        )
        self.block_validation_label.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        sequence_surface = tk.Frame(stack, bg=self.CONSOLE)
        sequence_surface.grid(row=3, column=0, sticky="nsew")
        sequence_surface.grid_rowconfigure(0, weight=1)
        sequence_surface.grid_columnconfigure(0, weight=1)

        self.block_listbox = tk.Listbox(
            sequence_surface,
            selectmode=tk.SINGLE,
            bg=self.CONSOLE,
            fg=self.TEXT,
            selectbackground=self.BLUE,
            selectforeground="white",
            highlightbackground=self.BORDER,
            highlightcolor=self.BLUE,
            relief="flat",
            font=(self.MONO_FONT, 11, "bold"),
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
        )
        self.block_listbox.grid(row=0, column=0, sticky="nsew")
        self.block_listbox.bind("<Delete>", lambda event: self._remove_selected_block())
        self.block_listbox.bind(
            f"<{SHORTCUT_MODIFIER}-Up>", lambda event: self._move_selected_block(-1)
        )
        self.block_listbox.bind(
            f"<{SHORTCUT_MODIFIER}-Down>", lambda event: self._move_selected_block(1)
        )

        self.block_empty_label = tk.Label(
            sequence_surface,
            text="Your sequence is empty\nChoose a command on the left to begin.",
            bg=self.CONSOLE,
            fg=self.TERTIARY_TEXT,
            font=(self.FONT, 12),
            justify="center",
        )
        self.block_empty_label.grid(row=0, column=0, sticky="nsew")

        controls = (
            ("Remove", self._remove_selected_block),
            (f"Move up  {SHORTCUT_LABEL}↑", lambda: self._move_selected_block(-1)),
            (f"Move down  {SHORTCUT_LABEL}↓", lambda: self._move_selected_block(1)),
            ("Clear", self._clear_blocks),
        )
        control_bar = tk.Frame(stack, bg=self.CARD)
        control_bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        for column, (label, command) in enumerate(controls):
            button = DarkButton(
                control_bar,
                text=label,
                command=command,
                bg=self.CONTROL,
                fg=self.TEXT,
                activebackground=self.CONTROL_HOVER,
                activeforeground=self.TEXT,
                disabledforeground=self.DISABLED_TEXT,
                highlightbackground=self.CARD,
                font=(self.FONT, 11),
                padx=9,
                pady=5,
            )
            button.pack(side="left", padx=(0, 5))
            self.block_sequence_buttons.append(button)

        self.block_run_button = DarkButton(
            stack,
            text="▶  Run sequence",
            command=self._run_block_program,
            bg=self.BLUE,
            fg="#ffffff",
            activebackground=self.BLUE_HOVER,
            activeforeground="#ffffff",
            disabledforeground="#9abfe8",
            highlightbackground=self.CARD,
            font=(self.FONT, 13, "bold"),
            pady=8,
        )
        self.block_run_button.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self._add_hover(self.block_run_button, self.BLUE, self.BLUE_HOVER)
        self.root.bind(
            f"<{SHORTCUT_MODIFIER}-Return>",
            lambda event: self._run_block_program(),
        )
        self._refresh_block_list()

        builder_layout = {"stacked": None}

        def adapt_builder(event: tk.Event) -> None:
            stacked = event.width < 820
            builder_description.configure(wraplength=max(300, event.width - 40))
            if stacked == builder_layout["stacked"]:
                return
            builder_layout["stacked"] = stacked
            if stacked:
                frame.grid_columnconfigure(0, weight=1)
                frame.grid_columnconfigure(1, weight=0)
                frame.grid_rowconfigure(2, weight=1)
                frame.grid_rowconfigure(3, weight=1)
                palette.grid_configure(
                    row=2, column=0, columnspan=2, padx=0, pady=(0, 8)
                )
                stack.grid_configure(
                    row=3, column=0, columnspan=2, padx=0, pady=(8, 0)
                )
            else:
                frame.grid_columnconfigure(0, weight=5)
                frame.grid_columnconfigure(1, weight=4)
                frame.grid_rowconfigure(2, weight=1)
                frame.grid_rowconfigure(3, weight=0)
                palette.grid_configure(
                    row=2, column=0, columnspan=1, padx=(0, 10), pady=0
                )
                stack.grid_configure(
                    row=2, column=1, columnspan=1, padx=(10, 0), pady=0
                )

        frame.bind("<Configure>", adapt_builder)
        return frame

    def _select_block_category(self, category: str) -> None:
        self.block_category = category
        self._render_block_palette()

    def _render_block_palette(self) -> None:
        for button in self.block_palette_buttons:
            button.destroy()
        self.block_palette_buttons.clear()
        for child in self.block_palette_frame.winfo_children():
            child.destroy()

        for category, button in self.block_category_buttons.items():
            selected = category == self.block_category
            button.configure(
                bg=self.SELECTED if selected else self.CARD,
                fg=self.TEXT if selected else self.MUTED_TEXT,
            )

        blocks = [block for block in BLOCK_ACTIONS if block.category == self.block_category]
        for column in range(2):
            self.block_palette_frame.grid_columnconfigure(column, weight=1, uniform="palette")
        for index, block in enumerate(blocks):
            row = tk.Frame(
                self.block_palette_frame,
                bg=self.CARD,
                padx=12,
                pady=10,
            )
            row.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0, 1) if index % 2 == 0 else 0,
                pady=(0, 1),
            )
            row.grid_columnconfigure(1, weight=1)
            color = self.BLOCK_CATEGORY_COLORS[block.category]
            symbol = self.BLOCK_CATEGORY_SYMBOLS[block.category]
            tk.Label(
                row,
                text=symbol,
                bg=self.CARD,
                fg=color,
                font=(self.FONT, 15, "bold"),
                width=2,
            ).grid(row=0, column=0, sticky="w", padx=(0, 6))
            label_group = tk.Frame(row, bg=self.CARD)
            label_group.grid(row=0, column=1, sticky="ew")
            tk.Label(
                label_group,
                text=block.name,
                bg=self.CARD,
                fg=self.TEXT,
                font=(self.FONT, 12, "bold"),
                anchor="w",
            ).pack(anchor="w")
            if block.python_code:
                tk.Label(
                    label_group,
                    text=f"Python: {block.python_code}",
                    bg=self.CARD,
                    fg=self.TERTIARY_TEXT,
                    font=(self.MONO_FONT, 9),
                    anchor="w",
                ).pack(anchor="w", pady=(3, 0))
            add_button = DarkButton(
                row,
                text="Add  +",
                command=lambda selected=block: self._add_block(selected),
                bg=self.CONTROL,
                fg=self.TEXT,
                activebackground=self.BLUE,
                activeforeground="#ffffff",
                disabledforeground=self.DISABLED_TEXT,
                highlightbackground=self.CARD,
                font=(self.FONT, 11, "bold"),
                padx=10,
                pady=5,
            )
            add_button.grid(row=0, column=2, sticky="e", padx=(8, 0))
            self._add_hover(add_button, self.CONTROL, self.BLUE)
            self.block_palette_buttons.append(add_button)

    def _add_block(self, block: BlockAction) -> None:
        selection = self.block_listbox.curselection()
        insertion = selection[0] + 1 if selection else len(self.block_sequence)

        matching_end = {
            "if": "end_if",
            "repeat": "end_repeat",
            "while": "end_while",
        }
        if block.kind in matching_end:
            self.block_sequence[insertion:insertion] = [
                block,
                BLOCKS_BY_KIND[matching_end[block.kind]],
            ]
        else:
            self.block_sequence.insert(insertion, block)
        self._refresh_block_list(insertion)

    def _remove_selected_block(self) -> None:
        selection = self.block_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.block_sequence.pop(index)
        next_index = min(index, len(self.block_sequence) - 1)
        self._refresh_block_list(next_index if next_index >= 0 else None)

    def _move_selected_block(self, direction: int) -> None:
        selection = self.block_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        new_index = index + direction
        if not 0 <= new_index < len(self.block_sequence):
            return
        self.block_sequence[index], self.block_sequence[new_index] = (
            self.block_sequence[new_index],
            self.block_sequence[index],
        )
        self._refresh_block_list(new_index)

    def _clear_blocks(self) -> None:
        self.block_sequence.clear()
        self._refresh_block_list()

    def _refresh_block_list(self, selected: int | None = None) -> None:
        self.block_listbox.delete(0, "end")
        indents = sequence_indents(self.block_sequence)
        for index, (block, indent) in enumerate(
            zip(self.block_sequence, indents, strict=True), start=1
        ):
            symbol = self.BLOCK_CATEGORY_SYMBOLS[block.category]
            label = block.python_code if block.python_code else block.name
            nesting = "    " * indent
            self.block_listbox.insert(
                "end", f"  {index:02}   {nesting}{symbol}  {label}"
            )
            self.block_listbox.itemconfigure(
                index - 1,
                bg=self.SIDEBAR,
                fg=self.BLOCK_CATEGORY_COLORS[block.category],
            )
        if selected is not None:
            self.block_listbox.selection_set(selected)
            self.block_listbox.see(selected)
        count = len(self.block_sequence)
        self.block_count_label.configure(text=f"{count} block" if count == 1 else f"{count} blocks")
        if count:
            self.block_listbox.tkraise()
        else:
            self.block_empty_label.tkraise()
        self._refresh_block_controls()

    def _refresh_block_controls(self) -> None:
        has_blocks = bool(self.block_sequence)
        valid, message = self._validate_block_sequence()
        if not has_blocks:
            color = self.TERTIARY_TEXT
        elif valid:
            color = self.GREEN
        else:
            color = self.WARNING
        self.block_validation_label.configure(text=message, fg=color)
        edit_state = "normal" if has_blocks and not self.busy else "disabled"
        for button in self.block_sequence_buttons:
            button.configure(state=edit_state)
        can_run = has_blocks and valid and self.connected and not self.busy
        self.block_run_button.configure(
            state="normal" if can_run else "disabled",
            bg=self.BLUE if can_run else self.CONTROL,
        )

    def _validate_block_sequence(self) -> tuple[bool, str]:
        if not self.block_sequence:
            return False, "Add a command to begin"
        try:
            nodes = parse_program(self.block_sequence)
            final_states = validate_flight_safety(nodes)
        except BlockProgramError as error:
            return False, f"⚠ {error}"

        if True in final_states:
            return True, "✓ Ready — automatic landing will be added"
        return True, "✓ Ready to run"

    def _run_block_program(self) -> None:
        if self.current_tab != "Block Builder":
            return
        if not self.connected or self.drone is None or self.busy:
            if not self.connected:
                self._write_log("Connect the controller first.")
            return
        if not self.block_sequence:
            self._write_log("Add at least one block first.")
            return
        valid, message = self._validate_block_sequence()
        if not valid:
            self._write_log(message.replace("⚠ ", ""))
            return

        sequence = tuple(self.block_sequence)
        try:
            program = parse_program(sequence)
            validate_flight_safety(program)
        except BlockProgramError as error:
            self._write_log(str(error))
            return
        drone = self.drone
        safe_drone = protect(drone, self._queue_log)
        self.busy = True
        self.stop_requested.clear()
        self._refresh_controls()
        self._write_log(f"Running block program ({len(sequence)} blocks)...")

        def work() -> None:
            result = ExecutionResult()
            try:
                execute_program(
                    program,
                    safe_drone,
                    self._queue_log,
                    self.stop_requested.is_set,
                    result,
                )
                if result.stopped:
                    self.events.put(("log", "Block program stopped."))
                else:
                    self.events.put(("log", "Block program finished."))
            except ObstacleDetected as error:
                self.events.put(("obstacle", str(error)))
            except Exception as error:
                self.events.put(("error", f"Block sequence stopped: {error}"))
            finally:
                landing_needed = result.airborne or (
                    result.takeoff_attempted and not result.takeoff_confirmed
                )
                if landing_needed and not self.stop_requested.is_set():
                    try:
                        self.events.put(("log", "Auto landing for safety..."))
                        drone.land()
                    except Exception as error:
                        self.events.put(
                            (
                                "error",
                                f"Automatic landing could not be confirmed: {error}. "
                                "Use Stop now or the physical controller.",
                            )
                        )
                self.events.put(("idle", None))

        threading.Thread(target=work, daemon=True).start()

    def _controller_button(
        self,
        parent: tk.Widget,
        label: str,
        row: int,
        column: int,
        action: Callable[[Drone], object],
    ) -> None:
        primary = label == "Take off"
        normal_color = self.BLUE if primary else self.CONTROL
        hover_color = self.BLUE_HOVER if primary else self.CONTROL_HOVER
        button = DarkButton(
            parent,
            text=label,
            command=lambda: self._start_custom_action(label.replace("\n", " "), action),
            bg=normal_color,
            fg=self.TEXT,
            activebackground=hover_color,
            activeforeground=self.TEXT,
            disabledforeground="#c7d8f7",
            highlightbackground=self.PANEL,
            font=(self.FONT, 13, "bold"),
            padx=8,
            pady=8,
        )
        button.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        self._add_hover(button, normal_color, hover_color)
        self.controller_buttons.append(button)

    def _add_hover(self, button: DarkButton, normal: str, hover: str) -> None:
        """Add a restrained desktop hover tint without changing control size."""
        button.bind(
            "<Enter>",
            lambda event: button.configure(bg=hover)
            if str(button.cget("state")) != "disabled"
            else None,
        )
        button.bind(
            "<Leave>",
            lambda event: button.configure(bg=normal)
            if str(button.cget("state")) != "disabled"
            else None,
        )

    def _show_tab(self, name: str) -> None:
        if name == "Controller" and not self.controller_unlocked:
            return
        frame = self.tab_frames.get(name)
        if frame is not None:
            frame.tkraise()
            self.current_tab = name
        for tab_name, button in self.tab_buttons.items():
            if tab_name == name:
                button.configure(bg=self.SELECTED, fg=self.TEXT)
            else:
                button.configure(bg=self.SIDEBAR, fg=self.MUTED_TEXT)

    def run(self) -> None:
        self._write_log("Ready. Connect the CoDrone EDU controller to begin.")
        self.root.mainloop()

    def _toggle_connection(self) -> None:
        if self.busy:
            return
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        self._hide_notice()
        self.busy = True
        self._refresh_controls()
        self._write_log("Connecting...")

        def work() -> None:
            connected = False
            try:
                drone = connect_ready_drone(Drone, ModeFlight.Ready)
                self.events.put(("connected", drone))
                connected = True
            except DroneConnectionError:
                self.events.put(
                    (
                        "error",
                        "Couldn’t connect. Check the USB data cable, turn on the "
                        "controller and drone, confirm they are paired, then try again.",
                    )
                )
            finally:
                if not connected:
                    # The SDK uses SystemExit for ordinary connection failures.
                    # Always return the UI to an actionable state.
                    self.events.put(("idle", None))

        threading.Thread(target=work, daemon=True).start()

    def _disconnect(self) -> None:
        drone = self.drone
        if drone is None:
            return
        self.busy = True
        self._refresh_controls()
        self._write_log("Disconnecting...")

        def work() -> None:
            try:
                drone.close()
            except (Exception, SystemExit):
                self.events.put(
                    (
                        "error",
                        "The controller did not disconnect cleanly. Unplug it before "
                        "starting another session.",
                    )
                )
            self.events.put(("disconnected", None))

        threading.Thread(target=work, daemon=True).start()

    def _start_program(self, program: Program) -> None:
        if not self.connected or self.drone is None or self.busy:
            if not self.connected:
                self._write_log("Connect the controller first.")
            return

        self.busy = True
        self.stop_requested.clear()
        self._refresh_controls()
        self._write_log(f"Running: {program.name}")
        drone = self.drone
        safe_drone = protect(drone, self._queue_log)

        def work() -> None:
            try:
                program.run(safe_drone, self._queue_log, self.stop_requested.is_set)
                if self.stop_requested.is_set():
                    self.events.put(("log", "Program stopped."))
                else:
                    self.events.put(("log", "Finished."))
            except ObstacleDetected as error:
                self.events.put(("obstacle", str(error)))
            except SafetySensorError as error:
                self.events.put(("error", str(error)))
            except Exception as error:
                self.events.put(
                    (
                        "error",
                        f"{program.name} stopped: {error}. Check the connection and "
                        "keep the flight area clear before trying again.",
                    )
                )
            finally:
                self.events.put(("idle", None))

        threading.Thread(target=work, daemon=True).start()

    def _start_custom_action(
        self,
        label: str,
        action: Callable[[Drone], object],
    ) -> None:
        if not self.connected or self.drone is None or self.busy:
            if not self.connected:
                self._write_log("Connect the controller first.")
            return

        self.busy = True
        self.stop_requested.clear()
        self._refresh_controls()
        self._write_log(f"Controller: {label}")
        drone = self.drone
        safe_drone = protect(drone, self._queue_log)

        def work() -> None:
            try:
                action(safe_drone)
                if not self.stop_requested.is_set():
                    self.events.put(("log", "Command complete."))
            except ObstacleDetected as error:
                self.events.put(("obstacle", str(error)))
            except SafetySensorError as error:
                self.events.put(("error", str(error)))
            except Exception as error:
                self.events.put(
                    (
                        "error",
                        f"{label} failed: {error}. Check the connection and try again.",
                    )
                )
            finally:
                self.events.put(("idle", None))

        threading.Thread(target=work, daemon=True).start()

    def _emergency_stop(self) -> None:
        if not self.connected or self.drone is None:
            return
        self.stop_requested.set()
        self._write_log("Sending emergency stop...")
        drone = self.drone

        def work() -> None:
            try:
                drone.emergency_stop()
                self.events.put(("log", "Emergency stop sent."))
            except (Exception, SystemExit) as error:
                self.events.put(
                    (
                        "error",
                        f"Emergency stop could not be confirmed: {error}. Use the "
                        "physical controller and keep clear of the drone.",
                    )
                )

        threading.Thread(target=work, daemon=True).start()

    def _process_events(self) -> None:
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self._write_log(str(value))
            elif event == "obstacle":
                message = str(value)
                self._write_log(message, "warning")
                self._show_obstacle_warning(message)
            elif event == "error":
                self._write_log(str(value), "error")
                self._show_notice(str(value))
            elif event == "connected":
                self.drone = value  # type: ignore[assignment]
                self.connected = True
                self.busy = False
                self._hide_notice()
                self._write_log("Connected.")
                self._refresh_controls()
            elif event == "disconnected":
                self.drone = None
                self.connected = False
                self.busy = False
                self._write_log("Disconnected.")
                self._refresh_controls()
            elif event == "idle":
                self.busy = False
                self._refresh_controls()

        self.root.after(100, self._process_events)

    def _queue_log(self, message: str) -> None:
        self.events.put(("log", message))

    def _activity_level(self, message: str) -> str:
        """Choose a plain visual state without exposing logging terminology."""
        lower = message.lower()
        if any(word in lower for word in ("failed", "couldn’t", "could not", "error")):
            return "error"
        if any(
            word in lower
            for word in ("obstacle", "stopped", "emergency", "safety sensor", "first")
        ):
            return "warning"
        if any(word in lower for word in ("finished", "complete", "connected.")):
            return "success"
        if any(
            lower.startswith(word)
            for word in (
                "running",
                "connecting",
                "disconnecting",
                "taking",
                "moving",
                "turning",
                "hovering",
                "flipping",
                "auto landing",
                "block ",
                "for loop",
                "while loop",
            )
        ):
            return "active"
        return "info"

    def _write_log(self, message: str, level: str | None = None) -> None:
        level = level or self._activity_level(message)
        styles = {
            "info": ("●", self.ACCENT, self.INFO_SURFACE, "#28505b"),
            "active": ("▶", self.ACCENT, self.INFO_SURFACE, "#28505b"),
            "success": ("✓", self.GREEN, self.SUCCESS_SURFACE, "#28623b"),
            "warning": ("!", self.WARNING, self.WARNING_SURFACE, "#76611c"),
            "error": ("×", "#ff8a84", self.ERROR_SURFACE, "#7f3038"),
        }
        symbol, color, surface, border = styles[level]
        self.activity_history.append((level, message))
        self.activity_history = self.activity_history[-5:]
        self.activity_latest.configure(bg=surface, highlightbackground=border)
        self.activity_icon.configure(text=symbol, fg=color, bg=surface)
        self.activity_message.configure(text=message, bg=surface)

        earlier = []
        earlier_symbols = {
            "info": "•",
            "active": "›",
            "success": "✓",
            "warning": "!",
            "error": "×",
        }
        for earlier_level, earlier_message in reversed(self.activity_history[:-1]):
            earlier.append(f"{earlier_symbols[earlier_level]}  {earlier_message}")
        self.activity_earlier.configure(text="   ".join(earlier[:3]))

    def _show_notice(self, message: str) -> None:
        self.notice_label.configure(text=message)
        if not self.notice_frame.winfo_manager():
            self.notice_frame.pack(
                fill="x",
                padx=18,
                pady=(0, 10),
                after=self.toolbar,
            )

    def _hide_notice(self) -> None:
        if self.notice_frame.winfo_manager():
            self.notice_frame.pack_forget()

    def _show_obstacle_warning(self, message: str) -> None:
        messagebox.showwarning(
            "Obstacle detected",
            f"{message}\n\nMove the obstacle away, then start the program again.",
            parent=self.root,
        )

    def _clear_log(self) -> None:
        self.activity_history.clear()
        self.activity_latest.configure(
            bg=self.INFO_SURFACE,
            highlightbackground="#28505b",
        )
        self.activity_icon.configure(text="●", fg=self.ACCENT, bg=self.INFO_SURFACE)
        self.activity_message.configure(text="Ready for the next activity", bg=self.INFO_SURFACE)
        self.activity_earlier.configure(text="")

    def _refresh_controls(self) -> None:
        program_state = "normal" if self.connected and not self.busy else "disabled"
        for button in self.program_buttons:
            button.set_state(program_state)
        for button in self.controller_buttons:
            button.configure(state=program_state)
        edit_state = "disabled" if self.busy else "normal"
        for button in self.block_edit_buttons:
            button.configure(state=edit_state)
        for button in self.block_palette_buttons:
            button.configure(state=edit_state)
        self._refresh_block_controls()

        self.connection_button.configure(
            text="Disconnect" if self.connected else "Connect",
            state="disabled" if self.busy else "normal",
        )
        self.emergency_button.configure(
            state="normal" if self.connected else "disabled",
            bg=self.RED if self.connected else "#3a2427",
        )

        if self.busy:
            status = "Running" if self.connected else "Connecting"
            color = "#fbbf24"
        elif self.connected:
            status = "Connected"
            color = self.GREEN
        else:
            status = "Disconnected"
            color = self.RED
        self.status_label.configure(text=status, fg=self.TEXT)
        self.status_dot.configure(fg=color)

    def _on_close(self) -> None:
        send_stop = False
        if self.busy and self.connected:
            should_close = messagebox.askyesno(
                "Close AeroStudio?",
                "A program is running. Send an emergency stop and close the app?",
            )
            if not should_close:
                return
            self.stop_requested.set()
            send_stop = True

        if self.drone is not None:
            if send_stop:
                stop_result = send_emergency_stop(self.drone)
                if not stop_result.completed or stop_result.error is not None:
                    messagebox.showwarning(
                        "Emergency stop not confirmed",
                        "AeroStudio could not confirm the emergency stop. Keep clear "
                        "of the drone and use the physical controller.",
                        parent=self.root,
                    )
            try:
                self.drone.close()
            except (Exception, SystemExit):
                pass
        self.root.destroy()
