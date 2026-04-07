from graders import TicketRuntimeSnapshot, grade_workspace
from tasks import get_task_catalog


def test_easy_ticket_grader_hits_perfect_score():
    task = get_task_catalog()["easy_damage_replacement"]
    ticket = TicketRuntimeSnapshot(
        ticket_id="E-101",
        queue="returns",
        priority="high",
        status="resolved",
        resolution="replacement",
        refund_amount=None,
        tags=["damage", "replacement", "photo_attached"],
        internal_note="Photo verified. Transit damage confirmed; no return required.",
        last_reply=(
            "We've created a replacement order for your lamp. "
            "There is no need to send the damaged item back, and tracking "
            "will be emailed once it ships."
        ),
    )
    score, breakdown = grade_workspace({"E-101": ticket}, task)
    assert score == 1.0
    assert breakdown["E-101"] == 1.0

