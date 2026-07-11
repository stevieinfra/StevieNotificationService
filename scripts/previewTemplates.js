"use strict";

/** Print every SMS template rendered with sample data. No creds, no sending. */
const { renderTemplate, listTemplates } = require("../src/messaging/templates");

// sample variables used to fill each template for the preview
const sample = {
  name: "Vennela",
  deadline: "Feb 28, 2026",
  category: "Innovation in Technology",
  level: "Gold",
  date: "March 15, 2026",
};

console.log("\n=== Stevie SMS Template Preview (sample data) ===\n");
for (const key of listTemplates()) {
  let body;
  try {
    body = renderTemplate(key, sample);
  } catch (e) {
    body = `(error: ${e.message})`;
  }
  const segments = Math.ceil(body.length / 160) || 1;
  process.stdout.write(
    `• ${key}  [${body.length} chars ~ ${segments} SMS segment(s)]\n  ${body}\n\n`
  );
}
