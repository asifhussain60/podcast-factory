#!/usr/bin/env bash
set -euo pipefail

LABEL="com.asif.podcast-factory.plan-dashboard"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
APP_DIR="/Users/asifhussain/PROJECTS/podcast-factory/plan-dashboard"
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

write_plist() {
  ensure_dirs
  cat >"${PLIST}" <<PLIST
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
    <string>cd ${APP_DIR} &amp;&amp; node scripts/regenerate-snapshots.mjs &amp;&amp; npm run dev -- --host 127.0.0.1 --port ${PORT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${APP_DIR}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

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
Usage: $0 <install|start|stop|restart|status|open|logs|uninstall>

Commands:
  install    Write plist and load launch agent
  start      Start (or install+start if missing)
  stop       Stop/unload launch agent
  restart    Stop then start
  status     Show launchctl + port + health status
  open       Open dashboard URL in browser
  logs       Tail launchd logs
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
  uninstall) uninstall_agent ;;
  *) usage; exit 1 ;;
esac
