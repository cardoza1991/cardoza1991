"""Outbound notification dispatchers.

Each dispatcher takes a normalized `Notification` and pushes it somewhere
the operator actually looks. Config-driven: a channel with no target
(empty webhook URL) is treated as disabled. Console is always on so the
demo and CI always see the audit trail.

Every dispatch attempt — success, skip, or failure — writes a
`NotificationLog` row. That's how the autonomous loop earns trust:
defense buyers want to see who got pinged about what, when.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models.models import ImpactScenario, NotificationLog

log = logging.getLogger(__name__)


@dataclass
class Notification:
    title: str
    severity: str                     # CRITICAL | HIGH | MEDIUM | LOW
    one_liner: str
    body_md: str
    scenario_id: Optional[int] = None
    signal_id: Optional[int] = None
    share_url: Optional[str] = None


def _redact(target: str) -> str:
    """Don't store full secrets in the audit log."""
    if not target:
        return ""
    if target.startswith("http"):
        # keep scheme + host, drop path/token
        try:
            from urllib.parse import urlparse
            p = urlparse(target)
            return f"{p.scheme}://{p.netloc}/…"
        except Exception:
            return target[:32] + "…"
    return target


def _log(db: Session, channel: str, target: str, status: str,
         note: Notification, error: Optional[str] = None) -> None:
    db.add(NotificationLog(
        channel=channel,
        target=_redact(target),
        scenario_id=note.scenario_id,
        signal_id=note.signal_id,
        status=status,
        error=error,
        payload_preview=note.one_liner[:500],
        created_at=datetime.utcnow(),
    ))


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

def _dispatch_console(db: Session, note: Notification) -> None:
    if not settings.notification_console_enabled:
        _log(db, "console", "stdout", "SKIPPED", note, "console disabled")
        return
    header = f"[AeroRisk {note.severity}] {note.title}"
    log.warning(header)
    log.warning("  → %s", note.one_liner)
    if note.share_url:
        log.warning("  ↗ %s", note.share_url)
    _log(db, "console", "stdout", "SENT", note)


def _dispatch_webhook(db: Session, note: Notification) -> None:
    url = settings.notification_webhook_url
    if not url:
        _log(db, "webhook", "", "SKIPPED", note, "no webhook url configured")
        return
    payload = {
        "title": note.title,
        "severity": note.severity,
        "one_liner": note.one_liner,
        "body_md": note.body_md,
        "scenario_id": note.scenario_id,
        "signal_id": note.signal_id,
        "share_url": note.share_url,
        "source": "AeroRisk",
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    try:
        with httpx.Client(timeout=settings.notification_http_timeout_seconds) as client:
            r = client.post(url, json=payload, headers={"User-Agent": "AeroRisk/1.0"})
            r.raise_for_status()
        _log(db, "webhook", url, "SENT", note)
    except httpx.HTTPError as e:
        log.warning("webhook dispatch failed: %s", e)
        _log(db, "webhook", url, "FAILED", note, str(e))


def _dispatch_slack(db: Session, note: Notification) -> None:
    url = settings.notification_slack_webhook_url
    if not url:
        _log(db, "slack", "", "SKIPPED", note, "no slack webhook configured")
        return
    color = {"CRITICAL": "#ef4444", "HIGH": "#f97316",
             "MEDIUM": "#eab308", "LOW": "#0ea5e9"}.get(note.severity, "#64748b")
    payload = {
        "text": f"*{note.title}*",
        "attachments": [{
            "color": color,
            "fields": [
                {"title": "Severity", "value": note.severity, "short": True},
                {"title": "Assessment", "value": note.one_liner, "short": False},
            ],
            "actions": [{"type": "button", "text": "View scenario", "url": note.share_url}] if note.share_url else [],
            "footer": "AeroRisk autonomous trigger",
            "ts": int(datetime.utcnow().timestamp()),
        }],
    }
    try:
        with httpx.Client(timeout=settings.notification_http_timeout_seconds) as client:
            r = client.post(url, json=payload, headers={"User-Agent": "AeroRisk/1.0"})
            r.raise_for_status()
        _log(db, "slack", url, "SENT", note)
    except httpx.HTTPError as e:
        log.warning("slack dispatch failed: %s", e)
        _log(db, "slack", url, "FAILED", note, str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def dispatch(db: Session, note: Notification) -> None:
    """Send to every configured channel. Failures in one don't block others."""
    for fn in (_dispatch_console, _dispatch_webhook, _dispatch_slack):
        try:
            fn(db, note)
        except Exception as e:                                          # pragma: no cover
            log.exception("notification dispatcher %s crashed: %s", fn.__name__, e)
            _log(db, fn.__name__.replace("_dispatch_", ""), "", "FAILED", note, str(e))
    # Mark the originating scenario as notified.
    if note.scenario_id is not None:
        scenario = db.query(ImpactScenario).filter(ImpactScenario.id == note.scenario_id).first()
        if scenario:
            scenario.notified = True
    db.commit()
