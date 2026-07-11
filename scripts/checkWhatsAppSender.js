"use strict";

/**
 * Read-only check: is TWILIO_PHONE_NUMBER (or arg) a registered WhatsApp sender?
 * Also confirms the number is owned by the account and its SMS capability.
 *
 *   node scripts/checkWhatsAppSender.js [+1XXXXXXXXXX]
 */
require("dotenv").config();

const sid = process.env.TWILIO_ACCOUNT_SID;
const token = process.env.TWILIO_AUTH_TOKEN;
const number = process.argv[2] || process.env.TWILIO_PHONE_NUMBER;

if (!sid || !token) {
  console.error("Missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in .env");
  process.exit(1);
}

const authHeader = "Basic " + Buffer.from(`${sid}:${token}`).toString("base64");

async function get(url) {
  const res = await fetch(url, { headers: { Authorization: authHeader } });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = null; }
  return { ok: res.ok, status: res.status, json, text };
}

(async () => {
  console.log(`\nChecking account for number: ${number || "(none set)"}\n`);

  // 1) Is the number owned by this account? (and its capabilities)
  try {
    const r = await get(
      `https://api.twilio.com/2010-04-01/Accounts/${sid}/IncomingPhoneNumbers.json?PageSize=100`
    );
    if (r.ok && r.json) {
      const nums = r.json.incoming_phone_numbers || [];
      console.log(`Owned numbers on this account: ${nums.length}`);
      nums.forEach((n) => {
        const c = n.capabilities || {};
        console.log(`  ${n.phone_number}  (SMS:${!!c.sms} MMS:${!!c.mms} Voice:${!!c.voice})`);
      });
      const match = nums.find((n) => n.phone_number === number);
      console.log(
        match
          ? `\n=> ${number} IS owned by this account (SMS capable: ${!!(match.capabilities || {}).sms}).`
          : `\n=> ${number} was NOT found among owned numbers (maybe a different account or a sandbox number).`
      );
    } else {
      console.log(`Could not list phone numbers (HTTP ${r.status}).`);
    }
  } catch (e) {
    console.log("Phone-number lookup failed:", e.message);
  }

  // 2) Is it a registered WhatsApp sender?
  console.log("\nLooking up WhatsApp senders...");
  const endpoints = [
    "https://messaging.twilio.com/v2/Channels/Senders?Channel=whatsapp",
    "https://messaging.twilio.com/v1/Channels/Senders?Channel=whatsapp",
  ];
  let handled = false;
  for (const url of endpoints) {
    try {
      const r = await get(url);
      if (r.status === 404) continue;
      handled = true;
      if (r.ok && r.json) {
        const senders = r.json.senders || r.json.data || [];
        const wa = senders.filter((s) =>
          JSON.stringify(s).toLowerCase().includes("whatsapp")
        );
        if (!wa.length) {
          console.log("=> No WhatsApp senders registered on this account.");
        } else {
          console.log(`=> WhatsApp senders found: ${wa.length}`);
          wa.forEach((s) =>
            console.log("   ", s.sender_id || s.senderId || JSON.stringify(s), "status:", s.status)
          );
          const mine = wa.find((s) => JSON.stringify(s).includes(String(number).replace("+", "")));
          console.log(
            mine
              ? `\n=> YES: ${number} is a registered WhatsApp sender.`
              : `\n=> ${number} is NOT among the registered WhatsApp senders.`
          );
        }
      } else {
        console.log(`WhatsApp senders query returned HTTP ${r.status}: ${r.text.slice(0, 200)}`);
      }
      break;
    } catch (e) {
      console.log("WhatsApp senders lookup error:", e.message);
    }
  }
  if (!handled) {
    console.log(
      "Could not query the WhatsApp Senders API from here.\n" +
        "Check manually: Twilio Console -> Messaging -> Senders -> WhatsApp senders."
    );
  }
  console.log("");
})();
