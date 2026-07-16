"use strict";

/**
 * Stevie broadcast MVP — filter subscribers for a program + reminder, then send
 * over the right channel (US -> SMS via Twilio, international -> WhatsApp via Meta).
 *
 *   npm run broadcast          -> DRY RUN (shows who + what, sends nothing)
 *   npm run broadcast -- --send  -> actually send
 *
 * Configure the campaign via env:
 *   SUBSCRIBERS_CSV               list to target (default: fixtures/sample_subscribers.csv)
 *   BROADCAST_TOPIC               ONE program code, e.g. IBA, ABA, WOMEN   (required)
 *   BROADCAST_REMINDER            e.g. "First Reminder"                    (optional)
 *   BROADCAST_INCLUDE_UNVERIFIED  "true" to include unconfirmed numbers (default false)
 *   BROADCAST_LINK                link used in messages (default https://stevieawards.com)
 *   WA_TEMPLATE                   WhatsApp template (default stevie_entry_reminder; 3 vars: name, program, link)
 *   WA_LANG                       template language (default "en")
 *   GAP_SEC                       seconds between sends when live (default 3)
 *
 * Safe by default: dry-run unless you pass --send.
 */
require("dotenv").config();

const { createMessenger } = require("../src/messaging");
const { loadSubscribers, filterRecipients, TOPIC_LABELS } = require("../src/subscribers");

const LIVE = process.argv.includes("--send");
const DRY_RUN = !LIVE;

const CSV = process.env.SUBSCRIBERS_CSV || "fixtures/sample_subscribers.csv";
// One or more program codes: BROADCAST_TOPICS=IBA,ABA  (BROADCAST_TOPIC still works for one).
const TOPICS = (process.env.BROADCAST_TOPICS || process.env.BROADCAST_TOPIC || "")
  .split(",").map((s) => s.trim()).filter(Boolean);
const REMINDER = (process.env.BROADCAST_REMINDER || "").trim();
// Optional custom SMS body from the form; {name}/{program}/{link} are substituted.
const SMS_BODY_TMPL = (process.env.BROADCAST_SMS_BODY || "").trim();
const INCLUDE_UNVERIFIED = /^true$/i.test(process.env.BROADCAST_INCLUDE_UNVERIFIED || "");
const LINK = process.env.BROADCAST_LINK || "https://stevieawards.com";
const WA_TEMPLATE = process.env.WA_TEMPLATE || "stevie_entry_reminder";
const WA_LANG = process.env.WA_LANG || "en";
const GAP_MS = (Number(process.env.GAP_SEC) || 3) * 1000;

// Each approved template has a specific number of body variables. Map the template
// name -> the ordered values it expects, so we never send the wrong count (Meta errors).
const WA_TEMPLATE_PARAMS = {
  stevie_entry_confirmation: (name, program, link) => [name, program, link],
  stevie_entry_incomplete: (name, program, link) => [name, program, link],
  stevie_entry_reminder: (name, program, link) => [name, program, link],
  stevie_winner_notification: (name, program, link) => [program, link], // no name
  stevie_entry_received: (name, program, link) => [name, program], // link is in the button
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function fail(msg) {
  console.error(`\n  ${msg}\n`);
  process.exit(1);
}

async function main() {
  if (!TOPICS.length) fail("Set BROADCAST_TOPIC or BROADCAST_TOPICS (e.g. IBA or IBA,ABA).");
  const programName = TOPICS.map((t) => TOPIC_LABELS[t] || t).join(" / ");

  const all = loadSubscribers(CSV);
  const recipients = filterRecipients(all, {
    topics: TOPICS,
    reminderType: REMINDER,
    includeUnverified: INCLUDE_UNVERIFIED,
  });

  const smsList = recipients.filter((r) => r.channel === "sms");
  const waList = recipients.filter((r) => r.channel === "whatsapp");

  console.log(`\n=== Stevie broadcast ${DRY_RUN ? "(DRY RUN — nothing sent)" : "(LIVE)"} ===`);
  console.log(`List:      ${CSV}  (${all.length} rows)`);
  console.log(`Program:   ${TOPICS.join(", ")} — ${programName}`);
  console.log(`Reminder:  ${REMINDER || "(any)"}`);
  console.log(`Consent:   ${INCLUDE_UNVERIFIED ? "including unverified" : "verified only"}`);
  console.log(`Matched:   ${recipients.length}  (SMS ${smsList.length}, WhatsApp ${waList.length})\n`);

  if (!recipients.length) { console.log("No recipients matched — nothing to send.\n"); return; }

  const messenger = createMessenger({
    accountSid: process.env.TWILIO_ACCOUNT_SID,
    authToken: process.env.TWILIO_AUTH_TOKEN,
    phoneNumber: process.env.TWILIO_PHONE_NUMBER,
    whatsAppPhoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID,
    whatsAppAccessToken: process.env.WHATSAPP_ACCESS_TOKEN,
    whatsAppWabaId: process.env.WHATSAPP_WABA_ID,
    dryRun: DRY_RUN,
  });

  let ok = 0;
  let failed = 0;
  for (let i = 0; i < recipients.length; i++) {
    const r = recipients[i];
    const name = r.name || "there";
    let res;
    try {
      if (r.channel === "sms") {
        let body;
        if (SMS_BODY_TMPL) {
          body = SMS_BODY_TMPL
            .replace(/\{name\}/g, name)
            .replace(/\{program\}/g, programName)
            .replace(/\{link\}/g, LINK);
          if (!/reply stop/i.test(body)) body += "  Reply STOP to opt out.";
        } else {
          body =
            `Hi ${name}, this is a reminder that entries for the ${programName} are closing soon. ` +
            `Enter now at ${LINK}. Reply STOP to opt out.`;
        }
        res = await messenger.sendMessage("sms", r.phone_e164, { body });
      } else {
        const build = WA_TEMPLATE_PARAMS[WA_TEMPLATE] || ((n, p, l) => [n, p, l]);
        const values = build(name, programName, LINK);
        const template = { name: WA_TEMPLATE, language: WA_LANG };
        if (values.length) {
          template.components = [
            { type: "body", parameters: values.map((text) => ({ type: "text", text })) },
          ];
        }
        res = await messenger.sendMessage("whatsapp", r.phone_e164, { template });
      }
    } catch (err) {
      res = { success: false, error: err.message };
    }

    if (res.success) { ok++; console.log(`  OK   [${r.channel}] ${name} ${r.phone_e164}`); }
    else { failed++; console.log(`  FAIL [${r.channel}] ${name} ${r.phone_e164} — ${res.error}`); }

    if (LIVE && i < recipients.length - 1) await sleep(GAP_MS);
  }

  console.log(`\nDone. ${ok} sent, ${failed} failed, ${recipients.length} total.`);
  if (DRY_RUN) console.log("This was a DRY RUN. Re-run with  -- --send  to actually send.\n");
}

main().catch((err) => {
  console.error("\nUnexpected error:", err.message);
  process.exit(1);
});
