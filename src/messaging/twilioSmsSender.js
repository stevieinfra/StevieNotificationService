"use strict";

const twilio = require("twilio");

// E.164: a leading + then 1–15 digits (first digit non-zero).
const E164 = /^\+[1-9]\d{1,14}$/;

/**
 * Twilio-backed SMS sender.
 *
 * Mirrors the reference pattern: config in the constructor, required-field
 * validation, and client.messages.create({ body, from, to }).
 *
 * @param {object} config
 * @param {string} config.accountSid   Twilio Account SID (starts with "AC")
 * @param {string} config.authToken    Twilio Auth Token
 * @param {string} config.phoneNumber  the "from" number in E.164
 */
class TwilioSmsSender {
  constructor(config = {}) {
    const { accountSid, authToken, phoneNumber, dryRun = false } = config;

    this.channel = "sms";
    this.dryRun = !!dryRun;
    // In dry-run we don't contact Twilio, so real creds aren't required.
    this.phoneNumber = phoneNumber || (this.dryRun ? "+10000000000" : phoneNumber);

    if (!this.dryRun) {
      const missing = [];
      if (!accountSid) missing.push("accountSid");
      if (!authToken) missing.push("authToken");
      if (!phoneNumber) missing.push("phoneNumber");
      if (missing.length) {
        throw new Error(
          `TwilioSmsSender: missing required config: ${missing.join(", ")}. ` +
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER in your .env " +
            "(or set DRY_RUN=true to test without credentials)."
        );
      }
      this.client = twilio(accountSid, authToken);
    }
  }

  /**
   * Send an SMS.
   * @param {string} to    recipient in E.164 (e.g. +14155551234)
   * @param {string} body  message text
   * @returns {Promise<{success: boolean, messageId?: string, error?: string}>}
   */
  async sendSMS(to, body) {
    if (!E164.test(to || "")) {
      throw new Error(`Invalid 'to' number (must be E.164 like +14155551234): "${to}"`);
    }
    if (!body || !String(body).trim()) {
      throw new Error("Cannot send an empty message body.");
    }

    if (this.dryRun) {
      console.log(
        "[sms][DRY_RUN] would send:\n" +
          `   to   = ${to}\n` +
          `   from = ${this.phoneNumber}\n` +
          `   body = ${body}`
      );
      return { success: true, messageId: `DRYRUN-${Date.now()}`, dryRun: true };
    }

    try {
      const msg = await this.client.messages.create({
        body,
        from: this.phoneNumber,
        to,
      });
      console.log(`[sms] sent to ${to} — sid=${msg.sid}`);
      return { success: true, messageId: msg.sid };
    } catch (err) {
      console.error(`[sms] FAILED to ${to} — ${err.message}`);
      return { success: false, error: err.message };
    }
  }

  /**
   * Generic interface used by the messenger facade.
   * payload = { body }. Keeps every channel sender uniform.
   */
  async send(to, payload = {}) {
    return this.sendSMS(to, payload.body);
  }
}

module.exports = { TwilioSmsSender, E164 };
