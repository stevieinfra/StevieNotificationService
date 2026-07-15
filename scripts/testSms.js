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

const has = (k) => process.env[k] && process.env[k].trim();

function requireEnv() {
  if (DRY_RUN) return; // dry-run needs nothing (falls back to a sample recipient)

  const missing = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"].filter(
    (k) => !has(k)
  );
  // A recipient can come from TEST_RECIPIENTS, TEST_TO_NUMBER, or ANIRUDH_TO_NUMBER.
  if (!has("TEST_RECIPIENTS") && !has("TEST_TO_NUMBER") && !has("ANIRUDH_TO_NUMBER")) {
    missing.push("TEST_RECIPIENTS (or TEST_TO_NUMBER)");
  }
  if (missing.length) {
    console.error("\n  Cannot run the SMS test — missing environment variables:");
    missing.forEach((k) => console.error(`    - ${k}`));
    console.error("\n  Fix: set them in .env (copy .env.example if needed),");
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

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // Random 10–15 MINUTE gap between message ROUNDS.
  const randGapMs = () => (10 + Math.floor(Math.random() * 6)) * 60 * 1000;

  // Recipients. Preferred: a TEST_RECIPIENTS list in .env, comma-separated
  // "Name:+number" pairs, e.g.  Vennela:+9183...,Anirudh Thadem:+1404...,Sarah:+4479...
  // Falls back to the individual TEST_TO_NUMBER / ANIRUDH_TO_NUMBER keys.
  let recipients = [];
  if (process.env.TEST_RECIPIENTS && process.env.TEST_RECIPIENTS.trim()) {
    recipients = process.env.TEST_RECIPIENTS.split(",")
      .map((pair) => {
        const i = pair.lastIndexOf(":"); // number has no ":", so split on the last one
        return { name: pair.slice(0, i).trim(), to: pair.slice(i + 1).trim() };
      })
      .filter((r) => r.name && r.to);
  } else {
    recipients = [
      { name: process.env.TEST_NAME || "Vennela", to: process.env.TEST_TO_NUMBER },
      { name: "Anirudh Thadem", to: process.env.ANIRUDH_TO_NUMBER },
    ].filter((r) => r.to && r.to.trim());
  }
  if (!recipients.length && DRY_RUN) {
    recipients = [{ name: "Vennela", to: "+15551234567" }];
  }

  // The 3 templates each recipient receives (personalized with their name).
  // To use the deadline reminder instead of finalist, swap the last line.
  const templatesFor = (name) => [
    { label: "generalized ", key: "winners2026.generalized", vars: {} },
    { label: "personalized", key: "winners2026.personalized", vars: { name } },
    { label: "finalist    ", key: "finalist.announcement", vars: { name, category: "Innovation in Technology" } },
    // { label: "deadline    ", key: "deadline.reminder", vars: { name, deadline: "Feb 28, 2026" } },
  ];

  const rounds = templatesFor("x").length; // messages per recipient (3)

  console.log(`Mode: ${DRY_RUN ? "DRY_RUN (nothing is actually sent)" : "LIVE"}`);
  console.log(`Recipients: ${recipients.map((r) => `${r.name} (${r.to})`).join(", ")}`);
  console.log(
    `Plan: ${rounds} rounds. In each round ALL recipients get the same message ` +
      `together, then a random 10-15 min gap before the next round.\n`
  );

  let allOk = true;
  // Round = one message to everyone (sent together), then wait before the next.
  for (let r = 0; r < rounds; r++) {
    console.log(`--- Round ${r + 1} of ${rounds} ---`);
    for (const person of recipients) {
      const m = templatesFor(person.name)[r];
      const body = renderTemplate(m.key, m.vars);
      const res = await messenger.sendMessage("sms", person.to, { body });
      console.log(
        `  [${person.name}] ${m.label}:`,
        res.success ? `OK sid=${res.messageId}` : `FAILED ${res.error}`
      );
      if (!res.success) allOk = false;
    }

    if (r < rounds - 1 && !DRY_RUN) {
      const g = randGapMs();
      console.log(`\n  ...waiting ${Math.round(g / 60000)} min before the next round...\n`);
      await sleep(g);
    }
  }

  console.log(`\nDone. ${allOk ? "All sent." : "One or more failed (see above)."}`);
  process.exit(allOk ? 0 : 1);
}

main().catch((err) => {
  console.error("\nUnexpected error:", err.message);
  process.exit(1);
});
