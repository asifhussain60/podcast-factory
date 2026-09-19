#!/usr/bin/env bash
set -euo pipefail

LABEL="com.asif.podcast-factory.plan-dashboard"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
# Resolve repo root relative to this script — works on any machine
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${REPO_ROOT}/plan-dashboard"
PORT="${PLAN_DASHBOARD_PORT:-4322}"
URL="http://127.0.0.1:${PORT}"
HEALTH_URL="${URL}/plan"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
OUT_LOG="${APP_DIR}/dev.launchd.log"
ERR_LOG="${APP_DIR}/dev.launchd.err.log"

ensure_dirs() {
  mkdir -p "${HOME}/Library/LaunchAgents"
  mkdir -p "${APP_DIR}"
}

# The job runs `zsh -lc` with a minimal PATH, and node lives under nvm, which only nvm.sh puts on PATH. Without
# this the job exits 127 ("command not found: node") and, with KeepAlive, spun 8,334 times (2026-09-19). Sourcing
# nvm.sh also selects the user's default alias, so it follows node upgrades instead of pinning a version.
NVM_PRELUDE='export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] &amp;&amp; . "$NVM_DIR/nvm.sh";'  # XML-escaped: it is pasted into the plist

plist_xml() {
  cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>${NVM_PRELUDE} cd ${APP_DIR} &amp;&amp; node scripts/regenerate-snapshots.mjs &amp;&amp; npm run dev -- --host 127.0.0.1 --port ${PORT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${APP_DIR}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <!-- A failing start is retried at most every 2 minutes, not every ~10 seconds. -->
  <key>ThrottleInterval</key>
  <integer>120</integer>

  <key>StandardOutPath</key>
  <string>${OUT_LOG}</string>

  <key>StandardErrorPath</key>
  <string>${ERR_LOG}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>NODE_ENV</key>
    <string>development</string>
  </dict>
</dict>
</plist>
PLIST
}

write_plist() {
  ensure_dirs
  plist_xml >"${PLIST}"
}

is_loaded() {
  launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1
}

install_agent() {
  write_plist

  if is_loaded; then
    launchctl bootout "${DOMAIN}" "${PLIST}" >/dev/null 2>&1 || true
  fi

  launchctl bootstrap "${DOMAIN}" "${PLIST}"
  launchctl enable "${DOMAIN}/${LABEL}" >/dev/null 2>&1 || true
  launchctl kickstart -k "${DOMAIN}/${LABEL}"
}

start_agent() {
  if ! is_loaded; then
    install_agent
    return
  fi
  launchctl kickstart -k "${DOMAIN}/${LABEL}"
}

stop_agent() {
  if is_loaded; then
    launchctl bootout "${DOMAIN}" "${PLIST}" >/dev/null 2>&1 || true
  fi
}

status_agent() {
  echo "label: ${LABEL}"
  echo "plist: ${PLIST}"
  if is_loaded; then
    echo "state: loaded"
    launchctl print "${DOMAIN}/${LABEL}" | grep -E "state =|pid =|last exit code" || true
  else
    echo "state: not loaded"
  fi

  echo
  echo "listener:"
  lsof -iTCP:"${PORT}" -sTCP:LISTEN -n -P || true

  echo
  echo "health: ${HEALTH_URL}"
  for _ in $(seq 1 10); do
    if curl -fsS --max-time 2 "${HEALTH_URL}" >/dev/null 2>&1; then
      echo "healthy"
      return 0
    fi
    sleep 1
  done
  echo "not healthy"
}

open_dashboard() {
  open "${URL}"
}

show_logs() {
  tail -n 120 "${OUT_LOG}" "${ERR_LOG}" 2>/dev/null || true
}

uninstall_agent() {
  stop_agent
  rm -f "${PLIST}"
}

usage() {
  cat <<USAGE
Usage: $0 <install|start|stop|restart|status|open|logs|print-plist|uninstall>

Commands:
  install    Write plist and load launch agent
  start      Start (or install+start if missing)
  stop       Stop/unload launch agent
  restart    Stop then start
  status     Show launchctl + port + health status
  open       Open dashboard URL in browser
  logs       Tail launchd logs
  print-plist  Print the plist that install would write (read-only)
  uninstall  Stop and remove plist
USAGE
}

cmd="${1:-status}"
case "${cmd}" in
  install) install_agent ;;
  start) start_agent ;;
  stop) stop_agent ;;
  restart) stop_agent; start_agent ;;
  status) status_agent ;;
  open) open_dashboard ;;
  logs) show_logs ;;
  print-plist) plist_xml ;;
  uninstall) uninstall_agent ;;
  *) usage; exit 1 ;;
esac
