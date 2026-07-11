"""Generate a shareable PDF explaining the review.csv triage (the 4 groups)."""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

OUT = "data/Subscriber_Review_Report.pdf"

NAVY = colors.HexColor("#1f3a5f")
GREY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#eef2f7")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], textColor=NAVY, fontSize=20, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], textColor=GREY, fontSize=10, spaceAfter=12)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontSize=10, leading=15, spaceAfter=6)
SMALL = ParagraphStyle("SMALL", parent=ss["Normal"], fontSize=9, textColor=GREY, leading=12)
CELL = ParagraphStyle("CELL", parent=ss["Normal"], fontSize=9.5, leading=13)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")


def cell(txt, style=CELL):
    return Paragraph(txt, style)


story = []
story.append(Paragraph("Subscriber Data Cleanup", H1))
story.append(Paragraph("Review File Analysis &mdash; Stevie Awards SMS/WhatsApp list &mdash; prepared 10 Jul 2026", SUB))
story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10))

# Overview
story.append(Paragraph("Overview", H2))
story.append(Paragraph(
    "The raw export contained <b>10,626 rows</b>. After cleaning (splitting the "
    "country code out of each phone number, converting to international E.164 format, "
    "repairing garbled names, and normalizing countries), the data split into two files:",
    BODY))
ov = Table([
    [cell("<b>Cleaned &mdash; ready to use</b>", CELLB), cell("7,878", CELLB), cell("74%")],
    [cell("Review &mdash; held back (this report)"), cell("2,748"), cell("26%")],
], colWidths=[3.6*inch, 1.2*inch, 1.0*inch])
ov.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f0e3")),
    ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(ov)
story.append(Paragraph(
    "The 2,748 review rows are <b>not broken data waiting to be fixed</b> &mdash; they are rows the "
    "cleaner correctly held back. They fall into four groups, only one of which can be recovered "
    "by further data cleaning.", BODY))

# Group summary table
story.append(Paragraph("The four groups", H2))
head = [cell("Group", CELLB), cell("Rows", CELLB), cell("Share", CELLB),
        cell("Can cleaning fix it?", CELLB), cell("What to do", CELLB)]
data = [
    head,
    [cell("1. Duplicates"), cell("474"), cell("17%"),
     cell("N/A"), cell("Ignore &mdash; the person is already in the cleaned list.")],
    [cell("2. Bot / spam signups"), cell("1,697"), cell("62%"),
     cell("No"), cell("Quarantine. Only a careful re-opt-in can ever qualify them.")],
    [cell("3. Bad name, valid phone"), cell("23"), cell("1%"),
     cell("Yes"), cell("Recover ~19 into the clean list (blank the junk name).")],
    [cell("4. Unusable numbers"), cell("554"), cell("20%"),
     cell("No"), cell("Discard &mdash; no real phone number exists in the row.")],
]
t = Table(data, colWidths=[1.5*inch, 0.6*inch, 0.6*inch, 1.15*inch, 2.6*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d4e0")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 6))

# Detail sections
def group(title, body):
    story.append(Paragraph(title, H2))
    story.append(Paragraph(body, BODY))

group("Group 1 &mdash; Duplicates (474)",
      "The same phone number appeared on more than one row (people who signed up several times). "
      "The cleaner already kept the best copy (confirmed / most recent) in the cleaned list, so these "
      "duplicates are simply the extra copies. <b>Nothing is lost and nothing needs fixing</b> &mdash; do not re-add them.")

group("Group 2 &mdash; Bot / spam signups (1,697)",
      "A large block of automated form-spam created on 20&ndash;21 June 2026. The numbers are correctly "
      "<i>formatted</i>, but the rows show the classic bot fingerprint: random gibberish names "
      "(e.g. &lsquo;afzda&rsquo;, &lsquo;qmoggnx&rsquo;), thousands created within minutes, frequently "
      "<b>sequential phone numbers</b>, identical filler fields, and <b>none confirmed</b>. These have "
      "no consent and are probably not real people. Data cleaning cannot fix a consent problem &mdash; "
      "the only way to test them is a small, careful re-opt-in message (&lsquo;Reply YES&rsquo;), which "
      "will likely reach mostly dead numbers. Keep them quarantined; do not include in normal sends.")

group("Group 3 &mdash; Bad name but valid phone (23) &mdash; the only recoverable group",
      "Here the phone number is genuinely valid; only the <i>name</i> field is junk (an email address, "
      "a number, or blank). About <b>19</b> of these can be moved into the cleaned list by simply "
      "clearing the bad name &mdash; the phone is what matters for messaging.")

group("Group 4 &mdash; Unusable numbers (554)",
      "These rows have no real phone number to recover: invalid numbers that are too short or too long "
      "(490), entries with letters where digits should be (49), and SQL/XSS junk submitted through the "
      "form (15). You cannot clean data that was never a valid number &mdash; discard them.")

story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=8, spaceAfter=8))
story.append(Paragraph("Bottom line", H2))
story.append(Paragraph(
    "Further data-cleaning recovers only about <b>19</b> more usable contacts. The rest is either "
    "already counted (duplicates), genuinely dead (no number), or a consent question (bots) &mdash; "
    "none of which more cleaning can solve. The usable list is the <b>7,878</b> in the cleaned file.",
    BODY))
story.append(Paragraph(
    "Separately &mdash; and more important than the review file &mdash; note that <b>1,241 numbers "
    "inside the cleaned list are valid but were never confirmed</b> (no verified consent). Sending to "
    "unconfirmed numbers risks TCPA penalties and high complaint/failure rates that can get the Twilio "
    "and WhatsApp senders throttled or blocked. Recommendation: send only to <b>confirmed</b> "
    "subscribers, and re-opt-in the unconfirmed ones in small batches before messaging.",
    BODY))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "Files: data/SMS subscribers export 7-8-26.cleaned.csv &nbsp;|&nbsp; "
    "data/SMS subscribers export 7-8-26.review.csv", SMALL))

SimpleDocTemplate(OUT, pagesize=LETTER,
                  leftMargin=0.8*inch, rightMargin=0.8*inch,
                  topMargin=0.7*inch, bottomMargin=0.7*inch).build(story)
print("wrote", OUT)
