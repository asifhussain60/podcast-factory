#!/usr/bin/env bash
#
# Put the Listener live: one command, repeatable, always the right account.
#
#   scripts/podcast/deploy_listener.sh <slug> [<slug> …] [--dry-run] [--worker-only]
#   scripts/podcast/deploy_listener.sh --all [--dry-run]
#
# It does three things in order — deploy the Worker, push each book's content,
# upload each book's media — and it refuses to run against any Cloudflare account
# but asifhussain60@gmail.com.
#
# WHAT `--all` MEANS
# ------------------
# Every book the Listener ALREADY HAS, not every book this repo calls published.
# A book reaches the site the first time by being NAMED; after that `--all` keeps
# it current, which is what makes it safe to reach for after an afternoon of
# writing Companion notes across several books. The reason is cost: a book never
# sent brings its entire recording library with it, and a command whose everyday
# use is "push what I just wrote" must not upload several gigabytes because a
# book was marked published last week. Nothing is hidden by that — a book
# published here and never sent is reported by name on every `--all` run.
# See `_listener_slugs.py`.
#
# WHAT IT WILL NOT DO
# -------------------
# It never makes a book visible. `content_unit.status` and `open_to_all` are the
# two columns that decide whether anyone can see a book, and nothing in this
# script writes them: a book lands complete but as a draft, and a human turns it
# on in /admin. That is the whole reason running this twice by mistake, or on the
# wrong slug, cannot expose a half-finished book.
#
# WHY THE ACCOUNT CHECK IS FIRST
# ------------------------------
# `wrangler` on this machine is logged in as asifhussain60@hotmail.com, which
# does not hold the safinaverse.com zone. Exporting CLOUDFLARE_API_TOKEN beats
# that stored login — but forgetting to export it is silent: the command runs, it
# just runs somewhere else. So the token is read from the keychain here rather
# than assumed, and the resolved account id is verified before anything is
# uploaded.
#
# WHY A NON-ZERO EXIT FROM `wrangler deploy` IS TOLERATED
# -------------------------------------------------------
# The Worker uploads successfully and then wrangler reads
# `/zones/{id}/workers/routes` to reconcile the custom domain, which this token
# is denied. The domain is already attached — it went on through the ACCOUNT
# endpoint, which the same token is allowed to call — so that failure is noise.
# This script looks for the "Uploaded podcast-listener" line instead of trusting
# the exit code, and still fails loudly if that line is absent.

set -uo pipefail

readonly ACCOUNT_ID="19cb05067ea7e704f94481df1685ec51"
readonly ACCOUNT_NAME="asifhussain60@gmail.com"
readonly KEYCHAIN_SERVICE="cloudflare_api_token"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly REPO_ROOT
readonly LISTENER="$REPO_ROOT/listener"

DRY_RUN=""
WORKER_ONLY=""
ALL=""
SLUGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY_RUN="--dry-run" ;;
    --worker-only) WORKER_ONLY="yes" ;;
    --all)         ALL="yes" ;;
    -h|--help)     sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)            echo "unknown option: $arg" >&2; exit 2 ;;
    *)             SLUGS+=("$arg") ;;
  esac
done

if [[ ${#SLUGS[@]} -gt 0 && -n "$ALL" ]]; then
  echo "naming a book AND --all says two different things about which books to" >&2
  echo "push. Refusing to pick one: run it again with either, not both." >&2
  exit 2
fi

if [[ ${#SLUGS[@]} -eq 0 && -z "$WORKER_ONLY" && -z "$ALL" ]]; then
  echo "usage: $(basename "$0") <slug> [<slug> …] [--dry-run] [--worker-only]" >&2
  echo "       $(basename "$0") --all [--dry-run]" >&2
  echo "       naming no slug does nothing; --worker-only ships code alone;" >&2
  echo "       --all re-pushes every book the Listener already has." >&2
  exit 2
fi

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
die()  { printf '\n\033[31mstopped: %s\033[0m\n' "$1" >&2; exit 1; }

# --- The account -------------------------------------------------------------

step "Cloudflare account"

if ! security find-generic-password -s "$KEYCHAIN_SERVICE" >/dev/null 2>&1; then
  die "no keychain item '$KEYCHAIN_SERVICE'. Asif stores it himself with:
    security add-generic-password -U -a \"\$USER\" -s $KEYCHAIN_SERVICE -w"
fi

# Read once, never printed. The trailing newline a stored secret usually carries
# produces Cloudflare error 6111 if it survives into the header.
CLOUDFLARE_API_TOKEN="$(security find-generic-password -s "$KEYCHAIN_SERVICE" -w | tr -d '[:space:]')"
export CLOUDFLARE_API_TOKEN
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"

cd "$LISTENER" || die "no listener/ directory at $LISTENER"

if ! npx wrangler whoami 2>&1 | grep -q "$ACCOUNT_ID"; then
  die "the token does not resolve to $ACCOUNT_NAME ($ACCOUNT_ID).
Refusing to deploy — the other account on this machine does not hold the
safinaverse.com zone, so anything published there is unreachable."
fi
echo "  ok — $ACCOUNT_NAME"

# --- The database ------------------------------------------------------------
#
# BEFORE the Worker, and that order is the whole point: code that reads a table
# must never reach production ahead of the table. Migration 0006 added the
# reader's own state — progress, bookmarks, annotations — and a Worker shipped
# without it answers 500 on every one of those routes.
#
# `wrangler d1 migrations` keeps its own ledger in the database, so this is safe
# to run on every deploy: it applies what is missing and says so when nothing is.
# A dry run lists rather than applies.

step "Database"

pending="$(npx wrangler d1 migrations list podcast-listener --remote 2>&1)"
if grep -qi "no migrations to apply" <<<"$pending"; then
  echo "  ok — schema is current"
elif [[ -n "$DRY_RUN" ]]; then
  grep -E "^│|Migrations to be applied" <<<"$pending" | sed 's/^/  /'
  echo "  dry run — not applying"
else
  grep -E "^│|Migrations to be applied" <<<"$pending" | sed 's/^/  /'
  npx wrangler d1 migrations apply podcast-listener --remote \
    || die "the migration failed — the Worker was NOT deployed, so production is
still running against the schema it was built for."
fi

# --- No invented people in production ----------------------------------------
#
# `listener/scripts/seed-people.mjs` fills the LOCAL database with a hundred
# invented readers so the access screen can be looked at at size. Nothing in this
# script or in publish_to_listener.py touches `invite` or `access_grant`, the
# local database is a Miniflare file that is gitignored, and the seed has no
# remote mode — so there is no path by which those rows reach production.
#
# This checks anyway, and the difference matters: the three facts above are
# properties of today's code, and every one of them is one edit away from being
# false. This verifies the DESTINATION instead of reasoning about the route.
#
# It matches any address in a `.invalid` domain, which RFC 2606 reserves so that
# it can never resolve — so a match is never a real person, and any future
# fixture that follows the same convention is caught by the same net. It runs
# before the Worker ships and on a dry run too, which makes
# `--worker-only --dry-run` a read-only audit of who can sign in to the live site.
#
# It fails CLOSED, including when the count cannot be parsed: an invitation row is
# permission to sign in, so "I could not verify" has to stop the deploy exactly
# as "I found some" does. That matches the account check above, which is equally
# unforgiving about wrangler's output changing shape.

step "Invented people"

people_json="$(npx wrangler d1 execute podcast-listener --remote --json --command "
  SELECT (SELECT count(*) FROM invite WHERE email LIKE '%.invalid'
                                         OR email_raw LIKE '%.invalid') AS invites,
         (SELECT count(*) FROM access_grant WHERE user_email LIKE '%.invalid') AS grants;
" 2>&1)"

# The payload is passed as an argument, not on stdin: `python3 -` would itself be
# reading the program from stdin, and a second redirection would silently replace
# one with the other. wrangler prints progress lines before the JSON, so parsing
# starts at the first bracket.
people_count="$(python3 -c '
import json, sys
raw = sys.argv[1]
at = raw.find("[")
try:
    rows = json.loads(raw[at:])[0]["results"][0]
    print(int(rows["invites"]) + int(rows["grants"]))
except Exception:
    print("unparseable")
' "$people_json")"

case "$people_count" in
  0) echo "  ok — no reserved-domain addresses can sign in" ;;
  unparseable)
    printf '%s\n' "$people_json" | tail -12 >&2
    die "could not read the invitation list from production, so it cannot be
cleared as safe. Nothing was deployed. An invitation row is permission to sign
in — this check refuses to be skipped rather than pass on an unread answer."
    ;;
  *)
    die "production holds $people_count reserved-domain invitation/grant rows.
Those are fixture people, and on the live site every one of them is an address
genuinely permitted to sign in. Nothing was deployed. Remove them with:

  npx wrangler d1 execute podcast-listener --remote --command \\
    \"DELETE FROM access_grant WHERE user_email LIKE '%.invalid';
      DELETE FROM invite WHERE email LIKE '%.invalid' OR email_raw LIKE '%.invalid';\"

then run this again."
    ;;
esac

# --- Which books, when nobody named one --------------------------------------
#
# BEFORE the Worker, so `--all --dry-run` is a read-only listing of exactly what
# a real run would touch, and so a book list that cannot be read stops the deploy
# rather than shipping code and then failing.
#
# The rule and its reasoning live in `_listener_slugs.py`; this end only asks the
# database which books it holds and prints the answer.
#
# `unit_detail`, NOT `content_unit`. They sound interchangeable and are not:
# content_unit is the ACCESS record and `0003_seed_catalog.sql` seeded a row for
# every book in the repo, so it says nothing about what has been pushed — asking
# it returned all twenty-one books, including twelve volumes that have never been
# near the Listener. unit_detail is written ONLY by publish_to_listener.py, so a
# row in it means exactly "this book has been sent at least once", which is the
# question --all asks.

if [[ -n "$ALL" && -z "$WORKER_ONLY" ]]; then
  step "Books"

  books_json="$(npx wrangler d1 execute podcast-listener --remote --json --command "
    SELECT slug FROM unit_detail ORDER BY slug;
  " 2>&1)"

  resolved="$(python3 "$REPO_ROOT/scripts/podcast/_listener_slugs.py" "$books_json")" || {
    printf '%s\n' "$books_json" | tail -8 >&2
    die "could not read the book list from production, so --all cannot know what
it would push. Nothing was deployed. Name the books instead, or retry."
  }

  field() { grep "^$1" <<<"$resolved" | cut -f2-; }
  read -r -a SLUGS <<<"$(field DEPLOY)"
  missing="$(field MISSING)"
  unsent="$(field UNSENT)"

  if [[ ${#SLUGS[@]} -eq 0 ]]; then
    echo "  the Listener holds no book whose content is still in this repo —"
    echo "  nothing to push. Name a book to send it for the first time."
    WORKER_ONLY="yes"
  else
    printf '  %s\n' "${SLUGS[@]}"
  fi

  # Both of these are ordinary states, not faults, so they are reported and the
  # run continues. Silence would make `--all` look like it covered everything.
  [[ -n "$missing" ]] && echo "  ! on the Listener with no content here, skipped: $missing"
  [[ -n "$unsent" ]] && echo "  ! published here and never sent, name it to send it: $unsent"
fi

# --- Has the About page kept up? ---------------------------------------------
#
# `/about` is the one page that tells readers what the site does, and a page like
# that goes stale the way documentation always does — silently, because nothing
# depends on it. This is the thing that depends on it.
#
# It compares two commit dates: the last change to the About CONTENT, and the
# last change to anything else under `listener/app`. If the app is newer, the
# page has fallen behind whatever shipped since, and this says so.
#
# GIT is the comparison, not a date written into the file. A hand-kept "updated"
# field is a second copy of a fact the repository already holds exactly, and the
# copy is the one that goes wrong.
#
# IT NEVER BLOCKS, and that is deliberate rather than lenient. publish_to_library.py
# runs this same script at the end of every book publish — so a failing check here
# would mean a stale paragraph on a help page could refuse to publish a finished
# book. It joins the other things this script REPORTS: the books on the Listener
# with no content here, the ones published and never sent. A warning that stops
# work gets skipped with a flag; one that names the gap gets acted on.

step "What's new"

ABOUT="listener/app/lib/about.ts"

if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "  not a git checkout — skipped"
elif [[ ! -f "$REPO_ROOT/$ABOUT" ]]; then
  echo "  ! $ABOUT is missing — the About page has no content to check"
else
  about_at="$(git -C "$REPO_ROOT" log -1 --format=%ct -- "$ABOUT" 2>/dev/null)"
  # Everything under the app EXCEPT the About content, or it would always be
  # comparing that file against itself and never report anything.
  app_at="$(git -C "$REPO_ROOT" log -1 --format=%ct -- listener/app ":!$ABOUT" 2>/dev/null)"

  if [[ -z "$about_at" || -z "$app_at" ]]; then
    echo "  no history for one side yet — skipped"
  elif (( app_at > about_at )); then
    changed="$(git -C "$REPO_ROOT" log --format=%H --since="@$about_at" -- listener/app ":!$ABOUT" | wc -l | tr -d ' ')"
    printf '  ! the app changed in %s commit(s) since the About page was last written.\n' "$changed"
    printf '    Readers will not see those changes described. To look at what moved:\n'
    printf '      git log --oneline --since=@%s -- listener/app ":!%s"\n' "$about_at" "$ABOUT"
    printf '    Then add a note to RELEASES in %s.\n' "$ABOUT"
    printf '    Deploying anyway — this never blocks.\n'
  else
    echo "  ok — the About page is current with the app"
  fi
fi

# --- The Worker --------------------------------------------------------------

if [[ -n "$DRY_RUN" ]]; then
  step "Worker"
  echo "  dry run — not deploying"
else
  step "Worker"
  deploy_log="$(mktemp)"
  npm run deploy >"$deploy_log" 2>&1
  if grep -q "Uploaded podcast-listener" "$deploy_log"; then
    grep -E "Total Upload|Uploaded podcast-listener" "$deploy_log" | sed 's/^/  /'
    if ! grep -q "^.*Deployed podcast-listener" "$deploy_log"; then
      echo "  (wrangler exited non-zero on the zone routes read — expected, see the header)"
    fi
  else
    tail -25 "$deploy_log" >&2
    rm -f "$deploy_log"
    die "the Worker did not upload"
  fi
  rm -f "$deploy_log"
fi

[[ -n "$WORKER_ONLY" ]] && { printf '\n\033[1mdone — worker only\033[0m\n'; exit 0; }

# --- Content and media -------------------------------------------------------

cd "$REPO_ROOT" || die "cannot return to $REPO_ROOT"

# --- Transcripts -------------------------------------------------------------
#
# BEFORE the content push, because publish_to_listener.py records the transcript
# it finds on disk and cannot record one that is made afterwards.
#
# This is here rather than in a runbook because a transcript that has to be
# REMEMBERED is one that half the library will not have. It is keyed on the file
# existing, so the everyday re-push — a book pushed again after an afternoon of
# Companion notes — asks Azure for nothing and costs nothing; only a genuinely
# new episode is paid for, at about $0.30 an audio-hour under the standing Azure
# authorization. `--dry-run` prices the work and spends nothing.
#
# It does NOT stop the deploy when it fails. A transcript is an addition to an
# episode, and a book whose transcription errored should still reach the site
# with its recordings — the episode simply ships without one and says so. The
# failure is printed rather than swallowed.

step "Transcripts"
if ! python3 scripts/podcast/ensure_transcripts.py "${SLUGS[@]}" $DRY_RUN; then
  echo "  ! transcription failed — continuing, these episodes ship without one" >&2
fi

step "Content"
python3 scripts/podcast/publish_to_listener.py "${SLUGS[@]}" --remote $DRY_RUN \
  || die "publishing failed — see above"

step "Media"
python3 scripts/podcast/upload_listener_media.py "${SLUGS[@]}" --remote $DRY_RUN \
  || die "uploading failed — the books that did land are already live"

printf '\n\033[1mdone\033[0m — https://podcast-factory.safinaverse.com\n'
printf 'Nothing here changed who can SEE anything. A book new to the Listener is a\n'
printf 'draft until you switch it on at /admin.\n'
