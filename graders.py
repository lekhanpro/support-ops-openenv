"""Deterministic task graders for SupportOps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

try:
    from .tasks import TaskSpec, TicketTarget
except ImportError:
    from tasks import TaskSpec, TicketTarget


@dataclass(frozen=True)
class TicketRuntimeSnapshot:
    ticket_id: str
    queue: str
    priority: str
    status: str
    resolution: str
    refund_amount: Optional[float]
    tags: Sequence[str]
    internal_note: str
    last_reply: str


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("$", " $").split())


def _normalize_tags(tags: Iterable[str]) -> Tuple[str, ...]:
    normalized = []
    for tag in tags:
        cleaned = "_".join(tag.strip().lower().replace("-", " ").split())
        if cleaned:
            normalized.append(cleaned)
    return tuple(sorted(dict.fromkeys(normalized)))


def _contains_all_phrases(text: str, phrases: Sequence[str]) -> float:
    if not phrases:
        return 1.0
    normalized = _normalize_text(text)
    hits = sum(1 for phrase in phrases if _normalize_text(phrase) in normalized)
    return hits / len(phrases)


def _contains_forbidden_phrases(text: str, phrases: Sequence[str]) -> bool:
    if not phrases:
        return False
    normalized = _normalize_text(text)
    return any(_normalize_text(phrase) in normalized for phrase in phrases)


def _tag_score(actual_tags: Sequence[str], expected_tags: Sequence[str]) -> float:
    actual = set(_normalize_tags(actual_tags))
    expected = set(_normalize_tags(expected_tags))
    if not expected:
        return 1.0 if not actual else 0.8
    overlap = len(actual & expected)
    recall = overlap / len(expected)
    precision = overlap / len(actual) if actual else 0.0
    if overlap == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def _amount_score(actual: Optional[float], expected: Optional[float]) -> float:
    if expected is None:
        return 1.0 if actual in (None, 0, 0.0) else 0.0
    if actual is None:
        return 0.0
    error = abs(actual - expected)
    if error <= 0.01:
        return 1.0
    relative_error = min(error / max(expected, 1.0), 1.0)
    return max(0.0, 1.0 - relative_error)


def grade_ticket(
    ticket: TicketRuntimeSnapshot,
    target: TicketTarget,
) -> float:
    """Score a single ticket from 0.0 to 1.0 with dense partial credit."""

    weights: Dict[str, float] = {
        "queue": 0.14,
        "priority": 0.12,
        "status": 0.12,
        "resolution": 0.14,
        "tags": 0.14,
        "amount": 0.12,
        "reply": 0.14,
        "note": 0.08,
    }

    if target.refund_amount is None:
        weights["amount"] = 0.06
        weights["reply"] = 0.18
        weights["note"] = 0.12

    score = 0.0
    total_weight = sum(weights.values())

    score += weights["queue"] * float(ticket.queue == target.queue)
    score += weights["priority"] * float(ticket.priority == target.priority)
    score += weights["status"] * float(ticket.status == target.status)
    score += weights["resolution"] * float(ticket.resolution == target.resolution)
    score += weights["tags"] * _tag_score(ticket.tags, target.tags)
    score += weights["amount"] * _amount_score(ticket.refund_amount, target.refund_amount)

    reply_score = _contains_all_phrases(ticket.last_reply, target.required_reply_phrases)
    if _contains_forbidden_phrases(ticket.last_reply, target.forbidden_reply_phrases):
        reply_score = 0.0
    score += weights["reply"] * reply_score

    note_score = _contains_all_phrases(ticket.internal_note, target.required_note_phrases)
    score += weights["note"] * note_score

    return round(max(0.0, min(score / total_weight, 1.0)), 4)


def grade_workspace(
    ticket_snapshots: Dict[str, TicketRuntimeSnapshot],
    task: TaskSpec,
) -> tuple[float, Dict[str, float]]:
    """Score the whole task by averaging per-ticket grader outputs."""

    breakdown: Dict[str, float] = {}
    if not task.targets:
        return 0.0, breakdown

    for ticket_id, target in task.targets.items():
        ticket = ticket_snapshots[ticket_id]
        breakdown[ticket_id] = grade_ticket(ticket, target)

    overall = sum(breakdown.values()) / len(breakdown)
    return round(max(0.0, min(overall, 1.0)), 4), breakdown
