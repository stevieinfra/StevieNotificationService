"use strict";

const { TwilioSmsSender } = require("./twilioSmsSender");

/**
 * Channel-agnostic facade. Register one sender per channel and route through a
 * single sendMessage(channel, to, payload). Today only "sms" is wired up;
 * WhatsApp plugs in here later WITHOUT touching callers:
 *
 *   senders.whatsapp = new TwilioWhatsAppSender({ ... });
 *
 * as long as it exposes the same async send(to, payload) method.
 *
 * @param {object} config { accountSid, authToken, phoneNumber }
 */
function createMessenger(config = {}) {
  const senders = {
    sms: new TwilioSmsSender({
      accountSid: config.accountSid,
      authToken: config.authToken,
      phoneNumber: config.phoneNumber,
      dryRun: config.dryRun,
    }),
    // whatsapp: <-- future extension point (same send(to, payload) interface)
  };

  /**
   * @param {"sms"|"whatsapp"} channel
   * @param {string} to       recipient in E.164
   * @param {object} payload  channel payload, e.g. { body }
   */
  async function sendMessage(channel, to, payload = {}) {
    const sender = senders[channel];
    if (!sender) {
      const available = Object.keys(senders).join(", ") || "(none)";
      throw new Error(
        `No sender registered for channel "${channel}". Available: ${available}. ` +
          "(WhatsApp is not wired up yet.)"
      );
    }
    return sender.send(to, payload);
  }

  return { sendMessage, senders };
}

module.exports = { createMessenger };
