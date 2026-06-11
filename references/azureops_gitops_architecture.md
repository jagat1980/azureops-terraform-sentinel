# AzureOps Sentinel: Enterprise GitOps Blueprint
### A Multi-Source Event-Driven Declarative Remediation Architecture for Terraform-Managed Public Cloud Infrastructures

This document provides an editable representation of the architectural blueprint and lifecycle specification for the **AzureOps Sentinel** auto-remediation engine.

---

## 1. End-to-End Event-Driven Functional Architecture Diagram

The diagram below represents the functional telemetry and remediation pipeline. It is written in **Mermaid** format, which can be natively edited or rendered in markdown previewers, Azure DevOps, and GitHub:

```mermaid
graph TD
    %% Detection & Ingest Phase
    subgraph Detection [1. DETECTION & INGEST]
        MD[Microsoft Defender<br/>Cloud security posture drift]
        LA[Azure Log Analytics<br/>Anomalous KQL alert signals]
        AM[Azure Monitor<br/>Metric threshold state alerts]
        EG[Azure Event Grid<br/>Universal CloudEvents Router]

        MD --> EG
        LA --> EG
        AM --> EG
    end

    %% Cognitive Swarm Phase
    subgraph Swarm [2. COGNITIVE SWARM]
        FN[Azure Function Runtime<br/>Python-based orchestration]
        AI[Azure OpenAI Service<br/>Cognitive LLM processing]
        
        Triage[1. Triage Schema & Target Locator]
        Patch[2. Generative HCL Patching]
        Copywrite[3. Draft PR Body Description]

        EG --> |Secure Webhook| FN
        FN <--> |AI Prompts| AI
        AI --> Triage
        AI --> Patch
        AI --> Copywrite
    end

    %% Git Control Plane Phase
    subgraph GitPlane [3. GIT CONTROL PLANE]
        Repo[Target Git Repository<br/>GitHub / Azure DevOps]
        Branch[Automated Branch<br/>secops/patch-inc-102458]
        PR[Pull Request Gateway<br/>Human-in-the-Loop Review]
        Audit[Audit Gate<br/>Immutable Git Ledger]

        FN --> |GitHub API| Repo
        Repo --> Branch
        Branch --> PR
        PR --> |Blocker / Human Check| Audit
    end

    %% Transactional CI/CD Phase
    subgraph CICD [4. TRANSACTIONAL CI/CD]
        Pipeline[Deployment Pipeline<br/>GitHub Actions / ADO Pipelines]
        Plan[terraform plan<br/>Dry-run state verification]
        Apply[terraform apply<br/>Idempotent execution barrier]

        Audit --> |Approval Merge| Pipeline
        Pipeline --> Plan
        Plan --> Apply
    end

    %% Live Azure Environment Phase
    subgraph LiveEnv [5. LIVE AZURE ENVIRONMENT]
        RG[Azure Resource Group<br/>Target Sub / Scope]
        Res[Remediated Resource<br/>Storage/Compute/Network/DB]
        Sync[Synchronized State<br/>Live Cloud matches Git Source]

        Apply --> RG
        RG --> Res
        Res --> Sync
    end

    classDef telemetry fill:#f9f,stroke:#333,stroke-width:1px;
    classDef orchestrator fill:#bbf,stroke:#333,stroke-width:1px;
    classDef git fill:#bfb,stroke:#333,stroke-width:1px;
    classDef cicd fill:#fbb,stroke:#333,stroke-width:1px;
    classDef live fill:#ffb,stroke:#333,stroke-width:1px;

    class MD,LA,AM,EG telemetry;
    class FN,AI,Triage,Patch,Copywrite orchestrator;
    class Repo,Branch,PR,Audit git;
    class Pipeline,Plan,Apply cicd;
    class RG,Res,Sync live;
```

---

## 2. Deep Dive Lifecycle Mappings & System Specifications

| Lifecycle Phase | Component & Technical Interface | Core Operational Mechanics | OpenAI Cognitive Footprint |
| :--- | :--- | :--- | :--- |
| **DIAGNOSING & INGESTION** | Azure Event Grid System Topic <br/>`monitoringService: "Defender"` | Ingests polymorphic JSON structures from divergent telemetry planes. Standardizes communication via the CloudEvents v1.0 standard, shielding downstream modules from Microsoft event schema modifications. | **Footprint #1: Cognitive Parser & Locator**<br/>Extracts nested variables (e.g. compromised asset) into a unified internal JSON definition and identifies target landing zone files dynamically. |
| **REMEDIATING & ORCHESTRATION** | Azure Function (Python) & GitHub API | The function checks out the repository context, passes the affected `.tf` block to OpenAI, handles branch creation, commits the altered declarative state, and programmatically spawns a Pull Request. | **Footprint #2: Generative HCL Patching**<br/>Analyzes existing configurations against policy violations and modifies specific attributes safely (e.g. turning public access off, restricting security group ports). |
| **VERIFYING & CI/CD** | CI/CD Engine & Terraform Core <br/>`terraform plan -out=tfplan` | Triggered dynamically upon PR creation. Runs transactional dry-runs against the active `.tfstate` storage backend to verify structural integrity, syntactic validity, and identify blast radius before changes touch target subscriptions. | *None.*<br/>(Decoupled completely from LLM code generation to enforce strict deterministic safeguards and state file alignment). |
| **REPORTING & AUDIT** | Pull Request Interface & Git Ledger | Consolidates automated analytical breakdowns directly within the standard engineering workflow. The merged branch generates an immutable, cryptographically signed ledger record inside the version control database. | **Footprint #3: PR Copywriting**<br/>Generates comprehensive Markdown documentation detailing Business Impact Summaries, blast radiuses, and compliance review metadata for SRE sign-off. |
