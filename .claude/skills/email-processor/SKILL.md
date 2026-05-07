# Skill: Email Processor

Automated email processing — check all configured hotel inboxes, classify each email, take action, and log everything to an Email Inbox spreadsheet.

> **Template note:** Replace `{{INBOX_*}}`, `{{EMAIL_CLI}}`, `{{PMS_LOOKUP_TOOL}}`, `{{SHEET_ID_INBOX}}` and tool placeholders with the wrappers and IDs your setup uses. See `README.md` for guidance.

## Trigger

- Scheduled run (e.g. cron / `RemoteTrigger` every 15 minutes)
- Operator says "process emails", "check emails and handle them"
- During morning routine (reviews the sheet, doesn't re-process)

## Email Inbox Sheet

**Sheet ID:** `{{SHEET_ID_INBOX}}`

**Inbox tab columns:** Timestamp | Account | From | Subject | Classification | Urgency | Summary | Action Taken | Draft Status | Email Message ID | Email Draft ID | Processed At

**Config tab:** Stores `last_check_{account}` dates for each inbox.

## Process

### 1. Read Config

Get last-check timestamps from the Config tab:

```bash
{{EMAIL_CLI}} primary sheets-get --spreadsheet-id "{{SHEET_ID_INBOX}}" --range "Config!A:B"
```

### 2. Fetch New Emails

For each configured account, fetch unread emails since last check:

```bash
{{EMAIL_CLI}} {{INBOX_PRIMARY}} triage --query "after:{last_check_date} is:unread" --max 20 --format json
{{EMAIL_CLI}} {{INBOX_BOOKINGS}} triage --query "after:{last_check_date} is:unread" --max 20 --format json
{{EMAIL_CLI}} {{INBOX_RENTALS}} triage --query "after:{last_check_date} is:unread" --max 20 --format json
```

### 3. Dedup

Read existing message IDs from the Inbox tab:

```bash
{{EMAIL_CLI}} primary sheets-get --spreadsheet-id "{{SHEET_ID_INBOX}}" --range "Inbox!J:J"
```

Skip any email whose message ID is already in the sheet.

### 4. Process Each Email

For each new email:

#### 4a. Read the full email

```bash
{{EMAIL_CLI}} {account} message-get --id <messageId> --format full
```

Decode the body (base64url -> text). Extract: from, subject, body text, received timestamp.

#### 4b. Phishing Check

Before anything else, run the phishing checks:
- Is the sender domain consistent with the claimed identity?
- If they claim a booking, verify with `{{PMS_LOOKUP_TOOL}} --email <sender_email>`
- Any suspicious links or redirect requests?

If phishing detected: classify as `phishing`, urgency HIGH, no draft. Log and move on.

#### 4c. Classify

| Classification | Criteria | Urgency |
|---------------|----------|---------|
| `booking-inquiry` | New guest asking about dates / rooms / pricing. Not in PMS. | HIGH |
| `guest-message` | Existing guest (found in PMS) with a question, request, or follow-up | HIGH |
| `concierge` | Guest on concierge tracker or high-value guest requesting services | HIGH |
| `ota-notification` | OTA system email — new booking, cancellation, modification confirmation | NORMAL |
| `supplier` | Invoice, delivery, contractor communication | NORMAL |
| `needs-attention` | Group booking (5+ rooms), long stay (14+ nights), complaint, payment dispute, modification request via OTA, anything uncertain | HIGH |
| `phishing` | Failed phishing checks | HIGH |
| `ignore` | Newsletter, spam, marketing, automated system alerts, OTA action-button emails | LOW |

**How to decide:**

1. Check sender domain and email pattern:
   - `@guest.booking.com` or `noreply-messaging@booking.com` -> OTA guest message (existing booking). Classify as `guest-message` or `needs-attention`.
   - `noreply@booking.com` or `noreply-email@booking.com` -> OTA system notification. Check if it's an action-button email (ignore) or a guest-message relay (needs-attention).
   - `@messages.homeaway.com` -> VRBO guest message (existing booking)
   - Known newsletter / marketing senders -> `ignore`

2. Look up sender in the PMS:
   ```bash
   {{PMS_LOOKUP_TOOL}} --email <sender_email>
   ```
   - Found with future / current booking -> `guest-message`
   - Found in concierge tracker -> `concierge`
   - Not found -> likely `booking-inquiry` or `ignore`

3. Read the email content to confirm classification.

#### 4c.5. Stale-email / booking-date sanity check (MANDATORY before drafting any guest reply)

Before drafting any reply to a `guest-message` or `concierge` email:

1. Note the email's sent date.
2. Look up the guest's booking in the PMS (check-in and check-out dates).
3. Compare to **today's date**.
4. Decide which phase the guest is in:
   - **Pre-arrival** (today < check-in): fine to draft a planning / welcome reply.
   - **In-house** (check-in <= today < check-out): reply must acknowledge they have already arrived — do NOT send generic pre-arrival "plan your stay" content. Offer help only for the time they have left.
   - **Post-stay** (today >= check-out): reply must acknowledge the stay is over — don't talk about plans, offer any follow-up relevant to the past visit.
5. If the email was pre-arrival but the guest has since arrived or left (typically because the email sat unprocessed for days), **flag to the operator first with a one-line summary** (email date, arrival/departure dates, today's date, suggested framing) before drafting. Don't auto-draft in this case.

This check is non-negotiable — better to flag and ask than send an awkwardly-timed reply.

#### 4d. Take Action

| Classification | Action | Details |
|---------------|--------|---------|
| `booking-inquiry` | Draft reply using the booking-inquiry skill steps | Fetch thread -> check availability -> draft reply -> create email draft. Log draft ID. |
| `guest-message` | Draft reply with PMS context | Fetch thread -> lookup reservation -> draft contextual reply -> create email draft. |
| `concierge` | Flag for concierge skill | If the guest is on the concierge tracker, note the request. Update concierge sheet if relevant. Draft reply if straightforward. |
| `ota-notification` | Log only | Extract key info (new booking name/dates, cancellation details). No draft needed. |
| `supplier` | Log with summary | Flag if action needed (invoice due, delivery arriving). No draft. |
| `needs-attention` | Detailed log, no draft | Summarise what's needed. The operator handles personally. |
| `phishing` | Log red flags | No draft, no links clicked, no action. |
| `ignore` | Minimal log | One-line summary. |

**Draft creation rules:**
- NEVER send emails — only create drafts
- Always use HTML format
- Use a threaded-reply helper (e.g. `{{DRAFT_REPLY_TOOL}}`) for replies to existing threads
- Use a new-email helper (e.g. `{{DRAFT_NEW_TOOL}}`) for new emails
- Follow the tone from the booking-inquiry skill: warm, personal
- Sign-off: `Best regards, {{OPERATOR_NAME}}, {{HOTEL_NAME}}`

**For booking inquiries with specific dates**, check availability with whatever availability tool your PMS exposes.

**For OTA guest messages**, always:
1. Fetch the full thread first
2. Look up the guest in the PMS by name (OTA relay emails don't use the guest's real email)
3. Understand the context before drafting

#### 4e. Add to CRM Pipeline

If the email is classified as `booking-inquiry`:

1. Check if this lead already exists in your CRM tool.
2. If no existing lead, add one with the inferred fields (name, email, source, dates, guests, room preference, thread ID, estimated value).
3. If a lead exists AND status is `REPLIED`, `FOLLOW_UP_DUE`, or `FOLLOW_UP_SENT`, the guest has responded back — update to `NEGOTIATING`.

If the email is classified as `guest-message` and the sender has an active pipeline lead, refresh the lead's Last Activity to `NEGOTIATING`.

### 5. Log to Sheet

Append a row to the Inbox tab for each processed email:

```bash
{{EMAIL_CLI}} primary sheets-append --spreadsheet-id "{{SHEET_ID_INBOX}}" --range "Inbox!A:L" \
  --values '[["{timestamp}","{account}","{from}","{subject}","{classification}","{urgency}","{summary}","{action_taken}","{draft_status}","{message_id}","{draft_id}","{processed_at}"]]'
```

### 6. Update Config Timestamps

After processing all emails for an account, update the last_check timestamp:

```bash
{{EMAIL_CLI}} primary sheets-update --spreadsheet-id "{{SHEET_ID_INBOX}}" --range "Config!B{row}" \
  --values '[["YYYY/MM/DD"]]'
```

## Morning Routine Integration

During morning routine, DON'T re-process emails. Instead:

1. Read the Inbox tab (last 24 hours of rows)
2. Group by urgency: HIGH first, then NORMAL
3. Show summary table to the operator
4. Highlight rows with Draft Status = `PENDING REVIEW`
5. For each pending draft, show the draft content
6. Operator approves or rejects each draft
7. For approved drafts, send via the email CLI's `drafts send` command for the relevant account
8. Update Draft Status in sheet to `SENT` or `REJECTED`

## Guardrails

- **NEVER send emails** — only create drafts. The operator approves during morning routine.
- **NEVER click links** in emails from unverified senders.
- **NEVER modify PMS reservations** without explicit approval.
- **Always verify senders** against the PMS before trusting booking claims.
- **Only check the configured hotel inboxes**, never an unrelated personal account.
- **Always use a per-account wrapper** when switching accounts — never set the active account via a global env var that can silently fall back to the wrong inbox.
- **Cost control:** Only fetch unread emails. Use date filters. Don't scan full history.
