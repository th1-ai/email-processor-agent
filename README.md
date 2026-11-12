# Email Processor Agent

A Claude Code skill for hotel operators. It runs on a 15-minute schedule (or on demand), checks every configured inbox, classifies each new email, drafts replies where appropriate, and logs every classification to a Google Sheet so morning routine can review them in one place.

Built on the **WAT framework** (Workflows, Agents, Tools): probabilistic AI handles reasoning, deterministic scripts handle execution. This repo is the workflow (one markdown skill file). The scripts are yours: your email CLI, your PMS lookup, your draft helpers.

---

## What it does

- **Reads new mail since last check** for every configured account, deduped against an inbox-tracking sheet
- **Phishing-checks first** — fake-OTA emails, unverifiable booking claims, and unsolicited links are flagged before classification
- **Classifies into eight buckets** — booking inquiry, guest message, concierge, OTA notification, supplier, needs-attention, phishing, ignore
- **Runs a stale-email sanity check** before drafting any guest reply, so the agent never drafts "plan your stay" copy for a guest who has already arrived
- **Drafts replies** for booking inquiries and guest messages — never sends, only drafts
- **Updates your CRM pipeline** for new inquiries and follow-ups, if you keep one (optional)
- **Holds instead of guessing** — complaints, refund requests, unverifiable senders and badly timed replies are marked `HELD` for you, with the reason
- **Ends each run with a short report** — counts per class, drafts created, items held, problems
- **Logs every email** to the Inbox tab (timestamp, account, classification, urgency, summary, draft status, IDs)
- **Plays nicely with morning routine** — that skill reads the sheet, doesn't re-process

---

## What you need

- [Claude Code](https://code.claude.com/docs/en/overview) installed
- One or more email accounts you can read programmatically, through a command-line wrapper that takes the account as its first argument (the reference setup is a Gmail / Google Workspace wrapper called `gws`). The skill needs it to list messages, read a message, read / append / update sheet rows, and create drafts. Subcommand names in the skill file are examples; change them to match your wrapper.
- A PMS with API access — the processor calls a `lookup_guest`-style tool. The reference setup is Cloudbeds, but any PMS with reservation lookup endpoints works.
- Draft helpers: one that creates a threaded reply draft and one that creates a new draft
- A Google Sheet (or equivalent) with two tabs: `Inbox` and `Config`
- A scheduler that can fire the skill every 15 minutes (cron, a Claude Code scheduled task, or whatever your setup supports)

---

## Quick start

1. **Clone the repo** into a Claude Code project:

   ```bash
   git clone https://github.com/th1-ai/email-processor-agent.git
   cd email-processor-agent
   ```

2. **Fill in the placeholders.** The quickest way is to open Claude Code in this folder and say:

   > "Read the README and set this agent up with me."

   Claude asks you for each value in [Customising](#customising), writes them into the skill file, and tells you what is still missing. Or edit [`.claude/skills/email-processor/SKILL.md`](.claude/skills/email-processor/SKILL.md) by hand.

3. **Copy the env template** if your own scripts read their settings from `.env`:

   ```bash
   cp .env.example .env
   ```

   The skill file does not read `.env`. It uses the values you put in place of the placeholders. `.env` is for your wrappers and their credentials, and it is git-ignored.

4. **Set up the spreadsheet:**
   - Inbox tab columns: `Timestamp | Account | From | Subject | Classification | Urgency | Summary | Action Taken | Draft Status | Email Message ID | Email Draft ID | Processed At`
   - Config tab columns: `Key | Value`, one row per inbox: `last_check_primary`, `last_check_bookings`, `last_check_rentals`, each with a date like `2026/05/01`

5. **Trigger the skill** in Claude Code:

   > "Process emails."

   or type `/email-processor`.

6. **Schedule it** once a manual run looks right. Any scheduler that can start Claude Code in this folder works, for example cron with the non-interactive mode:

   ```bash
   cd /path/to/email-processor-agent && claude -p "Process emails."
   ```

   A scheduled run cannot answer permission prompts, so allow the commands your wrappers need in `.claude/settings.json` first. Allow only those commands.

---

## Verify it works

Do this once before you schedule anything:

1. Send a test email to one of the inboxes from an address that is not in your PMS, asking about dates.
2. Say "Process emails." and check three things: a new row in the Inbox tab with class `booking-inquiry`, a draft in that mailbox with Draft Status `PENDING REVIEW`, and nothing in the Sent folder.
3. Run it again. The second run must add no row and no draft for the same email.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/email-processor` is not in the `/` menu | Claude Code was not started in this folder, or the skill file was moved out of `.claude/skills/email-processor/` |
| The run stops and lists `{{...}}` names | Those placeholders are still in the skill file. Fill them in, or delete the lines you do not use |
| The same email gets a second draft | The `Email Message ID` is not in column J of the Inbox tab, or the append to the sheet failed |
| Nothing is found although mail is unread | The `last_check_*` date in the Config tab is in the future, or the wrapper is pointed at another account |
| A scheduled run does nothing | It is waiting on a permission prompt. Run the same command by hand and allow the commands it asks for |

---

## File structure

```
email-processor-agent/
├── README.md                                      # This file
├── .env.example                                   # Settings template for your own wrappers
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
| `{{DRAFT_REPLY_TOOL}}` | Helper that creates a threaded reply draft | `tools/create_draft_reply.py` |
| `{{DRAFT_NEW_TOOL}}` | Helper that creates a new email draft | `tools/create_draft_email.py` |
| `{{OPERATOR_NAME}}` | Name used in sign-offs | `Jane Doe` |
| `{{HOTEL_NAME}}` | Hotel name used in sign-offs | `Your Hotel` |

The `tools/...` paths are examples from the reference setup. This repo does not ship those scripts. Yours can be named anything — the placeholders are the only thing the skill cares about.

If you have fewer than three inboxes, delete the fetch line for the placeholder you do not use (for example `{{INBOX_RENTALS}}`). The skill stops when it finds a placeholder that is still unfilled.

You can do replacements with any text editor or with one `sed` pass (macOS syntax; on Linux use `sed -i` without the `''`):

```bash
sed -i '' \
  -e 's|{{INBOX_PRIMARY}}|info@yourhotel.com|g' \
  -e 's|{{EMAIL_CLI}}|gws|g' \
  -e 's|{{PMS_LOOKUP_TOOL}}|tools/lookup_guest.py|g' \
  .claude/skills/email-processor/SKILL.md
```

---

## How memory works

This skill has no memory files of its own. It leans on Claude Code's auto memory, which keeps notes per repository on your machine (run `/memory` to see or edit them). Ask Claude to remember patterns such as:

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
- [`concierge-agent`](https://github.com/th1-ai/concierge-agent) — handles the guest service requests this processor classifies as `concierge`
- [`crm-pipeline-agent`](https://github.com/th1-ai/crm-pipeline-agent) — the lead pipeline this processor updates for new inquiries
- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — reads the sheet this processor populates, and is where you approve drafts

Each one is a separate repo. To use them together, copy their `.claude/skills/` (and `.claude/agents/`) folders into the same project.

The full set of 21 agents is at [th1.ai/agent-stack](https://th1.ai/agent-stack).

---

## License

MIT — see [LICENSE](LICENSE).
