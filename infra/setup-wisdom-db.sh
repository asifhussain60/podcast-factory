#!/usr/bin/env bash
# setup-wisdom-db.sh — one-time setup for the wisdom-mssql Docker container.
#
# Creates the container, waits for SQL Server to be ready, then restores all
# three databases from the local SQL dump files. Safe to re-run: skips steps
# that are already done (container exists, database already has rows).
#
# Usage:
#   bash scripts/setup-wisdom-db.sh
#
# Prerequisites:
#   - Docker (OrbStack or Docker Desktop) installed and running
#   - SQL dump files present at CONTENT/_shared/source-library/
#     (KQur.sql 15 MB, KSessions.sql 29 MB, Kashkole.sql 724 MB)
#
# Runtime: ~3-5 minutes (dominated by Kashkole restore)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SQL_DIR="$REPO_ROOT/CONTENT/_shared/source-library"
CONTAINER="wisdom-mssql"
PASSWORD="Kashkole_Local_2026!"
IMAGE="mcr.microsoft.com/mssql/server:2022-latest"

# ── colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${YELLOW}→${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── 1. Check docker is available ─────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    fail "docker not found. Install OrbStack (brew install orbstack) or Docker Desktop, then re-run."
fi
docker info &>/dev/null || fail "Docker daemon is not running. Start OrbStack or Docker Desktop first."

# ── 2. Check SQL dump files are present ──────────────────────────────────────
for f in KQur.sql KSessions.sql Kashkole.sql; do
    [[ -f "$SQL_DIR/$f" ]] || fail "Missing dump file: $SQL_DIR/$f"
done
ok "SQL dump files found"

# ── 3. Create container if it doesn't exist ───────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    info "Container '$CONTAINER' already exists — starting if stopped"
    docker start "$CONTAINER" &>/dev/null || true
else
    info "Creating container '$CONTAINER'..."
    docker run -d \
        --name "$CONTAINER" \
        -e "ACCEPT_EULA=Y" \
        -e "SA_PASSWORD=$PASSWORD" \
        -e "MSSQL_PID=Developer" \
        -p 1433:1433 \
        "$IMAGE" &>/dev/null
    ok "Container created"
fi

# ── 4. Wait for SQL Server to accept connections ──────────────────────────────
info "Waiting for SQL Server to be ready..."
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "$PASSWORD" -C \
        -Q "SELECT 1" &>/dev/null 2>&1; then
        ok "SQL Server ready (attempt $i)"
        break
    fi
    if [[ $i -eq 30 ]]; then
        fail "SQL Server did not become ready after 60s. Check: docker logs $CONTAINER"
    fi
    sleep 2
done

# ── 5. Helper: restore one database from a UTF-16 dump file ──────────────────
restore_db() {
    local db_name="$1"
    local sql_file="$2"
    local marker="$3"
    local count_query="$4"

    # Check if already has data
    local existing
    existing=$(docker exec "$CONTAINER" \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "$PASSWORD" -C \
        -Q "$count_query" 2>/dev/null | grep -E '^\s*[0-9]+' | tr -d ' ' || echo "0")

    if [[ "$existing" -gt 0 ]]; then
        ok "$db_name already restored ($existing rows) — skipping"
        return
    fi

    info "Restoring $db_name from $(basename "$sql_file")..."

    # Create database if missing
    docker exec "$CONTAINER" \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "$PASSWORD" -C \
        -Q "IF DB_ID('$db_name') IS NULL CREATE DATABASE [$db_name];" &>/dev/null

    # Convert UTF-16 → UTF-8, skip preamble, write to tmp, copy into container
    local tmp_utf8
    tmp_utf8=$(mktemp /tmp/wisdom_restore_XXXXXX.sql)
    python3 - "$sql_file" "$marker" "$tmp_utf8" << 'PYEOF'
import sys
path, marker, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, 'rb') as f:
    sql = f.read().decode('utf-16')
idx = sql.find(marker)
if idx == -1:
    print(f"ERROR: marker '{marker}' not found in {path}", file=sys.stderr)
    sys.exit(1)
with open(out_path, 'wb') as f:
    f.write(sql[idx:].encode('utf-8'))
PYEOF

    local size_mb=$(( $(wc -c < "$tmp_utf8") / 1048576 ))
    info "  Piping ${size_mb} MB into container..."

    local container_tmp="/tmp/wisdom_restore_$$.sql"
    docker cp "$tmp_utf8" "$CONTAINER:$container_tmp"
    rm -f "$tmp_utf8"

    docker exec "$CONTAINER" \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "$PASSWORD" -C \
        -i "$container_tmp" &>/dev/null

    docker exec "$CONTAINER" rm -f "$container_tmp" &>/dev/null || true
    ok "$db_name restored"
}

# ── 6. Restore each database ──────────────────────────────────────────────────
restore_db \
    "KQUR" \
    "$SQL_DIR/KQur.sql" \
    "USE [KQUR]" \
    "SELECT COUNT(*) FROM KQUR.dbo.QuranAyats;"

restore_db \
    "KSESSIONS" \
    "$SQL_DIR/KSessions.sql" \
    "USE [KSESSIONS]" \
    "SELECT COUNT(*) FROM KSESSIONS.dbo.Sessions;"

restore_db \
    "KASHKOLE" \
    "$SQL_DIR/Kashkole.sql" \
    "USE [KASHKOLE]" \
    "SELECT COUNT(*) FROM KASHKOLE.dbo.Topics;"

# ── 7. Verification ───────────────────────────────────────────────────────────
echo ""
info "Verifying row counts..."
docker exec "$CONTAINER" \
    /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P "$PASSWORD" -C \
    -Q "
SELECT 'KQUR.QuranAyats'         AS [table], COUNT(*) AS rows FROM KQUR.dbo.QuranAyats
UNION ALL
SELECT 'KSESSIONS.Sessions',       COUNT(*) FROM KSESSIONS.dbo.Sessions
UNION ALL
SELECT 'KASHKOLE.Topics',          COUNT(*) FROM KASHKOLE.dbo.Topics
" 2>&1 | grep -v "Changed database"

echo ""
ok "wisdom-mssql is ready. Start the source library server with:"
echo "   python3 scripts/podcast/source_library_server.py"
echo "   # or register with MCP:"
echo "   python3 scripts/podcast/source_library_server.py --register"
