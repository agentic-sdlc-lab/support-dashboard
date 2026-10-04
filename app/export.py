"""Support dashboard: tenant-scoped ticket export.

The security requirement this module exists to hold:

    Tenant A may export its own tickets. Tenant A must never receive tenant B's
    records.

That requirement is owned outside the authoring agent's write scope and is checked by
tests/test_tenant_isolation.py, which is CODEOWNERS-protected. If a change to this
file removes the tenant predicate below, that test must fail.
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
    """Return the caller's tickets.

    The tenant predicate is the whole control. `requested_tenant_id` is
    caller-controlled input: it may only ever equal the caller's own tenant. A
    version of this function that filters on the requested value instead of the
    authenticated one is an object-level authorization failure (IDOR), which is what
    the protected test checks for.
    """
    if requested_tenant_id is not None and requested_tenant_id != caller.tenant_id:
        raise ExportDenied(
            f"caller in tenant {caller.tenant_id} may not export tenant {requested_tenant_id}"
        )
    # The predicate below binds every row to the AUTHENTICATED tenant.
    return [t for t in store if t.tenant_id == caller.tenant_id]


def to_csv(tickets: list[Ticket]) -> str:
    """Serialise to CSV, quoting correctly for commas, quotes and newlines."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(["ticket_id", "tenant_id", "subject", "body", "status"])
    for t in tickets:
        writer.writerow([t.ticket_id, t.tenant_id, t.subject, t.body, t.status])
    return buf.getvalue()


def export_csv(
    store: list[Ticket], caller: Caller, requested_tenant_id: str | None = None
) -> str:
    return to_csv(select_tickets(store, caller, requested_tenant_id))
