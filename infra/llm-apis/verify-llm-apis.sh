#!/usr/bin/env bash
# verify-llm-apis.sh — confirm Claude (Max subscription via Claude Code)
# and Google Gemini (paid-tier API key) are both reachable from this Mac.
#
# Read-only. Does not modify keychain. Does not consume meaningful tokens
# (Gemini probe is a metadata GET; Claude probe is skipped by default to
# avoid burning a subscription call — pass --claude to include it).
#
# Exit codes:
#   0 = all checks passed
#   1 = at least one check failed (details in output)

set -uo pipefail

INCLUDE_CLAUDE=0
if [ "${1:-}" = "--claude" ]; then
  INCLUDE_CLAUDE=1
fi

FAIL=0

echo "==> [1/3] Anthropic (Claude Code + Max subscription)"
if command -v claude >/dev/null 2>&1; then
  echo "    claude CLI: $(claude --version 2>&1 | head -1)"
  if [ "$INCLUDE_CLAUDE" = "1" ]; then
    OUT=$(echo "say only the word: ready" | claude -p 2>&1 || true)
    if echo "$OUT" | grep -qi "ready"; then
      echo "    OK   claude -p responded with 'ready'"
    else
      echo "    FAIL claude -p response did not contain 'ready':"
      echo "         $OUT" | head -3
      FAIL=1
    fi
  else
    echo "    SKIP live probe (pass --claude to include — consumes one call)"
  fi
else
  echo "    FAIL claude CLI not on PATH (brew install --cask claude-code)"
  FAIL=1
fi

echo
echo "==> [2/3] Google Gemini (keychain entry + API reachability)"
if KEY=$(security find-generic-password -s gemini_api_key -a "$USER" -w 2>/dev/null); then
  echo "    OK   keychain entry service=gemini_api_key ($(printf %s "$KEY" | wc -c | tr -d ' ') chars)"
else
  echo "    FAIL keychain entry missing. Run bootstrap-llm-apis.sh."
  FAIL=1
  KEY=""
fi

if [ -n "$KEY" ]; then
  # Metadata GET — costs nothing, confirms the key is valid and project is reachable.
  HTTP_BODY=$(curl -sS "https://generativelanguage.googleapis.com/v1beta/models?key=$KEY" 2>&1 || true)
  MODEL_COUNT=$(echo "$HTTP_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'error' in d:
        print('ERROR:', d['error'].get('message', '')[:200])
    else:
        print(len(d.get('models', [])))
except Exception as e:
    print('PARSE-ERROR:', e)
" 2>&1)

  if [[ "$MODEL_COUNT" == ERROR:* ]] || [[ "$MODEL_COUNT" == PARSE-ERROR:* ]]; then
    echo "    FAIL Gemini API call failed: $MODEL_COUNT"
    FAIL=1
  elif [ "$MODEL_COUNT" -ge 1 ] 2>/dev/null; then
    echo "    OK   Gemini API listed $MODEL_COUNT models"

    # Tier check: try a tiny gemini-2.5-pro call. Free-tier projects fail with
    # 429 RESOURCE_EXHAUSTED / "limit: 0"; Paid-tier projects succeed.
    TIER_OUT=$(curl -sS -X POST \
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=$KEY" \
      -H 'Content-Type: application/json' \
      -d '{"contents":[{"parts":[{"text":"reply with just: ok"}]}],"generationConfig":{"temperature":0,"maxOutputTokens":10}}' \
      2>&1)
    if echo "$TIER_OUT" | grep -q "RESOURCE_EXHAUSTED"; then
      echo "    FAIL gemini-2.5-pro blocked on Free tier (limit: 0)"
      echo "         Fix: link the key's Cloud project to AHHOME billing."
      echo "         See infra/llm-apis/README.md §'Active key' rotation steps."
      FAIL=1
    elif echo "$TIER_OUT" | grep -q '"usageMetadata"'; then
      # 200 OK with usageMetadata = Paid-tier billable call succeeded, regardless of finishReason.
      echo "    OK   gemini-2.5-pro reachable (Paid tier confirmed)"
    elif echo "$TIER_OUT" | grep -q '"error"'; then
      ERR=$(echo "$TIER_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','?')[:200])" 2>/dev/null || echo "?")
      echo "    FAIL gemini-2.5-pro probe returned API error: $ERR"
      FAIL=1
    else
      echo "    WARN gemini-2.5-pro probe returned unexpected response:"
      echo "         $(echo "$TIER_OUT" | head -c 200)"
    fi
  else
    echo "    FAIL Gemini API returned $MODEL_COUNT (expected an integer)"
    FAIL=1
  fi
fi

echo
echo "==> [3/3] Summary"
if [ "$FAIL" = "0" ]; then
  echo "    All checks passed. This Mac can drive the podcast pipeline."
  exit 0
else
  echo "    One or more checks failed. See output above."
  echo "    Doc: infra/llm-apis/README.md"
  exit 1
fi
