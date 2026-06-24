"""
Statuts metier et transitions centralises.
"""

from __future__ import annotations

from typing import Iterable


ORDER_STATUS_VALUES = (
    "draft",
    "pending",
    "awaiting_payment",
    "payment_submitted",
    "confirmed",
    "preparing",
    "ready",
    "out_for_delivery",
    "delivered",
    "cancelled",
    "refunded",
)

PAYMENT_STATUS_VALUES = (
    "pending",
    "pending_verification",
    "proof_submitted",
    "confirmed",
    "rejected",
    "failed",
    "expired",
    "refunded",
)

RECEIPT_STATUS_VALUES = (
    "generated",
    "verified",
    "invalidated",
)

ORDER_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending"},
    "pending": {"awaiting_payment", "cancelled"},
    "awaiting_payment": {"payment_submitted", "cancelled"},
    "payment_submitted": {"confirmed", "awaiting_payment", "cancelled"},
    "confirmed": {"preparing", "cancelled", "refunded"},
    "preparing": {"ready", "cancelled"},
    "ready": {"delivered", "out_for_delivery", "cancelled"},
    "out_for_delivery": {"delivered"},
    "delivered": {"refunded"},
    "cancelled": set(),
    "refunded": set(),
}

PAYMENT_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"pending_verification", "proof_submitted", "expired"},
    "pending_verification": {"confirmed", "failed", "rejected", "expired"},
    "proof_submitted": {"confirmed", "rejected", "expired"},
    "confirmed": {"refunded"},
    "failed": {"pending"},
    "rejected": {"pending"},
    "expired": set(),
    "refunded": set(),
}

RECEIPT_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "generated": {"verified", "invalidated"},
    "verified": {"invalidated"},
    "invalidated": set(),
}

PAYMENT_STATUS_ALIASES = {
    "proof_submitted": "pending_verification",
    "rejected": "failed",
}


def normalize_payment_status(status: str) -> str:
    return PAYMENT_STATUS_ALIASES.get(status, status)


def can_transition(state_map: dict[str, set[str]], from_status: str, to_status: str) -> bool:
    return to_status in state_map.get(from_status, set())


def ensure_known_status(status: str, allowed: Iterable[str]) -> bool:
    return status in set(allowed)
