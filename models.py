"""Typed action, observation, and state models for SupportOps."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import BaseModel, Field

Priority = Literal["low", "medium", "high", "urgent"]
Queue = Literal["general", "returns", "billing", "risk", "safety"]
TicketStatus = Literal["open", "pending_customer", "resolved", "escalated"]
ResolutionCode = Literal[
    "none",
    "replacement",
    "refund",
    "store_credit",
    "safety_escalation",
    "risk_escalation",
]
ActionType = Literal[
    "view_ticket",
    "read_article",
    "update_ticket",
    "send_reply",
    "resolve_ticket",
    "finish",
]


class ConversationTurn(BaseModel):
    role: Literal["customer", "agent", "system"] = Field(
        ..., description="Role of the speaker"
    )
    text: str = Field(..., description="Natural-language text for the turn")


class TicketView(BaseModel):
    ticket_id: str = Field(..., description="Stable ticket identifier")
    customer_name: str = Field(..., description="Customer display name")
    subject: str = Field(..., description="Ticket subject")
    summary: str = Field(..., description="One-line issue summary")
    queue: Queue = Field(..., description="Assigned internal queue")
    priority: Priority = Field(..., description="Operational priority")
    status: TicketStatus = Field(..., description="Current ticket status")
    resolution: ResolutionCode = Field(..., description="Current resolution code")
    refund_amount: Optional[float] = Field(
        default=None, description="Refund or store-credit amount, if any"
    )
    tags: List[str] = Field(default_factory=list, description="Current ticket tags")


class TicketDetail(TicketView):
    order_reference: str = Field(..., description="Order reference")
    requested_outcome: str = Field(..., description="What the customer wants")
    facts: List[str] = Field(default_factory=list, description="Structured facts")
    conversation: List[ConversationTurn] = Field(
        default_factory=list, description="Conversation transcript"
    )
    internal_note: str = Field(
        default="", description="Internal case note written by the agent"
    )
    last_reply: str = Field(
        default="", description="Latest customer-facing reply drafted by the agent"
    )


class KnowledgeArticlePreview(BaseModel):
    article_id: str = Field(..., description="Knowledge-base article identifier")
    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="Short article summary")


class KnowledgeArticle(KnowledgeArticlePreview):
    content: str = Field(..., description="Full article body")


class TaskCard(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    title: str = Field(..., description="Human-readable task title")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Difficulty bucket"
    )
    objective: str = Field(..., description="Primary episode objective")
    max_steps: int = Field(..., description="Episode step budget")


class SupportOpsAction(Action):
    """Action schema for the support operations environment."""

    action_type: ActionType = Field(..., description="Environment action type")
    ticket_id: Optional[str] = Field(
        default=None, description="Ticket to inspect or modify"
    )
    article_id: Optional[str] = Field(
        default=None, description="Knowledge article to read"
    )
    queue: Optional[Queue] = Field(default=None, description="Queue assignment")
    priority: Optional[Priority] = Field(default=None, description="Priority update")
    status: Optional[TicketStatus] = Field(default=None, description="Status update")
    resolution: Optional[ResolutionCode] = Field(
        default=None, description="Chosen resolution"
    )
    refund_amount: Optional[float] = Field(
        default=None, ge=0.0, description="Refund or store-credit amount"
    )
    tags: List[str] = Field(default_factory=list, description="Tags to set or merge")
    internal_note: str = Field(
        default="", description="Internal note for support operations"
    )
    message: str = Field(
        default="", description="Customer-facing reply or confirmation"
    )


class SupportOpsObservation(Observation):
    """Observation schema for the support operations environment."""

    task: TaskCard = Field(..., description="Current task metadata")
    inbox: List[TicketView] = Field(
        default_factory=list, description="Current support inbox snapshot"
    )
    current_ticket: Optional[TicketDetail] = Field(
        default=None, description="Expanded detail for the selected ticket"
    )
    knowledge_base: List[KnowledgeArticlePreview] = Field(
        default_factory=list, description="Articles available to the agent"
    )
    visible_article: Optional[KnowledgeArticle] = Field(
        default=None, description="Most recently opened article"
    )
    last_action_result: str = Field(
        default="", description="Server-side result string for the last action"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Warnings about invalid or risky behavior"
    )
    remaining_steps: int = Field(
        default=0, description="Remaining steps before forced termination"
    )
    resolved_tickets: int = Field(
        default=0, description="How many tickets are currently in a terminal state"
    )
    total_tickets: int = Field(default=0, description="Total tickets in the task")


class SupportOpsState(State):
    """Internal state schema exposed through state()."""

    task_id: str = Field(..., description="Active task identifier")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Active task difficulty"
    )
    active_ticket_id: Optional[str] = Field(
        default=None, description="Currently selected ticket"
    )
    tickets: List[TicketDetail] = Field(
        default_factory=list, description="Full mutable ticket state"
    )
    read_article_ids: List[str] = Field(
        default_factory=list, description="Articles opened so far"
    )
    viewed_ticket_ids: List[str] = Field(
        default_factory=list, description="Tickets viewed so far"
    )
    action_history: List[str] = Field(
        default_factory=list, description="Compact action history"
    )
    current_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Current task score"
    )
    grader_breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Per-ticket grader scores"
    )
    finished: bool = Field(default=False, description="Whether the episode is over")

