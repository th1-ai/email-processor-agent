#!/usr/bin/env python3
"""PreToolUse guard for scheduled runs of the email processor.

Reads the hook JSON on stdin. For a Bash call it reads the `Level:` line in
AUTONOMY.md and blocks (exit 2) a command the current level does not allow.
Exit 0 = no decision, the normal permission rules still apply.

It looks only at the first words of each command (program, account,
subcommand), not at the arguments, so an email subject that contains the
word "send" does not block a sheet row.

EDIT the three patterns below to match the subcommand names of YOUR CLIs.
This is a second safety net. It does not replace the rules in the skill.
"""
import json
import os
import re
import shlex
import sys

# Words in the head of a command, and the level each needs.
NEVER = re.compile(r"(^|[^a-z])(rm|rmdir|delete|trash|purge|forward)([^a-z]|$)")
LEVEL3 = re.compile(r"(^|[^a-z])(send|archive|modify)([^a-z]|$)")
LEVEL2 = re.compile(r"(append|update|draft|create|insert)")

SEPARATORS = {"&&", "||", ";", "|", "|&", "&", "(", ")"}
HEAD_WORDS = 4


def block(reason):
    sys.stderr.write("autonomy guard: " + reason + "\n")
    sys.exit(2)


def read_level(project_dir):
    """Return 0-3, or "PAUSED".

    AUTONOMY.md has exactly one line "Level: <value>". A missing file, a missing
    line, more than one line or an unknown value all count as PAUSED.
    """
    try:
        with open(os.path.join(project_dir, "AUTONOMY.md"), encoding="utf-8") as fh:
            values = re.findall(r"^Level:[ \t]*(\S*)[ \t]*$", fh.read(), re.MULTILINE)
    except OSError:
        return "PAUSED"
    if len(values) == 1 and values[0] in ("0", "1", "2", "3"):
        return int(values[0])
    return "PAUSED"


def heads(command):
    """Yield the first words of each simple command, up to the first option."""
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        tokens = command.split()
    segment = []
    for tok in tokens + [";"]:
        if tok in SEPARATORS:
            if segment:
                yield segment
            segment = []
        else:
            segment.append(tok)


def head_of(segment):
    out = []
    for tok in segment:
        if tok.startswith("-") or len(out) >= HEAD_WORDS:
            break
        out.append(tok.lower())
    return " ".join(out)


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    level = read_level(project_dir)

    if level == "PAUSED":
        block("AUTONOMY.md is PAUSED (or has no valid Level line). Scheduled runs do not run commands.")
    if level == 0:
        block("AUTONOMY.md is at Level 0. Scheduled runs do not run commands.")
    if "$(" in command or "`" in command:
        block("command substitution is not allowed in a scheduled run.")

    for segment in heads(command):
        head = head_of(segment)
        if NEVER.search(head):
            block("'%s' deletes or forwards. That is never autonomous." % head)
        if LEVEL3.search(head) and level < 3:
            block("'%s' needs Level 3. AUTONOMY.md says Level %d." % (head, level))
        if LEVEL2.search(head) and level < 2:
            block("'%s' needs Level 2. AUTONOMY.md says Level %d." % (head, level))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed
        block("could not check the command (%s)." % exc.__class__.__name__)
