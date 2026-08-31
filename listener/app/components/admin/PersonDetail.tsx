import { useEffect, useState } from "react";
import {
  faChevronDown,
  faChevronRight,
  faEnvelope,
  faEye,
} from "@fortawesome/free-solid-svg-icons";
import { Form } from "react-router";

import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { GrantRow } from "~/components/admin/GrantRow";
import { InviteMessage } from "~/components/admin/InviteMessage";
import { count } from "~/lib/plural";
import { when } from "~/lib/adminDate";
import type { ContentUnit } from "~/server/access.server";
import type { Person } from "~/server/people.server";

/* -------------------------------------------------------------------------- */
/* One person, and what they can open                                          */
/* -------------------------------------------------------------------------- */

export function PersonDetail({
  person,
  catalog,
  granted,
  isSelf,
  siteUrl,
  plusTag,
  justGranted,
}: {
  person: Person;
  catalog: ContentUnit[];
  granted: Set<string>;
  /** Whether the administrator is looking at their own row. */
  isSelf: boolean;
  /** Where the site lives, for the link in the invitation message. */
  siteUrl: string;
  /** Their address keeps a `+tag`, which they must sign in with exactly. */
  plusTag: boolean;
  /** True on the render right after a grant to this person succeeded. */
  justGranted: boolean;
}) {
  const [showMessage, setShowMessage] = useState(false);

  // Opened by the grant itself, so the note to send is in front of the
  // administrator at the moment they have something to tell somebody — rather
  // than depending on them remembering a button afterwards.
  useEffect(() => {
    if (justGranted) setShowMessage(true);
  }, [justGranted]);
  const [find, setFind] = useState("");
  /** Ticked but not yet given — `unit:<slug>` / `work:<slug>`. */
  const [picked, setPicked] = useState<Set<string>>(() => new Set());
  /** Works whose volumes are showing. Collapsed is the default: twelve of the
   *  twenty-three rows in this catalogue are volumes of two works. */
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());

  // "Add more" offers only what a grant can actually take effect on today —
  // a draft is invisible to everyone regardless of who holds a grant on it
  // (per `statusHint` below), so offering one here as if it were an ordinary
  // book is what reads as a mistake once it turns out to do nothing (Asif,
  // 2026-08-17: "should only see books... that have the published flag set
  // ... to avoid confusion"). This does NOT touch `held` above: a book
  // already granted stays listed with its own "not published yet" hint even
  // in draft, because hiding an existing grant reads as a silent revoke.
  const works = catalog.filter(
    (u) => u.kind === "work" && u.status === "published",
  );
  const standalone = catalog.filter(
    (u) => u.kind === "book" && u.workSlug === null && u.status === "published",
  );
  const wholeLibrary = granted.has("library:*");
  const searching = find.trim() !== "";

  // Clear the ticks once the grants actually change — every ticked row has by
  // then moved up to "Already given", so a count left behind would offer to give
  // four books that are no longer on the list.
  const grantedKey = [...granted].sort().join("|");
  useEffect(() => setPicked(new Set()), [grantedKey]);

  const matches = (u: ContentUnit) =>
    find.trim() === "" ||
    u.title.toLowerCase().includes(find.trim().toLowerCase());

  // What they already hold, gathered first. The screen this replaces rendered
  // the entire catalogue as a flat list of toggles — twenty-three rows today,
  // and the question an administrator arrives with is "what does this person
  // have", which was the one thing that list never answered directly.
  const held = catalog.filter(
    (u) => granted.has(`unit:${u.slug}`) || granted.has(`work:${u.slug}`),
  );

  return (
    <>
      <div className="pf-panel">
        <div className="pf-panel__head pf-split">
          <div className="pf-split__main">
            <h2 className="pf-panel__title pf-panel__title--name">
              {person.displayName}
            </h2>
            {/* Only when it adds something. For anyone invited before names
                existed, `displayName` IS the address, and printing it twice
                reads as a rendering fault rather than as a fact. */}
            {person.displayName === person.emailRaw ? null : (
              <p className="pf-person__mail">{person.emailRaw}</p>
            )}
          </div>

          {/* You cannot revoke yourself.
              Admin is `ADMIN_EMAIL` and nothing else, so the administrator's own
              invite row is the one thing standing between them and a site they
              can no longer sign in to — and `revokeInvite` deletes live sessions,
              so the lock-out would be immediate and would need a database edit to
              undo. Offering the button and refusing the action would be worse
              than not offering it; this says why instead. */}
          <div className="pf-person__acts">
            {/* Called SIMULATE, and that is not a style preference. It read
                "See as them", which is a better description of what happens and
                a word nobody searches for — Asif went looking for this control
                with Cmd+F on 2026-08-04, typed "simulate", and the page said
                0/0 while the button was on screen. The intent, the banner and
                the way out all say simulate or simulation now, so finding any
                one of them finds all of them.

                Offered even for a revoked person: what they see is /no-access,
                and the banner that appears carries the way back out — the stop
                control is a public route precisely so this cannot be a dead end. */}
            <Form method="post">
              <input type="hidden" name="intent" value="simulate" />
              <input type="hidden" name="email" value={person.email} />
              <button
                type="submit"
                title={`Simulate ${person.displayName} — open the library as they see it`}
                className="pf-button pf-button--ghost pf-button--sm"
              >
                <Icon icon={faEye} /> Simulate
              </button>
            </Form>

            {isSelf ? (
              <p className="pf-note--quiet">This is you.</p>
            ) : (
              <Form method="post">
                <input
                  type="hidden"
                  name="intent"
                  value={
                    person.revokedAt === null ? "revoke-invite" : "re-invite"
                  }
                />
                <input type="hidden" name="email" value={person.email} />
                <button
                  type="submit"
                  className="pf-button pf-button--ghost pf-button--sm"
                >
                  {person.revokedAt === null ? "Revoke sign-in" : "Re-invite"}
                </button>
              </Form>
            )}
          </div>
        </div>

        <div className="pf-panel__body">
          <dl className="pf-facts">
            <Fact label="Invited" value={when(person.invitedAt)} />
            <Fact
              label="First signed in"
              value={person.redeemedAt ? when(person.redeemedAt) : "Never"}
            />
            <Fact
              label="Last signed in"
              value={person.lastSeenAt ? when(person.lastSeenAt) : "Never"}
            />
            <Fact
              label="Books"
              value={wholeLibrary ? "Everything" : String(person.grantCount)}
            />
          </dl>
          {person.note ? <p className="pf-note--quiet">{person.note}</p> : null}

          {plusTag ? (
            <p className="pf-message pf-message--warn">
              That address has a <code>+tag</code>. On this domain the tag is
              part of the identity, so it must match the account they sign in
              with exactly.
            </p>
          ) : null}

          {person.revokedAt !== null ? (
            <p className="pf-message pf-message--warn">
              Sign-in is revoked and their sessions were ended. What they had is
              kept below, so re-inviting restores it exactly.
            </p>
          ) : null}
        </div>
      </div>

      <div className="pf-panel">
        <div className="pf-panel__head">
          <h2 className="pf-panel__title">What they can open</h2>
        </div>

        <div className="pf-panel__body pf-stack-sm">
          <GrantRow
            label="Everything, including anything added later"
            on={wholeLibrary}
            onLabel="Granted"
            fields={{ email: person.email, scopeType: "library", scopeId: "*" }}
          />

          {/* Held first, and always visible — the search below filters what can
              be ADDED, never what is already given, or an administrator could
              type three letters and appear to have revoked everything. */}
          {held.length > 0 ? (
            <>
              {/* `.pf-subhead`, not `.pf-notes__heading`. That one belongs to the
                  reader's drawer, where it is a full-width row of a notes grid —
                  so restyling how a reader's notes are laid out silently
                  restyled this panel. */}
              <h3 className="pf-subhead">Already given</h3>
              {held.map((unit) => (
                <GrantRow
                  key={unit.slug}
                  label={unit.title}
                  hint={
                    unit.kind === "work"
                      ? "All volumes, including future ones"
                      : statusHint(unit)
                  }
                  on
                  onLabel="Granted"
                  fields={{
                    email: person.email,
                    scopeType: unit.kind === "work" ? "work" : "unit",
                    scopeId: unit.slug,
                  }}
                />
              ))}
            </>
          ) : null}

          <h3 className="pf-subhead">Add more</h3>

          {/* OUTSIDE the form below, deliberately. It filters what is shown and
              submits nothing, and a text input inside a form makes Enter grant
              whatever happens to be ticked. */}
          <SearchBox
            id="scope-find"
            label="Search the library"
            placeholder="Search the library"
            size="sm"
            action={{ kind: "filter", value: find, onChange: setFind }}
          />

          {/* ONE form for every book on offer, because provisioning someone new
              was eight page posts. Each ticked box is a `scope` field and the
              action grants them one at a time, so the audit trail still says
              which books rather than "four things". */}
          <Form method="post" preventScrollReset className="pf-stack-sm">
            <input type="hidden" name="intent" value="grant-many" />
            <input type="hidden" name="email" value={person.email} />

            {works.map((work) => {
              // A work already granted is not offered again, and neither are its
              // volumes: the grant covers every one of them, including volumes
              // added later, so the rows would be six ways of saying "yes, still".
              if (granted.has(`work:${work.slug}`)) return null;
              if (
                !matches(work) &&
                !catalog.some((v) => v.workSlug === work.slug && matches(v))
              ) {
                return null;
              }

              const volumes = catalog
                .filter((u) => u.workSlug === work.slug && matches(u))
                .filter((u) => !granted.has(`unit:${u.slug}`))
                // Same "only what's actually live" rule as `works`/`standalone`
                // above, applied per volume — a work can publish before every
                // one of its volumes does.
                .filter((u) => u.status === "published");

              return (
                <WorkScope
                  key={work.slug}
                  work={work}
                  volumes={volumes}
                  total={catalog.filter((u) => u.workSlug === work.slug).length}
                  // Searching expands everything that matched. A collapsed work
                  // hiding the volume someone just searched for reads as the
                  // search being broken.
                  open={searching || expanded.has(work.slug)}
                  frozen={searching}
                  onToggle={() => setExpanded(flip(expanded, work.slug))}
                  picked={picked}
                  onPick={(key) => setPicked(flip(picked, key))}
                  covered={wholeLibrary}
                />
              );
            })}

            {standalone
              .filter(matches)
              .filter((u) => !granted.has(`unit:${u.slug}`))
              .map((unit) => (
                <ScopeCheck
                  key={unit.slug}
                  scope={`unit:${unit.slug}`}
                  label={unit.title}
                  hint={statusHint(unit)}
                  covered={wholeLibrary}
                  picked={picked.has(`unit:${unit.slug}`)}
                  onPick={() => setPicked(flip(picked, `unit:${unit.slug}`))}
                />
              ))}

            {/* Centred and full size. It was a small pill hard against the left
                edge of a tall panel — the least prominent thing on a screen
                whose entire purpose it is. */}
            <div className="pf-scope-actions">
              <button
                type="submit"
                disabled={picked.size === 0}
                className="pf-button pf-button--primary"
              >
                {picked.size === 0
                  ? "Give access to the ticked books"
                  : `Give access to ${count(picked.size, "book")}`}
              </button>

              {/* Always, for anybody selected. It was offered only once they
                  held a book, which left the one case that needs it most with
                  nothing: a person invited a moment ago has no books yet, and
                  is exactly the person who has not been told the site exists.
                  The message says what they can open only when there is
                  something — see `whatTheyHave` — so it reads correctly either
                  way, and the reason to send it is not always the moment access
                  was given: somebody loses the link, or never got the first
                  message. */}
              <button
                type="button"
                onClick={() => setShowMessage(true)}
                className="pf-button pf-button--soft"
              >
                <Icon icon={faEnvelope} />
                Generate message
              </button>
            </div>
          </Form>

          <InviteMessage
            open={showMessage}
            onClose={() => setShowMessage(false)}
            displayName={person.displayName}
            email={person.emailRaw || person.email}
            siteUrl={siteUrl}
            books={held.map((u) => u.title)}
            wholeLibrary={wholeLibrary}
          />
        </div>
      </div>
    </>
  );
}

/** A set with one member added or removed — the whole of both pickers' state. */
function flip(current: Set<string>, key: string): Set<string> {
  const next = new Set(current);
  if (!next.delete(key)) next.add(key);
  return next;
}

/**
 * One multi-volume work: a row that expands.
 *
 * The chevron is a SIBLING of the checkbox label, never a parent of it. A work
 * carries two independent controls — "give me all of this" and "show me what is
 * in it" — and nesting either inside the other is both invalid markup and a
 * press that does the wrong thing.
 *
 * Ticking the work disables its volumes rather than hiding them: the volumes are
 * the reason someone opened the row, and a list that empties itself when you
 * tick the thing above it looks like a fault.
 */
function WorkScope({
  work,
  volumes,
  total,
  open,
  frozen,
  onToggle,
  picked,
  onPick,
  covered,
}: {
  work: ContentUnit;
  volumes: ContentUnit[];
  /** Every volume the work has, not just the ones on offer — this is the count. */
  total: number;
  open: boolean;
  /** Held open by a search, so the chevron would be lying if it offered to close. */
  frozen: boolean;
  onToggle: () => void;
  picked: Set<string>;
  onPick: (scope: string) => void;
  covered: boolean;
}) {
  const id = `vols-${work.slug}`;
  const wholeWork = picked.has(`work:${work.slug}`);

  return (
    <div className="pf-scope-work">
      <div className="pf-scope-work__head">
        <button
          type="button"
          onClick={onToggle}
          disabled={frozen}
          aria-expanded={open}
          aria-controls={id}
          aria-label={`${open ? "Hide" : "Show"} the volumes of ${work.title}`}
          className="pf-scope-work__toggle"
        >
          <Icon icon={open ? faChevronDown : faChevronRight} />
        </button>

        <ScopeCheck
          scope={`work:${work.slug}`}
          label={work.title}
          hint={`All ${count(total, "volume")}, including future ones`}
          covered={covered}
          picked={wholeWork}
          onPick={() => onPick(`work:${work.slug}`)}
        />
      </div>

      {open ? (
        <div id={id} className="pf-scope-work__volumes">
          {volumes.map((vol) => (
            <ScopeCheck
              key={vol.slug}
              scope={`unit:${vol.slug}`}
              label={vol.title}
              hint={statusHint(vol)}
              covered={covered || wholeWork}
              coveredNote={
                wholeWork ? "Covered by the whole work above" : undefined
              }
              picked={picked.has(`unit:${vol.slug}`)}
              onPick={() => onPick(`unit:${vol.slug}`)}
              disabled={wholeWork}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** One tickable book. A label, so the whole row is the target on a phone. */
function ScopeCheck({
  scope,
  label,
  hint,
  covered = false,
  coveredNote,
  picked,
  onPick,
  disabled = false,
}: {
  /** `unit:<slug>` or `work:<slug>` — the value the action reads back. */
  scope: string;
  label: string;
  hint?: string;
  covered?: boolean;
  coveredNote?: string;
  picked: boolean;
  onPick: () => void;
  disabled?: boolean;
}) {
  return (
    <label className={`pf-scope${disabled ? " pf-scope--off" : ""}`}>
      <input
        type="checkbox"
        name="scope"
        value={scope}
        checked={picked && !disabled}
        onChange={onPick}
        disabled={disabled}
        className="pf-scope__box"
      />
      <span className="pf-scope__what">
        <span className="pf-scope__label">{label}</span>
        {covered ? (
          <span className="pf-scope__hint">
            {coveredNote ?? "Already covered by a wider grant"}
          </span>
        ) : hint ? (
          <span className="pf-scope__hint">{hint}</span>
        ) : null}
      </span>
    </label>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="pf-facts__row">
      <dt className="pf-facts__label">{label}</dt>
      <dd className="pf-facts__value">{value}</dd>
    </div>
  );
}

function statusHint(unit: ContentUnit): string | undefined {
  if (unit.openToAll) return "Open to everyone";
  if (unit.status !== "published")
    return "Not published yet — a grant waits for it";
  return undefined;
}
