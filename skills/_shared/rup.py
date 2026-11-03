"""
rup.py — Shared RUP registry and console setup for every cp-* skill.

Single source of truth for the phases and the ordered disciplines (the order
`--auto` follows and the order in which a discipline sees the artifacts of the
earlier ones). Pure standard library.
"""
import sys

# Exit codes shared by every skill.
EXIT_OK = 0
EXIT_USAGE = 1            # bad arguments, unreadable input, incomplete artifact
EXIT_CONTEXT_NOT_WRITABLE = 4
EXIT_NEEDS_CONSENT = 5     # .context/ not authorized (no .rup-standard marker)
# (2 = "no LLM" and 3 = "crewai missing" were retired with ADR-0012: the host
#  agent is the LLM and the skills have no runtime dependency.)

PHASES = ["Inception", "Elaboration", "Construction", "Transition"]

ORCHESTRATOR_SKILL = "cp-orchestrator"

# Ordered: environment → … → deployment.
DISCIPLINES = {
    "environment": {"skill": "cp-environment", "title": "Environment"},
    "business-modeling": {"skill": "cp-business-modeling", "title": "Business Modeling"},
    "requirements": {"skill": "cp-requirements", "title": "Requirements"},
    "analysis-design": {"skill": "cp-analysis-design", "title": "Analysis & Design"},
    "implementation": {"skill": "cp-implementation", "title": "Implementation"},
    "test": {"skill": "cp-test", "title": "Test"},
    "ccm": {"skill": "cp-ccm", "title": "Configuration & Change Management"},
    "deployment": {"skill": "cp-deployment", "title": "Deployment"},
}

# Cap per earlier artifact embedded in a work packet (the full text stays in .context/).
MAX_PRIOR_ARTIFACT_CHARS = 12000


def setup_console():
    """Force UTF-8 on stdout/stderr (the Windows console is cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
