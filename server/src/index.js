// Babu Journal — local-only Claude API proxy.
// Listens on localhost:3001, reads the API key from macOS Keychain at startup,
// exposes the surface the journal site uses without exposing the key to the
// browser.
//
// Endpoints:
//   GET  /health                       — core.js
//   POST /api/voice-test               — core.js
//   POST /api/refine                   — core.js (memoir voice-DNA refinement)
//   POST /api/chat                     — core.js (generic passthrough)
//   GET  /api/reference-data/:name     — core.js (Tier 0 JSON)
//   GET  /api/usage/summary            — usage.js
//   POST /api/theme-swatches           — theme.js (tweaker)
//   POST /api/theme-review             — theme.js (tweaker)
//   POST /api/theme-save               — theme.js (tweaker)
//
// CORS is locked to ALLOWED_ORIGINS (defaults cover localhost + prod/dev Pages).

import express from "express";
import cors from "cors";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import Anthropic from "@anthropic-ai/sdk";
import { loadAnthropicKey } from "./lib/keychain.js";
import { usageLogger } from "./middleware/usage-logger.js";
import { buildRateLimiter } from "./middleware/rate-limit.js";
import { throttleBudget } from "./middleware/throttle-budget.js";
import { accessAuth } from "./middleware/access-auth.js";
import { createCoreRouter } from "./routes/core.js";
import { createUsageRouter } from "./routes/usage.js";
import { createThemeRouter } from "./routes/theme.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// --- Config ------------------------------------------------------------------
const PORT = Number(process.env.PORT ?? 3001);
const DEFAULT_MODEL = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6";
const ALLOWED_ORIGINS = (
  process.env.ALLOWED_ORIGINS ??
  "http://localhost:3000,https://journal.kashkole.com,https://journal-dev.kashkole.com"
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const MONTHLY_CAP = Number(process.env.MONTHLY_CAP ?? 50);

// --- Key load (fail fast if missing) -----------------------------------------
const { key: ANTHROPIC_API_KEY, source: KEY_SOURCE } = loadAnthropicKey();
const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY });

// --- App setup ---------------------------------------------------------------
const app = express();
app.set("trust proxy", "loopback");
app.use(
  cors({
    origin: (origin, cb) => {
      if (!origin) return cb(null, true);
      if (ALLOWED_ORIGINS.includes(origin)) return cb(null, true);
      cb(new Error(`CORS: origin not allowed: ${origin}`));
    },
    credentials: true,
    methods: ["GET", "POST", "PATCH", "DELETE"],
  })
);
app.use(express.json({ limit: "10mb" }));
app.use(accessAuth());
app.use(usageLogger());
app.use(buildRateLimiter());
app.use(throttleBudget({ monthlyCAP: MONTHLY_CAP }));

// --- Schema validator (theme-save) -------------------------------------------
const SCHEMA_DIR = path.resolve(__dirname, "./schemas");
const ajv = new Ajv({ strict: true, allErrors: true });
addFormats(ajv);
const themeSaveSchema = JSON.parse(
  await readFile(path.join(SCHEMA_DIR, "theme-save.schema.json"), "utf8")
);
const themeSaveValidator = ajv.compile(themeSaveSchema);

// --- Static: serve shared/ modules so the client can import them via <script type="module">
const REPO_ROOT = path.resolve(__dirname, "..", "..");
app.use("/shared", express.static(path.join(REPO_ROOT, "shared"), {
  fallthrough: true,
  maxAge: "1h",
  setHeaders: (res) => res.setHeader("Content-Type", "text/javascript"),
}));

// --- Mount routers -----------------------------------------------------------
app.use(createCoreRouter({ anthropic, DEFAULT_MODEL, KEY_SOURCE, PORT, ALLOWED_ORIGINS }));
app.use(createUsageRouter({ MONTHLY_CAP }));
app.use(createThemeRouter({ anthropic, DEFAULT_MODEL, themeSaveValidator }));

// --- Start -------------------------------------------------------------------
app.listen(PORT, "127.0.0.1", () => {
  console.log(
    `[babu-journal-proxy] listening on http://127.0.0.1:${PORT}  model=${DEFAULT_MODEL}  keySource=${KEY_SOURCE}`
  );
});
