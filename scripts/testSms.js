"use strict";

/**
 * Runnable SMS smoke test.
 *   npm run test:sms
 *
 * Sends the generalized + personalized "2026 winners" templates to TEST_TO_NUMBER.
 * If creds/.env are missing it exits with a clear message instead of crashing.
 */
require("dotenv").config();

const { createMessenger, renderTemplate } = require("../src/messaging");

// Dry-run if DRY_RUN=true in .env OR the --dry flag is passed (npm run test:sms:dry).
const DRY_RUN =
  /^true$/i.test(process.env.DRY_RUN || "") || process.argv.includes("--dry");

// Live sends need all four; dry-run only needs a recipient to display.
const REQUIRED = DRY_RUN
  ? ["TEST_TO_NUMBER"]
  : ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER", "TEST_TO_NUMBER"];

function requireEnv() {
  const missing = REQUIRED.filter((k) => !process.env[k] || !process.env[k].trim());
  if (missing.length) {
    // In dry-run, a missing recipient is non-fatal — fall back to a sample number.
    if (DRY_RUN && missing.length === 1 && missing[0] === "TEST_TO_NUMBER") return;
    console.error("\n  Cannot run the SMS test — missing environment variables:");
    missing.forEach((k) => console.error(`    - ${k}`));
    console.error("\n  Fix: copy .env.example to .env and fill in the values:");
    console.error("      cp .env.example .env");
    console.error("  ...or run the no-credentials dry run:  npm run test:sms:dry\n");
    process.exit(1);
  }
}

async function main() {
  requireEnv();

  const messenger = createMessenger({
    accountSid: process.env.TWILIO_ACCOUNT_SID,
    authToken: process.env.TWILIO_AUTH_TOKEN,
    phoneNumber: process.env.TWILIO_PHONE_NUMBER,
    dryRun: DRY_RUN,
  });

  const to = process.env.TEST_TO_NUMBER || (DRY_RUN ? "+15551234567" : undefined);
  console.log(`Mode: ${DRY_RUN ? "DRY_RUN (nothing is actually sent)" : "LIVE"}`);
  console.log(`Sending test messages to ${to} ...\n`);

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const name = process.env.TEST_NAME || "Vennela";

  // The 4 templates to test, in order.
  const MESSAGES = [
    { label: "generalized ", key: "winners2026.generalized", vars: {} },
    { label: "personalized", key: "winners2026.personalized", vars: { name } },
    { label: "deadline    ", key: "deadline.reminder", vars: { name, deadline: "Feb 28, 2026" } },
    { label: "finalist    ", key: "finalist.announcement", vars: { name, category: "Innovation in Technology" } },
  ];

  // 2.5 min between messages on a live run (avoids carrier filtering); no wait in dry-run.
  const GAP_MS = DRY_RUN ? 0 : 150000;
  let allOk = true;

  for (let i = 0; i < MESSAGES.length; i++) {
    const m = MESSAGES[i];
    const body = renderTemplate(m.key, m.vars);
    const res = await messenger.sendMessage("sms", to, { body });
    console.log(`${m.label}:`, res.success ? `OK sid=${res.messageId}` : `FAILED ${res.error}`);
    if (!res.success) allOk = false;

    if (i < MESSAGES.length - 1) {
      console.log(`  ...waiting ${GAP_MS / 1000}s before the next message...\n`);
      await sleep(GAP_MS);
    }
  }

  console.log(`\nDone. ${allOk ? "All sent." : "One or more failed (see above)."}`);
  process.exit(allOk ? 0 : 1);
}

main().catch((err) => {
  console.error("\nUnexpected error:", err.message);
  process.exit(1);
});
