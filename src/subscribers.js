"use strict";

const fs = require("fs");

// Stevie program codes -> friendly names (used to fill the {{program}} slot).
const TOPIC_LABELS = {
  ABA: "American Business Awards",
  APSA: "Asia-Pacific Stevie Awards",
  GSA: "German Stevie Awards",
  IBA: "International Business Awards",
  MENA: "Middle East & North Africa Stevie Awards",
  SALES: "Sales & Customer Service",
  WOMEN: "Women in Business",
  EMPLOYERS: "Great Employers",
  SATE: "Technology Excellence",
  WFC: "Women | Future of Work",
  IPRA: "Innovation & PR",
  "MENA-AR": "MENA (Arabic)",
};

// Minimal CSV parser that handles quoted fields containing commas/newlines.
function parseCsv(text) {
  const rows = [];
  let field = "";
  let record = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { record.push(field); field = ""; }
    else if (c === "\n") { record.push(field); rows.push(record); record = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field.length || record.length) { record.push(field); rows.push(record); }
  return rows;
}

// Load the cleaned subscriber CSV into an array of row objects.
function loadSubscribers(csvPath) {
  const text = fs.readFileSync(csvPath, "utf8");
  const rows = parseCsv(text).filter((r) => r.length && r.some((c) => c !== ""));
  if (!rows.length) return [];
  const header = rows[0].map((h) => h.trim());
  return rows.slice(1).map((r) => {
    const obj = {};
    header.forEach((h, i) => (obj[h] = (r[i] || "").trim()));
    return obj;
  });
}

/**
 * Filter subscribers for a campaign. Same rules as the schedule form:
 *  - must be active (not opted out)
 *  - must subscribe to at least one of the selected topics
 *  - reminder type must match (or the subscriber is on "All Reminders")
 *  - unverified numbers excluded unless includeUnverified is true
 *
 * @param {object[]} rows
 * @param {{topics?: string[], reminderType?: string, includeUnverified?: boolean}} opts
 */
function filterRecipients(rows, opts = {}) {
  const topics = new Set(opts.topics || []);
  const reminderType = opts.reminderType || "";
  const includeUnverified = !!opts.includeUnverified;

  return rows.filter((r) => {
    if (r.active !== "1") return false;
    const rowTopics = new Set(
      (r.topics || "").split(";").map((t) => t.trim()).filter(Boolean)
    );
    if (topics.size && ![...topics].some((t) => rowTopics.has(t))) return false;

    const reminders = r.reminder_types || "";
    if (reminderType && !reminders.includes(reminderType) && !reminders.includes("All Reminders")) {
      return false;
    }
    const verified = (r.number_confirmed || "").toLowerCase() === "yes";
    if (!includeUnverified && !verified) return false;
    return true;
  });
}

module.exports = { TOPIC_LABELS, loadSubscribers, filterRecipients };
