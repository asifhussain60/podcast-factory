"""The corrections tables as the repo side sees them: read rows, write a change
and its audit event in one statement batch.

Everything takes an injectable `d1` callable with the signature of
`upload_listener_media.d1(sql, *, remote) -> list[dict]`, so tests fake the
database and no test can reach wrangler. The default is LOCAL: nothing in this
module reaches the production database unless a caller passes `remote=True`,
and the three scripts that expose that refuse it without an explicit second
flag (see `refuse_remote_unless_confirmed`).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable

D1 = Callable[..., list]

#: The second flag every script demands before it will talk to the deployed
#: database. One string, so the refusal and the help text cannot drift apart.
REMOTE_CONFIRM_FLAG = "--i-understand-remote"


def now_iso() -> str:
    """`new Date().toISOString()` -- UTC, millisecond precision, trailing Z."""
    n = datetime.now(timezone.utc)
    return n.strftime("%Y-%m-%dT%H:%M:%S.") + f"{n.microsecond // 1000:03d}Z"


def sql_str(value: object) -> str:
    """A SQL literal, via the publisher's own quoting so there is one rule."""
    from publish_to_listener import sql_str as _sql_str

    return _sql_str(value)


def default_d1() -> D1:
    from upload_listener_media import d1

    return d1


def refuse_remote_unless_confirmed(remote: bool, confirmed: bool) -> str | None:
    """A message when `--remote` was asked for without the confirmation, else None."""
    if remote and not confirmed:
        return (
            "refusing --remote: this would read or write the DEPLOYED database. "
            f"Pass {REMOTE_CONFIRM_FLAG} as well if that is genuinely what you want."
        )
    return None


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html: str) -> str:
    """Rationale text without markup. The app sanitises on write and on read; here it
    is only being shown to a model or a terminal, where tags are noise."""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html or "")).strip()


def event_insert(
    *,
    at: str,
    actor: str,
    action: str,
    subject: str,
    scope_id: str,
    detail: str | None = None,
    only_if_changed: bool = False,
) -> str:
    """The `access_event` row for one state change -- same shape the app writes.

    `only_if_changed` mirrors the app's `SELECT ... WHERE changes() > 0` form: put
    it directly after an UPDATE and the event is recorded only if that UPDATE
    matched a row, so the audit log cannot claim a change that did not happen.
    """
    values = (
        f"{sql_str(at)}, {sql_str(actor)}, {sql_str(action)}, {sql_str(subject)}, 'correction', "
        f"{sql_str(scope_id)}, {sql_str(detail)}"
    )
    cols = "INSERT INTO access_event (at, actor, action, subject, scope_type, scope_id, detail) "
    return cols + (f"SELECT {values} WHERE changes() > 0" if only_if_changed else f"VALUES ({values})")


def fetch_corrections(
    d1: D1,
    slug: str,
    statuses: tuple[str, ...],
    *,
    remote: bool = False,
    correction_id: str | None = None,
) -> list[dict]:
    """Live (not soft-deleted) corrections of one book in the given statuses."""
    listed = ", ".join(sql_str(s) for s in statuses)
    sql = f"SELECT * FROM correction WHERE slug = {sql_str(slug)} AND status IN ({listed}) AND deleted_at IS NULL"
    if correction_id:
        sql += f" AND id = {sql_str(correction_id)}"
    sql += " ORDER BY raised_at, id"
    return list(d1(sql, remote=remote))
