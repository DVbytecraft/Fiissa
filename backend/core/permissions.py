"""
RBAC SmartCheckout.
"""

from enum import Enum
from typing import Set

from core.state_machine import ORDER_STATUS_TRANSITIONS as ORDER_STATE_TRANSITIONS


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_OWNER = "company_owner"
    STORE_MANAGER = "store_manager"
    ACCOUNTANT = "accountant"
    PREPARER = "preparer"
    SECURITY_AGENT = "security_agent"
    SUPPORT_AGENT = "support_agent"
    CUSTOMER = "customer"


ROLE_PERMISSIONS: dict[Role, Set[str]] = {
    Role.SUPER_ADMIN: {"*"},
    Role.COMPANY_OWNER: {
        "company.read", "company.update",
        "stores.*",
        "subscriptions.read",
        "users.read", "users.create", "users.update", "users.deactivate",
        "products.*",
        "categories.*",
        "stock.*",
        "orders.read", "orders.update_status", "orders.cancel",
        "payments.read", "payments.confirm", "payments.reject", "payments.refund",
        "receipts.read", "receipts.generate", "receipts.verify",
        "reports.*",
        "notifications.send", "notifications.read",
        "audit_logs.read",
        "support.*",
        "feature_flags.read", "feature_flags.update",
        "webhooks.*",
        "loyalty.*",
        "wallet.read",
        "customers.read",
        "promotions.*",
        "staff.read", "staff.invite", "staff.remove",
        "integrations.read", "integrations.manage",
    },
    Role.STORE_MANAGER: {
        "company.read", "company.update",
        "stores.read", "stores.update",
        "products.*",
        "categories.*",
        "stock.*",
        "orders.read", "orders.update_status", "orders.cancel",
        "payments.read", "payments.confirm", "payments.reject", "payments.refund",
        "receipts.read", "receipts.generate", "receipts.verify",
        "reports.read", "reports.export",
        "subscriptions.read",
        "notifications.send", "notifications.read",
        "users.read",
        "audit_logs.read",
        "feature_flags.read", "feature_flags.update",
        "support.read", "support.update",
        "webhooks.read", "webhooks.create", "webhooks.update",
        "loyalty.manage",
        "loyalty.read", "loyalty.cards.issue", "loyalty.cards.read",
        "loyalty.rewards.read", "loyalty.coupons.issue",
        "wallet.read",
        "customers.read",
        "promotions.read", "promotions.create", "promotions.update", "promotions.delete",
        "staff.read",
        "integrations.read",
    },
    Role.ACCOUNTANT: {
        "orders.read",
        "payments.read",
        "receipts.read",
        "reports.read", "reports.export",
        "commissions.read",
        "subscriptions.read",
    },
    Role.PREPARER: {
        "orders.read",
        "orders.update_status",
        "products.read",
        "stock.read",
        "notifications.send", "notifications.read",
    },
    Role.SECURITY_AGENT: {
        "orders.read",
        "receipts.verify",
        "receipts.read",
        "pickups.verify",
    },
    Role.SUPPORT_AGENT: {
        "orders.read",
        "payments.read",
        "receipts.read",
        "users.read",
        "support.*",
        "company.read",
        "stores.read",
        "notifications.read",
    },
    Role.CUSTOMER: {
        "catalog.read",
        "cart.*",
        "orders.create", "orders.read_own", "orders.cancel_own",
        "payments.create", "payments.read_own", "payments.submit_proof",
        "receipts.read_own",
        "profile.read", "profile.update",
        "notifications.read_own",
        "support.create", "support.read_own", "support.reply_own",
        "loyalty.read_own",
        "wallet.read_own", "wallet.manage_own",
    },
}


ORDER_ROLE_TRANSITIONS: dict[str, dict[str, list[Role]]] = {
    "draft": {
        "pending": [Role.CUSTOMER],
    },
    "pending": {
        "awaiting_payment": [Role.CUSTOMER, Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "cancelled": [Role.CUSTOMER, Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "awaiting_payment": {
        "payment_submitted": [Role.CUSTOMER],
        "cancelled": [Role.CUSTOMER, Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "payment_submitted": {
        "confirmed": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
        "awaiting_payment": [Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "cancelled": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "confirmed": {
        "preparing": [Role.PREPARER, Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "cancelled": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
        "refunded": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "preparing": {
        "ready": [Role.PREPARER, Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "cancelled": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "ready": {
        "delivered": [Role.SECURITY_AGENT, Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "out_for_delivery": [Role.STORE_MANAGER, Role.COMPANY_OWNER],
        "cancelled": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
    "out_for_delivery": {
        "delivered": [Role.STORE_MANAGER, Role.COMPANY_OWNER],
    },
    "delivered": {
        "refunded": [Role.STORE_MANAGER, Role.COMPANY_OWNER, Role.SUPER_ADMIN],
    },
}


def has_permission(role: Role, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        return True
    if permission in perms:
        return True
    resource = permission.split(".")[0]
    return f"{resource}.*" in perms


def can_transition_order(role: Role, from_status: str, to_status: str) -> bool:
    if to_status not in ORDER_STATE_TRANSITIONS.get(from_status, set()):
        return False
    return role in ORDER_ROLE_TRANSITIONS.get(from_status, {}).get(to_status, [])
