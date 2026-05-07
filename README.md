# Email Processor Agent

A Claude Code skill for hotel operators. It runs on a 15-minute schedule (or on demand), checks every configured inbox, classifies each new email, drafts replies where appropriate, and logs every classification to a Google Sheet so morning routine can review them in one place.

Built on the **WAT framework** (Workflows, Agents, Tools): probabilistic AI handles reasoning, deterministic scripts handle execution.

---

## What it does

- **Reads new mail since last check** for every configured account, deduped against an inbox-tracking sheet
- **Phishing-checks first** — fake-OTA emails, unverifiable booking claims, and unsolicited links are flagged before classification
- **Classifies into eight buckets** — booking inquiry, guest message, concierge, OTA notification, supplier, needs-attention, phishing, ignore
- **Runs a stale-email sanity check** before drafting any guest reply, so the agent never sends "plan your stay" copy to a guest who has already arrived
- **Drafts replies** for booking inquiries and guest messages — never sends, only drafts
- **Updates your CRM pipeline** for new inquiries and follow-ups
- **Logs every email** to the Inbox tab (timestamp, account, classification, urgency, summary, draft status, IDs)
- **Plays nicely with morning routine** — that skill reads the sheet, doesn't re-process

---

## What you need

- [Claude Code](https://claude.ai/code) installed
- One or more email accounts you can read programmatically (Gmail via the Google Workspace CLI is the reference setup)
- A PMS with API access — the processor calls a `lookup_guest`-style tool. The reference setup is Cloudbeds, but any PMS with reservation lookup endpoints works.
- A Google Sheet (or equivalent) with two tabs: `Inbox` and `Config`
- A scheduler that can fire the skill every 15 minutes (cron, a remote-trigger system, or whatever your harness supports)

---

## Quick start

1. **Clone the repo** into a Claude Code project:

   ```bash
   git clone https://github.com/th1-ai/email-processor-agent.git
   cd email-processor-agent
   ```

2. **Copy the env template** and fill it in:

   ```bash
   cp .env.example .env
   ```

3. **Edit [`.claude/skills/email-processor/SKILL.md`](.claude/skills/email-processor/SKILL.md)** — replace the placeholders described in [Customising](#customising).

4. **Set up the spreadsheet:**
   - Inbox tab columns: `Timestamp | Account | From | Subject | Classification | Urgency | Summary | Action Taken | Draft Status | Email Message ID | Email Draft ID | Processed At`
   - Config tab columns: `Key | Value` (rows like `last_check_primary | 2026/05/01`)

5. **Open in Claude Code** and trigger the skill:

   > "Process emails."

   Or wire it into a 15-minute schedule.

---

## File structure

```
email-processor-agent/
├── README.md                                      # This file
├── .env.example                                   # Inboxes, PMS auth, sheet ID
├── .gitignore
├── LICENSE
└── .claude/
    └── skills/
        └── email-processor/
            └── SKILL.md                           # The skill definition
```

---

## Customising

The skill file uses placeholders so it can be adapted to any email + PMS + sheet stack. Replace the following before first run:

| Placeholder | What to put | Example |
|---|---|---|
| `{{INBOX_PRIMARY}}` | Main business inbox address | `info@yourhotel.com` |
| `{{INBOX_BOOKINGS}}` | Inquiries / OTA inbox | `bookings@yourhotel.com` |
| `{{INBOX_RENTALS}}` | Whole-property / villa inbox (optional) | `rentals@yourhotel.com` |
| `{{EMAIL_CLI}}` | Command-line wrapper to your email + sheets provider | `gws` |
| `{{PMS_LOOKUP_TOOL}}` | Script that looks up reservations by email / name / confirmation # | `tools/lookup_guest.py` |
| `{{SHEET_ID_INBOX}}` | Google Sheet ID for the inbox tracker | (Google Sheet ID) |
| `{{OPERATOR_NAME}}` | Name used in sign-offs | `Jane Doe` |
| `{{HOTEL_NAME}}` | Hotel name used in sign-offs | `Your Hotel` |

The reference setup uses `tools/lookup_guest.py` and helpers like `tools/create_draft_reply.py` / `tools/create_draft_email.py`. Yours can be named anything — the placeholders are the only thing the skill cares about.

You can do replacements with any text editor or with one `sed` pass:

```bash
sed -i '' \
  -e 's|{{INBOX_PRIMARY}}|info@yourhotel.com|g' \
  -e 's|{{EMAIL_CLI}}|gws|g' \
  -e 's|{{PMS_LOOKUP_TOOL}}|tools/lookup_guest.py|g' \
  .claude/skills/email-processor/SKILL.md
```

---

## How memory works

This skill leans on Claude Code's per-project memory. After each run, useful patterns to record include:

- **Sender domains confirmed as recurring noise** so future runs skip them faster
- **OTA relay-name -> reservation-name mappings** the processor had to figure out the hard way
- **False-positive phishing flags** so the rule can be tightened

Keep memory concise — one line per pattern.

---

## Related agents

This processor pairs naturally with:

- [`email-triage-agent`](https://github.com/th1-ai/email-triage-agent) — the lower-level triage logic the processor builds on
- [`booking-inquiry-agent`](https://github.com/th1-ai/booking-inquiry-agent) — drafts the reply when this processor classifies as `booking-inquiry`
- [`email-draft-agent`](https://github.com/th1-ai/email-draft-agent) — the underlying draft-creation primitive
- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — reads the sheet this processor populates

---

## License

MIT — see [LICENSE](LICENSE).
