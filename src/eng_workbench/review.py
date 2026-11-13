"""Engineer review. The requester cannot approve their own draft."""

from typing import Any

from eng_workbench.errors import FlowError
from eng_workbench.identity import Actor, require_scope
from eng_workbench.store import Store


def submit_review(
    store: Store,
    actor: Actor,
    investigation_id: str,
    action: str,
    corrected_cause: str,
    note: str,
) -> dict[str, Any]:
    require_scope(actor, "investigation.review")
    row = store.get_investigation(investigation_id)
    if row is None or row["tenant_id"] != actor.tenant_id:
        raise FlowError("not_found", "investigation is not in this tenant", 404)
    if row["requester_id"] == actor.user_id:
        raise FlowError("same_actor", "requester cannot review their own draft", 403)
    if store.get_review(investigation_id) is not None:
        raise FlowError("already_reviewed", "investigation already has a review", 409)
    if action not in {"approve", "correct"}:
        raise FlowError("bad_action", "action must be approve or correct", 400)
    if action == "correct" and corrected_cause.strip() == "":
        raise FlowError("cause_required", "a correction needs a cause", 400)
    cause = row["cause"] if action == "approve" else corrected_cause.strip()
    status = "APPROVED" if action == "approve" else "CORRECTED"
    review = {
        "review_id": f"SYN-REV-{store.next_id():04d}",
        "investigation_id": investigation_id,
        "reviewer_id": actor.user_id,
        "action": action,
        "corrected_cause": cause,
        "note": note,
    }
    store.save_review(review)
    store.set_status(investigation_id, status, cause)
    store.record_usage(actor.user_id, "review", investigation_id)
    store.record_audit(actor.user_id, "review", "accepted", action)
    updated = store.get_investigation(investigation_id)
    if updated is None:
        raise RuntimeError("investigation disappeared after review")
    updated["review"] = review
    return updated
