# Gemini CLI Chat Client

A multi-turn CLI chat client for Gemini (`gemini-2.0-flash`) with support for
custom system instructions (Gems / personas) and knowledge file injection.

## Prerequisites

- Python 3.9+
- `google-genai` SDK — already installed in this repo's virtualenv
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

### 1. Set your API key

**Option A — environment variable (recommended for scripts):**

```bash
export GEMINI_API_KEY="your_key_here"
```

**Option B — `.env` file at the repo root:**

```bash
cp .env.example .env
# edit .env and fill in GEMINI_API_KEY
```

The script loads `.env` automatically if it exists.

**Option C — macOS Keychain (already used for pipeline work):**

The pipeline stores the Gemini key under keychain entry `llm-gemini-api-key`.
To use it for the CLI client, export it before running:

```bash
export GEMINI_API_KEY=$(security find-generic-password -s llm-gemini-api-key -w)
python3 scripts/gemini_chat.py
```

### 2. Verify installation

```bash
python3 -c "from google import genai; print('OK')"
```

## How to run

### Basic chat (no persona, no files)

```bash
python3 scripts/gemini_chat.py
```

Type your message and press Enter. Type `exit` to quit.

### With a system instruction (persona / Gem)

Pass the system prompt as a file path or an inline string:

```bash
# From a file
python3 scripts/gemini_chat.py --system path/to/my_gem_system_prompt.txt

# Inline string
python3 scripts/gemini_chat.py --system "You are a Socratic tutor. Never give direct answers."

# From the environment (useful for scripts)
export GEMINI_SYSTEM_INSTRUCTION="$(cat path/to/my_gem_system_prompt.txt)"
python3 scripts/gemini_chat.py
```

### With knowledge files

Provide one or more file paths as positional arguments:

```bash
# Single knowledge file
python3 scripts/gemini_chat.py content/Islamic/asaas-al-taveel-vol-1/_system/wisdom/ksessions-adam-cycle.md

# Multiple files + system instruction
python3 scripts/gemini_chat.py \
    --system path/to/persona.txt \
    content/Islamic/asaas-al-taveel-vol-1/_system/wisdom/ksessions-adam-cycle.md \
    content/Islamic/asaas-al-taveel-vol-1/_system/wisdom/kashkole-adam-cycle.md
```

**File size routing:**
- Files **< 20 MB** are read and injected inline into the first user turn.
- Files **>= 20 MB** are uploaded via the Gemini Files API; the returned URI is
  embedded as a file reference in the first user turn.

Knowledge files are visible to the model for the entire conversation — the first
user message carries the file content, and the model's full multi-turn history
is maintained from that point forward.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Your Gemini API key from Google AI Studio |
| `GEMINI_SYSTEM_INSTRUCTION` | No | Default system instruction / persona text. Overridden by `--system`. |

## Notes

- All conversation history is maintained in memory for the session. On exit,
  history is not persisted.
- The model is `gemini-2.0-flash`. To change it, edit `_MODEL` at the top of
  `scripts/gemini_chat.py`.
- API keys must never appear in source-controlled files. Use env vars or the
  macOS Keychain.
