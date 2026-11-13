"""Fixture actors. Tokens authorize nothing outside this process."""

import secrets
from dataclasses import dataclass

ORG = "SYN-ORG-RIDGEBENCH"
TENANT = "SYN-TENANT-RIDGEBENCH"
OTHER_TENANT = "SYN-TENANT-MARSHLINE"
NOTICE = "DRAFT_NOT_A_PRODUCT_DISPOSITION"
DATASET_ID = "lab-v1-fixed-29"


@dataclass(frozen=True)
class Actor:
    user_id: str
    tenant_id: str
    token: str
    scopes: frozenset[str]


IDA = Actor(
    "SYN-USER-IDA",
    TENANT,
    "lab-ida",
    frozenset({"investigation.run", "data.read"}),
)
OTTO = Actor(
    "SYN-USER-OTTO",
    TENANT,
    "lab-otto",
    frozenset({"investigation.review", "data.read"}),
)
NELL = Actor(
    "SYN-USER-NELL",
    TENANT,
    "lab-nell",
    frozenset({"investigation.run", "investigation.review", "data.read"}),
)
BEX = Actor(
    "SYN-USER-BEX",
    OTHER_TENANT,
    "lab-bex",
    frozenset({"investigation.run", "data.read"}),
)
ACTORS = (IDA, OTTO, NELL, BEX)


def actor_by_id(user_id: str) -> Actor | None:
    for actor in ACTORS:
        if actor.user_id == user_id:
            return actor
    return None


def actor_for_token(token: str) -> Actor | None:
    for actor in ACTORS:
        if len(token) == len(actor.token) and secrets.compare_digest(token, actor.token):
            return actor
    return None


def require_scope(actor: Actor, scope: str) -> None:
    from eng_workbench.errors import FlowError

    if scope not in actor.scopes:
        raise FlowError("missing_scope", "scope is not granted", 403)
