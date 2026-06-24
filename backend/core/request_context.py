from __future__ import annotations

from contextvars import ContextVar
from typing import Optional


_request_ip: ContextVar[Optional[str]] = ContextVar("request_ip", default=None)
_request_user_agent: ContextVar[Optional[str]] = ContextVar("request_user_agent", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_request_context(*, ip_address: Optional[str], user_agent: Optional[str], request_id: Optional[str]) -> None:
    _request_ip.set(ip_address)
    _request_user_agent.set(user_agent)
    _request_id.set(request_id)


def clear_request_context() -> None:
    _request_ip.set(None)
    _request_user_agent.set(None)
    _request_id.set(None)


def get_request_ip() -> Optional[str]:
    return _request_ip.get()


def get_request_user_agent() -> Optional[str]:
    return _request_user_agent.get()


def get_request_id() -> Optional[str]:
    return _request_id.get()
