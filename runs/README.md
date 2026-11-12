# runs/

The email processor's own memory. The skill writes here on every run. Everything in this folder except this file is git-ignored, because run entries point at guest email.

## `LOG.md`

One entry per run, appended at the end. The latest run summary is the last entry; other agents read that entry, not a separate file. The skill reads the last entries before it acts, so it does not do the same work twice. Entries hold message IDs, classes and counts. They hold no names, addresses or email text.

```
## 2026-05-01 09:15 | Level 2 | scheduled | shadow: no
- Checked: primary 3 new, bookings 0 new, rentals SKIPPED (auth error)
- Done: row + draft r-18f2 for msg 18c1a (booking-inquiry); row for msg 18c1b (ignore); row for msg 18c1c (needs-attention, HELD)
- Proposed: none
- Would have done: none
- Errors: rentals fetch failed (auth error)
- Needs you: msg 18c1c needs-attention (refund request); rentals inbox did not fetch
- Seen: 18c1a 18c1b 18c1c
```

- `Done` lists what was written, with the IDs that came back (draft ID, sheet row, sent message ID).
- `Proposed` lists what Level 1 would draft or log but did not.
- `Would have done` is filled only in shadow runs after a level change.
- `Seen` lists every message ID the run classified. Report-only runs (Level 1 and shadow runs) use it as their dedup list, because they write no sheet row. Full runs dedup against the sheet.
- A skipped run is one line with the reason: `## 2026-05-01 09:30 | PAUSED | scheduled | skipped: Level is PAUSED` (or `skipped: AUTONOMY.md has no valid Level line`).

## `handoff/email-processor-agent.md`

Work for sibling agents. One line per item, appended, never edited. The reader dedups by message ID.

```
| Time | Message ID | Account | For | Class | What is needed |
| 2026-05-01 09:15 | 18c1a | bookings | booking-inquiry-agent | booking-inquiry | availability reply, 2 guests, 12 to 15 June |
```

`For` is one of `booking-inquiry-agent`, `concierge-agent`, `crm-pipeline-agent` or `morning-routine-agent`.

## `cron.log`

Where the example scheduler command in the main README sends each run report. You can delete it at any time.
