#!/usr/bin/env bash
# UserPromptSubmit: when a prompt is about building or editing an HTML view, page,
# diagram or the Astro Site, remind the model that the Cortex HTML View Quality
# Standard applies without being asked. Belt-and-suspenders — not a substitute for
# following CLAUDE.md. Stdout is added to the model's context.
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
HOOK_INPUT="$(cat)"
prompt="$(json_field prompt)"
if printf '%s' "$prompt" | grep -qiE 'html|astro|plan-dashboard|\bview\b|\bpage\b|diagram|composer|studio|stylesheet|\bcss\b|\bsite\b'; then
  cat <<'MSG'
Reminder (Cortex HTML-view standard, LOCKED): this touches the Podcast Factory Astro Site or an HTML view.
Load the html-view-quality skill, follow docs/standards/html-view-quality-digest.md (external CSS/JS only,
no inline styles or scripts, existing --c-* tokens, colour theme unchanged), and finish with
`npm run lint:views` plus the html-view-challenger and site-health-sentinel gates.
MSG
fi
exit 0
