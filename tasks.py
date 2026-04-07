"""Task catalog and deterministic grading targets for SupportOps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TicketSeed:
    ticket_id: str
    customer_name: str
    subject: str
    summary: str
    order_reference: str
    requested_outcome: str
    facts: List[str]
    conversation: List[Dict[str, str]]
    starting_queue: str = "general"
    starting_priority: str = "medium"
    starting_status: str = "open"


@dataclass(frozen=True)
class ArticleSeed:
    article_id: str
    title: str
    summary: str
    content: str


@dataclass(frozen=True)
class TicketTarget:
    queue: str
    priority: str
    status: str
    resolution: str
    tags: List[str]
    refund_amount: Optional[float] = None
    required_reply_phrases: List[str] = field(default_factory=list)
    forbidden_reply_phrases: List[str] = field(default_factory=list)
    required_note_phrases: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    difficulty: str
    objective: str
    max_steps: int
    tickets: List[TicketSeed]
    articles: List[ArticleSeed]
    targets: Dict[str, TicketTarget]


def get_task_catalog() -> Dict[str, TaskSpec]:
    easy = TaskSpec(
        task_id="easy_damage_replacement",
        title="Damaged Lamp Replacement",
        difficulty="easy",
        objective=(
            "Handle a straightforward damaged-item case by sending the right "
            "replacement workflow without forcing an unnecessary return."
        ),
        max_steps=8,
        tickets=[
            TicketSeed(
                ticket_id="E-101",
                customer_name="Mia Patel",
                subject="Desk lamp arrived cracked",
                summary="Photo-attached transit damage report for a lamp delivered 18 days ago.",
                order_reference="ORD-48371",
                requested_outcome="Customer wants a fast replacement before a housewarming event.",
                facts=[
                    "Delivered 18 days ago.",
                    "Photo of the cracked shade is already attached.",
                    "Order total is $64.99.",
                    "Customer asks for a replacement, not a refund.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "My desk lamp arrived with the shade cracked. I've attached a photo. "
                            "Can you please send a replacement before my housewarming next week?"
                        ),
                    }
                ],
            )
        ],
        articles=[
            ArticleSeed(
                article_id="damage_window",
                title="Transit damage within 30 days",
                summary="Replacements or refunds are allowed for damaged items within 30 days.",
                content=(
                    "If a customer reports transit damage within 30 days of delivery, "
                    "support may offer either a replacement or a refund. When a photo is "
                    "already attached and the order value is below $200, do not require the "
                    "customer to return the damaged item. Replacements should mention that "
                    "tracking will be emailed once the warehouse scans the order."
                ),
            )
        ],
        targets={
            "E-101": TicketTarget(
                queue="returns",
                priority="high",
                status="resolved",
                resolution="replacement",
                tags=["damage", "replacement", "photo_attached"],
                required_reply_phrases=[
                    "replacement order",
                    "no need to send the damaged item back",
                    "tracking",
                ],
                required_note_phrases=[
                    "photo verified",
                    "no return required",
                ],
            )
        },
    )

    medium = TaskSpec(
        task_id="medium_billing_and_shipping",
        title="Billing and Wrong-Item Queue",
        difficulty="medium",
        objective=(
            "Resolve a duplicate-charge complaint and a wrong-item shipment "
            "without mixing billing and returns workflows."
        ),
        max_steps=14,
        tickets=[
            TicketSeed(
                ticket_id="M-201",
                customer_name="Arjun Sethi",
                subject="Charged twice for one standing mat",
                summary="Customer sees two settled payments for the same order.",
                order_reference="ORD-64012",
                requested_outcome="Customer wants the duplicate charge reversed quickly.",
                facts=[
                    "Wallet charge and card charge both show as settled.",
                    "Order total is $79.99.",
                    "Customer sent screenshots of both settled transactions.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "I was charged twice for the same standing mat. One charge hit my wallet "
                            "and another hit my card. Both have posted. Please fix this."
                        ),
                    }
                ],
            ),
            TicketSeed(
                ticket_id="M-202",
                customer_name="Leena Roy",
                subject="Wrong size chair cover in the box",
                summary="Customer ordered medium and received small.",
                order_reference="ORD-64055",
                requested_outcome="Customer wants the correct size sent before next week's office setup.",
                facts=[
                    "Delivered 9 days ago.",
                    "Customer ordered medium but received small.",
                    "Customer is willing to send the incorrect item back.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "I ordered the medium ergonomic chair cover but the box had a small one. "
                            "Can you send the correct size? I can return the incorrect one."
                        ),
                    }
                ],
            ),
        ],
        articles=[
            ArticleSeed(
                article_id="duplicate_charge",
                title="Duplicate settled charge policy",
                summary="Settled duplicate charges should be refunded to the original method.",
                content=(
                    "If two or more charges for the same order are fully settled, the duplicate "
                    "amount should be refunded to the original payment method. Do not ask the "
                    "customer to wait for their bank when the second charge has already settled. "
                    "Explain that bank posting timelines are usually 3-5 business days."
                ),
            ),
            ArticleSeed(
                article_id="wrong_item_exchange",
                title="Wrong item or wrong size exchange",
                summary="Wrong-item shipments qualify for a replacement plus a prepaid return label.",
                content=(
                    "If the warehouse shipped the wrong item or wrong size, route the case to Returns. "
                    "Send the correct item as a replacement and include a prepaid return label for the "
                    "incorrect item. The case can be resolved once the replacement is confirmed."
                ),
            ),
        ],
        targets={
            "M-201": TicketTarget(
                queue="billing",
                priority="high",
                status="resolved",
                resolution="refund",
                refund_amount=79.99,
                tags=["billing", "duplicate_charge", "refund"],
                required_reply_phrases=[
                    "duplicate charge",
                    "$79.99",
                    "3-5 business days",
                ],
                required_note_phrases=[
                    "two settled charges",
                    "refund to original payment method",
                ],
            ),
            "M-202": TicketTarget(
                queue="returns",
                priority="medium",
                status="resolved",
                resolution="replacement",
                tags=["wrong_item", "exchange"],
                required_reply_phrases=[
                    "correct size",
                    "prepaid return label",
                ],
                required_note_phrases=[
                    "wrong size confirmed",
                    "prepaid return label",
                ],
            ),
        },
    )

    hard = TaskSpec(
        task_id="hard_safety_risk_policy_mix",
        title="Safety, Risk, and Policy Exception Mix",
        difficulty="hard",
        objective=(
            "Handle a safety incident, a high-risk address-change request, and a "
            "premium policy exception without issuing unsafe or non-compliant resolutions."
        ),
        max_steps=20,
        tickets=[
            TicketSeed(
                ticket_id="H-301",
                customer_name="Nadia Khan",
                subject="Stroller wheel snapped during walk",
                summary="Potential product safety incident involving a child's stroller.",
                order_reference="ORD-77100",
                requested_outcome="Customer needs urgent escalation after the stroller caused a scrape.",
                facts=[
                    "A rear wheel detached during normal use.",
                    "Customer says their child got a scrape on the leg.",
                    "The stroller is still at home and photos can be provided.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "The rear wheel on our stroller snapped off while I was walking. "
                            "My toddler got a scrape on the leg. What do I do now?"
                        ),
                    }
                ],
            ),
            TicketSeed(
                ticket_id="H-302",
                customer_name="Rahul Menon",
                subject="Please reroute my laptop to a new address",
                summary="High-value shipment with risk signals after an account email change.",
                order_reference="ORD-77122",
                requested_outcome="Customer wants the shipment redirected immediately.",
                facts=[
                    "Order total is $1499.00.",
                    "Account email was changed two hours after purchase.",
                    "Customer now wants the laptop sent to a different city address.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "I just moved apartments. Please change the shipping address on my laptop order "
                            "to my new place right away."
                        ),
                    }
                ],
            ),
            TicketSeed(
                ticket_id="H-303",
                customer_name="Sara Thomas",
                subject="Espresso machine leaking after 37 days",
                summary="Premium member asks for a cash refund outside the normal 30-day window.",
                order_reference="ORD-77144",
                requested_outcome="Customer wants money back for a leaking espresso machine.",
                facts=[
                    "Delivered 37 days ago.",
                    "Customer is on the Premium membership tier.",
                    "Machine leaks from the base but still powers on.",
                    "Item price was $129.00.",
                ],
                conversation=[
                    {
                        "role": "customer",
                        "text": (
                            "My espresso machine started leaking after a little over a month. "
                            "I'm a Premium member and would like a full cash refund."
                        ),
                    }
                ],
            ),
        ],
        articles=[
            ArticleSeed(
                article_id="safety_incident",
                title="Safety incident and injury escalation",
                summary="Any injury or child-product failure must be escalated to Safety.",
                content=(
                    "Any product issue involving an injury or a child-related product must be routed "
                    "to the Safety queue with urgent priority. Do not close the case as a normal refund. "
                    "Ask the customer to keep the product, gather photos if available, and confirm that "
                    "a specialist will respond within 24 hours."
                ),
            ),
            ArticleSeed(
                article_id="high_risk_order_change",
                title="High-value address change after account change",
                summary="High-risk order changes require manual identity verification.",
                content=(
                    "If a high-value order has a shipping-address change request after an account email "
                    "change, route the case to Risk and place the shipment on temporary hold. Do not "
                    "refund or reroute until identity verification is completed."
                ),
            ),
            ArticleSeed(
                article_id="premium_exception",
                title="Premium defect exception after day 30",
                summary="Premium members can receive store credit or replacement up to day 60.",
                content=(
                    "Premium members reporting a defective appliance between days 31 and 60 are eligible "
                    "for either a replacement or store credit at the original item value. Cash refunds "
                    "are not allowed after day 30 under this exception."
                ),
            ),
        ],
        targets={
            "H-301": TicketTarget(
                queue="safety",
                priority="urgent",
                status="escalated",
                resolution="safety_escalation",
                tags=["safety_incident", "injury", "stroller"],
                required_reply_phrases=[
                    "specialist",
                    "within 24 hours",
                    "please keep the stroller",
                ],
                forbidden_reply_phrases=["return label", "refund"],
                required_note_phrases=[
                    "safety escalation",
                    "preserve product",
                    "photos requested",
                ],
            ),
            "H-302": TicketTarget(
                queue="risk",
                priority="urgent",
                status="escalated",
                resolution="risk_escalation",
                tags=["address_change", "account_change", "high_value", "verify_identity"],
                required_reply_phrases=[
                    "shipment is temporarily on hold",
                    "verify your identity",
                ],
                required_note_phrases=[
                    "manual verification",
                    "temporary shipment hold",
                ],
            ),
            "H-303": TicketTarget(
                queue="returns",
                priority="medium",
                status="resolved",
                resolution="store_credit",
                refund_amount=129.00,
                tags=["defect", "premium_exception", "store_credit"],
                required_reply_phrases=[
                    "store credit",
                    "$129.00",
                ],
                forbidden_reply_phrases=["cash refund"],
                required_note_phrases=[
                    "37 days from delivery",
                    "premium exception",
                ],
            ),
        },
    )

    return {
        easy.task_id: easy,
        medium.task_id: medium,
        hard.task_id: hard,
    }

