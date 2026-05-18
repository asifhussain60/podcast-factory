// keychain.js — retrieves the Anthropic API key from macOS Keychain.
// Falls back to env var if Keychain lookup fails. Never logs key values.

import { execFileSync } from "node:child_process";

const ANTHROPIC_SERVICE = "anthropic-api-key";

function readKeychain(service) {
  try {
    return execFileSync(
      "/usr/bin/security",
      ["find-generic-password", "-s", service, "-w"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
    ).trim();
  } catch {
    return null;
  }
}

export function loadAnthropicKey() {
  const keychainKey = readKeychain(ANTHROPIC_SERVICE);
  if (keychainKey && keychainKey.startsWith("sk-ant-")) {
    return { key: keychainKey, source: "keychain" };
  }
  const envKey = process.env.ANTHROPIC_API_KEY;
  if (envKey && envKey.startsWith("sk-ant-")) {
    return { key: envKey, source: "env" };
  }
  throw new Error(
    `No Anthropic API key found. Store one with:\n` +
    `  security add-generic-password -s ${ANTHROPIC_SERVICE} -a "$USER" -w 'sk-ant-...'\n` +
    `Or export ANTHROPIC_API_KEY before starting the server.`
  );
}
