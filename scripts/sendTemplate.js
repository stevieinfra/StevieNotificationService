"use strict";

/**
 * Generic WhatsApp template sender — send ANY approved template with ANY number
 * of body variables. This is the reusable piece (the schedule form / engine will
 * call the same messenger under the hood).
 *
 *   npm run wa:send        (real send)
 *   npm run wa:send:dry    (log only)
 *
 * Configure per run via env:
 *   WA_TEMPLATE        template name, e.g. stevie_entry_incomplete   (required)
 *   WA_LANG            language code (default "en")
 *   WHATSAPP_TEST_TO   recipient in E.164
 *   WA_VARS            body variables, pipe-separated, in order {{1}}|{{2}}|{{3}}
 *                      e.g. "Vennela|Women in Business|https://stevieawards.com"
 *                      Leave empty for templates with no variables (hello_world).
 *
 * Example (PowerShell):
 *   $env:WA_TEMPLATE="stevie_entry_incomplete"; `
 *   $env:WA_VARS="Vennela|Women in Business|https://stevieawards.com"; `
 *   npm run wa:send
 */
require("dotenv").config();

const { createMessenger } = require("../src/messaging");

const DRY_RUN =
  /^true$/i.test(process.env.DRY_RUN || "") || process.argv.includes("--dry");

const has = (k) => process.env[k] && process.env[k].trim();

const TEMPLATE = process.env.WA_TEMPLATE || "";
const LANG = process.env.WA_LANG || "en";
const VARS = (process.env.WA_VARS || "")
  .split("|")
  .map((v) => v.trim())
  .filter(Boolean);

function requireEnv() {
  const missing = [];
  if (!TEMPLATE) missing.push("WA_TEMPLATE");
  if (!DRY_RUN) {
    ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_TEST_TO"].forEach((k) => {
      if (!has(k)) missing.push(k);
    });
  }
  if (missing.length) {
    console.error("\n  Missing:", missing.join(", "));
    console.error("  Set WA_TEMPLATE (and creds), or run: npm run wa:send:dry\n");
    process.exit(1);
  }
}

async function main() {
  requireEnv();

  const messenger = createMessenger({
    whatsAppPhoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID,
    whatsAppAccessToken: process.env.WHATSAPP_ACCESS_TOKEN,
    whatsAppWabaId: process.env.WHATSAPP_WABA_ID,
    dryRun: DRY_RUN,
  });

  const to = process.env.WHATSAPP_TEST_TO || "+918328697349";

  // Build the template payload. Only add a "body" component if there are variables.
  const template = { name: TEMPLATE, language: LANG };
  if (VARS.length) {
    template.components = [
      { type: "body", parameters: VARS.map((text) => ({ type: "text", text })) },
    ];
  }

  console.log(`Mode: ${DRY_RUN ? "DRY_RUN (nothing sent)" : "LIVE"}`);
  console.log(`Template "${TEMPLATE}" (${LANG}) -> ${to}`);
  VARS.forEach((v, i) => console.log(`  {{${i + 1}}} = ${v}`));
  if (!VARS.length) console.log("  (no variables)");
  console.log("");

  const res = await messenger.sendMessage("whatsapp", to, { template });

  if (res.success) {
    console.log(`\nOK — sent. message id = ${res.messageId}`);
    console.log("Check your WhatsApp!");
  } else {
    console.error(`\nFAILED — ${res.error}`);
    if (res.details) console.error(JSON.stringify(res.details, null, 2));
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("\nUnexpected error:", err.message);
  process.exit(1);
});
