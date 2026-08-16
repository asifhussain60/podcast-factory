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
# Every remote Cloudflare command must resolve to the Gmail account that holds
# safinaverse.com. So the token is read from the keychain here rather than
# assumed, and the resolved account id is verified before anything is uploaded.
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

# --- Branch sweep --------------------------------------------------------------
#
# Every book runs on its own branch (see CLAUDE.md's branch policy), but the
# Listener is not book-specific code — a header fix or a title-plate fix made
# while a book branch happened to be checked out still belongs on develop, and
# production can only ever be built from develop's working tree. Before
# 2026-08-05 that fix could land on a book branch and simply never reach
# develop until someone noticed the live site still showed the bug — which is
# exactly what happened to the book-page title plate (fixed on
# Islamic/spiritual-ethos, never merged, still circular in production).
#
# This walks every other local/remote branch, finds commits touching
# `listener/` that are not yet reachable from develop, and cherry-picks them in
# (oldest first, by commit time) — `-x` so each pick records which commit it
# came from. Content-only commits (everything under `content/`) are never
# touched: a book's own branch stays the only place its content changes until
# that book's own publish step merges it.
#
# Asif, 2026-08-05: standing default from here on — always sweep before
# deploying, never a manual step to remember.

step "Branch sweep"

git -C "$REPO_ROOT" fetch origin --quiet 2>&1 || echo "  ! fetch failed — sweeping local refs only" >&2

current_branch="$(git -C "$REPO_ROOT" branch --show-current)"
if [[ "$current_branch" != "develop" ]]; then
  echo "  on $current_branch — switching to develop for the deploy"
  git -C "$REPO_ROOT" checkout develop || die "could not switch to develop"
fi
git -C "$REPO_ROOT" pull --ff-only origin develop \
  || die "develop is not fast-forwardable against origin — resolve manually, then re-run"

# Content-based, not SHA-based: a commit cherry-picked here on a previous
# sweep gets a NEW sha, so comparing shas would flag its original forever and
# re-pick it every run. `git patch-id` fingerprints a commit by its diff, so a
# commit already folded into develop under a different sha is recognised as
# already applied and skipped.
#
# (No `mapfile`/`readarray`/`declare -A` - this machine's `/bin/bash` is
# Apple's stock 3.2, which predates all three, so plain read loops and a temp
# file stand in for them. That same old bash also mis-parses a comment
# containing a multibyte character, such as an em dash, when the comment
# sits inside a process substitution `<( ... )` - it throws "bad
# substitution: no closing ')'" and swallows the rest of the script. So every
# comment explaining the exclusions below lives up here, in plain top-level
# script, and the loop itself stays ASCII and comment-free.
#
# `main`'s own release-promotion merges, and release-please's automated
# branches (which fork from main and carry its history), are not independent
# listener work - they are main's own bookkeeping. A commit reachable from
# develop OR from main is therefore excluded from the search entirely (`git
# log ref --not develop main`), not merely from the candidate list, so
# release's own merge commits are never even considered. Merge commits are
# excluded too (`--no-merges`): a merge's own "diff" is its conflict
# resolution rather than a feature in its own right, and cherry-picking one
# cleanly needs `-m` and a mainline choice this sweep has no basis to make -
# the ordinary commits it merged are picked up on their own instead.
develop_pids="$(mktemp)"
git -C "$REPO_ROOT" log develop --format=%H -- listener/ \
  | while read -r h; do git -C "$REPO_ROOT" show "$h" | git -C "$REPO_ROOT" patch-id --stable; done \
  | awk '{print $1}' | sort -u > "$develop_pids"

skip_ref() {
  case "$1" in
    (develop|origin/develop|origin/HEAD|main|origin/main|origin/release-please--*) return 0 ;;
    (*) return 1 ;;
  esac
}

stray=()
while IFS= read -r sha; do
  [[ -n "$sha" ]] || continue
  pid="$(git -C "$REPO_ROOT" show "$sha" | git -C "$REPO_ROOT" patch-id --stable | awk '{print $1}')"
  if [[ -n "$pid" ]] && grep -qxF "$pid" "$develop_pids"; then
    continue
  fi
  stray+=("$sha")
done < <(
  { for ref in $(git -C "$REPO_ROOT" for-each-ref --format='%(refname:short)' refs/heads refs/remotes/origin); do
      skip_ref "$ref" && continue
      git -C "$REPO_ROOT" log "$ref" --not develop main --no-merges --format='%ct %H' -- listener/ 2>/dev/null
    done
  } | sort -n | awk '{print $2}' | awk '!seen[$0]++'
)
rm -f "$develop_pids"

if [[ ${#stray[@]} -eq 0 ]]; then
  echo "  ok — nothing stranded on other branches"
elif [[ -n "$DRY_RUN" ]]; then
  echo "  found ${#stray[@]} listener commit(s) stranded elsewhere — dry run, not merging:"
  for sha in "${stray[@]}"; do
    printf '    %s\n' "$(git -C "$REPO_ROOT" log -1 --format='%h %s' "$sha")"
  done
else
  echo "  found ${#stray[@]} listener commit(s) stranded elsewhere — merging into develop:"
  for sha in "${stray[@]}"; do
    printf '    %s\n' "$(git -C "$REPO_ROOT" log -1 --format='%h %s' "$sha")"
    git -C "$REPO_ROOT" cherry-pick -x "$sha" \
      || die "cherry-pick of $sha failed — resolve the conflict manually, then re-run"
  done
  git -C "$REPO_ROOT" push origin develop || die "could not push develop after the sweep"
fi

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

# --- main, synced before anything reaches production --------------------------
#
# Asif, 2026-08-05: standing default — a production deploy first fast-forwards
# (or merges) `main` up to `develop`, so `main` always reflects what is
# actually live rather than lagging behind it. This supersedes, for this one
# flow only, the repo-wide "develop -> main is a manual, always-ask gate" rule
# in CLAUDE.md — that rule still governs every OTHER develop -> main merge
# (regular content releases, unrelated feature work). It does not remove the
# separate, still-mandatory gate that nothing here runs until Asif has tried
# the change on localhost:5273 himself; this step runs only once that has
# already happened, immediately before the Worker upload below.

if [[ -z "$DRY_RUN" ]]; then
  step "Production branch"

  git -C "$REPO_ROOT" fetch origin main --quiet 2>&1 || echo "  ! fetch failed — using local main" >&2
  git -C "$REPO_ROOT" checkout main || die "could not switch to main"
  git -C "$REPO_ROOT" pull --ff-only origin main \
    || die "main is not fast-forwardable against origin — resolve manually, then re-run"

  if git -C "$REPO_ROOT" merge --ff-only develop >/dev/null 2>&1; then
    echo "  fast-forwarded main to develop"
  else
    git -C "$REPO_ROOT" merge --no-ff develop -m "release: sync main with develop for Listener deploy" \
      || die "main would not merge cleanly with develop — resolve the conflict manually, then re-run"
    echo "  merged develop into main"
  fi
  git -C "$REPO_ROOT" push origin main || die "could not push main"
  git -C "$REPO_ROOT" checkout develop || die "could not switch back to develop"
else
  step "Production branch"
  echo "  dry run — not merging into main"
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

  # Record what just shipped. Read by `_production_publish.code_behind`, so the
  # Publish button on the Composer can say "the live site is N commits behind"
  # instead of guessing — that button moves a BOOK and never ships code, which
  # is only safe if it can tell when code is stale. Untracked on purpose: it is
  # a fact about THIS machine's last deploy, and a tracked file would conflict
  # on every deploy while telling a fresh clone something untrue.
  git -C "$REPO_ROOT" rev-parse HEAD > "$REPO_ROOT/listener/.deployed-commit"
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

# Groups multi-volume works (content/<Bucket>/_listener-groups/*.yml,
# content/<Bucket>/<slug>/work.yml) into their `kind='work'` parent row and
# links each volume's `work_slug` — the site's stacked-card grouping needs
# both to exist before it will show a set instead of separate books. Runs
# over EVERY manifest in the repo, not just $SLUGS: a volume can be pushed
# on its own run long before its siblings are, and the work row has to
# exist the moment two of them are visible together, not only on the run
# that happens to touch every volume at once. Idempotent (see the script's
# own ON CONFLICT clauses), so running it on every deploy costs nothing
# when nothing changed.
step "Work groups"
python3 scripts/podcast/sync_listener_work_groups.py --remote $DRY_RUN \
  || die "grouping multi-volume works failed — see above"

step "Media"
python3 scripts/podcast/upload_listener_media.py "${SLUGS[@]}" --remote $DRY_RUN \
  || die "uploading failed — the books that did land are already live"

printf '\n\033[1mdone\033[0m — https://podcast-factory.safinaverse.com\n'
printf 'Nothing here changed who can SEE anything. A book new to the Listener is a\n'
printf 'draft until you switch it on at /admin.\n'
