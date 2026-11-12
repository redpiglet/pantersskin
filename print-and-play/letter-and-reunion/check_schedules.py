#!/usr/bin/env python3
"""Enumerate schedules for the Letter and Reunion print-and-play prototype.

This is a rules-model check, not a reconstruction of historical travel times.
Route lengths, the two-action round, and Pridon's three preparation actions are
gameplay abstractions. The script reads and writes no project data or files.

There are no optional handoffs or empty waiting rounds. A round uses up to two
sequential actions by different actors and may end voluntarily after one.
Notice delivery advances at each round end, including the dispatch round.

Run: python3 print-and-play/letter-and-reunion/check_schedules.py
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from functools import lru_cache


A, T, S, P = 1, 2, 4, 8
NAMES = {A: "Avtandil", T: "Tariel", S: "Asmat", P: "Pridon"}
PLACES = (
    "Gulansharo",
    "Sea Landing",
    "Shore Road",
    "Reeds",
    "Cave",
    "Riding Road",
    "Pridon's Land",
)


@dataclass(frozen=True)
class State:
    a: int = 0
    t: int = 3
    s: int = 4
    notice: int = 0  # 0 unsent; 1 dispatched; 2 at sea; 3 arrived
    letter_read: bool = False
    treasury_open: bool = False
    armor_carrier: int = 0
    preparation: int = 0
    armor_delivered: bool = False


@dataclass(frozen=True)
class Action:
    actor: int
    label: str
    result: State


def won(state: State) -> bool:
    return (
        state.a == state.t == state.s == 6
        and state.notice == 3
        and state.letter_read
        and state.treasury_open
        and state.preparation == 3
        and state.armor_delivered
    )


@lru_cache(maxsize=None)
def actions(state: State) -> tuple[Action, ...]:
    """Legal single-actor actions; co-present characters are not activated."""
    available = []

    if state.a == 0 and state.notice == 0:
        available.append(
            Action(A, "Avtandil dispatches his notice", replace(state, notice=1))
        )

    for actor, field in ((A, "a"), (T, "t"), (S, "s")):
        position = getattr(state, field)
        can_move = position < 6
        if actor == A and position == 0 and state.notice == 0:
            can_move = False
        if position == 3 and not state.letter_read:
            can_move = False
        if position == 4 and not state.treasury_open:
            can_move = False
        if can_move:
            available.append(
                Action(
                    actor,
                    f"{NAMES[actor]}: {PLACES[position]} -> {PLACES[position + 1]}",
                    replace(state, **{field: position + 1}),
                )
            )

    if state.a == state.t == 3 and not state.letter_read:
        available.append(
            Action(
                T,
                "Tariel reads Nestan's letter and receives the veil",
                replace(state, letter_read=True),
            )
        )

    if (
        state.a == state.t == state.s == 4
        and state.letter_read
        and not state.treasury_open
    ):
        for carrier in (A, T, S):
            available.append(
                Action(
                    T,
                    f"Tariel opens the chambers; {NAMES[carrier]} carries Pridon's armor",
                    replace(state, treasury_open=True, armor_carrier=carrier),
                )
            )

    if state.notice == 3 and state.preparation < 3:
        next_preparation = state.preparation + 1
        label = (
            "Pridon reads Avtandil's notice",
            "Pridon gathers 300 horsemen",
            "Pridon readies the crossing",
        )[state.preparation]
        available.append(
            Action(P, label, replace(state, preparation=next_preparation))
        )

    if state.treasury_open and not state.armor_delivered:
        carrier_field = {A: "a", T: "t", S: "s"}[state.armor_carrier]
        if getattr(state, carrier_field) == 6:
            available.append(
                Action(
                    state.armor_carrier,
                    f"{NAMES[state.armor_carrier]} gives Pridon his armor",
                    replace(state, armor_delivered=True),
                )
            )

    return tuple(available)


def round_end(state: State) -> State:
    if state.notice in (1, 2):
        return replace(state, notice=state.notice + 1)
    return state


@lru_cache(maxsize=None)
def rounds(state: State) -> tuple[tuple[State, tuple[str, ...]], ...]:
    """All ordered rounds; retain distinct choices reaching the same state."""
    first_actions = actions(state)
    outcomes = []
    if not first_actions:
        advanced = round_end(state)
        if advanced != state:
            outcomes.append((advanced, ("Notice travels; no actor can act",)))
        return tuple(outcomes)

    for first in first_actions:
        # A player may end the round voluntarily after this first action.
        outcomes.append((round_end(first.result), (first.label,)))
        second_actions = [
            second for second in actions(first.result) if second.actor != first.actor
        ]
        if second_actions:
            for second in second_actions:
                outcomes.append(
                    (round_end(second.result), (first.label, second.label))
                )
    return tuple(outcomes)


def reconstruct(parents, depth: int, state: State):
    schedule = []
    for round_number in range(depth, 0, -1):
        previous, chosen_actions = parents[round_number][state]
        schedule.append(chosen_actions)
        state = previous
    assert state == State()
    return tuple(reversed(schedule))


def validate(schedule, carrier: int) -> State:
    """Replay an example against the same explicit legal-action interface."""
    state = State()
    for chosen_actions in schedule:
        matching = [
            result
            for result, candidate_actions in rounds(state)
            if candidate_actions == chosen_actions
        ]
        assert len(matching) == 1, f"Illegal or ambiguous round: {chosen_actions}"
        state = matching[0]
    assert won(state)
    assert state.armor_carrier == carrier
    return state


def display_schedule(title: str, schedule) -> None:
    print(title)
    for number, chosen_actions in enumerate(schedule, 1):
        print(f"  {number:2}: {'; '.join(chosen_actions)}")


def solve() -> None:
    initial = State()
    frontier = {initial: 1}
    unordered_frontier = {initial: 1}
    parents = [{}]
    minimum = None
    results = {}
    examples = {}

    # Every completion uses exactly 18 irreversible actions. Without empty
    # waiting rounds, 20 rounds safely covers all plans, including courier-only
    # rounds. The search stops after the first slower benchmark is checked.
    for depth in range(1, 21):
        next_frontier = defaultdict(int)
        next_unordered_frontier = defaultdict(int)
        this_parent = {}
        for state, count in frontier.items():
            seen_results = set()
            for result, chosen_actions in rounds(state):
                next_frontier[result] += count
                this_parent.setdefault(result, (state, chosen_actions))
                # Independent actions may be performed in either order. Count
                # their common round result once in the comparison measure.
                if result not in seen_results:
                    next_unordered_frontier[result] += unordered_frontier[state]
                    seen_results.add(result)
        parents.append(this_parent)

        winners = {
            state: count for state, count in next_frontier.items() if won(state)
        }
        if winners:
            if minimum is None:
                minimum = depth
            counts = defaultdict(int)
            unordered_counts = defaultdict(int)
            for state, count in winners.items():
                counts[state.armor_carrier] += count
                unordered_counts[state.armor_carrier] += next_unordered_frontier[state]
                schedule = reconstruct(parents, depth, state)
                validate(schedule, state.armor_carrier)
                examples[depth, state.armor_carrier] = schedule
            results[depth] = (dict(counts), dict(unordered_counts))

        # A completed game ends immediately; do not count waiting after victory.
        frontier = {
            state: count for state, count in next_frontier.items() if not won(state)
        }
        unordered_frontier = {
            state: count
            for state, count in next_unordered_frontier.items()
            if not won(state)
        }
        if minimum is not None and depth >= minimum + 1:
            break
        if not frontier:
            break

    assert minimum is not None, "No winning schedule exists"
    assert all(carrier in results[minimum][0] for carrier in (A, T, S)), (
        "Not every armor carrier can meet the minimum-round benchmark"
    )

    print("Letter and Reunion: scheduling check")
    print("Model: up to two actions/round; one action/actor/round; no handoffs.")
    print("A round may end voluntarily after one action; empty waits are omitted.")
    print("Travel, action limits, and preparation stages are gameplay abstractions.")
    print(f"Minimum winning rounds: {minimum}")
    print("Ordered counts distinguish the two actions' order within a round.")
    print("Round-plan counts merge commuting action orders with the same round result.")
    for depth, (counts, unordered_counts) in sorted(results.items()):
        total = sum(counts.values())
        unordered_total = sum(unordered_counts.values())
        details = ", ".join(f"{NAMES[c]} armor: {counts.get(c, 0):,}" for c in (A, T, S))
        print(f"  Exactly {depth} rounds: {total:,} ordered schedules; {unordered_total:,} round plans")
        print(f"    Ordered carrier breakdown: {details}")

    print()
    fast = examples[minimum, A]
    display_schedule("Example minimum-round schedule (Avtandil carries armor):", fast)
    print()
    print("All three armor carriers meet the benchmark:")
    for carrier in (A, T, S):
        schedule = examples[minimum, carrier]
        handover_round = next(
            number
            for number, chosen_actions in enumerate(schedule, 1)
            if any("gives Pridon his armor" in label for label in chosen_actions)
        )
        print(f"  {NAMES[carrier]}: completes in {minimum}; armor delivered in round {handover_round}")

    slower_depth = minimum + 1
    if slower_depth in results:
        slower_carrier = next(c for c in (A, T, S) if (slower_depth, c) in examples)
        slower = examples[slower_depth, slower_carrier]
        reference = examples[minimum, slower_carrier]
        first_difference = next(
            number
            for number, (fast_round, slow_round) in enumerate(zip(reference, slower), 1)
            if fast_round != slow_round
        )
        print()
        display_schedule(
            f"Legal slower example ({NAMES[slower_carrier]} carries armor):", slower
        )
        print(f"  First changed round versus that carrier's fast example: {first_difference}")
        print("  No empty waits were inserted; one-action rounds are permitted.")


if __name__ == "__main__":
    solve()
