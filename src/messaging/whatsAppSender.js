"use strict";

/**
 * WhatsApp sender via the Meta (WhatsApp) Cloud API — Graph API.
 *
 * Mirrors TwilioSmsSender's shape so it plugs into the messenger facade with the
 * same async send(to, payload) interface. No SDK needed — the Cloud API is a
 * plain HTTPS POST, so we use global fetch (Node 18+).
 *
 * Business-initiated WhatsApp messages MUST use a pre-approved TEMPLATE. A plain
 * text body only works inside the 24h customer-service window, so send() defaults
 * to template mode and falls back to text only when payload.body is given.
 *
 * @param {object} config
 * @param {string} config.phoneNumberId  Meta "Phone Number ID" (NOT the phone number)
 * @param {string} config.accessToken    permanent System User token (whatsapp_business_messaging)
 * @param {string} [config.wabaId]       WhatsApp Business Account ID (for reference/logging)
 * @param {string} [config.apiVersion]   Graph API version (default v21.0)
 * @param {boolean}[config.dryRun]       log instead of calling Meta
 */
const E164 = /^\+[1-9]\d{1,14}$/;

class WhatsAppSender {
  constructor(config = {}) {
    const {
      phoneNumberId,
      accessToken,
      wabaId,
      apiVersion = "v21.0",
      dryRun = false,
    } = config;

    this.channel = "whatsapp";
    this.dryRun = !!dryRun;
    this.phoneNumberId = phoneNumberId;
    this.accessToken = accessToken;
    this.wabaId = wabaId;
    this.apiVersion = apiVersion;

    if (!this.dryRun) {
      const missing = [];
      if (!phoneNumberId) missing.push("phoneNumberId");
      if (!accessToken) missing.push("accessToken");
      if (missing.length) {
        throw new Error(
          `WhatsAppSender: missing required config: ${missing.join(", ")}. ` +
            "Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN in your .env " +
            "(or set DRY_RUN=true to test without credentials)."
        );
      }
    }
  }

  get endpoint() {
    return `https://graph.facebook.com/${this.apiVersion}/${this.phoneNumberId}/messages`;
  }

  // Meta wants the number in international format, digits only (no leading +).
  static normalize(to) {
    return String(to || "").replace(/[^\d]/g, "");
  }

  async _post(body, label, to) {
    if (this.dryRun) {
      console.log(
        `[whatsapp][DRY_RUN] would send (${label}):\n` +
          `   to      = ${to}\n` +
          `   payload = ${JSON.stringify(body.template || body.text || body)}`
      );
      return { success: true, messageId: `DRYRUN-${Date.now()}`, dryRun: true };
    }

    try {
      const res = await fetch(this.endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        const msg = data?.error?.message || `HTTP ${res.status}`;
        console.error(`[whatsapp] FAILED to ${to} — ${msg}`);
        return { success: false, error: msg, details: data?.error };
      }
      const id = data?.messages?.[0]?.id;
      console.log(`[whatsapp] sent to ${to} — id=${id}`);
      return { success: true, messageId: id };
    } catch (err) {
      console.error(`[whatsapp] FAILED to ${to} — ${err.message}`);
      return { success: false, error: err.message };
    }
  }

  /**
   * Send an approved template message (the only way to initiate a conversation).
   * @param {string} to            recipient in E.164 (e.g. +918328697349)
   * @param {string} templateName  e.g. "hello_world", "event_reminder"
   * @param {string} [languageCode] e.g. "en_US", "en"
   * @param {Array}  [components]   template variable components, e.g.
   *   [{ type: "body", parameters: [{ type: "text", text: "Vennela" }] }]
   */
  async sendTemplate(to, templateName, languageCode = "en_US", components = []) {
    if (!E164.test(to || "")) {
      throw new Error(`Invalid 'to' number (must be E.164 like +918328697349): "${to}"`);
    }
    if (!templateName) throw new Error("sendTemplate: templateName is required.");

    const template = { name: templateName, language: { code: languageCode } };
    if (components.length) template.components = components;

    return this._post(
      {
        messaging_product: "whatsapp",
        to: WhatsAppSender.normalize(to),
        type: "template",
        template,
      },
      `template:${templateName}`,
      to
    );
  }

  /**
   * Send a plain text message. ONLY delivers inside the 24h service window
   * (i.e. after the user has messaged you). For first contact use a template.
   */
  async sendText(to, body) {
    if (!E164.test(to || "")) {
      throw new Error(`Invalid 'to' number (must be E.164 like +918328697349): "${to}"`);
    }
    if (!body || !String(body).trim()) throw new Error("Cannot send an empty message body.");

    return this._post(
      {
        messaging_product: "whatsapp",
        to: WhatsAppSender.normalize(to),
        type: "text",
        text: { body },
      },
      "text",
      to
    );
  }

  /**
   * Generic interface used by the messenger facade. Uniform with the SMS sender.
   * payload = { template: { name, language, components } }  (preferred), or
   * payload = { body }  (text — 24h window only).
   */
  async send(to, payload = {}) {
    if (payload.template) {
      const t = payload.template;
      return this.sendTemplate(to, t.name, t.language, t.components || []);
    }
    if (payload.body) {
      return this.sendText(to, payload.body);
    }
    throw new Error(
      "WhatsAppSender.send: payload needs { template: {...} } or { body }."
    );
  }
}

module.exports = { WhatsAppSender, E164 };
