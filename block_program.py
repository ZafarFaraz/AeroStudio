"""Parse, validate, and safely execute Block Builder control structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from block_actions import BlockAction, Log


ShouldStop = Callable[[], bool]
MAX_NESTING = 4
MAX_COMMAND_STEPS = 100


class BlockProgramError(ValueError):
    """A student-readable structural or flight-safety problem."""


@dataclass(frozen=True)
class CommandNode:
    block: BlockAction
    index: int


@dataclass(frozen=True)
class IfNode:
    block: BlockAction
    index: int
    when_true: tuple[Node, ...]
    when_false: tuple[Node, ...]


@dataclass(frozen=True)
class LoopNode:
    block: BlockAction
    index: int
    body: tuple[Node, ...]


Node = CommandNode | IfNode | LoopNode


@dataclass
class ExecutionResult:
    airborne: bool = False
    stopped: bool = False
    command_steps: int = 0


def parse_program(sequence: Sequence[BlockAction]) -> tuple[Node, ...]:
    """Turn a flat visual sequence into nested executable nodes."""
    nodes, position, terminator = _parse_body(sequence, 0, frozenset(), 0)
    if terminator is not None:
        block = sequence[position]
        raise BlockProgramError(f"Block {position + 1}: {block.name} has no matching start")
    return nodes


def _parse_body(
    sequence: Sequence[BlockAction],
    position: int,
    terminators: frozenset[str],
    depth: int,
) -> tuple[tuple[Node, ...], int, str | None]:
    nodes: list[Node] = []
    closing_kinds = {"else", "end_if", "end_repeat", "end_while"}

    while position < len(sequence):
        block = sequence[position]
        kind = block.kind
        if kind in terminators:
            return tuple(nodes), position, kind
        if kind in closing_kinds:
            raise BlockProgramError(
                f"Block {position + 1}: {block.name} has no matching start"
            )
        if kind == "command":
            nodes.append(CommandNode(block, position))
            position += 1
            continue
        if depth >= MAX_NESTING:
            raise BlockProgramError(
                f"Block {position + 1}: keep control blocks to {MAX_NESTING} nested levels"
            )

        if kind == "if":
            true_nodes, marker, marker_kind = _parse_body(
                sequence, position + 1, frozenset({"else", "end_if"}), depth + 1
            )
            if marker_kind is None:
                raise BlockProgramError(
                    f"Block {position + 1}: If path is clear needs End if"
                )
            false_nodes: tuple[Node, ...] = ()
            if marker_kind == "else":
                false_nodes, end_position, end_kind = _parse_body(
                    sequence, marker + 1, frozenset({"end_if"}), depth + 1
                )
                if end_kind is None:
                    raise BlockProgramError(
                        f"Block {marker + 1}: Otherwise needs End if"
                    )
                marker = end_position
            if not true_nodes:
                raise BlockProgramError(
                    f"Block {position + 1}: add a command inside the If block"
                )
            nodes.append(IfNode(block, position, true_nodes, false_nodes))
            position = marker + 1
            continue

        expected_end = "end_repeat" if kind == "repeat" else "end_while"
        body, end_position, end_kind = _parse_body(
            sequence, position + 1, frozenset({expected_end}), depth + 1
        )
        if end_kind is None:
            label = "End repeat" if kind == "repeat" else "End while"
            raise BlockProgramError(f"Block {position + 1}: {block.name} needs {label}")
        if not body:
            raise BlockProgramError(
                f"Block {position + 1}: add a command inside {block.name}"
            )
        nodes.append(LoopNode(block, position, body))
        position = end_position + 1

    return tuple(nodes), position, None


def validate_flight_safety(nodes: Iterable[Node]) -> set[bool]:
    """Return possible final flight states or raise on an unsafe path."""
    return _analyse_nodes(tuple(nodes), {False})


def _analyse_nodes(nodes: tuple[Node, ...], states: set[bool]) -> set[bool]:
    current = set(states)
    for node in nodes:
        if isinstance(node, CommandNode):
            block = node.block
            if block.name == "Take off":
                if True in current:
                    raise BlockProgramError(
                        f"Block {node.index + 1}: the drone may already be airborne"
                    )
                current = {True}
            elif block.name == "Land":
                if False in current:
                    raise BlockProgramError(
                        f"Block {node.index + 1}: the drone may not have taken off"
                    )
                current = {False}
            elif block.category in {"Movement", "Tricks"} or block.name == "Hover 1 second":
                if False in current:
                    raise BlockProgramError(
                        f"Block {node.index + 1}: movement needs Take off on every path"
                    )
            continue

        if isinstance(node, IfNode):
            true_states = _analyse_nodes(node.when_true, set(current))
            false_states = (
                _analyse_nodes(node.when_false, set(current))
                if node.when_false
                else set(current)
            )
            current = true_states | false_states
            continue

        if node.block.kind == "repeat":
            for _ in range(node.block.repeat_count):
                current = _analyse_nodes(node.body, current)
            continue

        possible = set(current)
        iteration_states = set(current)
        for _ in range(node.block.max_iterations):
            iteration_states = _analyse_nodes(node.body, iteration_states)
            possible |= iteration_states
        current = possible
    return current


def execute_program(
    nodes: Iterable[Node],
    drone: Any,
    log: Log,
    should_stop: ShouldStop,
    result: ExecutionResult | None = None,
) -> ExecutionResult:
    """Execute parsed nodes with bounded loops and an emergency-stop check."""
    if result is None:
        result = ExecutionResult()

    def run_nodes(items: Iterable[Node]) -> None:
        for node in items:
            if should_stop():
                result.stopped = True
                return
            if isinstance(node, CommandNode):
                result.command_steps += 1
                if result.command_steps > MAX_COMMAND_STEPS:
                    raise BlockProgramError(
                        f"Stopped after {MAX_COMMAND_STEPS} commands for safety"
                    )
                block = node.block
                if block.execute is None:
                    raise BlockProgramError(f"{block.name} has no command")
                log(f"Block {node.index + 1}: {block.name}")
                block.execute(drone, log, should_stop)
                if block.name == "Take off":
                    result.airborne = True
                elif block.name == "Land":
                    result.airborne = False
                continue

            if isinstance(node, IfNode):
                if node.block.condition is None:
                    raise BlockProgramError(f"{node.block.name} has no condition")
                log(f"Block {node.index + 1}: checking if path is clear...")
                branch = node.when_true if node.block.condition(drone, log) else node.when_false
                run_nodes(branch)
                if result.stopped:
                    return
                continue

            if node.block.kind == "repeat":
                for iteration in range(1, node.block.repeat_count + 1):
                    if should_stop():
                        result.stopped = True
                        return
                    log(f"For loop: repeat {iteration} of {node.block.repeat_count}")
                    run_nodes(node.body)
                    if result.stopped:
                        return
                continue

            if node.block.condition is None:
                raise BlockProgramError(f"{node.block.name} has no condition")
            for iteration in range(1, node.block.max_iterations + 1):
                if should_stop():
                    result.stopped = True
                    return
                log(f"While loop: condition check {iteration} of {node.block.max_iterations}")
                if not node.block.condition(drone, log):
                    log("While loop finished because the condition is false.")
                    break
                run_nodes(node.body)
                if result.stopped:
                    return
            else:
                log(f"While loop reached its safe limit of {node.block.max_iterations} repeats.")

    run_nodes(nodes)
    return result


def sequence_indents(sequence: Sequence[BlockAction]) -> list[int]:
    """Calculate readable visual indentation for the flat sequence list."""
    depth = 0
    indents: list[int] = []
    for block in sequence:
        if block.kind in {"else", "end_if", "end_repeat", "end_while"}:
            depth = max(0, depth - 1)
        indents.append(depth)
        if block.kind in {"if", "else", "repeat", "while"}:
            depth += 1
    return indents
