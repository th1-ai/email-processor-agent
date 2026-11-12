# Email Processor Agent

A Claude Code skill for hotel operators. It runs on a schedule (or on demand), checks every configured inbox, classifies each new email, drafts replies where appropriate, and logs every classification to a Google Sheet so morning routine can review them in one place. How much it does on its own is set by one line in [`AUTONOMY.md`](AUTONOMY.md); the default is "report only".

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
- **Works at the autonomy level you set** — report only, prepare drafts, or act inside fixed limits ([`AUTONOMY.md`](AUTONOMY.md))
- **Remembers its runs** — a run log in `runs/` stops double work and lists what needs you first

---

## What you need

- [Claude Code](https://code.claude.com/docs/en/overview) installed
- One or more email accounts you can read programmatically, through a command-line wrapper that takes the account as its first argument (the reference setup is a Gmail / Google Workspace wrapper called `gws`). The skill needs it to list messages, read a message, read / append / update sheet rows, and create drafts. Subcommand names in the skill file are examples; change them to match your wrapper.
- A PMS with API access — the processor calls a `lookup_guest`-style tool. The reference setup is Cloudbeds, but any PMS with reservation lookup endpoints works.
- Draft helpers: one that creates a threaded reply draft and one that creates a new draft
- A Google Sheet (or equivalent) with two tabs: `Inbox` and `Config`
- For unattended runs: a scheduler (cron is enough) and `python3` for the optional guard hook. See [Run it on its own](#run-it-on-its-own)

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

6. **Schedule it** once a manual run looks right. See [Run it on its own](#run-it-on-its-own).

---

## Verify it works

Do this once before you schedule anything:

1. Send a test email to one of the inboxes from an address that is not in your PMS, asking about dates.
2. Say "Process emails." and check three things: a new row in the Inbox tab with class `booking-inquiry`, a draft in that mailbox with Draft Status `PENDING REVIEW`, and nothing in the Sent folder.
3. Run it again. The second run must add no row and no draft for the same email.

## Run it on its own

The skill reads [`AUTONOMY.md`](AUTONOMY.md) at the start of every run. One line there, `Level: <value>`, sets the level:

| Level | A scheduled run does this |
|---|---|
| PAUSED | Nothing. It logs why and stops. A missing file or an invalid `Level:` line counts as PAUSED. |
| 0 | Nothing. The skill runs only when you ask. |
| 1 (default) | Reads and classifies, then reports what it would draft and log. Writes only to `runs/`. |
| 2 | Also creates the drafts, the Inbox rows and the lead updates. You approve each draft before it is sent. |
| 3 | Also sends one fixed acknowledgement that you wrote to known guests, and archives listed junk senders, inside the limits in `AUTONOMY.md`. Both are off until you fill in their settings. |

No written reply is ever sent without your approval, at any level. `Level: PAUSED` stops the scheduled runs.

### 1. Make the permissions file

A scheduled run cannot answer a permission prompt. Copy the example and fill in the same placeholders as in the skill file:

```bash
cp .claude/settings.example.json .claude/settings.scheduled.json
```

The copy is passed only to the scheduled run (with `--settings`), so your own Claude Code sessions in this folder, where you approve and send drafts, stay as they are. It allows file reads, writes to `runs/`, and your four CLIs. It denies `.env`, edits to `AUTONOMY.md` and `.claude/`, `rm`, `curl`, `wget`, web fetch and web search. Bash rules match the command text as written, so each placeholder must be replaced with the command exactly as the skill file calls it.

### 2. The guard hook (optional, recommended)

The same file registers a [PreToolUse hook](https://code.claude.com/docs/en/hooks), [`.claude/hooks/autonomy_guard.py`](.claude/hooks/autonomy_guard.py). Before each shell command of a scheduled run it reads the `Level:` line and blocks:

- every command, when `AUTONOMY.md` is at `Level: PAUSED` or `Level: 0` (a missing file, a missing or repeated `Level:` line and an unknown value all count as PAUSED)
- commands whose first words contain `append`, `update`, `draft`, `create` or `insert`, below Level 2
- commands whose first words contain `send`, `archive` or `modify`, below Level 3
- commands whose first words contain `rm`, `delete`, `trash`, `purge` or `forward`, always

Those words fit the example command names in the skill file. **Edit the three patterns at the top of the script to fit your own CLIs**, then test it:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"{{EMAIL_CLI}} {{INBOX_PRIMARY}} drafts-send --id x"}}' \
  | CLAUDE_PROJECT_DIR="$PWD" python3 .claude/hooks/autonomy_guard.py; echo "exit $?"
```

Exit 2 with a reason means blocked; exit 0 means the hook has no objection. The hook is a second safety net that checks command names. It does not check the daily caps or who an email goes to; the skill does that. If `python3` is missing, the hook fails and Claude Code lets the command through, so check that it runs. To leave the hook out, delete the `hooks` block from your copy.

### 3. The scheduled command

```bash
cd /path/to/email-processor-agent && \
  /full/path/to/claude -p "/email-processor Scheduled run." \
    --settings .claude/settings.scheduled.json \
    --permission-mode dontAsk \
    --max-turns 80 \
    < /dev/null >> runs/cron.log 2>&1
```

- `-p` runs Claude Code without a terminal; `/email-processor` in the prompt starts the skill.
- `--permission-mode dontAsk` denies everything the settings file does not allow, instead of waiting for an answer.
- `--max-turns` stops a run that goes on too long. Raise it if a busy inbox needs more.
- Do not add `--bare`: it skips skills and hooks.
- Run `which claude` to get the full path. Run the command once by hand before you schedule it.

Example crontab line (every 30 minutes from 07:00 to 22:59; an example, adjust it):

```
*/30 7-22 * * * cd /path/to/email-processor-agent && /full/path/to/claude -p "/email-processor Scheduled run." --settings .claude/settings.scheduled.json --permission-mode dontAsk --max-turns 80 < /dev/null >> runs/cron.log 2>&1
```

Choose an interval longer than one run takes, so two runs do not overlap. Cron starts with a small environment: if the first run in `runs/cron.log` shows a login or "command not found" error, make your CLIs and the Claude Code login available to cron on your machine. Claude Code also has its own schedulers ([Desktop scheduled tasks, cloud routines and `/loop`](https://code.claude.com/docs/en/scheduled-tasks)). Desktop tasks run on your machine like cron. Cloud routines run on a fresh clone without your local CLIs or `.env`, so they do not fit this skill as it is.

Headless use of a personal Pro or Max plan is subject to Anthropic's usage policy; for a heavy or business-critical schedule use an API key or a team plan.

### 4. Move up one level at a time

1. Run at the current level for at least 7 days.
2. Read `runs/LOG.md` (or `runs/cron.log`): were the classes right, were the proposals what you would have done, was "Needs you" complete?
3. Change the one `Level:` line in `AUTONOMY.md`. For Level 3 also fill in the setting of each action you want.
4. The next 3 scheduled runs are shadow runs: they work at the old level and list what the new level would have done. Read them.

To go back, lower the number. To stop, write `Level: PAUSED`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/email-processor` is not in the `/` menu | Claude Code was not started in this folder, or the skill file was moved out of `.claude/skills/email-processor/` |
| The run stops and lists `{{...}}` names | Those placeholders are still in the skill file. Fill them in, or delete the lines you do not use |
| The same email gets a second draft | The `Email Message ID` is not in column J of the Inbox tab, or the append to the sheet failed |
| Nothing is found although mail is unread | The `last_check_*` date in the Config tab is in the future, or the wrapper is pointed at another account |
| A scheduled run does nothing | `AUTONOMY.md` says `Level: PAUSED` or `Level: 0` (or has no valid `Level:` line), or a command is not allowed. Read the last lines of `runs/cron.log`; add the missing command to `.claude/settings.scheduled.json` |
| The report shows an `autonomy guard:` message | The command needs a higher level, or a pattern in `.claude/hooks/autonomy_guard.py` matches one of your read commands. Fix the pattern |
| A scheduled run writes no drafts | Level 1 only reports, and the first 3 runs after a level change are shadow runs |

---

## File structure

```
email-processor-agent/
├── README.md                                      # This file
├── AUTONOMY.md                                    # The autonomy level and its limits (you edit this)
├── .env.example                                   # Settings template for your own wrappers
├── .gitignore
├── LICENSE
├── runs/
│   ├── README.md                                  # Format of the run log and handoff file
│   └── .gitkeep                                   # LOG.md, handoff/ and cron.log appear here (git-ignored)
└── .claude/
    ├── settings.example.json                      # Permissions + hook for scheduled runs (copy, do not rename)
    ├── hooks/
    │   └── autonomy_guard.py                      # Optional guard hook for scheduled runs
    └── skills/
        └── email-processor/
            └── SKILL.md                           # The skill definition
```

---

## Customising

The skill file uses placeholders so it can be adapted to any email + PMS + sheet stack. Replace the following before first run (four of them are also in `.claude/settings.example.json`):

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

What the skill did is in the run log (`runs/LOG.md`, see [`runs/README.md`](runs/README.md)). For what it learned, it leans on Claude Code's auto memory, which keeps notes per repository on your machine (run `/memory` to see or edit them). Ask Claude to remember patterns such as:

- **Sender domains confirmed as recurring noise** so future runs skip them faster
- **OTA relay-name -> reservation-name mappings** the processor had to figure out the hard way
- **False-positive phishing flags** so the rule can be tightened

Keep memory concise — one line per pattern.

---

## Related agents

This processor pairs naturally with:

- [`email-triage-agent`](https://github.com/th1-ai/email-triage-agent) — the lower-level triage logic the processor builds on
- [`booking-inquiry-agent`](https://github.com/th1-ai/booking-inquiry-agent) — drafts the reply when this processor classifies as `booking-inquiry`; picks its work up from `runs/handoff/email-processor-agent.md`
- [`email-draft-agent`](https://github.com/th1-ai/email-draft-agent) — the underlying draft-creation primitive
- [`concierge-agent`](https://github.com/th1-ai/concierge-agent) — handles the guest service requests this processor classifies as `concierge`
- [`crm-pipeline-agent`](https://github.com/th1-ai/crm-pipeline-agent) — the lead pipeline this processor updates for new inquiries
- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — reads the sheet this processor populates, the last entry in `runs/LOG.md` and the `Level:` line, and is where you approve drafts

Each one is a separate repo. To use them together, copy their `.claude/skills/` (and `.claude/agents/`) folders into the same project.

The full set of 21 agents is at [th1.ai/agent-stack](https://th1.ai/agent-stack).

---

## License

MIT — see [LICENSE](LICENSE).
