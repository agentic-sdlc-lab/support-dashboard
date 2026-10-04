"""Support dashboard: ticket export.

Tenant-scoped CSV export.

The security requirement the implementation must satisfy:

    Tenant A may export its own tickets. Tenant A must never receive tenant B's
    records.

That requirement is owned outside the authoring agent's write scope and is checked by
tests/test_tenant_isolation.py, which is CODEOWNERS-protected. Those tests fail until
the export is implemented correctly, and they must not be edited to make them pass.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    tenant_id: str
    subject: str
    body: str
    status: str


@dataclass(frozen=True)
class Caller:
    """Who is asking. tenant_id comes from the authenticated session, never a parameter."""

    user_id: str
    tenant_id: str


class ExportDenied(Exception):
    """Raised when a caller asks for an export it is not entitled to."""


def select_tickets(
    store: list[Ticket], caller: Caller, requested_tenant_id: str | None = None
) -> list[Ticket]:
    """Return the tickets this caller is entitled to export.

    `requested_tenant_id` is caller-controlled input; it may only equal the caller's
    own tenant id. Rows are always filtered on the authenticated tenant.
    """
    if requested_tenant_id is not None and requested_tenant_id != caller.tenant_id:
        raise ExportDenied("cannot export another tenant's tickets")
    return [t for t in store if t.tenant_id == caller.tenant_id]


def to_csv(tickets: list[Ticket]) -> str:
    """Serialise tickets to CSV, quoting commas, double quotes and newlines."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["ticket_id", "tenant_id", "subject", "body", "status"])
    for t in tickets:
        writer.writerow([t.ticket_id, t.tenant_id, t.subject, t.body, t.status])
    return buf.getvalue()


def export_csv(
    store: list[Ticket], caller: Caller, requested_tenant_id: str | None = None
) -> str:
    """Export the caller's tickets as CSV."""
    return to_csv(select_tickets(store, caller, requested_tenant_id))
