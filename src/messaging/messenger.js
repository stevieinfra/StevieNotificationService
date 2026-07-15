"use strict";

const { TwilioSmsSender } = require("./twilioSmsSender");
const { WhatsAppSender } = require("./whatsAppSender");

/**
 * Channel-agnostic facade. Register one sender per channel and route through a
 * single sendMessage(channel, to, payload). Both channels expose the same
 * async send(to, payload) method, so callers never care which one runs.
 *
 *   sms      -> Twilio            payload = { body }
 *   whatsapp -> Meta Cloud API    payload = { template: {...} } or { body }
 *
 * @param {object} config
 *   Twilio (SMS):   accountSid, authToken, phoneNumber
 *   WhatsApp (Meta): whatsAppPhoneNumberId, whatsAppAccessToken, whatsAppWabaId
 *   dryRun applies to both.
 */
function createMessenger(config = {}) {
  // Factories, not instances: a sender is built only when its channel is first
  // used. This way testing WhatsApp doesn't require Twilio creds (and vice versa)
  // — each sender validates its own config at construction time.
  const factories = {
    sms: () =>
      new TwilioSmsSender({
        accountSid: config.accountSid,
        authToken: config.authToken,
        phoneNumber: config.phoneNumber,
        dryRun: config.dryRun,
      }),
    whatsapp: () =>
      new WhatsAppSender({
        phoneNumberId: config.whatsAppPhoneNumberId,
        accessToken: config.whatsAppAccessToken,
        wabaId: config.whatsAppWabaId,
        dryRun: config.dryRun,
      }),
  };

  const senders = {}; // lazily-populated cache

  function getSender(channel) {
    if (!factories[channel]) return null;
    if (!senders[channel]) senders[channel] = factories[channel]();
    return senders[channel];
  }

  /**
   * @param {"sms"|"whatsapp"} channel
   * @param {string} to       recipient in E.164
   * @param {object} payload  channel payload, e.g. { body } or { template }
   */
  async function sendMessage(channel, to, payload = {}) {
    const sender = getSender(channel);
    if (!sender) {
      const available = Object.keys(factories).join(", ") || "(none)";
      throw new Error(
        `No sender registered for channel "${channel}". Available: ${available}.`
      );
    }
    return sender.send(to, payload);
  }

  return { sendMessage, getSender, senders };
}

module.exports = { createMessenger };
