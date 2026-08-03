import type { Config } from "@react-router/dev/config";

export default {
  // Server rendering stays on: it is what lets one <audio> element live in the
  // root layout and survive every navigation, and it puts the API routes in the
  // same Worker as the UI. It is NOT here for SEO — the site is invite-only.
  ssr: true,
} satisfies Config;
