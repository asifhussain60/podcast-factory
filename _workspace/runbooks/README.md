# `_workspace/runbooks/` — one-time procedures

Step-by-step procedures that run once per machine or per provisioning event.
Not workflows; not the canonical plan. If you find yourself running a runbook
more than twice, lift it into a script under `scripts/` and replace the
runbook with a one-line pointer.

## Index

| File                          | Purpose                                                                   |
|-------------------------------|---------------------------------------------------------------------------|
| `primary-mac-activation.md`   | Bring a primary Mac to 100% Azure activation (Translator + Doc Intel + Speech + Keychain + skills). One-time per machine. |

## Future runbooks (anticipated)

- `secondary-mac-activation.md` — Air-class bootstrap (no Azure; Anthropic-only).
- `azure-key-rotation.md` — quarterly key rotation for the primary Mac.
- `new-book-onboarding.md` — operator-driven steps before a new book enters
  the autonomous pipeline (PDF intake + scope confirmation + assignment).
