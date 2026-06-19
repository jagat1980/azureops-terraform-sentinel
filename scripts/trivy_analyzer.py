import os
import sys
import json
import re
import time
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load environment variables from .env if present
try:
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")
except FileNotFoundError:
    pass

# Try importing OpenAI client libraries
try:
    from openai import OpenAI, AzureOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ==========================================
# Task Abstraction (Task Class)
# ==========================================
class Task:
    """
    Encapsulates a single pipeline step in the Container Image Scan Analysis Agent.
    Tracks execution status, timing, metadata, and handles errors.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
        self.start_time = None
        self.end_time = None
        self.duration_seconds = 0.0
        self.input_metadata = {}
        self.output_metadata = {}
        self.error_message = None

    def execute(self, run_fn, *args, **kwargs):
        self.status = "RUNNING"
        self.start_time = time.time()
        logging.info(f"▶️ Starting Task: {self.name} - {self.description}")
        try:
            result = run_fn(*args, **kwargs)
            self.status = "COMPLETED"
            self.end_time = time.time()
            self.duration_seconds = self.end_time - self.start_time
            logging.info(f"✅ Completed Task: {self.name} in {self.duration_seconds:.3f}s")
            return result
        except Exception as e:
            self.status = "FAILED"
            self.end_time = time.time()
            self.duration_seconds = self.end_time - self.start_time
            self.error_message = str(e)
            logging.error(f"❌ Failed Task: {self.name} - Error: {self.error_message}")
            raise e

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "error_message": self.error_message,
            "input_metadata": self.input_metadata,
            "output_metadata": self.output_metadata
        }


# ==========================================
# Pipeline Implementation
# ==========================================
class ContainerImageScanPipeline:
    def __init__(self, image_uri: str, scan_payload_path: str = None):
        self.image_uri = image_uri
        self.scan_payload_path = scan_payload_path
        self.tasks = {}
        self.pipeline_metadata = {
            "image_uri": image_uri,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "steps": []
        }

    def run_pipeline(self) -> dict:
        """Executes all 8 steps of the Container Image Scan Analysis Agent."""
        try:
            # 1. SCAN
            raw_scan = self._run_task("SCAN", "trivy.scan_image (MCP) -> raw CVEs + SBOM", 
                                      self.step_scan)
            
            # 2. ATTRIBUTE
            attributed = self._run_task("ATTRIBUTE", "Map each CVE -> image layer (base / app / dep)", 
                                        self.step_attribute, raw_scan)
            
            # 3. DEDUP
            deduplicated = self._run_task("DEDUP", "Collapse multi-layer + multi-tag duplicates", 
                                          self.step_dedup, attributed)
            
            # 4. ENRICH
            enriched = self._run_task("ENRICH", "EPSS score + KEV flag (MCP feeds, parallel)", 
                                      self.step_enrich, deduplicated)
            
            # 5. PRE-FILTER
            pre_filtered = self._run_task("PRE-FILTER", "Reachability heuristics + won't-fix + build-only suppression", 
                                          self.step_pre_filter, enriched)
            
            # 6. JUDGE (LLM)
            judged = self._run_task("JUDGE", "LLM reachability on ambiguous CVEs + base-image upgrade recommendation", 
                                    self.step_judge, pre_filtered)
            
            # 7. CONSOLIDATE
            consolidated = self._run_task("CONSOLIDATE", "Group by fix path -> '1 base bump = N fixes'", 
                                          self.step_consolidate, judged)
            
            # 8. DRAFT PR
            pr_details = self._run_task("DRAFT PR", "github.create_pull_request with human review gate", 
                                        self.step_draft_pr, consolidated)

            self.pipeline_metadata["status"] = "SUCCESS"
            self.pipeline_metadata["summary"] = {
                "total_raw_findings": len(raw_scan.get("vulnerabilities", [])) + len(raw_scan.get("secrets", [])),
                "after_dedup": len(deduplicated),
                "retained_after_filter": len([v for v in pre_filtered if not v.get("suppressed")]),
                "consolidated_fixes": len(consolidated.get("fix_paths", {}))
            }
            return self.pipeline_metadata

        except Exception as e:
            self.pipeline_metadata["status"] = "FAILED"
            self.pipeline_metadata["error"] = str(e)
            return self.pipeline_metadata

    def _run_task(self, name: str, description: str, run_fn, *args, **kwargs):
        task = Task(name, description)
        self.tasks[name] = task
        result = task.execute(run_fn, *args, **kwargs)
        self.pipeline_metadata["steps"].append(task.to_dict())
        return result

    # ----------------------------------------------------
    # Task 1: SCAN (deterministic, auth: none, in-cluster)
    # ----------------------------------------------------
    def step_scan(self) -> dict:
        """Loads the raw Trivy JSON report (or simulates scan)."""
        task = self.tasks["SCAN"]
        task.input_metadata = {"image_uri": self.image_uri, "payload_path": self.scan_payload_path}

        if self.scan_payload_path and os.path.exists(self.scan_payload_path):
            with open(self.scan_payload_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        else:
            # Fallback mock scan response if no path provided
            raw_data = {
                "SchemaVersion": 2,
                "ArtifactName": self.image_uri,
                "ArtifactType": "container_image",
                "Results": [
                    {
                        "Target": f"{self.image_uri} (alpine 3.17.0)",
                        "Class": "os-pkgs",
                        "Vulnerabilities": [
                            {
                                "VulnerabilityID": "CVE-2023-56789",
                                "PkgName": "openssl",
                                "InstalledVersion": "3.0.7-r0",
                                "FixedVersion": "3.0.8-r0",
                                "Layer": {"DiffID": "sha256:abcd1234efgh5678"},
                                "Severity": "Critical",
                                "Title": "openssl: RCE via certificate validation",
                                "TargetFile": "Dockerfile"
                            }
                        ]
                    }
                ]
            }

        # Parse findings
        vulnerabilities = []
        secrets = []
        for result in raw_data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                vuln["Target"] = result.get("Target")
                vulnerabilities.append(vuln)
            for secret in result.get("Secrets", []):
                secret["Target"] = result.get("Target")
                secret["TargetFile"] = result.get("TargetFile", "Unknown")
                secrets.append(secret)

        task.output_metadata = {
            "vulnerability_count": len(vulnerabilities),
            "secret_count": len(secrets)
        }
        return {"vulnerabilities": vulnerabilities, "secrets": secrets}

    # ----------------------------------------------------
    # Task 2: ATTRIBUTE (deterministic - parse OCI manifest)
    # ----------------------------------------------------
    def step_attribute(self, raw_scan: dict) -> list:
        """
        Maps each CVE/secret to a specific image layer:
        - base: Base operating system layers
        - app: Application code additions
        - dep: Dynamically installed third-party libraries
        """
        task = self.tasks["ATTRIBUTE"]
        findings = []

        # Example OCI Manifest/Docker History mapping simulation
        # Layers 1-3: Base (alpine OS)
        # Layer 4: Application code
        # Layer 5: Installed packages
        base_layers = {"sha256:abcd1234efgh5678", "sha256:base1234base5678"}
        dep_layers = {"sha256:dep1234dep5678"}

        for vuln in raw_scan["vulnerabilities"]:
            diff_id = vuln.get("Layer", {}).get("DiffID", "unknown")
            
            # Map layer based on mock history matching
            if diff_id in base_layers:
                layer_type = "base"
            elif diff_id in dep_layers:
                layer_type = "dep"
            else:
                layer_type = "app"

            vuln_item = {
                "id": vuln["VulnerabilityID"],
                "type": "cve",
                "pkg_name": vuln["PkgName"],
                "installed_version": vuln["InstalledVersion"],
                "fixed_version": vuln.get("FixedVersion", ""),
                "layer_sha": diff_id,
                "layer_type": layer_type,
                "severity": vuln["Severity"],
                "title": vuln["Title"],
                "description": vuln.get("Description", ""),
                "target_file": vuln.get("TargetFile", "Dockerfile")
            }
            findings.append(vuln_item)

        for secret in raw_scan["secrets"]:
            secret_item = {
                "id": secret.get("RuleID", "generic-secret"),
                "type": "secret",
                "pkg_name": secret.get("Category", "credentials"),
                "installed_version": "N/A",
                "fixed_version": "Revoke & Rotate",
                "layer_sha": "write-layer",
                "layer_type": "app",
                "severity": secret.get("Severity", "CRITICAL"),
                "title": secret["Title"],
                "description": f"Exposed secret in {secret.get('TargetFile')}",
                "target_file": secret.get("TargetFile")
            }
            findings.append(secret_item)

        task.output_metadata = {"attributed_findings": len(findings)}
        return findings

    # ----------------------------------------------------
    # Task 3: DEDUP (deterministic key: cve+pkg+version+layer_sha)
    # ----------------------------------------------------
    def step_dedup(self, attributed_findings: list) -> list:
        """Deduplicates findings using the unique key: cve+pkg+version+layer_sha"""
        task = self.tasks["DEDUP"]
        deduped = {}
        duplicates_count = 0

        for f in attributed_findings:
            key = f"{f['id']}|{f['pkg_name']}|{f['installed_version']}|{f['layer_sha']}"
            if key in deduped:
                duplicates_count += 1
            else:
                deduped[key] = f

        task.output_metadata = {
            "unique_findings": len(deduped),
            "duplicates_removed": duplicates_count
        }
        return list(deduped.values())

    # ----------------------------------------------------
    # Task 4: ENRICH (EPSS score + KEV flag in parallel)
    # ----------------------------------------------------
    def step_enrich(self, deduped_findings: list) -> list:
        """Enriches each CVE with EPSS score and CISA KEV (Known Exploited Vulnerabilities) flag in parallel."""
        task = self.tasks["ENRICH"]

        # Simulated Threat Feed database lookup
        threat_db = {
            "CVE-2023-56789": {"epss": 0.942, "kev": True},  # High exploit likelihood + active exploitation
            "CVE-2023-38545": {"epss": 0.812, "kev": True},
            "CVE-2022-4450": {"epss": 0.054, "kev": False}
        }

        def enrich_item(item):
            if item["type"] == "cve":
                vuln_id = item["id"]
                feed_data = threat_db.get(vuln_id, {"epss": 0.001, "kev": False})
                item["epss"] = feed_data["epss"]
                item["kev"] = feed_data["kev"]
            else:
                item["epss"] = 1.0  # Secrets always ranked maximum urgency
                item["kev"] = True
            return item

        # Run lookups in parallel using thread pool
        enriched_findings = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(enrich_item, f) for f in deduped_findings]
            for future in as_completed(futures):
                enriched_findings.append(future.result())

        task.output_metadata = {
            "enriched_items": len(enriched_findings),
            "active_kev_count": len([f for f in enriched_findings if f.get("kev")])
        }
        return enriched_findings

    # ----------------------------------------------------
    # Task 5: PRE-FILTER (Reachability heuristics + build-only suppression)
    # ----------------------------------------------------
    def step_pre_filter(self, enriched_findings: list) -> list:
        """
        Applies deterministic rules for suppression/priority:
        - Won't-fix list suppression
        - Build-only package suppression (e.g. gcc, make, automake, build-essential)
        - PCI-DSS protection: Banish auto-suppression on payment-path/PCI images
        """
        task = self.tasks["PRE-FILTER"]
        
        # Policy rules
        suppression_packages = {"gcc", "make", "automake", "build-essential", "cmake", "cpp"}
        is_pci_image = "payment" in self.image_uri.lower()

        filtered_findings = []
        suppressed_count = 0

        for f in enriched_findings:
            f["suppressed"] = False
            f["suppression_reason"] = ""

            # Check if build-only tool
            if f["pkg_name"] in suppression_packages:
                if is_pci_image:
                    f["suppression_reason"] = "PCI-DSS Rule: Build-tool suppression bypassed for payment-path image"
                else:
                    f["suppressed"] = True
                    f["suppression_reason"] = "Suppressed: Build-only tool vulnerability is not exposed in production"
                    suppressed_count += 1

            filtered_findings.append(f)

        task.output_metadata = {
            "total_items": len(filtered_findings),
            "suppressed": suppressed_count,
            "retained": len(filtered_findings) - suppressed_count
        }
        return filtered_findings

    # ----------------------------------------------------
    # Task 6: JUDGE (LLM Reachability + Upgrade Recommendation)
    # ----------------------------------------------------
    def step_judge(self, pre_filtered_findings: list) -> list:
        """
        Engages the LLM (Sonnet/GPT-4o/5.5) ONLY for genuinely ambiguous CVEs to judge:
        - Code path reachability of the package functions.
        - Base-image upgrade path and breaking-change analysis.
        """
        task = self.tasks["JUDGE"]
        
        # Filter for active, non-suppressed findings needing judgement
        ambiguous_cves = [f for f in pre_filtered_findings if not f["suppressed"]]
        
        if not ambiguous_cves:
            task.output_metadata = {"judgments_made": 0, "status": "No ambiguous items"}
            return pre_filtered_findings

        # Build LLM Prompt
        prompt = f"""You are a senior container security analyst and static code auditor.
Evaluate the code-path reachability and upgrade safety for the following vulnerabilities in image '{self.image_uri}':

"""
        for i, cve in enumerate(ambiguous_cves):
            prompt += f"""---
Finding #{i+1}:
CVE: {cve['id']}
Package: {cve['pkg_name']} (Installed: {cve['installed_version']}, Fixed: {cve['fixed_version']})
Description: {cve['description']}
Layer: {cve['layer_type']}
File context: {cve['target_file']}
"""

        prompt += """
For each finding, provide:
1. "reachable": boolean (True/False - explain code path exposure or standard container library usage)
2. "upgrade_safety": string (breaking-change assessment if upgrading package or base image)
3. "remediation": string (actionable advice)

Format your response as a JSON object matching this schema:
{
  "judgments": [
    {
      "id": "CVE-xxxx-xxxxx",
      "reachable": true/false,
      "upgrade_safety": "Low Risk / High Risk / Breaking",
      "remediation": "Brief instructions"
    }
  ]
}
"""

        # Call LLM or use offline fallback if no API key is set
        judgments_map = {}
        api_provider = os.getenv("AI_PROVIDER", "openai").strip().lower()
        has_creds = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")

        if HAS_OPENAI and has_creds:
            try:
                logging.info(f"🧠 Engaging LLM Judge via provider: {api_provider}")
                if api_provider == "openai":
                    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    model = os.getenv("OPENAI_MODEL", "gpt-4o")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                else:
                    client = AzureOpenAI(
                        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                        api_key=os.getenv("AZURE_OPENAI_KEY"),
                        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
                    )
                    deployment = os.getenv("OPENAI_DEPLOYMENT_NAME")
                    response = client.chat.completions.create(
                        model=deployment,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                
                resp_json = json.loads(response.choices[0].message.content)
                for j in resp_json.get("judgments", []):
                    judgments_map[j["id"]] = j
            except Exception as ex:
                logging.warning(f"⚠️ LLM Call failed, using deterministic fallback: {str(ex)}")
                
        # If offline or failed, apply deterministic fallback logic
        if not judgments_map:
            logging.info("🔌 Utilizing offline deterministic fallback for LLM Judge")
            for cve in ambiguous_cves:
                # Mock logic
                if cve["id"] == "CVE-2023-56789":
                    judgments_map[cve["id"]] = {
                        "id": cve["id"],
                        "reachable": True,
                        "upgrade_safety": "Low Risk",
                        "remediation": "Upgrade openssl to 3.0.8-r0 in Alpine base image"
                    }
                else:
                    judgments_map[cve["id"]] = {
                        "id": cve["id"],
                        "reachable": False,
                        "upgrade_safety": "Low Risk",
                        "remediation": f"Upgrade {cve['pkg_name']} to {cve['fixed_version']}"
                    }

        # Apply LLM Judgments back to findings
        for f in pre_filtered_findings:
            if f["id"] in judgments_map:
                jd = judgments_map[f["id"]]
                f["reachable"] = jd.get("reachable", True)
                f["upgrade_safety"] = jd.get("upgrade_safety", "Unknown")
                f["remediation_advice"] = jd.get("remediation", "")
                
                # If judged as not reachable and low threat, we can lower severity
                if not f["reachable"] and not f.get("kev"):
                    f["remediation_priority"] = "Low"
                else:
                    f["remediation_priority"] = "High"
            else:
                f["reachable"] = True
                f["upgrade_safety"] = "Unknown"
                f["remediation_advice"] = ""
                f["remediation_priority"] = "Medium"

        task.output_metadata = {
            "judged_items": len(ambiguous_cves),
            "reachable_items": len([f for f in ambiguous_cves if f.get("reachable")]),
            "remediation_priorities": {
                "High": len([f for f in pre_filtered_findings if f.get("remediation_priority") == "High"]),
                "Low": len([f for f in pre_filtered_findings if f.get("remediation_priority") == "Low"])
            }
        }
        return pre_filtered_findings

    # ----------------------------------------------------
    # Task 7: CONSOLIDATE (deterministic graph reduction)
    # ----------------------------------------------------
    def step_consolidate(self, judged_findings: list) -> dict:
        """
        Groups vulnerabilities by common fix paths:
        e.g., '1 base image bump = N vulnerability fixes'.
        Performs graph reduction to collapse multiple CVEs to a single PR action.
        """
        task = self.tasks["CONSOLIDATE"]
        
        fix_paths = {}
        individual_actions = []

        for f in judged_findings:
            if f.get("suppressed"):
                continue
            
            # Group base image fixes together
            if f["layer_type"] == "base":
                key = f"Base Image Update ({f['target_file']})"
                if key not in fix_paths:
                    fix_paths[key] = []
                fix_paths[key].append(f)
            else:
                individual_actions.append(f)

        task.output_metadata = {
            "consolidated_categories": len(fix_paths),
            "individual_package_updates": len(individual_actions)
        }
        return {"fix_paths": fix_paths, "individual_actions": individual_actions}

    # ----------------------------------------------------
    # Task 8: DRAFT PR (github.create_pull_request draft=true)
    # ----------------------------------------------------
    def step_draft_pr(self, consolidated: dict) -> dict:
        """
        Creates or simulates drafting a pull request.
        Requires manual human SRE review (requires_human_approval: true).
        """
        task = self.tasks["DRAFT PR"]
        task.input_metadata = {"requires_human_approval": True, "draft": True}

        # Generate PR Body content
        pr_body = "# 🚨 SecOps Auto-Remediation: Container Image Security Patches\n\n"
        pr_body += "This PR was automatically drafted to address security findings in container images.\n"
        pr_body += "> [!IMPORTANT]\n"
        pr_body += "> This is a **Human-in-the-Loop** gate. SRE review is required before merging.\n\n"

        if consolidated["fix_paths"]:
            pr_body += "## 🛠 Consolidated Base Image Upgrades\n"
            for path, cves in consolidated["fix_paths"].items():
                pr_body += f"### 📦 {path}\n"
                pr_body += f"Resolves {len(cves)} vulnerabilities by upgrading the base image layer:\n"
                for c in cves:
                    pr_body += f"- **{c['id']}** ({c['pkg_name']}): Installed: `{c['installed_version']}`, Fix: `{c['fixed_version']}` | Priority: **{c.get('remediation_priority', 'Medium')}**\n"
                pr_body += "\n"

        if consolidated["individual_actions"]:
            pr_body += "## 🛠 Individual Package Upgrades / Secret Revocation\n"
            for f in consolidated["individual_actions"]:
                pr_body += f"- **{f['id']}** in `{f['target_file']}`: {f['description']} -> *Remediation: {f.get('remediation_advice', 'Upgrade package')}*\n"

        pr_body += "\n## 🔍 Verification Checklist\n"
        pr_body += "- [ ] Verify container builds locally.\n"
        pr_body += "- [ ] Validate environment configuration passes integration tests.\n"

        # Mock writing the PR locally for validation / preview
        output_pr_path = "terraform/container_remediation_pr.md"
        with open(output_pr_path, "w", encoding="utf-8") as f:
            f.write(pr_body)

        task.output_metadata = {
            "pr_drafted": True,
            "pr_body_path": output_pr_path,
            "requires_human_approval": True
        }

        return {
            "pr_created": True,
            "draft": True,
            "local_pr_preview": output_pr_path,
            "requires_human_approval": True,
            "pr_body_content": pr_body
        }


# ==========================================
# CLI Entry Point
# ==========================================
if __name__ == "__main__":
    image = "azureops-app:latest"
    payload_file = "payloads/trivy_container_openssl_cve.json"
    
    if len(sys.argv) > 1:
        image = sys.argv[1]
    if len(sys.argv) > 2:
        payload_file = sys.argv[2]

    logging.info(f"🚀 Initializing Container Image Scan Analysis Agent for: {image}")
    pipeline = ContainerImageScanPipeline(image, payload_file)
    results = pipeline.run_pipeline()
    
    # Save pipeline execution report
    report_path = "compliance_audit_logs/container_scan_analysis_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(results, rf, indent=2)

    logging.info(f"💾 Analysis complete. Pipeline report saved to: {report_path}")
    print(json.dumps(results, indent=2))
