"use strict";

/**
 * SMS message templates (free-form text — no Twilio/Meta approval needed for SMS).
 *
 * Cost note: these are kept to the plain GSM-7 character set (no emoji, no fancy
 * "—" dashes or curly quotes) so each message stays in the cheap 160-char/segment
 * encoding instead of the 70-char/segment Unicode one.
 *
 * Each template is a function (vars) => string. Render by key with
 * renderTemplate(key, vars). A WhatsApp variant of any key can live alongside
 * later (e.g. "winners2026.personalized.whatsapp").
 */

const WINNERS_URL = "https://stevieawards.com/winners/2026";
const ENTER_URL = "https://stevieawards.com/enter";

function need(vars, keys, templateKey) {
  const missing = keys.filter((k) => !vars || vars[k] === undefined || vars[k] === "");
  if (missing.length) {
    throw new Error(`Template "${templateKey}" requires: ${missing.join(", ")}`);
  }
}

const templates = {
  // 1) Winners announced — GENERALIZED (no personal data).
  "winners2026.generalized": () =>
    "Stevie Awards: The 2026 winners have been announced! See who took home " +
    `Gold, Silver and Bronze: ${WINNERS_URL}`,

  // 2) Winners announced — PERSONALIZED (needs { name }).
  "winners2026.personalized": (v = {}) => {
    need(v, ["name"], "winners2026.personalized");
    return (
      `${v.name}, the 2026 Stevie Awards winners are official! ` +
      `See this year's Gold, Silver and Bronze honorees: ${WINNERS_URL}`
    );
  },

  // 3) Entry deadline reminder (needs { name, deadline }).
  "deadline.reminder": (v = {}) => {
    need(v, ["name", "deadline"], "deadline.reminder");
    return (
      `${v.name}, entries for the 2026 Stevie Awards close ${v.deadline}. ` +
      `Don't miss your chance - enter now: ${ENTER_URL}`
    );
  },

  // 4) Finalist announcement (needs { name }; optional { category }).
  "finalist.announcement": (v = {}) => {
    need(v, ["name"], "finalist.announcement");
    const cat = v.category ? ` in ${v.category}` : "";
    return (
      `Congratulations ${v.name}! You're a 2026 Stevie Awards finalist${cat}. ` +
      `Winners are revealed soon: ${WINNERS_URL}`
    );
  },

  // 5) Winner congratulations (needs { name, level }; optional { category }).
  "winner.congrats": (v = {}) => {
    need(v, ["name", "level"], "winner.congrats");
    const cat = v.category ? ` for ${v.category}` : "";
    return (
      `${v.name}, congratulations! You've won a ${v.level} Stevie Award${cat} in 2026. ` +
      `See your win: ${WINNERS_URL}`
    );
  },

  // 6) Thank-you for entering (needs { name }).
  "thankYou.entry": (v = {}) => {
    need(v, ["name"], "thankYou.entry");
    return (
      `Thank you for entering the 2026 Stevie Awards, ${v.name}! ` +
      "We'll notify you as soon as finalists are announced. - The Stevie Awards"
    );
  },

  // 7) Ceremony reminder (needs { name, date }).
  "ceremony.reminder": (v = {}) => {
    need(v, ["name", "date"], "ceremony.reminder");
    return (
      `${v.name}, the 2026 Stevie Awards ceremony is on ${v.date}. ` +
      `We hope to celebrate with you! Details: ${WINNERS_URL}`
    );
  },
};

/**
 * Render a template body by key.
 * @param {string} key   e.g. "winner.congrats"
 * @param {object} vars  variables the template needs (e.g. { name, level })
 * @returns {string}     the final message body
 */
function renderTemplate(key, vars = {}) {
  const tpl = templates[key];
  if (typeof tpl !== "function") {
    throw new Error(`Unknown template "${key}". Known: ${Object.keys(templates).join(", ")}`);
  }
  return tpl(vars);
}

/** List available template keys. */
function listTemplates() {
  return Object.keys(templates);
}

module.exports = { templates, renderTemplate, listTemplates, WINNERS_URL, ENTER_URL };
