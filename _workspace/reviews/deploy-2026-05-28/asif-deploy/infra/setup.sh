#!/usr/bin/env bash
# =============================================================================
# asif-deploy / infra / setup.sh
#
# One-file fire-and-forget installer for the asif-deploy + Cloudflare Pages +
# Cloudflare Access stack. Run on any fresh macOS or Linux machine and end up
# with a working public + SSO-gated deploy pipeline.
#
# Idempotent. Safe to re-run. Each phase checks state before acting.
#
# Phases:
#   0. Prerequisites              brew / node / jq / curl / python3
#   1. wrangler install           npm i -g wrangler
#   2. asif-deploy CLI symlink    ~/.local/bin/asif-deploy
#   3. wrangler OAuth login       wrangler login (interactive once)
#   4. Cloudflare API token       prompt + store in keychain
#   5. Cloudflare Pages projects  create asif-studio + asif-studio-private
#   6. Cloudflare Zero Trust      ensure org/team exists
#   7. Access identity provider   add One-Time PIN (email-based SSO)
#   8. Access application+policy  gate *.asif-studio-private.pages.dev
#   9. Smoke test — public        deploy examples/asif-studio-landing
#  10. Smoke test — private       deploy a small SSO-gated example
#  11. AI surface wrappers        install Claude Code agent, Cowork skill, Copilot prompt
#
# Usage:
#   ./infra/setup.sh                       # full run, interactive prompts
#   ./infra/setup.sh --dry-run             # print what would happen, no changes
#   ./infra/setup.sh --skip 0,11           # skip specific phases (comma-sep)
#   ./infra/setup.sh --only 4,5            # run only specific phases
#   ./infra/setup.sh --reset-token         # re-prompt for the Cloudflare API token
#   ./infra/setup.sh --help                # show this header
#
# Environment overrides (optional):
#   ASIF_DEPLOY_EMAIL           Email allowlisted on Access (default: prompt once)
#   ASIF_DEPLOY_PUBLIC_PROJECT  Public Pages project name (default: asif-studio)
#   ASIF_DEPLOY_PRIVATE_PROJECT Private Pages project name (default: asif-studio-private)
#   ASIF_DEPLOY_NONINTERACTIVE  If set, fail instead of prompting (CI mode)
#
# Exit codes:
#   0  success / no changes needed
#   1  user aborted
#   2  bad arguments
#   3  missing prerequisite (after install attempt)
#   4  Cloudflare API error
#   5  network failure
# =============================================================================

set -euo pipefail

# ---------- constants ----------
PUBLIC_PROJECT="${ASIF_DEPLOY_PUBLIC_PROJECT:-asif-studio}"
PRIVATE_PROJECT="${ASIF_DEPLOY_PRIVATE_PROJECT:-asif-studio-private}"
KEYCHAIN_TOKEN_SERVICE="cloudflare_asif_deploy_api_token"
CF_API="https://api.cloudflare.com/client/v4"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------- color / logging ----------
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    C_RESET="$(tput sgr0)"; C_BOLD="$(tput bold)"
    C_GREEN="$(tput setaf 2)"; C_YELLOW="$(tput setaf 3)"
    C_RED="$(tput setaf 1)"; C_BLUE="$(tput setaf 4)"; C_DIM="$(tput dim)"
else
    C_RESET=""; C_BOLD=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_BLUE=""; C_DIM=""
fi

phase() { printf "\n%s%s>>> Phase %s — %s%s\n" "$C_BOLD" "$C_BLUE" "$1" "$2" "$C_RESET"; }
ok()    { printf "    %s✓%s %s\n" "$C_GREEN" "$C_RESET" "$1"; }
info()  { printf "    %s•%s %s\n" "$C_DIM" "$C_RESET" "$1"; }
warn()  { printf "    %s⚠%s %s\n" "$C_YELLOW" "$C_RESET" "$1"; }
err()   { printf "    %s✗%s %s\n" "$C_RED" "$C_RESET" "$1" >&2; }
act()   { printf "    %s→%s %s\n" "$C_BLUE" "$C_RESET" "$1"; }
ask()   { printf "    %s?%s %s " "$C_YELLOW" "$C_RESET" "$1"; }

die() { err "$1"; exit "${2:-1}"; }

# ---------- argv parsing ----------
DRY_RUN=0; SKIP=""; ONLY=""; RESET_TOKEN=0; SHOW_HELP=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --skip) SKIP="${2:-}"; shift 2 ;;
        --only) ONLY="${2:-}"; shift 2 ;;
        --reset-token) RESET_TOKEN=1; shift ;;
        -h|--help) SHOW_HELP=1; shift ;;
        *) die "unknown arg: $1  (try --help)" 2 ;;
    esac
done

if [ "$SHOW_HELP" = 1 ]; then
    sed -n '2,/^# =\{30,\}/p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi

should_run() {
    local n="$1"
    [ -n "$ONLY" ] && { case ",$ONLY," in *",$n,"*) return 0 ;; *) return 1 ;; esac; }
    [ -n "$SKIP" ] && { case ",$SKIP," in *",$n,"*) return 1 ;; *) return 0 ;; esac; }
    return 0
}

dry() { if [ "$DRY_RUN" = 1 ]; then act "[dry-run] $*"; return 0; else "$@"; fi; }

# ---------- platform detect ----------
OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="macos"; KEYCHAIN_OK=1 ;;
    Linux)  PLATFORM="linux"; KEYCHAIN_OK=0 ;;
    *)      die "unsupported OS: $OS" 3 ;;
esac

# ---------- keychain helpers (macOS) / file fallback (Linux) ----------
TOKEN_FILE="$HOME/.config/asif-deploy/cf_api_token"

token_get() {
    if [ "$KEYCHAIN_OK" = 1 ]; then
        security find-generic-password -s "$KEYCHAIN_TOKEN_SERVICE" -a "$USER" -w 2>/dev/null || return 1
    else
        [ -f "$TOKEN_FILE" ] && cat "$TOKEN_FILE" || return 1
    fi
}

token_set() {
    local t="$1"
    if [ "$KEYCHAIN_OK" = 1 ]; then
        security delete-generic-password -s "$KEYCHAIN_TOKEN_SERVICE" -a "$USER" >/dev/null 2>&1 || true
        security add-generic-password -s "$KEYCHAIN_TOKEN_SERVICE" -a "$USER" -w "$t"
    else
        mkdir -p "$(dirname "$TOKEN_FILE")"
        umask 077; printf '%s\n' "$t" > "$TOKEN_FILE"
    fi
}

# ---------- Cloudflare API helpers ----------
cf_api() {
    local method="$1" path="$2" body="${3:-}"
    local token; token="$(token_get)" || die "no API token in keychain — re-run with --reset-token" 4
    local curl_args=(-sS -X "$method" -H "Authorization: Bearer $token" -H "Content-Type: application/json")
    [ -n "$body" ] && curl_args+=(--data "$body")
    curl "${curl_args[@]}" "${CF_API}${path}"
}

cf_ok() { echo "$1" | jq -e '.success == true' >/dev/null 2>&1; }
cf_err() { echo "$1" | jq -r '.errors[]?.message // "unknown error"' 2>/dev/null | head -1; }

# ---------- phases ----------

phase_0_prerequisites() {
    phase 0 "Prerequisites — brew, node, jq, curl, python3"

    if [ "$PLATFORM" = "macos" ]; then
        if ! command -v brew >/dev/null 2>&1; then
            warn "Homebrew not found. Installing…"
            dry /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        ok "brew $(brew --version 2>/dev/null | head -1)"
    fi

    for tool in node jq curl python3; do
        if command -v "$tool" >/dev/null 2>&1; then
            ok "$tool ($(command -v "$tool"))"
        else
            warn "$tool missing — installing"
            if [ "$PLATFORM" = "macos" ]; then
                dry brew install "$tool"
            else
                if command -v apt-get >/dev/null 2>&1; then
                    dry sudo apt-get install -y "$tool"
                elif command -v dnf >/dev/null 2>&1; then
                    dry sudo dnf install -y "$tool"
                else
                    die "no supported package manager — install $tool manually" 3
                fi
            fi
        fi
    done
}

phase_1_wrangler() {
    phase 1 "wrangler install"
    if command -v wrangler >/dev/null 2>&1; then
        ok "wrangler $(wrangler --version 2>/dev/null | head -1) already installed"
        return 0
    fi
    act "npm i -g wrangler"
    dry npm i -g wrangler
    [ "$DRY_RUN" = 1 ] && return 0
    command -v wrangler >/dev/null 2>&1 || die "wrangler install failed" 3
    ok "wrangler installed"
}

phase_2_cli_symlink() {
    phase 2 "asif-deploy CLI symlink"
    local target="$HOME/.local/bin/asif-deploy"
    local src="$REPO_DIR/bin/asif-deploy"
    [ -x "$src" ] || die "$src not found or not executable" 3
    mkdir -p "$HOME/.local/bin"
    if [ -L "$target" ] && [ "$(readlink "$target")" = "$src" ]; then
        ok "symlink already correct"
    else
        dry rm -f "$target"
        dry ln -s "$src" "$target"
        ok "symlinked $target → $src"
    fi
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ok "~/.local/bin on PATH" ;;
        *) warn "~/.local/bin NOT on PATH. Add:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
    esac
}

phase_3_wrangler_login() {
    phase 3 "wrangler OAuth login"
    if wrangler whoami 2>&1 | grep -q "You are logged in"; then
        local email
        email="$(wrangler whoami 2>&1 | grep -oE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+" | head -1)"
        ok "logged in as ${email:-<unknown>}"
        return 0
    fi
    if [ -n "${ASIF_DEPLOY_NONINTERACTIVE:-}" ]; then
        die "not logged in and ASIF_DEPLOY_NONINTERACTIVE set" 3
    fi
    act "wrangler login (will open browser)"
    dry wrangler login
    [ "$DRY_RUN" = 1 ] && return 0
    wrangler whoami 2>&1 | grep -q "You are logged in" || die "login still failing" 3
    ok "wrangler authenticated"
}

phase_4_api_token() {
    phase 4 "Cloudflare API token (for Access management)"

    if [ "$RESET_TOKEN" = 1 ]; then
        warn "Token reset requested"
    elif token_get >/dev/null 2>&1; then
        # Verify token still works
        local resp
        resp="$(cf_api GET /user/tokens/verify)" || true
        if cf_ok "$resp"; then
            ok "API token valid (stored in $([ "$KEYCHAIN_OK" = 1 ] && echo keychain || echo "$TOKEN_FILE"))"
            return 0
        fi
        warn "stored token failed verification — prompting for replacement"
    fi

    cat <<EOF
    Create an API token at:
      ${C_BOLD}https://dash.cloudflare.com/profile/api-tokens${C_RESET}
    Click "Create Token" → "Create Custom Token" → name it ${C_BOLD}asif-deploy${C_RESET}.

    Required permissions (add each row):
      Account  →  Cloudflare Pages         →  Edit
      Account  →  Access: Apps and Policies →  Edit
      Account  →  Access: Organizations, Identity Providers, and Groups  →  Edit
      Account  →  Account Settings         →  Read
      User     →  User Details             →  Read

    Account Resources: Include → All accounts (or just your one account)
    TTL: leave default (no expiry) or set 1 year.
EOF
    if [ -n "${ASIF_DEPLOY_NONINTERACTIVE:-}" ]; then
        die "need API token, in non-interactive mode" 3
    fi
    [ "$DRY_RUN" = 1 ] && { act "[dry-run] would prompt for token"; return 0; }
    printf "    %s?%s Paste token: " "$C_YELLOW" "$C_RESET"
    read -rs token; echo
    [ -z "$token" ] && die "no token entered" 1
    # Verify before storing
    local verify
    verify="$(curl -sS -H "Authorization: Bearer $token" "${CF_API}/user/tokens/verify")"
    cf_ok "$verify" || die "token verification failed: $(cf_err "$verify")" 4
    token_set "$token"
    ok "API token stored"
}

ACCOUNT_ID=""
get_account_id() {
    [ -n "$ACCOUNT_ID" ] && { echo "$ACCOUNT_ID"; return; }
    if [ "$DRY_RUN" = 1 ] && ! token_get >/dev/null 2>&1; then
        ACCOUNT_ID="<dry-run-no-token>"; echo "$ACCOUNT_ID"; return
    fi
    local resp; resp="$(cf_api GET /accounts)"
    cf_ok "$resp" || die "could not list accounts: $(cf_err "$resp")" 4
    ACCOUNT_ID="$(echo "$resp" | jq -r '.result[0].id')"
    [ -n "$ACCOUNT_ID" ] && [ "$ACCOUNT_ID" != "null" ] || die "no accounts returned" 4
    echo "$ACCOUNT_ID"
}

# Skip Cloudflare-API phases gracefully in dry-run when no token exists yet
needs_token() {
    if ! token_get >/dev/null 2>&1; then
        if [ "$DRY_RUN" = 1 ]; then
            info "(dry-run, no token) — would issue Cloudflare API calls"
            return 1
        fi
        die "no API token in keychain — re-run with --reset-token" 4
    fi
    return 0
}

phase_5_pages_projects() {
    phase 5 "Cloudflare Pages projects"
    needs_token || return 0
    local acct; acct="$(get_account_id)"
    for project in "$PUBLIC_PROJECT" "$PRIVATE_PROJECT"; do
        local resp; resp="$(cf_api GET "/accounts/$acct/pages/projects/$project" 2>/dev/null || true)"
        if cf_ok "$resp"; then
            ok "$project exists"
        else
            act "creating $project"
            if [ "$DRY_RUN" = 1 ]; then
                act "[dry-run] would POST /accounts/$acct/pages/projects (name=$project, production_branch=main)"
            else
                local body; body="$(jq -nc --arg n "$project" '{name: $n, production_branch: "main"}')"
                resp="$(cf_api POST "/accounts/$acct/pages/projects" "$body")"
                cf_ok "$resp" || die "create $project: $(cf_err "$resp")" 4
                ok "created $project"
            fi
        fi
    done
}

phase_6_zero_trust() {
    phase 6 "Cloudflare Zero Trust organization"
    needs_token || return 0
    local acct; acct="$(get_account_id)"
    local resp; resp="$(cf_api GET "/accounts/$acct/access/organizations" 2>/dev/null || true)"
    if cf_ok "$resp" && [ "$(echo "$resp" | jq -r '.result.auth_domain // ""')" != "" ]; then
        ok "Zero Trust org: $(echo "$resp" | jq -r '.result.auth_domain')"
        return 0
    fi
    local team="${ASIF_DEPLOY_TEAM_NAME:-asif-deploy-$(date +%s | tail -c 6)}"
    act "creating Zero Trust org with team subdomain '$team'"
    if [ "$DRY_RUN" = 1 ]; then
        act "[dry-run] would POST /accounts/$acct/access/organizations (auth_domain=$team.cloudflareaccess.com)"
        return 0
    fi
    local body; body="$(jq -nc --arg t "$team" '{
        name: "asif-deploy",
        auth_domain: ($t + ".cloudflareaccess.com"),
        login_design: { background_color: "#0f1115", text_color: "#f4f4f5", header_text: "asif-studio" }
    }')"
    resp="$(cf_api POST "/accounts/$acct/access/organizations" "$body")"
    cf_ok "$resp" || die "Zero Trust org create: $(cf_err "$resp")" 4
    ok "Zero Trust org created: $(echo "$resp" | jq -r '.result.auth_domain')"
}

phase_7_identity_provider() {
    phase 7 "Access identity provider (One-Time PIN)"
    needs_token || return 0
    local acct; acct="$(get_account_id)"
    local resp; resp="$(cf_api GET "/accounts/$acct/access/identity_providers")"
    if cf_ok "$resp" && echo "$resp" | jq -e '.result[] | select(.type == "onetimepin")' >/dev/null; then
        ok "One-Time PIN IdP already configured"
        return 0
    fi
    act "adding One-Time PIN IdP"
    if [ "$DRY_RUN" = 1 ]; then
        act "[dry-run] would POST /accounts/$acct/access/identity_providers (type=onetimepin)"
        return 0
    fi
    local body; body='{"name":"One-Time PIN","type":"onetimepin","config":{}}'
    resp="$(cf_api POST "/accounts/$acct/access/identity_providers" "$body")"
    cf_ok "$resp" || die "IdP create: $(cf_err "$resp")" 4
    ok "One-Time PIN IdP added"
}

phase_8_access_app() {
    phase 8 "Access application + policy for $PRIVATE_PROJECT"
    needs_token || return 0
    local acct; acct="$(get_account_id)"

    # Find the allowlist email
    local email="${ASIF_DEPLOY_EMAIL:-}"
    if [ -z "$email" ]; then
        email="$(wrangler whoami 2>&1 | grep -oE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+" | head -1 || true)"
    fi
    if [ -z "$email" ] && [ -z "${ASIF_DEPLOY_NONINTERACTIVE:-}" ]; then
        ask "Email to allow on $PRIVATE_PROJECT (yours):"
        read -r email
    fi
    [ -z "$email" ] && die "no allowlist email" 1

    local app_name="asif-studio-private"
    local app_domain="*.${PRIVATE_PROJECT}.pages.dev"

    # Check if app exists
    local resp; resp="$(cf_api GET "/accounts/$acct/access/apps")"
    cf_ok "$resp" || die "list access apps: $(cf_err "$resp")" 4
    local app_id; app_id="$(echo "$resp" | jq -r --arg n "$app_name" '.result[] | select(.name == $n) | .id' | head -1)"

    if [ -z "$app_id" ]; then
        act "creating Access app on $app_domain"
        if [ "$DRY_RUN" = 1 ]; then
            act "[dry-run] would create Access app + policy"
            return 0
        fi
        local body; body="$(jq -nc --arg name "$app_name" --arg d "$app_domain" '{
            name: $name, domain: $d, type: "self_hosted", session_duration: "24h",
            allowed_idps: [], auto_redirect_to_identity: false
        }')"
        resp="$(cf_api POST "/accounts/$acct/access/apps" "$body")"
        cf_ok "$resp" || die "create access app: $(cf_err "$resp")" 4
        app_id="$(echo "$resp" | jq -r '.result.id')"
        ok "Access app created (id=$app_id)"
    else
        ok "Access app already exists (id=$app_id)"
    fi

    # Check policy
    resp="$(cf_api GET "/accounts/$acct/access/apps/$app_id/policies")"
    cf_ok "$resp" || die "list policies: $(cf_err "$resp")" 4
    local pol_id; pol_id="$(echo "$resp" | jq -r '.result[] | select(.name == "Allowed users") | .id' | head -1)"

    if [ -z "$pol_id" ]; then
        act "creating policy 'Allowed users' (email=$email)"
        if [ "$DRY_RUN" = 1 ]; then
            act "[dry-run] would POST policy"
            return 0
        fi
        local body; body="$(jq -nc --arg email "$email" '{
            name: "Allowed users", decision: "allow", precedence: 1,
            include: [{ email: { email: $email } }]
        }')"
        resp="$(cf_api POST "/accounts/$acct/access/apps/$app_id/policies" "$body")"
        cf_ok "$resp" || die "create policy: $(cf_err "$resp")" 4
        ok "Policy created"
    else
        # Make sure email is in the allowlist
        local existing; existing="$(cf_api GET "/accounts/$acct/access/apps/$app_id/policies/$pol_id" \
            | jq -r --arg e "$email" '[.result.include[]?.email?.email] | any(. == $e)')"
        if [ "$existing" = "true" ]; then
            ok "Policy already allows $email"
        else
            act "adding $email to allowlist"
            if [ "$DRY_RUN" = 1 ]; then return 0; fi
            local current; current="$(cf_api GET "/accounts/$acct/access/apps/$app_id/policies/$pol_id" \
                | jq '.result.include // []')"
            local body; body="$(jq -nc --argjson cur "$current" --arg e "$email" '{
                include: ($cur + [{ email: { email: $e } }])
            }')"
            resp="$(cf_api PUT "/accounts/$acct/access/apps/$app_id/policies/$pol_id" "$body")"
            cf_ok "$resp" || die "update policy: $(cf_err "$resp")" 4
            ok "$email added"
        fi
    fi
}

phase_9_smoke_public() {
    phase 9 "Smoke test — public deploy"
    local example="$REPO_DIR/examples/asif-studio-landing"
    if [ ! -d "$example" ]; then
        warn "$example missing — skipping (set up the landing page manually or run phase later)"
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        act "[dry-run] would deploy $example to $PUBLIC_PROJECT"
        return 0
    fi
    "$REPO_DIR/bin/asif-deploy" "$example" --slug main -m "infra/setup.sh smoke test" --json | jq .
    ok "public smoke test deploy complete"
}

phase_10_smoke_private() {
    phase 10 "Smoke test — private deploy"
    local example="$REPO_DIR/examples/private-smoke"
    if [ ! -d "$example" ]; then
        info "creating $example/index.html for smoke test"
        if [ "$DRY_RUN" = 0 ]; then
            mkdir -p "$example"
            cat > "$example/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>asif-studio-private smoke test</title>
<style>body{font-family:system-ui;background:#0f1115;color:#f4f4f5;display:grid;place-items:center;min-height:100vh;margin:0}</style>
<main><h1>🔒 SSO-gated test page</h1><p>If you see this, Cloudflare Access let you in.</p></main>
HTML
        fi
    fi
    if [ "$DRY_RUN" = 1 ]; then
        act "[dry-run] would deploy $example to $PRIVATE_PROJECT"
        return 0
    fi
    "$REPO_DIR/bin/asif-deploy" "$example" --slug smoke --private -m "infra/setup.sh smoke test" --json | jq .
    ok "private smoke test deployed — visit URL above, expect login page"
}

phase_11_ai_wrappers() {
    phase 11 "AI surface wrappers"

    # Claude Code agent
    local cc_dir="$HOME/.claude/agents"
    local cc_src="$REPO_DIR/wrappers/claude-code/site-deployer.md"
    if [ -f "$cc_src" ]; then
        dry mkdir -p "$cc_dir"
        dry cp "$cc_src" "$cc_dir/site-deployer.md"
        ok "Claude Code: $cc_dir/site-deployer.md"
    else
        warn "Claude Code wrapper not found at $cc_src"
    fi

    # Copilot prompt (user-level on macOS)
    if [ "$PLATFORM" = "macos" ]; then
        local cp_dir="$HOME/Library/Application Support/Code/User/prompts"
        local cp_src="$REPO_DIR/wrappers/copilot/deploy-site.prompt.md"
        if [ -f "$cp_src" ]; then
            dry mkdir -p "$cp_dir"
            dry cp "$cp_src" "$cp_dir/deploy-site.prompt.md"
            ok "Copilot (VS Code user prompts): $cp_dir/deploy-site.prompt.md"
            info "In VS Code settings.json: set \"chat.promptFiles\": true"
        else
            warn "Copilot wrapper not found at $cp_src"
        fi
    fi

    # Cowork skill
    local sk_src="$REPO_DIR/wrappers/cowork-skill/site-deployer.skill"
    if [ -f "$sk_src" ]; then
        ok "Cowork skill bundle: $sk_src"
        info "open it in Cowork to install (cannot be done programmatically)"
    else
        warn "Cowork .skill bundle not found at $sk_src"
    fi
}

# ---------- final report ----------
summary() {
    local acct; acct="$(token_get >/dev/null 2>&1 && get_account_id || echo "<not set>")"
    echo
    printf "%s================================================================%s\n" "$C_BOLD" "$C_RESET"
    printf "%s  asif-deploy infra summary%s\n" "$C_BOLD" "$C_RESET"
    printf "%s================================================================%s\n" "$C_BOLD" "$C_RESET"
    printf "  Account ID:        %s\n" "$acct"
    printf "  Public project:    %s   →  https://%s.pages.dev\n" "$PUBLIC_PROJECT" "$PUBLIC_PROJECT"
    printf "  Private project:   %s   →  https://%s.pages.dev  (SSO-gated)\n" "$PRIVATE_PROJECT" "$PRIVATE_PROJECT"
    printf "  CLI:               %s\n" "$(command -v asif-deploy || echo '~/.local/bin/asif-deploy')"
    printf "  Token storage:     %s\n" "$([ "$KEYCHAIN_OK" = 1 ] && echo "macOS keychain ($KEYCHAIN_TOKEN_SERVICE)" || echo "$TOKEN_FILE")"
    echo
    printf "  Try it:\n"
    printf "    asif-deploy ./some-folder                 # public deploy\n"
    printf "    asif-deploy ./some-folder --private       # SSO-gated deploy\n"
    printf "    asif-deploy --doctor                      # verify\n"
    echo
}

# ---------- main ----------
main() {
    if [ "$DRY_RUN" = 1 ]; then
        printf "%s%s[DRY RUN — no changes will be made]%s\n" "$C_BOLD" "$C_YELLOW" "$C_RESET"
    fi

    for n in 0 1 2 3 4 5 6 7 8 9 10 11; do
        if ! should_run "$n"; then
            info "skipping phase $n"
            continue
        fi
        case "$n" in
            0) phase_0_prerequisites ;;
            1) phase_1_wrangler ;;
            2) phase_2_cli_symlink ;;
            3) phase_3_wrangler_login ;;
            4) phase_4_api_token ;;
            5) phase_5_pages_projects ;;
            6) phase_6_zero_trust ;;
            7) phase_7_identity_provider ;;
            8) phase_8_access_app ;;
            9) phase_9_smoke_public ;;
            10) phase_10_smoke_private ;;
            11) phase_11_ai_wrappers ;;
        esac
    done

    summary
}

main "$@"
