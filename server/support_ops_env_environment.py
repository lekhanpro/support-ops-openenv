"""OpenEnv implementation for SupportOps customer-support operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..graders import TicketRuntimeSnapshot, grade_workspace
    from ..models import (
        ConversationTurn,
        KnowledgeArticle,
        KnowledgeArticlePreview,
        SupportOpsAction,
        SupportOpsObservation,
        SupportOpsState,
        TaskCard,
        TicketDetail,
        TicketView,
    )
    from ..tasks import ArticleSeed, TaskSpec, TicketSeed, get_task_catalog
except ImportError:
    from graders import TicketRuntimeSnapshot, grade_workspace
    from models import (
        ConversationTurn,
        KnowledgeArticle,
        KnowledgeArticlePreview,
        SupportOpsAction,
        SupportOpsObservation,
        SupportOpsState,
        TaskCard,
        TicketDetail,
        TicketView,
    )
    from tasks import ArticleSeed, TaskSpec, TicketSeed, get_task_catalog


@dataclass
class RuntimeTicket:
    ticket_id: str
    customer_name: str
    subject: str
    summary: str
    order_reference: str
    requested_outcome: str
    facts: List[str]
    conversation: List[ConversationTurn]
    queue: str
    priority: str
    status: str
    resolution: str = "none"
    refund_amount: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    internal_note: str = ""
    last_reply: str = ""

    @classmethod
    def from_seed(cls, seed: TicketSeed) -> "RuntimeTicket":
        turns = [
            ConversationTurn(role=item["role"], text=item["text"])
            for item in seed.conversation
        ]
        return cls(
            ticket_id=seed.ticket_id,
            customer_name=seed.customer_name,
            subject=seed.subject,
            summary=seed.summary,
            order_reference=seed.order_reference,
            requested_outcome=seed.requested_outcome,
            facts=list(seed.facts),
            conversation=turns,
            queue=seed.starting_queue,
            priority=seed.starting_priority,
            status=seed.starting_status,
        )

    def to_view(self) -> TicketView:
        return TicketView(
            ticket_id=self.ticket_id,
            customer_name=self.customer_name,
            subject=self.subject,
            summary=self.summary,
            queue=self.queue,  # type: ignore[arg-type]
            priority=self.priority,  # type: ignore[arg-type]
            status=self.status,  # type: ignore[arg-type]
            resolution=self.resolution,  # type: ignore[arg-type]
            refund_amount=self.refund_amount,
            tags=list(self.tags),
        )

    def to_detail(self) -> TicketDetail:
        return TicketDetail(
            ticket_id=self.ticket_id,
            customer_name=self.customer_name,
            subject=self.subject,
            summary=self.summary,
            queue=self.queue,  # type: ignore[arg-type]
            priority=self.priority,  # type: ignore[arg-type]
            status=self.status,  # type: ignore[arg-type]
            resolution=self.resolution,  # type: ignore[arg-type]
            refund_amount=self.refund_amount,
            tags=list(self.tags),
            order_reference=self.order_reference,
            requested_outcome=self.requested_outcome,
            facts=list(self.facts),
            conversation=list(self.conversation),
            internal_note=self.internal_note,
            last_reply=self.last_reply,
        )

    def to_grader_snapshot(self) -> TicketRuntimeSnapshot:
        return TicketRuntimeSnapshot(
            ticket_id=self.ticket_id,
            queue=self.queue,
            priority=self.priority,
            status=self.status,
            resolution=self.resolution,
            refund_amount=self.refund_amount,
            tags=list(self.tags),
            internal_note=self.internal_note,
            last_reply=self.last_reply,
        )


class SupportOpsEnvironment(Environment):
    """Real-world support operations environment with deterministic graders."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._catalog = get_task_catalog()
        self._task: TaskSpec = self._catalog["easy_damage_replacement"]
        self._state = SupportOpsState(
            episode_id=str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,  # type: ignore[arg-type]
        )
        self._tickets: Dict[str, RuntimeTicket] = {}
        self._articles: Dict[str, ArticleSeed] = {}
        self._active_ticket_id: Optional[str] = None
        self._visible_article_id: Optional[str] = None
        self._viewed_ticket_ids: set[str] = set()
        self._read_article_ids: set[str] = set()
        self._current_score = 0.0
        self._grader_breakdown: Dict[str, float] = {}
        self._finished = False
        self._last_action_signature: Optional[str] = None
        self._action_history: List[str] = []

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs,
    ) -> SupportOpsObservation:
        del seed
        task_id = kwargs.get("task_id", "easy_damage_replacement")
        if task_id not in self._catalog:
            task_id = "easy_damage_replacement"

        self._task = self._catalog[task_id]
        self._tickets = {
            seed_ticket.ticket_id: RuntimeTicket.from_seed(seed_ticket)
            for seed_ticket in self._task.tickets
        }
        self._articles = {article.article_id: article for article in self._task.articles}
        self._active_ticket_id = None
        self._visible_article_id = None
        self._viewed_ticket_ids = set()
        self._read_article_ids = set()
        self._current_score = 0.0
        self._grader_breakdown = {
            ticket.ticket_id: 0.0 for ticket in self._task.tickets
        }
        self._finished = False
        self._last_action_signature = None
        self._action_history = []
        self._state = SupportOpsState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,  # type: ignore[arg-type]
        )
        self._sync_state()
        return self._build_observation(
            reward=0.0,
            done=False,
            last_action_result=(
                f"Task '{self._task.title}' loaded. Inspect tickets, consult policy "
                "articles when needed, and finish once the inbox is handled."
            ),
            warnings=[],
        )

    def step(self, action: SupportOpsAction, timeout_s: Optional[float] = None, **kwargs) -> SupportOpsObservation:  # type: ignore[override]
        del timeout_s, kwargs
        if self._finished:
            return self._build_observation(
                reward=0.0,
                done=True,
                last_action_result="Episode already finished. Call reset() to start a new task.",
                warnings=["episode_finished"],
            )

        self._state.step_count += 1
        warnings: List[str]
        penalty = 0.0
        exploration_bonus = 0.0
        result_text = ""

        signature = self._action_signature(action)
        self._action_history.append(
            f"{self._state.step_count}:{action.action_type}:{action.ticket_id or action.article_id or '-'}"
        )
        if signature == self._last_action_signature:
            penalty -= 0.02
            warnings = ["repeated_action"]
        else:
            warnings = []
        self._last_action_signature = signature

        if action.action_type == "view_ticket":
            result_text, exploration_bonus, new_warnings = self._handle_view_ticket(action)
        elif action.action_type == "read_article":
            result_text, exploration_bonus, new_warnings = self._handle_read_article(action)
        elif action.action_type == "update_ticket":
            result_text, update_penalty, new_warnings = self._handle_ticket_update(action)
            penalty += update_penalty
        elif action.action_type == "send_reply":
            result_text, update_penalty, new_warnings = self._handle_reply(action)
            penalty += update_penalty
        elif action.action_type == "resolve_ticket":
            result_text, update_penalty, new_warnings = self._handle_resolution(action)
            penalty += update_penalty
        elif action.action_type == "finish":
            unresolved = [
                ticket
                for ticket in self._tickets.values()
                if ticket.status not in {"resolved", "escalated"}
            ]
            if unresolved:
                penalty -= 0.05
                new_warnings = ["unfinished_tickets"]
                result_text = (
                    f"Attempted to finish early with {len(unresolved)} ticket(s) still open."
                )
            else:
                new_warnings = []
                result_text = "Agent finished the episode."
            self._finished = True
        else:
            penalty -= 0.05
            new_warnings = ["unknown_action"]
            result_text = f"Unsupported action type: {action.action_type}"

        warnings.extend(new_warnings)

        previous_score = self._current_score
        self._current_score, self._grader_breakdown = grade_workspace(
            {
                ticket_id: ticket.to_grader_snapshot()
                for ticket_id, ticket in self._tickets.items()
            },
            self._task,
        )
        reward = (self._current_score - previous_score) + penalty + exploration_bonus

        if self._state.step_count >= self._task.max_steps:
            self._finished = True
            warnings.append("max_steps_reached")
            result_text = (
                result_text + " " if result_text else ""
            ) + "Episode ended because the step budget was exhausted."

        self._sync_state()
        return self._build_observation(
            reward=round(max(min(reward, 1.0), -1.0), 4),
            done=self._finished,
            last_action_result=result_text,
            warnings=warnings,
        )

    @property
    def state(self) -> SupportOpsState:
        self._sync_state()
        return self._state

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata.name = "SupportOpsEnvironment"
        metadata.description = (
            "Customer support operations environment for triage, policy lookup, "
            "resolution, and escalation workflows."
        )
        metadata.version = "0.1.0"
        return metadata

    def _handle_view_ticket(
        self, action: SupportOpsAction
    ) -> tuple[str, float, List[str]]:
        if not action.ticket_id or action.ticket_id not in self._tickets:
            return "Ticket not found for inspection.", 0.0, ["unknown_ticket"]

        self._active_ticket_id = action.ticket_id
        if action.ticket_id not in self._viewed_ticket_ids:
            self._viewed_ticket_ids.add(action.ticket_id)
            return f"Opened ticket {action.ticket_id} for review.", 0.02, []
        return f"Re-opened ticket {action.ticket_id}.", -0.01, ["repeated_view"]

    def _handle_read_article(
        self, action: SupportOpsAction
    ) -> tuple[str, float, List[str]]:
        if not action.article_id or action.article_id not in self._articles:
            return "Article not found in the knowledge base.", -0.03, ["unknown_article"]

        self._visible_article_id = action.article_id
        if action.article_id not in self._read_article_ids:
            self._read_article_ids.add(action.article_id)
            return f"Read article {action.article_id}.", 0.01, []
        return f"Re-read article {action.article_id}.", -0.01, ["repeated_article"]

    def _handle_ticket_update(
        self, action: SupportOpsAction
    ) -> tuple[str, float, List[str]]:
        ticket = self._resolve_ticket_from_action(action)
        if ticket is None:
            return "Cannot update ticket because no valid ticket was selected.", -0.04, [
                "unknown_ticket"
            ]
        self._apply_ticket_fields(ticket, action)
        return f"Updated ticket {ticket.ticket_id}.", 0.0, []

    def _handle_reply(
        self, action: SupportOpsAction
    ) -> tuple[str, float, List[str]]:
        ticket = self._resolve_ticket_from_action(action)
        if ticket is None:
            return "Cannot send reply because no valid ticket was selected.", -0.04, [
                "unknown_ticket"
            ]
        if not action.message.strip():
            return "Reply was empty and was ignored.", -0.03, ["empty_reply"]
        ticket.last_reply = action.message.strip()
        return f"Stored a reply draft on ticket {ticket.ticket_id}.", 0.0, []

    def _handle_resolution(
        self, action: SupportOpsAction
    ) -> tuple[str, float, List[str]]:
        ticket = self._resolve_ticket_from_action(action)
        if ticket is None:
            return "Cannot resolve ticket because no valid ticket was selected.", -0.04, [
                "unknown_ticket"
            ]
        self._apply_ticket_fields(ticket, action)
        if action.resolution in {"safety_escalation", "risk_escalation"}:
            ticket.status = action.status or "escalated"
        else:
            ticket.status = action.status or "resolved"
        if action.message.strip():
            ticket.last_reply = action.message.strip()
        if action.internal_note.strip():
            ticket.internal_note = action.internal_note.strip()
        return f"Resolved workflow recorded for ticket {ticket.ticket_id}.", 0.0, []

    def _resolve_ticket_from_action(self, action: SupportOpsAction) -> Optional[RuntimeTicket]:
        ticket_id = action.ticket_id or self._active_ticket_id
        if ticket_id is None or ticket_id not in self._tickets:
            return None
        self._active_ticket_id = ticket_id
        return self._tickets[ticket_id]

    def _apply_ticket_fields(self, ticket: RuntimeTicket, action: SupportOpsAction) -> None:
        if action.queue:
            ticket.queue = action.queue
        if action.priority:
            ticket.priority = action.priority
        if action.status:
            ticket.status = action.status
        if action.resolution:
            ticket.resolution = action.resolution
        if action.refund_amount is not None:
            ticket.refund_amount = round(action.refund_amount, 2)
        if action.tags:
            cleaned = []
            for tag in action.tags:
                normalized = "_".join(tag.strip().lower().replace("-", " ").split())
                if normalized:
                    cleaned.append(normalized)
            ticket.tags = sorted(dict.fromkeys(cleaned))
        if action.internal_note.strip():
            ticket.internal_note = action.internal_note.strip()

    def _build_observation(
        self,
        reward: float,
        done: bool,
        last_action_result: str,
        warnings: List[str],
    ) -> SupportOpsObservation:
        previews = [
            KnowledgeArticlePreview(
                article_id=article.article_id,
                title=article.title,
                summary=article.summary,
            )
            for article in self._task.articles
        ]
        visible_article = None
        if self._visible_article_id is not None:
            article = self._articles[self._visible_article_id]
            visible_article = KnowledgeArticle(
                article_id=article.article_id,
                title=article.title,
                summary=article.summary,
                content=article.content,
            )

        current_ticket = None
        if self._active_ticket_id is not None:
            current_ticket = self._tickets[self._active_ticket_id].to_detail()

        resolved_count = sum(
            1 for ticket in self._tickets.values() if ticket.status in {"resolved", "escalated"}
        )

        metadata = {
            "current_score": self._current_score,
            "grader_breakdown": self._grader_breakdown,
            "viewed_ticket_ids": sorted(self._viewed_ticket_ids),
            "read_article_ids": sorted(self._read_article_ids),
        }

        return SupportOpsObservation(
            task=TaskCard(
                task_id=self._task.task_id,
                title=self._task.title,
                difficulty=self._task.difficulty,  # type: ignore[arg-type]
                objective=self._task.objective,
                max_steps=self._task.max_steps,
            ),
            inbox=[ticket.to_view() for ticket in self._tickets.values()],
            current_ticket=current_ticket,
            knowledge_base=previews,
            visible_article=visible_article,
            last_action_result=last_action_result,
            warnings=warnings,
            remaining_steps=max(self._task.max_steps - self._state.step_count, 0),
            resolved_tickets=resolved_count,
            total_tickets=len(self._tickets),
            done=done,
            reward=reward,
            metadata=metadata,
        )

    def _sync_state(self) -> None:
        self._state.task_id = self._task.task_id
        self._state.difficulty = self._task.difficulty  # type: ignore[assignment]
        self._state.active_ticket_id = self._active_ticket_id
        self._state.tickets = [ticket.to_detail() for ticket in self._tickets.values()]
        self._state.read_article_ids = sorted(self._read_article_ids)
        self._state.viewed_ticket_ids = sorted(self._viewed_ticket_ids)
        self._state.current_score = self._current_score
        self._state.grader_breakdown = dict(self._grader_breakdown)
        self._state.finished = self._finished
        self._state.action_history = list(self._action_history)

    def _action_signature(self, action: SupportOpsAction) -> str:
        return action.model_dump_json(exclude_none=True)
