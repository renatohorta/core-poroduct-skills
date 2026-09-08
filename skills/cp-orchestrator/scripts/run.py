#!/usr/bin/env python3
"""
cp-orchestrator — Software Factory Orchestrator (self-contained)

Coordinates the entire development pipeline. Two modes:

  SIMULATION (default):  Uses CrewAI to plan, simulate and document the pipeline.
  AUTO (--auto):        Runs the real crews in sequence, passing artifacts
                        between phases and applying quality gates automatically.

Pipeline modes:
  full              — All 8 crews (requirements → architecture → implementation
                      → testing → security → devops → documentation → quality)
  sprint            — requirements → architecture → implementation → testing → devops
  micro             — implementation → testing (bug fix)
  security-audit    — security → quality
  documentation     — documentation → quality
  bugfix            — cp-bug-fix (Developer → QA → Evidence Collector)
  competitive       — cp-competitive-analysis (competitive intelligence)
  full-dev          — full NEXUS pipeline (native, merge of cp-full-dev)
  goal-loop         — cp-goal-loop (trial-and-correction until success)
  maintenance       — cp-maintenance (bug-fix/refactor/improvement/full)
  agile             — cp-agile (execution pipeline + feedback loop)

Usage:
  # Simulation (planning)
  python run.py "scheduling system for clinics"

  # Automatic execution (runs the real crews)
  python run.py "scheduling system for clinics" --auto
  python run.py "PDF report feature" --mode sprint --auto
  python run.py "fix login error" --mode micro --auto
  python run.py "finance app" --mode security-audit --auto
  python run.py --input briefing.txt --auto
  python run.py "inventory system" --start-phase implementation --auto

  # Complementary skills via orchestrator
  python run.py "the /login endpoint returns 500" --mode bugfix --auto
  python run.py "clinics SaaS; competitors: Doctoralia" --mode competitive --auto
  python run.py "scheduling system" --mode full-dev --auto
  python run.py "deploy to staging working" --mode goal-loop --auto
  python run.py "refactor payments module" --mode maintenance --auto
"""

import argparse
import sys
import json
import os
import subprocess
import re
import time
from pathlib import Path
from datetime import datetime
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import build_crew_llm, require_llm, setup_console

setup_console()  # DT-01: UTF-8 no stdout/stderr (console Windows e cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION — skill paths
# ═══════════════════════════════════════════════════════════════════════════

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent  # skills/
ORCHESTRATOR_DIR = Path(__file__).resolve().parent.parent

SKILL_PATHS = {
    "requirements": SKILLS_DIR / "cp-requirements" / "scripts" / "run.py",
    "architecture": SKILLS_DIR / "cp-architecture" / "scripts" / "run.py",
    "implementation": SKILLS_DIR / "cp-implementation" / "scripts" / "run.py",
    "testing": SKILLS_DIR / "cp-testing" / "scripts" / "run.py",
    "security": SKILLS_DIR / "cp-security" / "scripts" / "run.py",
    "devops": SKILLS_DIR / "cp-devops" / "scripts" / "run.py",
    "documentation": SKILLS_DIR / "cp-software-spec" / "scripts" / "run.py",
    "quality": SKILLS_DIR / "cp-quality" / "scripts" / "run.py",
    # Complementary skills — triggerable by the orchestrator
    "bug-fix": SKILLS_DIR / "cp-bug-fix" / "scripts" / "run.py",
    "competitive-analysis": SKILLS_DIR / "cp-competitive-analysis" / "scripts" / "run.py",
    "goal-loop": SKILLS_DIR / "cp-goal-loop" / "scripts" / "run.py",
    "maintenance": SKILLS_DIR / "cp-maintenance" / "scripts" / "run.py",
    "agile": SKILLS_DIR / "cp-agile" / "scripts" / "run.py",
    "software-spec": SKILLS_DIR / "cp-software-spec" / "scripts" / "run.py",
}

# ═══════════════════════════════════════════════════════════════════════════
# CREW / PIPELINE PHASE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

CREWS = {
    "requirements": {
        "name": "Requirements Engineering",
        "skill": "cp-requirements",
        "description": "Elicits, specifies, validates and prioritizes software requirements.",
        "agents": ["Business Analyst", "Requirements Specifier",
                    "Requirements Validator", "Product Owner (Proxy)"],
        "inputs": ["Client briefing"],
        "outputs": ["Requirements Document", "Prioritized Backlog (MoSCoW)"],
        "quality_gate": "Validation of completeness, consistency and feasibility",
        "cli_args": [],
    },
    "architecture": {
        "name": "Software Architecture and Design",
        "skill": "cp-architecture",
        "description": "Designs the system architecture: ADRs, diagrams, schemas, APIs.",
        "agents": ["Software Architect", "Data Architect",
                    "API Architect", "UX Architect", "Technical Reviewer"],
        "inputs": ["Requirements Document"],
        "outputs": ["Architecture Document", "ADRs", "Data Modeling", "API Contracts"],
        "quality_gate": "Architecture review: technical feasibility, adherence to non-functional requirements",
        "cli_args": ["--input"],
    },
    "implementation": {
        "name": "Software Implementation",
        "skill": "cp-implementation",
        "description": "Implements backend, frontend and mobile code with code review.",
        "agents": ["Backend Developer", "Frontend Developer",
                    "Mobile Developer", "Code Reviewer", "Integrator"],
        "inputs": ["Architecture Document", "API Contracts"],
        "outputs": ["Source Code", "Code Review Report", "Integration Report"],
        "quality_gate": "Code review approved, integration validated, unit tests passing",
        "cli_args": ["--input", "--type"],
    },
    "testing": {
        "name": "Software Testing",
        "skill": "cp-testing",
        "description": "Runs unit, integration, E2E and performance tests.",
        "agents": ["Unit Testing Eng.", "Integration Testing Eng.",
                    "E2E Testing Eng.", "Performance Testing Eng.", "Results Analyst"],
        "inputs": ["Source Code", "Acceptance Criteria"],
        "outputs": ["Test Report", "Evidence", "Coverage"],
        "quality_gate": "Minimum coverage ≥ 80%, 0 critical bugs, performance within SLA",
        "cli_args": ["--input", "--source"],
    },
    "security": {
        "name": "Software Security",
        "skill": "cp-security",
        "description": "Security analysis, pentest, LGPD/GDPR compliance.",
        "agents": ["Security Analyst", "Penetration Tester",
                    "Compliance Specialist", "Fix Engineer"],
        "inputs": ["Source Code", "Architecture Document"],
        "outputs": ["Security Report", "Implemented Fixes"],
        "quality_gate": "0 critical/high vulnerabilities, compliance verified",
        "cli_args": ["--input"],
    },
    "devops": {
        "name": "DevOps and Infrastructure",
        "skill": "cp-devops",
        "description": "CI/CD, infrastructure as code, monitoring, deploy.",
        "agents": ["CI/CD Eng.", "Infrastructure Eng.",
                    "Monitoring Eng.", "Infra Security Eng."],
        "inputs": ["Source Code", "Architecture Document", "Non-Functional Requirements"],
        "outputs": ["CI/CD Pipeline", "Provisioned Infrastructure", "Active Monitoring"],
        "quality_gate": "Green CI/CD pipeline, automated deploy validated, monitoring operational",
        "cli_args": ["--input"],
    },
    "documentation": {
        "name": "Software Spec & Documentation",
        "skill": "cp-software-spec",
        "description": "Reverse-engineers the codebase into concise RUP docs (.context/docs/) — architecture, API contracts, data dictionary and devops infra.",
        "agents": ["Spec Analyst"],
        "inputs": ["Source Code", "Architecture Document", "API Contracts"],
        "outputs": [".context/docs/ (RUP 4 phases)", "API Contracts", "Data Dictionary"],
        "quality_gate": "Complete, concise RUP docs consistent with the implemented code",
        "cli_args": ["--inspect"],
        "invoke": {"briefing_arg": "inspect", "output": False},
    },
    "quality": {
        "name": "Software Quality",
        "skill": "cp-quality",
        "description": "Final audit: metrics, artifacts, continuous improvement.",
        "agents": ["Quality Auditor", "Metrics Analyst",
                    "Continuous Improvement Eng.", "Artifact Validator"],
        "inputs": ["All pipeline artifacts"],
        "outputs": ["Quality Report", "Quality Certificate"],
        "quality_gate": "All previous quality gates PASS, complete and consistent artifacts",
        "cli_args": ["--input"],
    },
    # ── Complementary skills (triggerable by the orchestrator) ──
    "bug-fix": {
        "name": "Bug Fix (NEXUS-Micro)",
        "skill": "cp-bug-fix",
        "description": "Fixes bugs with crew Developer → QA → Evidence Collector (max. 3 retries).",
        "agents": ["Developer", "QA (API Tester)", "Test Automation Engineer", "Evidence Collector"],
        "inputs": ["Bug description"],
        "outputs": ["Implemented fix", "Automated tests", "Evidence"],
        "quality_gate": "Bug fixed, tests passing, evidence collected",
        "cli_args": ["--type"],
        "invoke": {"briefing_arg": "positional", "output": False},
    },
    "competitive-analysis": {
        "name": "Competitive Analysis",
        "skill": "cp-competitive-analysis",
        "description": "Analyzes competitors, features, pricing, positioning and market strategy.",
        "agents": ["Market Analyst", "Competitor Analyst",
                    "Pricing/Positioning Analyst", "Strategist"],
        "inputs": ["Context: product, competitors, industry"],
        "outputs": ["Competitive Intelligence Report", "Battle Cards", "SWOT"],
        "quality_gate": "Complete report with competitor data and strategic recommendations",
        "cli_args": ["--input"],
        "invoke": {"briefing_arg": "positional", "output": True},
    },
    "goal-loop": {
        "name": "Autonomous Trial-and-Correction Loop",
        "skill": "cp-goal-loop",
        "description": "Runs a process until the success condition is reached, fixing blockers along the way.",
        "agents": ["Executor", "Diagnostician", "Fixer", "Validator"],
        "inputs": ["Goal (--goal)", "Steps (--steps)"],
        "outputs": ["Process completed successfully", "Attempt log"],
        "quality_gate": "Success condition reached within the attempt limit",
        "cli_args": ["--goal", "--steps", "--max-attempts", "--max-time"],
        "invoke": {"briefing_arg": "goal", "output": False},
    },
    "maintenance": {
        "name": "Software Maintenance and Evolution",
        "skill": "cp-maintenance",
        "description": "Diagnoses bugs, implements fixes, refactors code and assesses impact.",
        "agents": ["Bug Analyst", "Fix Developer",
                    "Refactoring Engineer", "Impact Analyst"],
        "inputs": ["Bug / improvement / refactoring description"],
        "outputs": ["Implemented fixes", "Refactored code", "Impact report"],
        "quality_gate": "Fix/refactoring validated without regressions",
        "cli_args": ["--mode"],
        "invoke": {"briefing_arg": "positional", "output": True},
    },
    "agile": {
        "name": "Agile (Execution Pipeline)",
        "skill": "cp-agile",
        "description": "Monitors the backlog, dispatches ready tasks to the orchestrator and manages the bidirectional feedback loop (questions, blockers, resume).",
        "agents": ["CPAgileDaemon", "CPAgileFeedbackLoop", "TrelloIntegration", "LocalIntegration"],
        "inputs": ["Backlog (local .context/kanban/ or Trello)"],
        "outputs": ["Dispatched tasks (TASK_DISPATCHED)", "Registered questions/blockers", "Resumes (HUMAN_CLARIFICATION_RECEIVED)"],
        "quality_gate": "Ready tasks dispatched, bidirectional feedback operational",
        "cli_args": ["--daemon", "--source", "--question", "--blocker", "--resume"],
        "invoke": {"briefing_arg": "daemon", "output": False},
    },
    "software-spec": {
        "name": "Software Spec Initializer",
        "skill": "cp-software-spec",
        "description": "Centralizes the project context in .context/ (single source of truth), creates CLAUDE.md/AGENT.md pointers and generates the RUP documentation structure (4 phases).",
        "agents": ["SoftwareSpec"],
        "inputs": ["Project directory"],
        "outputs": [".context/ (docs RUP, inbox, tracking)", "CLAUDE.md", "AGENT.md"],
        "quality_gate": ".context/ structure created, root pointers, vision.md ingested",
        "cli_args": ["--init", "--dir", "--dry-run"],
        "invoke": {"briefing_arg": "dir", "output": False},
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE MODES
# ═══════════════════════════════════════════════════════════════════════════

MODOS = {
    "full": {
        "name": "Full",
        "description": "Runs all 8 crews in sequence — from requirement to delivery",
        "crews": ["requirements", "architecture", "implementation", "testing",
                   "security", "devops", "documentation", "quality"],
    },
    "sprint": {
        "name": "Sprint",
        "description": "Runs 5 crews — requirements → architecture → implementation → testing → devops",
        "crews": ["requirements", "architecture", "implementation", "testing", "devops"],
    },
    "micro": {
        "name": "Micro (Bug Fix)",
        "description": "Runs 2 crews — implementation → testing (for quick fixes)",
        "crews": ["implementation", "testing"],
    },
    "security-audit": {
        "name": "Security Audit",
        "description": "Runs 2 crews — security → quality",
        "crews": ["security", "quality"],
    },
    "documentation": {
        "name": "Documentation",
        "description": "Runs 2 crews — documentation → quality",
        "crews": ["documentation", "quality"],
    },
    "bugfix": {
        "name": "Bug Fix",
        "description": "Runs the cp-bug-fix crew (Developer → QA → Evidence Collector)",
        "crews": ["bug-fix"],
    },
    "competitive": {
        "name": "Competitive Analysis",
        "description": "Runs the cp-competitive-analysis crew (competitive intelligence)",
        "crews": ["competitive-analysis"],
    },
    "full-dev": {
        "name": "Full NEXUS Pipeline",
        "description": "Runs the native NEXUS pipeline (Discovery → ... → Operate), merge of cp-full-dev",
        "crews": ["full-dev"],
    },
    "goal-loop": {
        "name": "Autonomous Loop",
        "description": "Runs the cp-goal-loop skill (trial-and-correction until success)",
        "crews": ["goal-loop"],
    },
    "maintenance": {
        "name": "Maintenance and Evolution",
        "description": "Runs the cp-maintenance crew (bug-fix/refactor/improvement/full)",
        "crews": ["maintenance"],
    },
    "agile": {
        "name": "Agile (Execution Pipeline)",
        "description": "Runs the cp-agile skill (polling daemon + feedback loop)",
        "crews": ["agile"],
    },
    "software-spec": {
        "name": "Software Spec Initializer",
        "description": "Runs the cp-software-spec skill (.context/ RUP structure + pointers)",
        "crews": ["software-spec"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# NEXUS PIPELINE (merge of cp-full-dev) — embedded agents
# ═══════════════════════════════════════════════════════════════════════════

NEXUS_AGENTS = {
    # ── Engineering ──
    "engineering-backend-architect": {
        "role": "Backend Architect",
        "goal": "Design and implement scalable, secure, and performant backend systems",
        "backstory": "Senior backend architect specializing in scalable system design, database architecture, API development, and cloud infrastructure. Strategic, security-focused, scalability-minded.",
    },
    "engineering-frontend-developer": {
        "role": "Frontend Developer",
        "goal": "Build responsive, accessible, and performant web applications",
        "backstory": "Expert frontend developer specializing in modern web technologies, React/Vue/Angular, UI implementation, and performance optimization. Detail-oriented and user-centric.",
    },
    "engineering-ai-engineer": {
        "role": "AI Engineer",
        "goal": "Design and implement AI/ML solutions that integrate with the application",
        "backstory": "AI/ML engineer specializing in LLM integration, RAG pipelines, and intelligent automation. Experienced in production AI systems.",
    },
    "engineering-devops-automator": {
        "role": "DevOps Automator",
        "goal": "Automate infrastructure, CI/CD, and deployment pipelines",
        "backstory": "DevOps specialist who automates everything. Expert in CI/CD, containerization, cloud infrastructure, and infrastructure as code.",
    },
    "engineering-mobile-app-builder": {
        "role": "Mobile App Builder",
        "goal": "Build cross-platform mobile applications",
        "backstory": "Mobile developer specializing in React Native and Flutter. Builds performant, native-feeling mobile apps.",
    },
    "engineering-senior-developer": {
        "role": "Senior Developer",
        "goal": "Implement premium, production-ready features with high quality",
        "backstory": "Senior full-stack developer who creates premium web experiences. Creative, detail-oriented, performance-focused, and innovation-driven.",
    },
    "engineering-rapid-prototyper": {
        "role": "Rapid Prototyper",
        "goal": "Quickly build functional prototypes to validate ideas",
        "backstory": "Rapid prototyping specialist who builds functional MVPs fast. Focuses on speed-to-validation over polish.",
    },

    # ── Testing ──
    "testing-api-tester": {
        "role": "API Tester",
        "goal": "Validate APIs through comprehensive functional, security, and performance testing",
        "backstory": "Expert API testing specialist focused on comprehensive API validation. Thorough, security-conscious, automation-driven. Breaks APIs before users do.",
    },
    "testing-test-automation-engineer": {
        "role": "Test Automation Engineer",
        "goal": "Create deterministic, reliable automated test suites",
        "backstory": "Expert end-to-end test automation engineer. Allergic to sleep(), obsessive about root causes. Every test owns its data and waits on conditions, not clocks.",
    },
    "testing-evidence-collector": {
        "role": "Evidence Collector",
        "goal": "Verify quality with visual evidence — screenshots, logs, test output",
        "backstory": "Skeptical QA specialist who requires visual proof. Screenshots don't lie. Default to finding issues — first implementations always have 3-5+ issues.",
    },
    "testing-performance-benchmarker": {
        "role": "Performance Benchmarker",
        "goal": "Measure and validate system performance under load",
        "backstory": "Performance testing specialist who benchmarks systems under realistic load. Identifies bottlenecks and validates SLAs.",
    },
    "testing-reality-checker": {
        "role": "Reality Checker",
        "goal": "Validate that plans and implementations are realistic and achievable",
        "backstory": "Pragmatic validator who checks if plans are realistic. Questions assumptions, identifies risks, and ensures feasibility before commitment.",
    },
    "testing-test-results-analyzer": {
        "role": "Test Results Analyzer",
        "goal": "Analyze test results and provide actionable insights",
        "backstory": "Analytical QA who digs into test results to find patterns, regressions, and improvement opportunities.",
    },
    "testing-tool-evaluator": {
        "role": "Tool Evaluator",
        "goal": "Evaluate and recommend tools, frameworks, and technologies",
        "backstory": "Technology assessment specialist who evaluates tools against project requirements. Objective, data-driven recommendations.",
    },
    "testing-workflow-optimizer": {
        "role": "Workflow Optimizer",
        "goal": "Optimize development workflows for efficiency and quality",
        "backstory": "Process improvement specialist who identifies bottlenecks and optimizes workflows. Focuses on reducing cycle time and improving quality.",
    },

    # ── Design ──
    "design-ux-architect": {
        "role": "UX Architect",
        "goal": "Design intuitive, accessible user experiences",
        "backstory": "UX architect who designs user-centered interfaces. Expert in information architecture, user flows, and accessibility (WCAG).",
    },
    "design-ux-researcher": {
        "role": "UX Researcher",
        "goal": "Conduct user research to inform design decisions",
        "backstory": "UX researcher who gathers user insights through interviews, surveys, and usability testing. Data-driven design advocate.",
    },
    "design-ui-designer": {
        "role": "UI Designer",
        "goal": "Create beautiful, consistent, and accessible user interfaces",
        "backstory": "UI designer who creates pixel-perfect interfaces. Expert in design systems, typography, color theory, and visual hierarchy.",
    },
    "design-brand-guardian": {
        "role": "Brand Guardian",
        "goal": "Ensure brand consistency across all touchpoints",
        "backstory": "Brand guardian who protects and enforces brand identity. Ensures visual and tonal consistency across all outputs.",
    },

    # ── Product ──
    "product-trend-researcher": {
        "role": "Trend Researcher",
        "goal": "Research market trends and competitive landscape",
        "backstory": "Market researcher who identifies trends, competitive moves, and opportunities. Data-driven and forward-looking.",
    },
    "product-feedback-synthesizer": {
        "role": "Feedback Synthesizer",
        "goal": "Synthesize user feedback into actionable product insights",
        "backstory": "Product insights specialist who distills user feedback into prioritized, actionable recommendations.",
    },
    "product-sprint-prioritizer": {
        "role": "Sprint Prioritizer",
        "goal": "Prioritize backlog items based on value, effort, and dependencies",
        "backstory": "Agile prioritization specialist who balances business value, technical effort, and dependencies to optimize sprint planning.",
    },
    "product-manager": {
        "role": "Product Manager",
        "goal": "Define product vision, strategy, and roadmap",
        "backstory": "Product manager who defines what to build and why. Balances user needs, business goals, and technical feasibility.",
    },

    # ── Project Management ──
    "project-management-studio-producer": {
        "role": "Studio Producer",
        "goal": "Coordinate project execution across teams and phases",
        "backstory": "Project coordinator who keeps teams aligned, tracks progress, and removes blockers. Ensures smooth execution.",
    },
    "project-manager-senior": {
        "role": "Senior Project Manager",
        "goal": "Manage complex projects from planning to delivery",
        "backstory": "Senior project manager with expertise in agile and waterfall methodologies. Risk management and stakeholder communication specialist.",
    },

    # ── Marketing ──
    "marketing-growth-hacker": {
        "role": "Growth Hacker",
        "goal": "Drive user acquisition and growth through creative strategies",
        "backstory": "Growth marketing specialist who experiments with channels and tactics to drive measurable user growth.",
    },
    "marketing-content-creator": {
        "role": "Content Creator",
        "goal": "Create compelling marketing content across channels",
        "backstory": "Content marketing specialist who creates engaging copy, blog posts, and marketing materials that convert.",
    },
    "marketing-social-media-strategist": {
        "role": "Social Media Strategist",
        "goal": "Develop and execute social media strategies",
        "backstory": "Social media strategist who builds brand presence across platforms. Data-driven content planning and community management.",
    },
    "marketing-twitter-engager": {
        "role": "Twitter Engager",
        "goal": "Build Twitter/X presence and engagement",
        "backstory": "Twitter/X specialist who grows following, drives engagement, and builds thought leadership on the platform.",
    },
    "marketing-tiktok-strategist": {
        "role": "TikTok Strategist",
        "goal": "Create TikTok content strategy for brand awareness",
        "backstory": "TikTok content strategist who creates viral-worthy content and builds brand presence on the platform.",
    },
    "marketing-instagram-curator": {
        "role": "Instagram Curator",
        "goal": "Curate Instagram content for brand storytelling",
        "backstory": "Instagram content curator who builds visual brand storytelling through feeds, stories, and reels.",
    },
    "marketing-reddit-community-builder": {
        "role": "Reddit Community Builder",
        "goal": "Build and engage Reddit communities around the brand",
        "backstory": "Reddit community manager who builds authentic engagement in relevant subreddits without being spammy.",
    },

    # ── Support ──
    "support-analytics-reporter": {
        "role": "Analytics Reporter",
        "goal": "Track, analyze, and report key metrics and KPIs",
        "backstory": "Data analyst who builds dashboards and reports. Turns raw data into actionable insights for decision-making.",
    },
    "support-executive-summary-generator": {
        "role": "Executive Summary Generator",
        "goal": "Create concise executive summaries of project status and outcomes",
        "backstory": "Executive communicator who distills complex project information into clear, actionable summaries for leadership.",
    },
    "support-finance-tracker": {
        "role": "Finance Tracker",
        "goal": "Track project costs, budget, and financial metrics",
        "backstory": "Financial analyst who monitors project budgets, tracks costs, and forecasts financial outcomes.",
    },
    "support-infrastructure-maintainer": {
        "role": "Infrastructure Maintainer",
        "goal": "Maintain and monitor production infrastructure",
        "backstory": "Infrastructure engineer who keeps systems running. Monitoring, alerting, incident response, and capacity planning.",
    },
    "support-legal-compliance-checker": {
        "role": "Legal Compliance Checker",
        "goal": "Ensure legal and regulatory compliance across the project",
        "backstory": "Compliance specialist who reviews projects for legal and regulatory requirements. GDPR, LGPD, SOC2, and industry-specific regulations.",
    },
    "support-support-responder": {
        "role": "Support Responder",
        "goal": "Provide user support and triage issues",
        "backstory": "Customer support specialist who handles user inquiries, triages issues, and ensures timely resolution.",
    },

    # ── Specialized ──
    "specialized-agents-orchestrator": {
        "role": "Agents Orchestrator",
        "goal": "Coordinate multiple specialized agents for complex tasks",
        "backstory": "Orchestration specialist who coordinates multiple AI agents to work together efficiently on complex, multi-step tasks.",
    },
}


def nexus_get_agent(slug: str):
    """Get a CrewAI Agent from the embedded NEXUS definitions."""
    from crewai import Agent
    _crew_llm = build_crew_llm()
    data = NEXUS_AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agent not found: {slug} — using defaults")
        return Agent(
            role=name,
            goal=f"Complete the assigned task with excellence as {name}",
            backstory=f"Specialized AI agent working as {name}.",
            llm=_crew_llm,
            verbose=True,
            allow_delegation=False,
        )
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        llm=_crew_llm,
        verbose=True,
        allow_delegation=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# NEXUS PIPELINE — phases
# ═══════════════════════════════════════════════════════════════════════════

NEXUS_PHASES = {
    "full": {
        "phase-0-discovery": {
            "name": "Discovery",
            "agents": [
                "product-trend-researcher",
                "product-feedback-synthesizer",
                "design-ux-researcher",
                "support-analytics-reporter",
                "support-legal-compliance-checker",
                "testing-tool-evaluator",
            ],
            "gate_keeper": "support-executive-summary-generator",
            "description": "Validate the opportunity before committing resources",
        },
        "phase-1-strategy": {
            "name": "Strategy",
            "agents": [
                "project-management-studio-producer",
                "design-brand-guardian",
                "support-finance-tracker",
                "design-ux-architect",
                "engineering-backend-architect",
                "engineering-ai-engineer",
                "project-manager-senior",
                "product-sprint-prioritizer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Define what to build, how, and what success looks like",
        },
        "phase-2-foundation": {
            "name": "Foundation",
            "agents": [
                "engineering-devops-automator",
                "support-infrastructure-maintainer",
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "design-ux-architect",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Build the technical and operational foundation",
        },
        "phase-3-build": {
            "name": "Build",
            "agents": [
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "engineering-ai-engineer",
                "engineering-mobile-app-builder",
                "engineering-senior-developer",
                "engineering-rapid-prototyper",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-automation-engineer",
                "testing-performance-benchmarker",
                "design-ui-designer",
                "design-brand-guardian",
            ],
            "gate_keeper": "specialized-agents-orchestrator",
            "description": "Implement features through Dev-QA loops",
        },
        "phase-4-hardening": {
            "name": "Hardening",
            "agents": [
                "testing-reality-checker",
                "testing-evidence-collector",
                "testing-performance-benchmarker",
                "testing-api-tester",
                "testing-test-results-analyzer",
                "support-legal-compliance-checker",
                "support-infrastructure-maintainer",
                "testing-workflow-optimizer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Final quality gauntlet before production",
        },
        "phase-5-launch": {
            "name": "Launch",
            "agents": [
                "marketing-growth-hacker",
                "marketing-content-creator",
                "marketing-social-media-strategist",
                "marketing-twitter-engager",
                "marketing-tiktok-strategist",
                "marketing-instagram-curator",
                "marketing-reddit-community-builder",
                "engineering-devops-automator",
                "support-infrastructure-maintainer",
                "support-support-responder",
                "support-analytics-reporter",
                "support-executive-summary-generator",
            ],
            "gate_keeper": "project-management-studio-producer",
            "description": "Coordinate go-to-market execution",
        },
        "phase-6-operate": {
            "name": "Operate",
            "agents": [
                "support-analytics-reporter",
                "support-infrastructure-maintainer",
                "support-support-responder",
                "engineering-devops-automator",
                "product-feedback-synthesizer",
                "product-sprint-prioritizer",
                "support-finance-tracker",
                "support-legal-compliance-checker",
                "support-executive-summary-generator",
            ],
            "gate_keeper": "project-management-studio-producer",
            "description": "Sustained operations with continuous improvement",
        },
    },
    "sprint": {
        "phase-1-strategy": {
            "name": "Strategy",
            "agents": [
                "project-manager-senior",
                "product-sprint-prioritizer",
                "design-ux-architect",
                "engineering-backend-architect",
                "design-brand-guardian",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Define architecture and sprint plan",
        },
        "phase-2-foundation": {
            "name": "Foundation",
            "agents": [
                "engineering-devops-automator",
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "design-ux-architect",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Scaffold the feature foundation",
        },
        "phase-3-build": {
            "name": "Build",
            "agents": [
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-automation-engineer",
            ],
            "gate_keeper": "specialized-agents-orchestrator",
            "description": "Implement the feature with Dev-QA loops",
        },
        "phase-4-hardening": {
            "name": "Hardening",
            "agents": [
                "testing-reality-checker",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-results-analyzer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Quality validation before merge",
        },
    },
    "micro": {
        "phase-3-build": {
            "name": "Build & Fix",
            "agents": [
                "engineering-backend-architect",
                "engineering-frontend-developer",
                "testing-api-tester",
                "testing-test-automation-engineer",
                "testing-evidence-collector",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Implement and validate the change",
        },
    },
}


def nexus_detect_mode(requirement: str) -> str:
    """Detect the NEXUS mode based on requirement scope."""
    req_lower = requirement.lower()

    full_keywords = [
        "build", "create from scratch", "complete product", "complete system",
        "application", "platform", "from scratch", "build from scratch",
        "system for", "app for", "application",
    ]
    sprint_keywords = [
        "feature", "functionality", "implement", "add", "create a",
        "new screen", "new module", "export", "import",
        "report", "dashboard", "integration",
    ]
    micro_keywords = [
        "fix", "bug", "error", "fix", "adjust", "adjust", "change",
        "alter", "replace", "small",
    ]

    full_score = sum(1 for kw in full_keywords if kw in req_lower)
    sprint_score = sum(1 for kw in sprint_keywords if kw in req_lower)
    micro_score = sum(1 for kw in micro_keywords if kw in req_lower)

    if full_score >= sprint_score and full_score >= micro_score:
        return "full"
    elif sprint_score >= micro_score:
        return "sprint"
    else:
        return "micro"


def nexus_build_phase_crew(phase_key: str, phase_def: dict, requirement: str, project_name: str):
    """Build a CrewAI crew for a single NEXUS phase."""
    from crewai import Task, Crew, Process

    agents = []
    tasks = []

    for slug in phase_def["agents"]:
        agents.append(nexus_get_agent(slug))

    gate_keeper = nexus_get_agent(phase_def["gate_keeper"])

    phase_task = Task(
        description=f"""
        PROJECT: {project_name}
        REQUIREMENT: {requirement}
        PHASE: {phase_def['name']} — {phase_def['description']}

        YOUR JOB:
        Execute this phase of the NEXUS pipeline. Each agent contributes their
        specialized expertise to produce the deliverables for this phase.

        Coordinate with each other. Produce concrete, actionable outputs.
        Document all decisions and rationale.

        When all agents have completed their work, produce a consolidated
        phase deliverable package.
        """,
        expected_output=f"Phase {phase_def['name']} deliverable package with all agent outputs consolidated",
        agent=agents[0],
    )

    gate_task = Task(
        description=f"""
        PROJECT: {project_name}
        PHASE: {phase_def['name']}

        YOUR JOB — QUALITY GATE:
        Review the phase deliverables from all agents.
        Verify that the phase objectives were met.

        Issue verdict: PASS or FAIL.

        If PASS: the project can advance to the next phase.
        If FAIL: provide specific issues that must be addressed before retry.

        Evidence required — no assertions without proof.
        """,
        expected_output=f"Quality gate verdict for Phase {phase_def['name']}: PASS/FAIL with evidence",
        agent=gate_keeper,
    )

    crew = Crew(
        agents=agents + [gate_keeper],
        tasks=[phase_task, gate_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


class NexusExecutor:
    """Runs the NEXUS pipeline natively (merge of cp-full-dev)."""

    def __init__(self, requirement: str, mode: str = "auto", start_phase: str = None,
                 project_name: str = None, output_dir: str = None,
                 kanban_task: str = None, python_cmd: str = None):
        self.requirement = requirement
        self.mode = mode if mode != "auto" else nexus_detect_mode(requirement)
        self.start_phase = start_phase
        self.project_name = project_name or requirement[:60].strip()
        self.output_dir = output_dir
        self.kanban_task = kanban_task
        self.python_cmd = python_cmd or sys.executable

    def run(self) -> dict:
        phases = NEXUS_PHASES.get(self.mode, NEXUS_PHASES["micro"])
        phase_keys = list(phases.keys())

        # Kanban: mark as doing at the start
        if self.kanban_task:
            self._kanban_update_status("doing")

        if self.start_phase:
            if self.start_phase in phase_keys:
                idx = phase_keys.index(self.start_phase)
                phase_keys = phase_keys[idx:]
            else:
                print(f"[!] Phase not found: {self.start_phase}")
                print(f"    Available phases: {', '.join(phase_keys)}")
                return {"status": "failed", "error": f"Phase '{self.start_phase}' not found"}

        print(f"\n{'='*60}")
        print(f"  NEXUS Pipeline — Mode: {self.mode.upper()} (native in orchestrator)")
        print(f"  Project: {self.project_name}")
        print(f"  Phases: {len(phase_keys)}")
        print(f"{'='*60}\n")

        total_agents = 0
        for i, pk in enumerate(phase_keys):
            phase = phases[pk]
            total_agents += len(phase["agents"])
            print(f"  Phase {i}: {phase['name']} ({len(phase['agents'])} agents)")
            print(f"    Gate: {phase['gate_keeper']}")
            print(f"    {phase['description']}")
            print()

        print(f"  Total: {total_agents} agents in {len(phase_keys)} phases\n")

        results = {}
        failed_phase = None
        for i, pk in enumerate(phase_keys):
            phase = phases[pk]
            print(f"\n{'='*60}")
            print(f"  PHASE {i+1}/{len(phase_keys)}: {phase['name']}")
            print(f"  {phase['description']}")
            print(f"{'='*60}\n")

            try:
                require_llm()  # DT-08: fail early, with a message, if there is no LLM
                crew = nexus_build_phase_crew(pk, phase, self.requirement, self.project_name)
                print(f"  [>] Running {len(phase['agents'])} agents...")
                result = crew.kickoff()
                results[pk] = {
                    "status": "completed",
                    "phase": phase["name"],
                    "result": str(result)[:500],
                }
                print(f"  [OK] Phase {phase['name']} completed")
            except Exception as e:
                print(f"  [!!] Phase {phase['name']} failed: {e}")
                results[pk] = {
                    "status": "failed",
                    "phase": phase["name"],
                    "error": str(e),
                }
                failed_phase = pk
                print("\n  The phase failed. Fix the error and re-run with --start-phase")
                break

        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETED")
        print(f"{'='*60}\n")
        for pk, r in results.items():
            status_icon = "[OK]" if r["status"] == "completed" else "[!!]"
            print(f"  {status_icon} {r['phase']}: {r['status']}")

        completed = sum(1 for r in results.values() if r["status"] == "completed")
        print(f"\n  {completed}/{len(phase_keys)} phases completed")

        # Save results
        if self.output_dir:
            out_dir = Path(self.output_dir)
        else:
            out_dir = ORCHESTRATOR_DIR / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = out_dir / f"nexus_{self.mode}_{timestamp}.json"
        output_file.write_text(json.dumps({
            "project": self.project_name,
            "requirement": self.requirement,
            "mode": self.mode,
            "timestamp": timestamp,
            "phases": results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Results saved to: {output_file}")

        # Kanban: mark as done or blocked at the end
        if self.kanban_task:
            if failed_phase:
                self._kanban_update_status("blocked")
            else:
                self._kanban_update_status("done")

        return {
            "status": "failed" if failed_phase else "completed",
            "mode": self.mode,
            "failed_phase": failed_phase,
            "completed": completed,
            "total": len(phase_keys),
            "output_file": str(output_file),
        }

    def _kanban_update_status(self, status: str):
        """Updates the kanban task status via cp-agile (best-effort)."""
        if not self.kanban_task:
            return
        agile_run = SKILL_PATHS.get("agile")
        if not agile_run or not agile_run.exists():
            return
        try:
            subprocess.run(
                [self.python_cmd, str(agile_run),
                 "--task", self.kanban_task,
                 "--update-status", status],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# AUTO MODE — PIPELINE EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════

class PipelineExecutor:
    """Runs the real pipeline by calling the skills via subprocess."""

    def __init__(self, briefing: str, mode: str, start_phase: str = None,
                 output_dir: str = None, python_cmd: str = None,
                 kanban_task: str = None):
        self.briefing = briefing
        self.mode = mode
        self.start_phase = start_phase
        self.python_cmd = python_cmd or sys.executable
        self.kanban_task = kanban_task  # task ID in the kanban (cp-agile)

        # Resolve artifacts directory
        if output_dir:
            self.artifacts_dir = Path(output_dir)
        else:
            self.artifacts_dir = ORCHESTRATOR_DIR / "outputs" / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Pipeline state
        self.artifacts = {}  # phase -> artifact path
        self.gate_results = {}  # phase -> {"status": "PASS"/"FAIL"/"WARN", "detail": "..."}
        self.phase_outputs = {}  # phase -> full output text
        self.timing = {}  # phase -> seconds
        self.failed_phase = None

    def _get_skill_path(self, crew_key: str) -> Path:
        """Returns the path to the skill's run.py script."""
        return SKILL_PATHS.get(crew_key)

    def _get_artifact_path(self, crew_key: str) -> Path:
        """Returns the path where the phase artifact will be saved."""
        return self.artifacts_dir / f"{crew_key}.md"

    def _get_previous_artifact(self, crew_key: str) -> str:
        """Returns the content of the previous phase artifact, if it exists."""
        # Maps which previous phase feeds this one
        prev_map = {
            "architecture": "requirements",
            "implementation": "architecture",
            "testing": "implementation",
            "security": "implementation",
            "devops": "implementation",
            "documentation": "implementation",
            "quality": None,  # receives from all
        }
        prev_key = prev_map.get(crew_key)
        if prev_key and prev_key in self.artifacts:
            path = self.artifacts[prev_key]
            if path and path.exists():
                return path.read_text(encoding="utf-8")[:2000]  # limited context
        return ""

    def _build_cli_args(self, crew_key: str) -> list:
        """Builds the CLI arguments to call the skill.

        Respects each crew's `invoke` metadata:
          briefing_arg: "positional" (passes briefing as positional arg),
                        "goal" (passes via --goal, e.g.: cp-goal-loop),
                        "input" (passes via --input, e.g.: pipeline phases)
          output:       True if the skill accepts --output, False otherwise
        """
        crew = CREWS[crew_key]
        skill_path = self._get_skill_path(crew_key)

        if not skill_path or not skill_path.exists():
            print(f"  ⚠️  Skill not found: {crew['skill']} at {skill_path}")
            print(f"     Skipping phase {crew['name']}...")
            return None

        invoke = crew.get("invoke", {"briefing_arg": "input", "output": True})
        briefing_arg = invoke.get("briefing_arg", "input")
        supports_output = invoke.get("output", True)

        args = [str(self.python_cmd), str(skill_path)]

        # `inspect` (cp-software-spec reverse engineering): always targets the
        # current project directory, never receives a briefing or previous
        # artifact via --input.
        if briefing_arg == "inspect":
            args.extend(["--inspect", str(Path.cwd())])
            return args

        # Briefing or previous artifact as input
        prev_artifact = self._get_previous_artifact(crew_key)
        if prev_artifact:
            # Save temporary context and pass as --input
            ctx_file = self.artifacts_dir / f"_ctx_{crew_key}.txt"
            ctx_file.write_text(
                f"# Context for {crew['name']}\n\n"
                f"Original briefing: {self.briefing}\n\n"
                f"Previous phase artifact:\n{prev_artifact[:3000]}",
                encoding="utf-8"
            )
            args.extend(["--input", str(ctx_file)])
        else:
            # First phase: pass the briefing according to the invocation mode
            if briefing_arg == "goal":
                args.extend(["--goal", self.briefing])
            elif briefing_arg == "daemon":
                # Agile: starts the polling daemon (always reads from local)
                args.extend(["--daemon"])
            elif briefing_arg == "dir":
                # Software-spec initializer: uses the current directory (no positional briefing)
                args.extend(["--init", "--dir", str(Path.cwd())])
            elif briefing_arg == "positional":
                args.append(self.briefing)
            else:  # "input"
                args.append(self.briefing)

        # --output (only if the skill supports it)
        if supports_output:
            out_path = self._get_artifact_path(crew_key)
            args.extend(["--output", str(out_path)])

        return args

    @staticmethod
    def _count_keywords(keywords: list, text_upper: str) -> int:
        """Counts keywords matching by WHOLE WORD.

        BUG-04: with `kw in text`, the success keyword "OK" matched inside
        "TOKEN" and "BROKEN" — and "invalid API token" (the most common error
        when a credential is missing) was classified as PASS.
        """
        return sum(1 for kw in keywords
                   if re.search(r"\b" + re.escape(kw) + r"\b", text_upper))

    def _check_quality_gate(self, crew_key: str, output_text: str,
                            returncode: int = 0) -> dict:
        """Analyzes the skill output and determines whether the quality gate passed."""
        # BUG-03: exit code != 0 is unconditional FAIL. Before, a skill that
        # died with a traceback contained no fail_keyword, fell into the default
        # branch (WARN) and the pipeline kept reporting success.
        if returncode != 0:
            return {"status": "FAIL",
                    "detail": f"Skill finished with exit code {returncode}"}

        output_upper = output_text.upper()

        # Failure keywords
        fail_keywords = ["FAIL", "FAILED", "REJECTED", "DENIED", "BLOCKED",
                         "CRITICAL", "CRITICAL VULNERABILITY",
                         "TRACEBACK", "MODULENOTFOUNDERROR"]
        # Warning keywords
        warn_keywords = ["WARN", "CAVEAT", "ATTENTION", "PENDING", "ALERT"]
        # Success keywords
        pass_keywords = ["PASS", "APPROVED", "SUCCESS", "COMPLETED", "OK",
                         "ZERO VULNERABILITIES", "COVERAGE"]

        fail_score = self._count_keywords(fail_keywords, output_upper)
        warn_score = self._count_keywords(warn_keywords, output_upper)
        pass_score = self._count_keywords(pass_keywords, output_upper)

        if fail_score > pass_score:
            return {"status": "FAIL", "detail": "Failure keywords detected in the output"}
        elif warn_score > 0 and pass_score == 0:
            return {"status": "WARN", "detail": "Caveats detected, no success confirmation"}
        elif pass_score > 0:
            return {"status": "PASS", "detail": "Success indicators detected"}
        else:
            return {"status": "WARN", "detail": "Could not determine the result — review manually"}

    # Maps crew -> RUP doc file in .context/docs/ (4-phase structure)
    CONTEXT_DOC_MAP = {
        "requirements": "01-inception/requirements.md",
        "architecture": "02-elaboration/architecture.md",
        "implementation": "02-elaboration/architecture.md",
        "testing": "04-transition/test-strategy.md",
        "security": "01-inception/requirements.md",
        "devops": "04-transition/devops-infra.md",
        "documentation": "03-construction/api-contracts.md",
        "quality": "04-transition/test-strategy.md",
        "bug-fix": "04-transition/test-strategy.md",
        "competitive-analysis": "01-inception/requirements.md",
        "goal-loop": "04-transition/devops-infra.md",
        "maintenance": "02-elaboration/architecture.md",
        "agile": "06-kanban.md",
    }

    def _document_to_context(self, crew_key: str, output_text: str):
        """Documents the phase artifact in .context/docs/<discipline>.md.

        Every cp-* skill documents its artifacts in the .context/ structure
        (the project's source of truth). The discipline file is created/updated
        with the phase output.
        """
        doc_file = self.CONTEXT_DOC_MAP.get(crew_key)
        if not doc_file:
            return None
        # .context/ lives at the project root (orchestrator cwd)
        context_dir = Path.cwd() / ".context" / "docs"
        context_dir.mkdir(parents=True, exist_ok=True)
        dest = context_dir / doc_file
        dest.parent.mkdir(parents=True, exist_ok=True)  # RUP subdirs (e.g. 01-inception/)

        crew = CREWS[crew_key]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = (
            f"\n\n## Artifact — {crew['name']} ({now})\n\n"
            f"```\n{output_text[:4000]}\n```\n"
        )
        # If the file already exists, append; otherwise create with header
        if dest.exists():
            dest.write_text(dest.read_text(encoding="utf-8") + block, encoding="utf-8")
        else:
            dest.write_text(
                f"# {crew['name']}\n\n> Document managed by the `{crew['skill']}` skill.\n"
                + block,
                encoding="utf-8",
            )
        return dest

    def _kanban_update_status(self, status: str):
        """Updates the kanban task status via cp-agile.

        Only runs if `self.kanban_task` was provided.
        """
        if not self.kanban_task:
            return
        agile_run = SKILL_PATHS.get("agile")
        if not agile_run or not agile_run.exists():
            return
        try:
            subprocess.run(
                [self.python_cmd, str(agile_run),
                 "--task", self.kanban_task,
                 "--update-status", status],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass  # best-effort: does not break the pipeline if kanban fails

    def run(self) -> dict:
        """Runs the complete pipeline."""
        mode_info = MODOS[self.mode]
        crew_keys = mode_info["crews"]

        # Filter by start_phase
        if self.start_phase:
            if self.start_phase in crew_keys:
                idx = crew_keys.index(self.start_phase)
                crew_keys = crew_keys[idx:]
            else:
                print(f"❌ Phase '{self.start_phase}' not found in mode '{self.mode}'")
                print(f"   Available phases: {', '.join(crew_keys)}")
                return {"status": "failed", "error": f"Phase '{self.start_phase}' not found"}

        print(f"\n{'='*60}")
        print(f"  🚀 AUTO PIPELINE — {mode_info['name']}")
        print(f"  {mode_info['description']}")
        print(f"  📁 Artifacts: {self.artifacts_dir}")
        if self.kanban_task:
            print(f"  📋 Kanban task: {self.kanban_task}")
        print(f"{'='*60}\n")

        # If there is a kanban_task, mark as doing at the start
        if self.kanban_task:
            self._kanban_update_status("doing")

        for i, ck in enumerate(crew_keys, 1):
            crew = CREWS[ck]
            print(f"\n{'─'*50}")
            print(f"  📌 PHASE {i}/{len(crew_keys)}: {crew['name']}")
            print(f"  🛠️  Skill: {crew['skill']}")
            print(f"  🎯 Quality Gate: {crew['quality_gate']}")
            print(f"{'─'*50}\n")

            # Build arguments
            args = self._build_cli_args(ck)
            if args is None:
                self.gate_results[ck] = {"status": "SKIP", "detail": "Skill not found"}
                continue

            print(f"  🔧 Running: {' '.join(str(a) for a in args)}")
            print()

            # Execute
            start_time = time.time()
            try:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 min per phase
                    cwd=str(SKILLS_DIR),
                )
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed

                output = result.stdout + "\n" + result.stderr
                self.phase_outputs[ck] = output

                # Save artifact
                out_path = self._get_artifact_path(ck)
                out_path.write_text(output, encoding="utf-8")
                self.artifacts[ck] = out_path

                # Document the artifact in .context/docs/ (source of truth)
                self._document_to_context(ck, output)

                # Quality gate
                gate = self._check_quality_gate(ck, output, result.returncode)
                self.gate_results[ck] = gate

                print(f"  ⏱️  {elapsed:.1f}s | Quality Gate: {gate['status']}")
                if gate["status"] == "FAIL":
                    print(f"  ❌ PHASE {crew['name']} FAILED!")
                    print(f"     Reason: {gate['detail']}")
                    self.failed_phase = ck
                    break
                elif gate["status"] == "WARN":
                    print(f"  ⚠️  Phase approved with caveats: {gate['detail']}")
                else:
                    print(f"  ✅ Phase completed successfully!")

                # Show output preview
                preview = output[:500].strip()
                if preview:
                    print(f"\n  📄 Preview:\n{preview}\n")

            except subprocess.TimeoutExpired:
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed
                self.gate_results[ck] = {"status": "FAIL", "detail": "Timeout after 10 minutes"}
                print(f"  ⏰ Timeout after {elapsed:.0f}s")
                self.failed_phase = ck
                break

            except Exception as e:
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed
                self.gate_results[ck] = {"status": "FAIL", "detail": f"Error: {e}"}
                print(f"  ❌ Error: {e}")
                self.failed_phase = ck
                break

        # Update kanban status at the end of the pipeline
        if self.kanban_task:
            if self.failed_phase:
                self._kanban_update_status("blocked")
            else:
                self._kanban_update_status("done")

        # Final report
        return self._generate_report(crew_keys)

    def _generate_report(self, crew_keys: list) -> dict:
        """Generates the final pipeline report."""
        total = len(crew_keys)
        passed = sum(1 for g in self.gate_results.values() if g["status"] == "PASS")
        warned = sum(1 for g in self.gate_results.values() if g["status"] == "WARN")
        failed = sum(1 for g in self.gate_results.values() if g["status"] == "FAIL")
        skipped = sum(1 for g in self.gate_results.values() if g["status"] == "SKIP")
        total_time = sum(self.timing.values())

        report = {
            "status": "failed" if self.failed_phase else "completed",
            "mode": self.mode,
            "total_phases": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "skipped": skipped,
            "total_time_seconds": total_time,
            "failed_phase": self.failed_phase,
            "phases": {},
            "artifacts_dir": str(self.artifacts_dir),
        }

        for ck in crew_keys:
            crew = CREWS[ck]
            report["phases"][ck] = {
                "name": crew["name"],
                "skill": crew["skill"],
                "gate": self.gate_results.get(ck, {"status": "UNKNOWN", "detail": ""}),
                "time_seconds": self.timing.get(ck, 0),
                "artifact": str(self.artifacts.get(ck, "")),
            }

        # Print report
        print(f"\n{'='*60}")
        print(f"  📊 FINAL PIPELINE REPORT")
        print(f"{'='*60}\n")

        if self.failed_phase:
            print(f"  ❌ Pipeline stopped at phase: {CREWS[self.failed_phase]['name']}")
        else:
            print(f"  ✅ Pipeline completed successfully!")

        print(f"\n  📊 Dashboard:")
        print(f"     Phases: {total} | ✅ {passed} | ⚠️  {warned} | ❌ {failed} | ⏭️  {skipped}")
        print(f"     ⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f}min)")
        print(f"     📁 Artifacts: {self.artifacts_dir}")

        print(f"\n  📋 Breakdown by phase:")
        for ck in crew_keys:
            crew = CREWS[ck]
            gate = self.gate_results.get(ck, {"status": "UNKNOWN", "detail": ""})
            icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️", "UNKNOWN": "❓"}
            t = self.timing.get(ck, 0)
            print(f"     {icon.get(gate['status'], '❓')} {crew['name']} ({t:.1f}s)")
            if gate["detail"]:
                print(f"        {gate['detail']}")

        # Save report
        report_file = self.artifacts_dir / "pipeline_report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  📄 Report saved: {report_file}")

        return report


# ═══════════════════════════════════════════════════════════════════════════
# SIMULATION MODE — CrewAI (original)
# ═══════════════════════════════════════════════════════════════════════════

def build_simulation_crew(briefing: str, mode: str, start_phase: str = None):
    """Build a CrewAI crew for pipeline simulation/planning."""
    from crewai import Agent, Task, Crew, Process

    # ── Embedded agents ──
    AGENTS = {
        "pipeline-orchestrator": {
            "role": "Pipeline Orchestrator",
            "goal": "Coordinate the sequential execution of all specialized crews",
            "backstory": (
                "Software orchestra conductor with 15 years coordinating complex pipelines. "
                "You know every instrument (crew) of the software factory and know exactly "
                "when each one should play. Plans the sequence, allocates resources, sets deadlines "
                "and monitors progress. Your motto: 'A well-orchestrated pipeline is a symphony.'"
            ),
        },
        "artifact-manager": {
            "role": "Artifact Manager",
            "goal": "Ensure each crew's outputs are versioned and delivered as inputs to the next phase",
            "backstory": (
                "Meticulous software librarian who organizes and versions every artifact. "
                "Implements semantic versioning: requirements_v1.2, architecture_v1.0. "
                "Maintains a traceability matrix linking requirement → code → test → doc. "
                "Your motto: 'An artifact without a version is a lost artifact.'"
            ),
        },
        "decision-maker": {
            "role": "Decision Maker",
            "goal": "Analyze quality gates and decide to advance, pause or roll back",
            "backstory": (
                "Project manager with 20 years delivering critical software. "
                "Analyzes each quality gate: PASS → advance, WARN → advance with caveats, "
                "FAIL → block and determine rollback. "
                "Your motto: 'Quality without delivery is art; delivery without quality is junk.'"
            ),
        },
        "progress-reporter": {
            "role": "Progress Reporter",
            "goal": "Generate status reports, dashboards and executive summaries",
            "backstory": (
                "PM who turns technical progress into reports stakeholders understand. "
                "Generates a progress dashboard, executive summary, technical report and decision log. "
                "Your motto: 'A report nobody reads is worse than no report.'"
            ),
        },
    }

    def get_agent(slug):
        _crew_llm = build_crew_llm()
        data = AGENTS.get(slug)
        if not data:
            return Agent(role=slug, goal="Complete the task", backstory="Specialized agent.",
                         llm=_crew_llm,
                         verbose=True, allow_delegation=False)
        return Agent(role=data["role"], goal=data["goal"], backstory=data["backstory"],
                     llm=_crew_llm,
                     verbose=True, allow_delegation=False)

    orchestrator = get_agent("pipeline-orchestrator")
    manager = get_agent("artifact-manager")
    decision_maker = get_agent("decision-maker")
    reporter = get_agent("progress-reporter")

    mode_info = MODOS[mode]
    crew_keys = mode_info["crews"]

    if start_phase:
        if start_phase in crew_keys:
            idx = crew_keys.index(start_phase)
            crew_keys = crew_keys[idx:]
        else:
            print(f"  [!] Phase '{start_phase}' not found in mode '{mode}'")
            sys.exit(1)

    crews_info = []
    for ck in crew_keys:
        crew = CREWS[ck]
        crews_info.append(f"  {ck}: {crew['name']} ({crew['skill']})")
        crews_info.append(f"    Description: {crew['description']}")
        crews_info.append(f"    Agents: {', '.join(crew['agents'])}")
        crews_info.append(f"    Inputs: {', '.join(crew['inputs'])}")
        crews_info.append(f"    Outputs: {', '.join(crew['outputs'])}")
        crews_info.append(f"    Quality Gate: {crew['quality_gate']}")
        crews_info.append("")
    crews_text = "\n".join(crews_info)

    task_planning = Task(
        description=f"""
BRIEFING: {briefing}
MODE: {mode_info['name']} — {mode_info['description']}
PHASES: {', '.join(crew_keys)}

PLANNING:
1. Analyze the briefing and identify the scope
2. For each phase: objectives, estimated duration, dependencies, acceptance criteria
3. Create a sequential schedule with milestones
4. Identify pipeline risks

AVAILABLE CREWS:
{crews_text}
""",
        expected_output="Complete pipeline plan with schedule, phases and risks",
        agent=orchestrator,
    )

    task_execution = Task(
        description=f"""
BRIEFING: {briefing}
MODE: {mode_info['name']}
PHASES: {', '.join(crew_keys)}

PHASED EXECUTION:
For EACH phase, document:
1. Start: phase, skill, agents, received inputs
2. Execution: what each agent produces, decisions, problems
3. Generated artifacts: name, version, format
4. Artifact handoff to the next phase
5. Quality gate: PASS/WARN/FAIL with evidence

CREWS:
{crews_text}
""",
        expected_output="Complete pipeline execution with artifacts and quality gates",
        agent=orchestrator,
    )

    task_decisions = Task(
        description=f"""
BRIEFING: {briefing}
PHASES: {', '.join(crew_keys)}

QUALITY GATE DECISIONS:
For each phase, decide:
1. ✅ ADVANCE: phase approved
2. ⚠️ ADVANCE WITH CAVEATS: approved with pending items
3. 🔄 ROLL BACK: phase failed
4. ⏸️ PAUSE: pipeline paused

Justify each decision with impact on the schedule and assumed risk.
""",
        expected_output="Quality gate decisions with justifications",
        agent=decision_maker,
    )

    task_report = Task(
        description=f"""
BRIEFING: {briefing}
PHASES: {', '.join(crew_keys)}

FINAL REPORT:
1. Executive summary (1 paragraph)
2. Dashboard: completed/in-progress/pending phases, PASS/WARN/FAIL gates
3. Breakdown by phase with status and artifacts
4. Traceability matrix (requirement → code → test → doc)
5. Decision log
6. Metrics: artifacts, agents, approved gates
7. Final recommendations
""",
        expected_output="Complete final pipeline report",
        agent=reporter,
    )

    crew = Crew(
        agents=[orchestrator, manager, decision_maker, reporter],
        tasks=[task_planning, task_execution, task_decisions, task_report],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-orchestrator: Software Factory Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run.py "scheduling system for clinics"
  python run.py "scheduling system" --auto
  python run.py "PDF report feature" --mode sprint --auto
  python run.py "fix login error" --mode micro --auto
  python run.py "finance app" --mode security-audit --auto
  python run.py --input briefing.txt --auto
  python run.py "inventory system" --start-phase implementation --auto
  python run.py "scheduling system" --dry-run

Complementary skills (modes):
  python run.py "the /login endpoint returns 500" --mode bugfix --auto
  python run.py "clinics SaaS; competitors: Doctoralia" --mode competitive --auto
  python run.py "scheduling system" --mode full-dev --auto
  python run.py "deploy to staging working" --mode goal-loop --auto
  python run.py "refactor payments module" --mode maintenance --auto
        """,
    )
    parser.add_argument("briefing", nargs="?", help="Client briefing / project description")
    parser.add_argument("--input", "-i", dest="input_file", help="File with the briefing")
    parser.add_argument("--mode", "-m", choices=list(MODOS.keys()), default="full",
                        help="Pipeline mode (default: full)")
    parser.add_argument("--output", "-o", default=None, help="Output directory for artifacts")
    parser.add_argument("--start-phase", default=None,
                        help="Start from a specific phase (e.g: implementation)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only shows the pipeline plan, without executing")
    parser.add_argument("--auto", action="store_true",
                        help="Automatic mode: runs the real crews in sequence")
    parser.add_argument("--python", default=None,
                        help="Path to the Python interpreter (default: same as this script)")
    parser.add_argument("--kanban-task", default=None,
                        help="Task ID in the kanban (cp-agile). Updates status during execution")
    args = parser.parse_args()

    # ── Resolve briefing ──
    briefing = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ File not found: {args.input_file}")
            sys.exit(1)
        briefing = input_path.read_text(encoding="utf-8")
    elif args.briefing:
        briefing = args.briefing
    else:
        parser.print_help()
        print("\n❌ Error: provide the project briefing (argument or --input)")
        sys.exit(1)

    mode = args.mode
    mode_info = MODOS[mode]
    crew_keys = mode_info["crews"]

    if args.start_phase:
        if args.start_phase in crew_keys:
            idx = crew_keys.index(args.start_phase)
            crew_keys = crew_keys[idx:]
        else:
            print(f"❌ Phase '{args.start_phase}' not found in mode '{mode}'")
            print(f"   Available phases: {', '.join(crew_keys)}")
            sys.exit(1)

    # ── HEADER ──
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║       cp-orchestrator — Software Factory Orchestrator        ║
╚══════════════════════════════════════════════════════════════╝
""")
    print(f"📋 Briefing: {briefing[:120]}...")
    print(f"🔧 Mode: {mode_info['name']} — {mode_info['description']}")
    print(f"📂 Phases: {len(crew_keys)}")
    print(f"🚀 Mode: {'AUTO (real execution)' if args.auto else 'SIMULATION (CrewAI)'}")
    print()

    # ── Show plan ──
    print(f"{'='*60}")
    print(f"  PIPELINE PLAN")
    print(f"{'='*60}\n")

    # full-dev mode: shows the native NEXUS phases (merge of cp-full-dev)
    if mode == "full-dev":
        nexus_mode = nexus_detect_mode(briefing)
        phases = NEXUS_PHASES.get(nexus_mode, NEXUS_PHASES["micro"])
        phase_keys = list(phases.keys())
        total_agents = 0
        for i, pk in enumerate(phase_keys, 1):
            phase = phases[pk]
            n_agents = len(phase["agents"])
            total_agents += n_agents
            print(f"  Phase {i}: {phase['name']} ({n_agents} agents)")
            print(f"    Gate: {phase['gate_keeper']}")
            print(f"    {phase['description']}")
            print()
        print(f"  Total: {total_agents} agents in {len(phase_keys)} phases (NEXUS mode {nexus_mode})\n")
        # full-dev runs natively via NexusExecutor (--auto mode). Without --auto,
        # only shows the plan (there is no CrewAI simulation crew for NEXUS).
        if not args.auto:
            print("🧪 NEXUS plan displayed. Use --auto to run the native NEXUS pipeline.\n")
            return

    total_agents = 0
    if mode != "full-dev":
        for i, ck in enumerate(crew_keys, 1):
            crew = CREWS[ck]
            n_agents = len(crew["agents"])
            total_agents += n_agents
            print(f"  Phase {i}: {crew['name']}")
            print(f"    Skill: {crew['skill']}")
            print(f"    Agents: {n_agents} ({', '.join(crew['agents'])})")
            print(f"    Inputs: {', '.join(crew['inputs'])}")
            print(f"    Outputs: {', '.join(crew['outputs'])}")
            print(f"    Quality Gate: {crew['quality_gate']}")
            print()

        print(f"  Total: {total_agents} agents in {len(crew_keys)} phases\n")

        if args.dry_run:
            print("🧪 DRY RUN — plan displayed. Remove --dry-run to execute.\n")
            return

    # ── AUTO MODE ──
    if args.auto:
        # full-dev mode: runs the NEXUS pipeline natively (merge of cp-full-dev)
        if mode == "full-dev":
            nexus = NexusExecutor(
                requirement=briefing,
                mode="auto",
                start_phase=args.start_phase,
                output_dir=args.output,
                kanban_task=args.kanban_task,
                python_cmd=args.python,
            )
            report = nexus.run()
            if report["status"] == "failed":
                print(f"\n❌ NEXUS pipeline failed at phase: {report['failed_phase']}")
                print(f"   Fix the problem and re-run with --start-phase {report['failed_phase']}")
                sys.exit(1)
            else:
                print(f"\n✅ NEXUS pipeline completed successfully!")
            return

        executor = PipelineExecutor(
            briefing=briefing,
            mode=mode,
            start_phase=args.start_phase,
            output_dir=args.output,
            python_cmd=args.python,
            kanban_task=args.kanban_task,
        )
        report = executor.run()

        if report["status"] == "failed":
            print(f"\n❌ Pipeline failed at phase: {CREWS[report['failed_phase']]['name']}")
            print(f"   Fix the problem and re-run with --start-phase {report['failed_phase']}")
            sys.exit(1)
        else:
            print(f"\n✅ Pipeline completed successfully!")
        return

    # ── SIMULATION MODE (CrewAI) ──
    try:
        from crewai import Agent, Task, Crew, Process
    except ImportError:
        print("❌ crewai not installed. Run: pip install crewai")
        print("   Or use --auto if you prefer direct execution without CrewAI.")
        sys.exit(3)  # standardized code: 3 = crewai missing (see require_crewai)

    print("🚀 Building orchestration crew (simulation)...\n")
    crew = build_simulation_crew(briefing, mode, args.start_phase)

    print("🤖 Agents in the crew:")
    for agent in crew.agents:
        print(f"  - {agent.role}")
    print(f"\n📋 Tasks ({len(crew.tasks)}):")
    task_names = [
        "1. Pipeline Planning",
        "2. Phased Execution with Artifact Handoff",
        "3. Quality Gate Decisions",
        "4. Final Report",
    ]
    for i, tn in enumerate(task_names, 1):
        agent_name = crew.tasks[i-1].agent.role if hasattr(crew.tasks[i-1], 'agent') and crew.tasks[i-1].agent else "?"
        print(f"  {tn} → {agent_name}")
    print()

    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    print("🚀 Running pipeline simulation...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n{'='*60}")
    print(f"  ✅ SIMULATION COMPLETED")
    print(f"{'='*60}\n")
    print(result_str)

    # Save
    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {out_file.resolve()}")
    else:
        output_dir = ORCHESTRATOR_DIR / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"simulation_{mode}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()