#!/usr/bin/env bash
#
# Put the Listener live: one command, repeatable, always the right account.
#
#   scripts/podcast/deploy_listener.sh <slug> [<slug> …] [--dry-run] [--worker-only]
#
# It does three things in order — deploy the Worker, push each book's content,
# upload each book's media — and it refuses to run against any Cloudflare account
# but asifhussain60@gmail.com.
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
SLUGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY_RUN="--dry-run" ;;
    --worker-only) WORKER_ONLY="yes" ;;
    -h|--help)     sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)            echo "unknown option: $arg" >&2; exit 2 ;;
    *)             SLUGS+=("$arg") ;;
  esac
done

if [[ ${#SLUGS[@]} -eq 0 && -z "$WORKER_ONLY" ]]; then
  echo "usage: $(basename "$0") <slug> [<slug> …] [--dry-run] [--worker-only]" >&2
  echo "       naming no slug does nothing; --worker-only ships code alone." >&2
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

step "Content"
python3 scripts/podcast/publish_to_listener.py "${SLUGS[@]}" --remote $DRY_RUN \
  || die "publishing failed — see above"

step "Media"
python3 scripts/podcast/upload_listener_media.py "${SLUGS[@]}" --remote $DRY_RUN \
  || die "uploading failed — the books that did land are already live"

printf '\n\033[1mdone\033[0m — https://podcast-factory.safinaverse.com\n'
printf 'Nothing here changed who can SEE anything. A book new to the Listener is a\n'
printf 'draft until you switch it on at /admin.\n'
