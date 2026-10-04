#!/usr/bin/env python3
"""
cp-devops — DevOps and Infrastructure Crew (self-contained)

Creates a CrewAI crew with agents specialized in DevOps:
  CI/CD Eng. → Infrastructure Eng. → Monitoring Eng. → Infra Security Eng.

Usage:
  python run.py "set up a staging environment with PostgreSQL and Redis"
  python run.py --mode ci-cd "configure GitHub Actions"
  python run.py --input requirements.txt --output report.md
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # DT-07: the lib is only required for real execution, not for --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # DT-01: UTF-8 on stdout/stderr (Windows console is cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS (self-contained)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "ci-cd-engineer": {
        "role": "CI/CD Engineer",
        "goal": "Configure automated, reliable build, test and deploy pipelines",
        "backstory": (
            "CI/CD engineer obsessed with automation. You hate manual deploys "
            "and believe every repetitive process should be automated. "
            "Specialist in GitHub Actions, GitLab CI, Jenkins and CircleCI. "
            "You configure pipelines with build, automated tests, static analysis, "
            "security scan, Docker container builds and deploy to multiple environments. "
            "Your motto: 'If it needs a human to run it, it's not a pipeline — it's a task.' "
            "You ensure each pipeline has clear stages, smart caching, "
            "and fails fast with useful error messages."
        ),
    },
    "infrastructure-engineer": {
        "role": "Infrastructure Engineer",
        "goal": "Provision scalable, secure, reproducible infrastructure as code",
        "backstory": (
            "Infrastructure engineer who treats everything as code. "
            "You NEVER SSH into a server to configure it — everything is Terraform, "
            "Pulumi, CloudFormation, Docker Compose or Kubernetes. "
            "Specialist in AWS, GCP and Azure, with deep knowledge of "
            "VPCs, subnets, security groups, IAM roles, load balancers, "
            "auto-scaling groups, managed databases and Kubernetes. "
            "You design infrastructure following the Well-Architected Framework: "
            "operational excellence, security, reliability, performance efficiency "
            "and cost optimization. Your mantra: 'If it's not in the repository, it doesn't exist.'"
        ),
    },
    "monitoring-engineer": {
        "role": "Monitoring Engineer",
        "goal": "Configure complete observability: metrics, logs, tracing and proactive alerts",
        "backstory": (
            "Experienced SRE who discovers problems before users. "
            "You configure end-to-end observability with Prometheus, "
            "Grafana, Datadog, New Relic, ELK Stack and OpenTelemetry. "
            "You create dashboards that tell the system's story, "
            "alerts with smart thresholds (avoiding alert fatigue), "
            "and structured logging that enables fast debugging. "
            "You implement SLIs, SLOs and error budgets. "
            "Your motto: 'If it's not being monitored, it's not in production.' "
            "You hate pretty but useless dashboards — every metric must "
            "answer a specific question about the system's health."
        ),
    },
    "infra-security-engineer": {
        "role": "Infrastructure Security Engineer",
        "goal": "Identify and mitigate security vulnerabilities in the infrastructure",
        "backstory": (
            "Paranoid security engineer — and rightly so. You assume everything is "
            "compromised until proven otherwise. Cloud security specialist: "
            "IAM policies, security groups, network ACLs, encryption at rest and in transit, "
            "secret management, vulnerability scanning and compliance (SOC2, HIPAA, PCI). "
            "You review every open port, every IAM permission, every environment variable "
            "that could contain a secret. You implement the principle of least privilege "
            "religiously. Your motto: 'It's not paranoia if they really are after you.' "
            "You always ask: 'If this container is compromised, what's the blast radius?'"
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    """Get a CrewAI Agent from the embedded definitions."""
    data = AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agent not found: {slug} — using generic fallback")
        return Agent(
            role=name,
            goal=f"Complete the task with excellence as {name}",
            backstory=f"Specialized agent acting as {name}.",
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
# Crew builder
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(description: str, mode: str = "full"):
    """Build a CrewAI crew for DevOps and Infrastructure."""

    eng_ci_cd = get_agent("ci-cd-engineer")
    eng_infra = get_agent("infrastructure-engineer")
    eng_monitoring = get_agent("monitoring-engineer")
    eng_security = get_agent("infra-security-engineer")

    tasks = []

    # ── Task 1: Infra Requirements Analysis ──────────────────────────
    if mode in ("full", "infra"):
        task_analysis = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — INFRASTRUCTURE REQUIREMENTS ANALYSIS:
            Analyze the project description and produce a detailed infrastructure plan:

            1. **Infrastructure requirements** — compute, storage, network, database
            2. **Recommended cloud provider** — AWS, GCP or Azure with justification
            3. **Proposed architecture** — textual diagram of the components and their connections
            4. **Necessary services** — EC2/ECS/EKS, RDS, ElastiCache, S3, CloudFront, etc.
            5. **Estimated sizing** — instances, storage, bandwidth
            6. **Deploy strategy** — blue/green, canary, rolling update
            7. **Cost estimate** — approximate monthly per service

            Be specific. Nothing generic like "use the cloud".
            """,
            expected_output=(
                "Detailed infrastructure plan: provider, architecture, "
                "services, sizing, deploy strategy and cost estimate"
            ),
            agent=eng_infra,
        )
        tasks.append(task_analysis)

    # ── Task 2: CI/CD Configuration ──────────────────────────────────
    if mode in ("full", "ci-cd"):
        task_cicd = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — CI/CD PIPELINE CONFIGURATION:
            Design and describe the complete CI/CD pipeline configuration:

            1. **Chosen platform** — GitHub Actions, GitLab CI, Jenkins (justify)
            2. **Pipeline structure** — stages, jobs, dependencies
            3. **Mandatory stages**:
               - Build: application compilation/build
               - Lint: static code analysis
               - Test: unit, integration, e2e tests
               - Security Scan: SAST, dependency scanning
               - Docker Build: image build and push
               - Deploy: deploy to staging/production
            4. **Cache strategy** — dependencies, Docker layers
            5. **Secrets management** — how to expose secure environment variables
            6. **Deploy strategy** — blue/green, canary, rolling
            7. **Rollback** — how to revert in case of failure
            8. **Notifications** — Slack, email, Discord on failure/success

            Provide the real pipeline YAML/config, not just a textual description.
            """,
            expected_output=(
                "Complete CI/CD pipeline configuration with real YAML, "
                "deploy strategy, secrets management and rollback"
            ),
            agent=eng_ci_cd,
        )
        tasks.append(task_cicd)

    # ── Task 3: Infrastructure Provisioning ──────────────────────
    if mode in ("full", "infra"):
        task_provisioning = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — INFRASTRUCTURE PROVISIONING:
            Based on the requirements analysis, produce the necessary IaC code:

            1. **Terraform/HCL** — main resources (VPC, subnets, security groups, EC2/ECS, RDS, etc.)
            2. **Docker Compose or Kubernetes manifests** — if applicable
            3. **Directory structure** — organization of the infra repository
            4. **Variables and outputs** — module parameterization
            5. **State management** — remote backend (S3 + DynamoDB, GCS, etc.)
            6. **Network topology** — VPC, public/private subnets, NAT gateway, load balancer
            7. **Database** — RDS, backup configuration, multi-AZ
            8. **Storage** — S3 buckets, lifecycle policies
            9. **IAM** — roles and policies with least privilege

            Provide the real HCL code, not just a description.
            """,
            expected_output=(
                "Complete IaC code (Terraform HCL, Docker Compose or K8s manifests) "
                "with variables, outputs, state management and network topology"
            ),
            agent=eng_infra,
        )
        tasks.append(task_provisioning)

    # ── Task 4: Monitoring Configuration ──────────────────────────
    if mode in ("full", "monitoring"):
        task_monitoring = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — MONITORING CONFIGURATION:
            Design the complete observability strategy:

            1. **Metrics** — Prometheus/Datadog:
               - Infrastructure metrics (CPU, memory, disk, network)
               - Application metrics (latency, throughput, error rate, saturation)
               - Business metrics (active users, transactions, revenue)
            2. **Dashboards** — Grafana:
               - System overview dashboard
               - Performance and latency dashboard
               - Errors and exceptions dashboard
               - Costs dashboard
            3. **Logging** — ELK/Loki/CloudWatch:
               - Structured logging (JSON)
               - Log levels (debug, info, warn, error, fatal)
               - Centralized aggregation and search
            4. **Alerts**:
               - Alert rules with thresholds and severities
               - Escalations (PagerDuty/OpsGenie)
               - Notifications (Slack, email)
            5. **Tracing** — OpenTelemetry/Jaeger:
               - Distributed tracing for cross-service requests
            6. **SLOs/SLIs**:
               - Service Level Objectives definition
               - Error budgets

            Be specific in the configurations: thresholds, PromQL queries, panels.
            """,
            expected_output=(
                "Complete observability strategy: metrics, dashboards, "
                "logging, alerts, tracing and SLOs with specific configurations"
            ),
            agent=eng_monitoring,
        )
        tasks.append(task_monitoring)

    # ── Task 5: Security Review ────────────────────────────────────
    if mode in ("full", "security"):
        task_security = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — INFRASTRUCTURE SECURITY REVIEW:
            Review all the proposed infrastructure and identify vulnerabilities:

            1. **Network Security**:
               - Unnecessarily exposed ports?
               - Overly permissive security groups (0.0.0.0/0)?
               - Correct public vs private subnets?
               - WAF configured?
            2. **IAM and Access**:
               - Least privilege principle applied?
               - Roles vs users vs service accounts?
               - MFA mandatory?
               - Access keys rotated?
            3. **Data Security**:
               - Encryption at rest (EBS, RDS, S3)?
               - Encryption in transit (TLS)?
               - Secrets management (Vault, AWS Secrets Manager)?
            4. **Container Security**:
               - Images scanned for vulnerabilities?
               - Container running as root?
               - Resource limits configured?
               - Read-only filesystem?
            5. **Compliance**:
               - Does the application need SOC2, HIPAA, PCI, LGPD?
               - Audit logging configured?
            6. **Incident Response**:
               - Incident response plan?
               - Backup and disaster recovery?
               - Documented runbooks?

            For each vulnerability found, classify: CRITICAL, HIGH, MEDIUM, LOW.
            Provide specific mitigation recommendations for each one.
            """,
            expected_output=(
                "Complete security report: vulnerabilities classified "
                "by severity, mitigation recommendations, and compliance checklist"
            ),
            agent=eng_security,
        )
        tasks.append(task_security)

    # ── Task 6: Quality Gate ────────────────────────────────────────────
    if mode == "full":
        quality_gate = Task(
            description=f"""
            PROJECT DESCRIPTION:
            {description}

            YOUR JOB — FINAL QUALITY GATE:
            Review all the deliverables from the previous stages and issue a verdict.

            Verify:

            1. **CI/CD Pipeline**:
               - Pipeline configured with all necessary stages?
               - Deploy strategy defined?
               - Rollback configured?
               - Secrets managed securely?

            2. **Infrastructure**:
               - Complete and reproducible IaC code?
               - State management configured?
               - Secure network topology?
               - Backup and disaster recovery?

            3. **Monitoring**:
               - Essential metrics collected?
               - Dashboards created?
               - Alerts configured with thresholds?
               - Structured logging?

            4. **Security**:
               - No CRITICAL or HIGH vulnerabilities?
               - Encryption configured (at rest and in transit)?
               - IAM with least privilege?
               - Secrets management implemented?

            Issue the verdict:

            ✅ **PASS** — All green. The infrastructure is ready for production.
            ❌ **FAIL** — Items to fix before proceeding.

            If FAIL, list exactly what needs to be fixed, prioritized by severity.
            """,
            expected_output=(
                "Final Quality Gate: PASS/FAIL verdict with complete checklist "
                "of each dimension (CI/CD, infra, monitoring, security)"
            ),
            agent=eng_security,
        )
        tasks.append(quality_gate)

    # ── Crew ────────────────────────────────────────────────────────────
    agents = []
    if mode in ("full", "ci-cd"):
        agents.append(eng_ci_cd)
    if mode in ("full", "infra"):
        agents.append(eng_infra)
    if mode in ("full", "monitoring"):
        agents.append(eng_monitoring)
    if mode in ("full", "security"):
        agents.append(eng_security)

    # Ensure all agents are included for full mode
    if mode == "full":
        agents = [eng_ci_cd, eng_infra, eng_monitoring, eng_security]

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-devops: DevOps and Infrastructure Crew (self-contained)",
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Project description and infrastructure requirements",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the report",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "ci-cd", "infra", "monitoring", "security"],
        default="full",
        help="Execution mode (default: full — complete pipeline)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only build the crew and show the agents, without executing",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of traceback

    # --- Resolve description ---
    description = None
    if args.input_file:
        description = Path(args.input_file).read_text(encoding="utf-8")
    elif args.description:
        description = args.description
    else:
        parser.print_help()
        print("\n❌ Error: provide the project description (argument or --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    mode_labels = {
        "full": "Complete pipeline (CI/CD + Infra + Monitoring + Security + Quality Gate)",
        "ci-cd": "CI/CD only",
        "infra": "Infrastructure only",
        "monitoring": "Monitoring only",
        "security": "Security only",
    }

    print(f"\n📋 Project: {description[:120]}...")
    print(f"🔧 Mode: {mode_labels.get(mode, mode)}")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(description, mode)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            desc_short = task.description[:80].replace("\n", " ").strip()
            print(f"  {i}. {task.agent.role}: {desc_short}...")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running DevOps crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ DevOps Report generated!\n")
    print(result_str)

    # --- Save output ---
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")
    else:
        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"devops_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
