"use strict";

// Public surface of the messaging module.
const { createMessenger } = require("./messenger");
const { TwilioSmsSender } = require("./twilioSmsSender");
const { WhatsAppSender } = require("./whatsAppSender");
const { templates, renderTemplate } = require("./templates");

module.exports = {
  createMessenger,
  TwilioSmsSender,
  WhatsAppSender,
  templates,
  renderTemplate,
};
