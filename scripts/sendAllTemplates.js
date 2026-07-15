"use strict";

/**
 * Send ALL the Stevie WhatsApp templates to WHATSAPP_TEST_TO, one by one,
 * with a small gap between each. Handy for eyeballing how they all look.
 *
 *   npm run wa:all         (real send)
 *   npm run wa:all:dry     (log only)
 *
 * Note: Utility templates deliver reliably; the Marketing one
 * (stevie_entry_reminder) is included but Meta may frequency-cap it (esp. India),
 * so it might not arrive — that's expected, not a bug.
 */
require("dotenv").config();

const { createMessenger } = require("../src/messaging");

const DRY_RUN =
  /^true$/i.test(process.env.DRY_RUN || "") || process.argv.includes("--dry");

const has = (k) => process.env[k] && process.env[k].trim();

// Recipient personalization (override per run with WA_NAME / WA_PROGRAM / WA_LINK).
const NAME = process.env.WA_NAME || "Vennela";
const PROGRAM = process.env.WA_PROGRAM || "American Business Awards";
const PROGRAM2 = process.env.WA_PROGRAM2 || "International Business Awards";
const LINK = process.env.WA_LINK || "https://stevieawards.com";

// Each template + its body variables (order = {{1}}, {{2}}, ...).
const TEMPLATES = [
  { name: "stevie_entry_confirmation", vars: [NAME, PROGRAM, LINK] },
  { name: "stevie_entry_incomplete",   vars: [NAME, PROGRAM2, LINK] },
  { name: "stevie_winner_notification", vars: [PROGRAM2, LINK] }, // no name in this one
  { name: "stevie_entry_received",      vars: [NAME, PROGRAM] },  // link is in the button
  { name: "stevie_entry_reminder",      vars: [NAME, PROGRAM, LINK], marketing: true },
];

const LANG = process.env.WA_LANG || "en";
// Gap between sends. Default 5 minutes; override with WA_GAP_MIN. No wait in dry-run.
const GAP_MS = DRY_RUN ? 0 : (Number(process.env.WA_GAP_MIN) || 5) * 60 * 1000;

function requireEnv() {
  if (DRY_RUN) return;
  const missing = ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_TEST_TO"].filter(
    (k) => !has(k)
  );
  if (missing.length) {
    console.error("\n  Missing:", missing.join(", "));
    console.error("  Set them in .env, or run: npm run wa:all:dry\n");
    process.exit(1);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  requireEnv();

  const messenger = createMessenger({
    whatsAppPhoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID,
    whatsAppAccessToken: process.env.WHATSAPP_ACCESS_TOKEN,
    whatsAppWabaId: process.env.WHATSAPP_WABA_ID,
    dryRun: DRY_RUN,
  });

  const to = process.env.WHATSAPP_TEST_TO || "+918328697349";

  console.log(`Mode: ${DRY_RUN ? "DRY_RUN (nothing sent)" : "LIVE"}`);
  console.log(`Sending ${TEMPLATES.length} templates to ${to}\n`);

  let ok = 0;
  for (let i = 0; i < TEMPLATES.length; i++) {
    const t = TEMPLATES[i];
    const template = { name: t.name, language: LANG };
    if (t.vars && t.vars.length) {
      template.components = [
        { type: "body", parameters: t.vars.map((text) => ({ type: "text", text })) },
      ];
    }
    const tag = t.marketing ? " (Marketing — may be capped)" : "";
    const res = await messenger.sendMessage("whatsapp", to, { template });
    if (res.success) {
      ok++;
      console.log(`  OK   ${t.name}${tag}  id=${res.messageId}`);
    } else {
      console.log(`  FAIL ${t.name}${tag}  ${res.error}`);
    }
    // Wait only *between* sends, not after the last one.
    if (i < TEMPLATES.length - 1) {
      console.log(`  ...waiting ${GAP_MS / 60000} min before next...`);
      await sleep(GAP_MS);
    }
  }

  console.log(`\nDone. ${ok}/${TEMPLATES.length} accepted by Meta. Check your WhatsApp!`);
  console.log("(Utility ones should arrive; the Marketing one may not — that's expected.)");
}

main().catch((err) => {
  console.error("\nUnexpected error:", err.message);
  process.exit(1);
});
