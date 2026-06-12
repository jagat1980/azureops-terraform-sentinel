import azure.functions as func
import logging
import json
import os
import time
import re
from openai import AzureOpenAI
from github import Github

# Initialize the Azure Functions Python V2 Programming Model with Function Authentication Level
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ---------------------------------------------------------------------------
# POLICY ENGINE: Load external remediation policies at cold-start
# ---------------------------------------------------------------------------
_policies_path = os.path.join(os.path.dirname(__file__), "remediation_policies.json")
with open(_policies_path, "r", encoding="utf-8") as f:
    REMEDIATION_POLICIES = json.load(f)
    # Remove the description key (not a policy entry)
    REMEDIATION_POLICIES.pop("_description", None)


def parse_alert_deterministic(req_body: dict) -> dict:
    """
    Attempts to extract incident metadata from various Azure alert schemas
    using pure Python (deterministic parsing). Returns None if the schema
    is completely unrecognized, signaling that LLM cognitive fallback should be used.
    """
    # 1. Common Alert Schema (data.essentials)
    essentials = req_body.get("data", {}).get("essentials")
    if essentials:
        incident_id = essentials.get("alertId", f"INC-{int(time.time())}")
        target_resource = (essentials.get("configurationItems") or ["UnknownAsset"])[0]
        vulnerability = essentials.get("description", "Security Policy Drift Detected")
        
        resource_type = None
        target_ids = essentials.get("alertTargetIDs", [])
        if target_ids:
            parts = target_ids[0].split("/providers/")
            if len(parts) > 1:
                provider_segments = parts[-1].split("/")
                if len(provider_segments) >= 2:
                    resource_type = f"{provider_segments[0]}.{provider_segments[1]}"
                    
        return {
            "incident_id": incident_id,
            "target_resource": target_resource,
            "vulnerability": vulnerability,
            "resource_type": resource_type
        }

    # 2. Legacy / Direct Monitor Alerts (alertContext)
    alert_context = req_body.get("alertContext")
    if alert_context:
        incident_id = alert_context.get("correlationId") or alert_context.get("operationId") or alert_context.get("eventDataId") or f"INC-{int(time.time())}"
        target_resource = "UnknownAsset"
        resource_type = None
        vulnerability = alert_context.get("operationName", "Azure Alert Context Event")

        # Scope-based type resolution
        auth = alert_context.get("authorization")
        if auth and auth.get("scope"):
            scope = auth["scope"]
            target_resource = scope.split("/")[-1]
            parts = scope.split("/providers/")
            if len(parts) > 1:
                resource_type = "/".join(parts[-1].split("/")[:2]).replace("/", ".")

        # Properties-based extraction
        properties = alert_context.get("properties") or {}
        if properties.get("compromisedEntity"):
            target_resource = properties["compromisedEntity"]
        elif alert_context.get("AffectedConfigurationItems"):
            target_resource = alert_context["AffectedConfigurationItems"][0]
            
        # Extra: check properties resourceType / attackedResourceType
        res_type_prop = properties.get("resourceType") or properties.get("attackedResourceType")
        if res_type_prop and "virtual machine" in res_type_prop.lower():
            resource_type = "Microsoft.Compute.virtualMachines"

        # Condition-based extraction
        condition = alert_context.get("condition") or {}
        all_of = condition.get("allOf")
        if all_of and len(all_of) > 0:
            metric_ns = all_of[0].get("metricNamespace")
            if metric_ns:
                resource_type = metric_ns.replace("/", ".")
                
            # Check targetResourceTypes in condition allOf
            target_res_types = all_of[0].get("targetResourceTypes")
            if target_res_types and "microsoft.compute/virtualmachines" in target_res_types.lower():
                resource_type = "Microsoft.Compute.virtualMachines"
                
            target_resource = all_of[0].get("metricName", target_resource)
            vulnerability = f"Metric Threshold Breached: {all_of[0].get('metricName')} {all_of[0].get('operator')} {all_of[0].get('threshold')}"
            
        return {
            "incident_id": incident_id,
            "target_resource": target_resource,
            "vulnerability": vulnerability,
            "resource_type": resource_type
        }

    # 3. Defender for Cloud Alerts (root-level properties/vendorName/productName)
    properties = req_body.get("properties")
    if properties and (req_body.get("type") == "Microsoft.Security/Locations/alerts" or "Defender" in properties.get("productName", "")):
        incident_id = req_body.get("name") or req_body.get("systemAlertId") or f"INC-{int(time.time())}"
        target_resource = properties.get("compromisedEntity", "UnknownAsset")
        vulnerability = properties.get("alertDisplayName") or properties.get("description", "Defender Security Alert")
        
        resource_type = None
        resource_identifiers = properties.get("resourceIdentifiers", [])
        if resource_identifiers:
            res_id = resource_identifiers[0].get("azureResourceId")
            if res_id:
                parts = res_id.lower().split("/providers/")
                if len(parts) > 1:
                    provider_segments = parts[-1].split("/")
                    if len(provider_segments) >= 2:
                        resource_type = f"{provider_segments[0].title()}.{provider_segments[1].title()}"

        return {
            "incident_id": incident_id,
            "target_resource": target_resource,
            "vulnerability": vulnerability,
            "resource_type": resource_type
        }

    return None


# ---------------------------------------------------------------------------
# CONFIG-DRIVEN FILE RESOLVER: Maps a resource type to a Terraform file path
# using the external policy engine config. Returns None if no policy matches.
# ---------------------------------------------------------------------------
def resolve_target_file(resource_type: str, tf_files: list) -> str | None:
    """
    Looks up the resource type in REMEDIATION_POLICIES and finds the matching
    Terraform file from the repository tree. Returns None if no policy exists
    for this resource type (signaling the LLM should locate the file).
    """
    if not resource_type:
        return None

    for provider_key, policy in REMEDIATION_POLICIES.items():
        if provider_key.lower() in resource_type.lower():
            module_prefix = policy["module_path"]
            matches = [f for f in tf_files if f.startswith(module_prefix)]
            if matches:
                return matches[0]
    return None  # Unknown resource type → LLM fallback


# ---------------------------------------------------------------------------
# HCL SYNTAX VALIDATOR: Prevents committing malformed code to Git
# ---------------------------------------------------------------------------
def validate_hcl_syntax(hcl_code: str) -> tuple[bool, str]:
    """
    Performs basic syntax integrity checks on generated HCL code to prevent 
    committing obviously malformed configuration files.
    Returns (is_valid, error_reason).
    """
    if "```" in hcl_code:
        return False, "Code contains markdown ticks (```). Please return ONLY raw HCL code without markdown wrappers."

    stack = []
    pairs = { '}': '{', ']': '[', ')': '(' }
    for char in hcl_code:
        if char in pairs.values():
            stack.append(char)
        elif char in pairs.keys():
            if not stack or stack[-1] != pairs[char]:
                return False, f"Mismatched bracket/brace detected: '{char}' does not match the open brackets."
            stack.pop()
    
    if len(stack) != 0:
        return False, f"Unclosed brackets/braces detected: {stack}. All opened blocks must be closed."

    trimmed = hcl_code.strip()
    if not trimmed or len(trimmed.splitlines()) < 2:
        return False, "Generated code is empty or truncated. Ensure the full file is returned."
        
    return True, "Valid"


@app.route(route="swarm-triage", methods=["POST"])
def swarm_triage(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("🚨 AzureOps Swarm: Ingestion Webhook Event Captured.")

    # 1. Safely Parse Incoming HTTP Request Payload
    try:
        req_body = req.get_json()
    except ValueError:
        logging.error("❌ Failed to parse payload: Invalid JSON data received.")
        return func.HttpResponse("Invalid JSON payload.", status_code=400)

    # -----------------------------------------------------------------
    # NATIVE SAFEGUARD: Handle Azure Event Grid Handshake Verification
    # -----------------------------------------------------------------
    if isinstance(req_body, list) and req_body[0].get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
        validation_code = req_body[0]["data"]["validationCode"]
        logging.info(f"✅ Event Grid Validation Request Handled. Echoing Code: {validation_code}")
        return func.HttpResponse(json.dumps({"validationResponse": validation_code}), mimetype="application/json")

    # -----------------------------------------------------------------
    # PHASE 1: Git Repository Inspection (List available Landing Zone files)
    # -----------------------------------------------------------------
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        repo_path = os.getenv("GITHUB_REPO")
        if not github_token or not repo_path:
            raise ValueError("Missing GITHUB_TOKEN or GITHUB_REPO environment variable.")

        g = Github(github_token)
        repo = g.get_repo(repo_path)
        
        git_tree = repo.get_git_tree("main", recursive=True)
        tf_files = [element.path for element in git_tree.tree if element.path.endswith(".tf")]
        logging.info(f"📂 Git Landing Zone files retrieved: {tf_files}")
    except Exception as e:
        logging.error(f"❌ Phase 1 (Git Inspection) Failed: {str(e)}")
        return func.HttpResponse(f"Git inspection failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 2: Alert Parsing & Targeting (Tiered: Deterministic → Cognitive)
    # -----------------------------------------------------------------
    try:
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai_key = os.getenv("AZURE_OPENAI_KEY")
        openai_deployment = os.getenv("OPENAI_DEPLOYMENT_NAME")
        if not openai_endpoint or not openai_key or not openai_deployment:
            raise ValueError("Missing AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, or OPENAI_DEPLOYMENT_NAME environment variable.")

        ai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-05-01-preview"
        )

        # --- TIER 1: Deterministic fast-path (zero tokens, zero latency) ---
        parsed = parse_alert_deterministic(req_body)
        
        if parsed and parsed["resource_type"]:
            incident_id = parsed["incident_id"]
            target_asset = parsed["target_resource"]
            vulnerability = parsed["vulnerability"]
            resource_type = parsed["resource_type"]
            target_file_path = resolve_target_file(resource_type, tf_files)

            if target_file_path:
                # Fully deterministic path: known schema + known resource type
                triage_mode = "DETERMINISTIC"
                logging.info(f"⚡ Tier 1 Deterministic Triage -> Resource: {resource_type} | File: {target_file_path}")
            else:
                # Known schema but unknown resource type → LLM locates the file only
                triage_mode = "HYBRID"
                logging.info(f"🔀 Tier 1.5 Hybrid Triage -> Resource type '{resource_type}' has no policy. Using LLM for file targeting.")

                file_locate_prompt = f"""
                You are a cloud infrastructure file locator. Given the following repository Terraform files and the Azure resource type, select the single file path that most likely defines or configures this resource.

                Repository Terraform Files:
                {json.dumps(tf_files)}

                Azure Resource Type: {resource_type}
                Target Asset Name: {target_asset}
                Alert Description: {vulnerability}

                CRITICAL GUARDRAIL: The 'target_file_path' value MUST be chosen strictly from the 'Available Terraform Files' array provided above. Do not invent or hallucinate file paths.
                Output ONLY a strict JSON object with a single key 'target_file_path'. If no file clearly matches, choose the most relevant one.
                """
                locate_response = ai_client.chat.completions.create(
                    model=openai_deployment,
                    messages=[{"role": "user", "content": file_locate_prompt}],
                    response_format={"type": "json_object"}
                )
                locate_result = json.loads(locate_response.choices[0].message.content)
                target_file_path = locate_result.get("target_file_path", tf_files[0] if tf_files else "modules/storage/main.tf")
        else:
            # --- TIER 2: Full LLM cognitive fallback (unrecognized schema) ---
            triage_mode = "COGNITIVE"
            logging.info("🧠 Tier 2 Cognitive Fallback -> Unrecognized alert schema. Full LLM triage engaged.")

            triage_prompt = f"""
            You are an advanced cloud security triage engine. Analyze the incoming unparsed cloud alert payload.
            
            Available Terraform Files in the Repository:
            {json.dumps(tf_files)}
            
            Tasks:
            1. Locate any unique correlation identifiers (like alertId, id, trackingId, name). Map to 'incident_id'. If missing, synthesize a unique tracking code.
            2. Locate the compromised or target asset name. Map to 'target_resource'.
            3. Identify the explicit security vulnerability or policy drift. Map to 'vulnerability'.
            4. Select the target file path from the available files list that most likely defines or configures the target resource.
            
            CRITICAL GUARDRAIL: The 'target_file_path' value MUST be chosen strictly from the 'Available Terraform Files' array provided above. Do not invent or hallucinate file paths.
            Output ONLY a strict, flat JSON dictionary with keys: 'incident_id', 'target_resource', 'vulnerability', 'target_file_path'.
            
            Alert Payload:
            {json.dumps(req_body)}
            """
            triage_response = ai_client.chat.completions.create(
                model=openai_deployment,
                messages=[{"role": "user", "content": triage_prompt}],
                response_format={"type": "json_object"}
            )
            normalized = json.loads(triage_response.choices[0].message.content)
            incident_id = normalized.get("incident_id", f"INC-{int(time.time())}")
            target_asset = normalized.get("target_resource", "UnknownAsset")
            vulnerability = normalized.get("vulnerability", "Security Policy Drift Detected")
            
            # Anti-Hallucination: Python-side enforcement of the Enum
            extracted_path = normalized.get("target_file_path")
            if extracted_path in tf_files:
                target_file_path = extracted_path
            else:
                logging.warning(f"⚠️ Hallucination Detected: LLM suggested invalid file path '{extracted_path}'. Falling back to default.")
                target_file_path = tf_files[0] if tf_files else "modules/storage/main.tf"
            
            resource_type = "Unknown"
        
        logging.info(f"🧠 Triage Complete [{triage_mode}] -> ID: {incident_id} | Asset: {target_asset} | File: {target_file_path}")
    except Exception as e:
        logging.error(f"❌ Phase 2 (Triage & Targeting) Failed: {str(e)}")
        return func.HttpResponse(f"Triage processing failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 3: Source File Retrieval (Connect to Git Monorepo context)
    # -----------------------------------------------------------------
    try:
        file_content = repo.get_contents(target_file_path, ref="main")
        raw_tf_code = file_content.decoded_content.decode("utf-8")
        logging.info(f"📂 Git Context Fetched: Successfully read '{target_file_path}' from main branch.")
    except Exception as e:
        logging.error(f"❌ Phase 3 (Git Retrieval) Failed: {str(e)}")
        return func.HttpResponse(f"Git retrieval failure for {target_file_path}: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 4: Generative HCL Patching & Code Validation (Tiered Rules)
    # -----------------------------------------------------------------
    try:
        # Build remediation instructions based on policy tier
        matched_policy = None
        if resource_type and resource_type != "Unknown":
            for provider_key, policy in REMEDIATION_POLICIES.items():
                if provider_key.lower() in resource_type.lower():
                    matched_policy = policy
                    break

        if matched_policy:
            # TIER 1: Specific, focused remediation rules from policy config
            remediation_instructions = matched_policy["remediation_rules"]
            logging.info(f"📋 Using policy-defined remediation rules for {resource_type}.")
        else:
            # TIER 2: Generic remediation — let the LLM reason about the code
            remediation_instructions = f"""Analyze the vulnerability description and the current Terraform code carefully.
            Apply the minimum surgical change needed to mitigate the described security vulnerability or policy drift.
            Common remediation patterns include:
            - Disabling public access or anonymous access
            - Restricting network rules to private IP ranges (e.g. 10.0.0.0/8)
            - Enabling encryption, TLS, or secure authentication methods
            - Removing overly permissive wildcard rules
            Use your expertise to determine the correct fix for this specific resource type and vulnerability."""
            logging.info(f"🤖 No policy match for '{resource_type}'. Using generic LLM-driven remediation reasoning.")

        patch_prompt = f"""
        You are an automated DevSecOps patch engineer specialized in HashiCorp Terraform HCL.
        Vulnerability: {vulnerability}
        Target Vulnerable Asset: {target_asset}
        Target File: {target_file_path}
        
        Review this current Terraform file content:
        ```hcl
        {raw_tf_code}
        ```
        
        Remediation Instructions:
        {remediation_instructions}
        
        General Rules:
        - Do NOT alter any random string resource structures, provider definitions, or resource group scopes.
        - Ensure all original syntax blocks remain fully valid.
        
        Return ONLY the updated raw configuration file text. Do not include markdown ticks (```hcl), explanations, or notes.
        """

        validation_passed = False
        attempts = 0
        corrected_tf_code = ""
        current_prompt = patch_prompt

        while not validation_passed and attempts < 2:
            attempts += 1
            patch_response = ai_client.chat.completions.create(
                model=openai_deployment,
                messages=[{"role": "user", "content": current_prompt}]
            )
            corrected_tf_code = patch_response.choices[0].message.content.strip()
            
            # Clean up markdown code blocks if returned
            if corrected_tf_code.startswith("```"):
                corrected_tf_code = corrected_tf_code.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            
            is_valid, error_msg = validate_hcl_syntax(corrected_tf_code)
            if is_valid:
                validation_passed = True
                logging.info(f"✅ HCL Syntax Validation Passed on Attempt {attempts}.")
            else:
                logging.warning(f"⚠️ HCL Syntax Validation Failed on Attempt {attempts}. Reason: {error_msg}. Retrying self-correction...")
                current_prompt = patch_prompt + f"\n\nCRITICAL ERROR IN PREVIOUS GENERATION: {error_msg}\nEnsure all syntax rules are met and return the FULL valid HCL file."

        if not validation_passed:
            raise ValueError("Generative HCL patch failed syntax validation. Aborting commit to prevent build breaks.")

    except Exception as e:
        logging.error(f"❌ Phase 4 (HCL Patching) Failed: {str(e)}")
        return func.HttpResponse(f"Generative patching failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 5: Cognitive PR Copywriting & Git Branch Commit Pipeline
    # -----------------------------------------------------------------
    try:
        timestamp = int(time.time())
        new_branch = f"secops-swarm-fix-{incident_id.lower().replace(' ', '-')}-{timestamp}"
        # Sanitize branch name: only allow alphanumeric, hyphens, and forward slashes
        new_branch = re.sub(r'[^a-z0-9\-/]', '-', new_branch)
        main_branch = repo.get_git_ref("heads/main")
        
        # 1. Create a dynamic security branch tracking timeline
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=main_branch.object.sha)
        
        # 2. Write and commit the updated HCL block onto the tracking branch
        repo.update_file(
            path=target_file_path,
            message=f"secops(swarm): automatic remediation compliance patch for incident {incident_id}",
            content=corrected_tf_code,
            sha=file_content.sha,
            branch=new_branch
        )

        # 3. Generate structured Markdown description via OpenAI for the Pull Request body
        pr_doc_prompt = f"""
        Write a professional enterprise GitOps Markdown description for a Pull Request resolving the following incident.
        Vulnerability: {vulnerability}
        Target Asset: {target_asset}
        Incident ID Reference: {incident_id}
        Target File: {target_file_path}
        Triage Mode: {triage_mode}
        
        Include sections for: 
        - '#### 🚨 Security Risk Analysis' (Analysis of the threat vector and enterprise risk)
        - '#### 🛠 Automated Remediation Patch' (Specific changes applied to the HCL configuration)
        - '#### 🔍 Peer Validation Guidance' (Steps for SRE review, linting results, and terraform plan checklist)
        
        Highlight that this is a Human-in-the-Loop gate and the changes will only deploy to Azure after approval.
        Keep the tone highly technical and precise for SRE review.
        """
        
        pr_doc_response = ai_client.chat.completions.create(
            model=openai_deployment,
            messages=[{"role": "user", "content": pr_doc_prompt}]
        )
        pr_markdown_body = pr_doc_response.choices[0].message.content

        # 4. Programmatically Open the Pull Request human gate
        # Extract a clean, concise alert description (truncate if too long)
        clean_vuln = vulnerability.replace("[SAMPLE ALERT] ", "").strip()
        # Clean up any potential markdown ticks or double quotes
        clean_vuln = clean_vuln.replace("`", "").replace('"', "")
        if len(clean_vuln) > 60:
            clean_vuln = clean_vuln[:57] + "..."
            
        # Shorten GUID for human readability in PR title (similar to a Git commit hash)
        short_id = incident_id.split("/")[-1].split("-")[0].upper() if "-" in incident_id else incident_id.upper()

        pr = repo.create_pull(
            title=f"🚨 SecOps Auto-Fix [{short_id}]: {clean_vuln} on {target_asset}",
            body=pr_markdown_body,
            head=new_branch,
            base="main"
        )

        logging.info(f"🚀 Success: Gateway Pull Request Opened -> {pr.html_url}")
        return func.HttpResponse(
            body=json.dumps({
                "status": "PR_CREATED",
                "url": pr.html_url,
                "incident_id": incident_id,
                "file_patched": target_file_path,
                "triage_mode": triage_mode
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"❌ Phase 5 (Git Execution) Failed: {str(e)}")
        return func.HttpResponse(f"Git branch execution barrier error: {str(e)}", status_code=500)