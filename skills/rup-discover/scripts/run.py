#!/usr/bin/env python3
"""
rup-discover — discovery conversation before anything new is built (host-LLM, ADR-0012).

The agent running this skill is the LLM: this script prints the work packet and
records the agent's document into .context/ (mandatory, ADR-0011). The agent
first TALKS with the user (one question per message), plays the answers back,
and writes the document only after the user confirms.

Usage:
  python run.py "idea or demand"                       # 1. print the work packet (Inception)
  python run.py --record doc.md "idea or demand"       # 2. validate + write .context/
"""

import sys
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import discipline  # noqa: E402
from _shared.rup import setup_console  # noqa: E402

SPEC = {
    "key": None,
    "title": "Discovery",
    "default_phase": "Inception",
    "instructions": [
        "Talk with the user BEFORE writing anything: ask one question per message, "
        "build each question on the last answer, and say why you ask when it is not obvious.",
        "Play back each part of the discovery in your own words and ask what is wrong or "
        "missing. Write and record the document only after the user confirms the playback.",
    ],
    "agents": [
        {"slug": "discovery-facilitator",
         "role": "Discovery Facilitator",
         "goal": "Turn a raw idea into a confirmed shared understanding of the problem, "
                 "the people, the goals and the limits, before any requirement is written.",
         "backstory": "Facilitator who listens first: you ask short, focused questions, "
                      "challenge vague answers kindly, and never fill a gap with your own guess.",
         "mission": "Run the discovery conversation with the user and record what they "
                    "confirmed: problem, users, goals, non-goals, anti-goals, constraints "
                    "and what is still unknown.",
         "artifacts": ["Problem", "Users", "Goals", "Non-goals", "Anti-goals",
                       "Constraints", "Open questions"]},
    ],
}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
