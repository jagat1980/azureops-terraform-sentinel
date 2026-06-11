import azure.functions as func
import logging
import json
import os
import time
from openai import AzureOpenAI
from github import Github

# Initialize the Azure Functions Python V2 Programming Model with Function Authentication Level
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def validate_hcl_syntax(hcl_code: str) -> bool:
    """
    Performs basic syntax integrity checks on generated HCL code to prevent 
    committing obviously malformed configuration files.
    """
    # 1. Balance check for braces {}, brackets [], and parentheses ()
    stack = []
    pairs = { '}': '{', ']': '[', ')': '(' }
    for char in hcl_code:
        if char in pairs.values():
            stack.append(char)
        elif char in pairs.keys():
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
    
    if len(stack) != 0:
        return False

    # 2. Check for empty or obviously truncated output
    trimmed = hcl_code.strip()
    if not trimmed or len(trimmed.splitlines()) < 2:
        return False
        
    return True

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
    # Event Grid sends an array for verification. CloudEvents sends standard headers.
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
        
        # Query the repository git tree recursively to locate all Terraform files
        git_tree = repo.get_git_tree("main", recursive=True)
        tf_files = [element.path for element in git_tree.tree if element.path.endswith(".tf")]
        logging.info(f"📂 Git Landing Zone files retrieved: {tf_files}")
    except Exception as e:
        logging.error(f"❌ Phase 1 (Git Inspection) Failed: {str(e)}")
        return func.HttpResponse(f"Git inspection failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 2: Cognitive Triage & Targeting (Normalize alerts & locate target file)
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

        triage_prompt = f"""
        You are an advanced cloud security triage engine. Analyze the incoming unparsed Azure cloud alert payload.
        
        Available Terraform Files in the Repository:
        {json.dumps(tf_files)}
        
        Tasks:
        1. Locate any unique correlation identifiers (like alertId, id, trackingId, name). Map that value to 'incident_id'. If missing, synthesize a unique tracking code.
        2. Locate the compromised or target asset name and map it to 'target_resource'.
        3. Identify the explicit security vulnerability or policy drift and map it to 'vulnerability'.
        4. Select the target file path from the 'Available Terraform Files in the Repository' list that defines the target resource or configuration block.
           - For storage accounts/containers, look for files in modules/storage/
           - For compute/VM resources, look for files in modules/compute/
           - For networks/NSGs/firewalls, look for files in modules/network/
           - For SQL database/firewall resources, look for files in modules/database/
           If no file matches or if you are unsure, default to 'modules/storage/main.tf'.
        
        Output ONLY a strict, flat JSON dictionary containing these exact keys: 'incident_id', 'target_resource', 'vulnerability', 'target_file_path'.
        
        Alert Payload:
        {json.dumps(req_body)}
        """

        triage_response = ai_client.chat.completions.create(
            model=openai_deployment,
            messages=[{"role": "user", "content": triage_prompt}],
            response_format={"type": "json_object"}
        )
        
        normalized_alert = json.loads(triage_response.choices[0].message.content)
        incident_id = normalized_alert.get("incident_id", "INC-GENERIC")
        target_asset = normalized_alert.get("target_resource", "UnknownAsset")
        vulnerability = normalized_alert.get("vulnerability", "Security Policy Drift Detected")
        target_file_path = normalized_alert.get("target_file_path", "modules/storage/main.tf")
        
        logging.info(f"🧠 AI Normalized Event -> ID: {incident_id} | Asset: {target_asset} | File Path: {target_file_path}")
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
    # PHASE 4: Generative HCL Patching & Code Validation
    # -----------------------------------------------------------------
    try:
        patch_prompt = f"""
        You are an automated DevSecOps patch engineer specialized in HashiCorp Terraform HCL.
        Vulnerability Metric: {vulnerability}
        Target Vulnerable Asset: {target_asset}
        Target File: {target_file_path}
        
        Review this current Terraform file content:
        ```hcl
        {raw_tf_code}
        ```
        
        Surgically rewrite this code to mitigate the security vulnerability / policy drift:
        - For storage containers: Ensure container_access_type is explicitly set to "private" and allow_nested_items_to_be_public is set to false.
        - For network security groups (NSG) exposing ports 22 (SSH) or 3389 (RDP) publicly: Restrict access by changing access = "Deny" or narrowing source_address_prefix to a secure corporate network block (e.g. "10.0.0.0/8").
        - For compute resources (Virtual Machines) exposing password auth: Set disable_password_authentication = true.
        - For databases with open firewall rules: Narrow start_ip_address and end_ip_address to secure corporate network blocks (e.g. "10.0.0.0" to "10.255.255.255").
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
            
            if validate_hcl_syntax(corrected_tf_code):
                validation_passed = True
                logging.info(f"✅ HCL Syntax Validation Passed on Attempt {attempts}.")
            else:
                logging.warning(f"⚠️ HCL Syntax Validation Failed on Attempt {attempts}. Retrying self-correction...")
                current_prompt = patch_prompt + "\n\nCRITICAL: The previous generation failed basic brace-balancing checks. Ensure all braces '{' and '}' are properly matching, closed, and valid HCL."

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
        pr = repo.create_pull(
            title=f"🚨 SecOps Auto-Fix [{incident_id.upper()}]: Remediate Drift on {target_asset}",
            body=pr_markdown_body,
            head=new_branch,
            base="main"
        )

        logging.info(f"🚀 Success: Gateway Pull Request Opened -> {pr.html_url}")
        return func.HttpResponse(
            body=json.dumps({"status": "PR_CREATED", "url": pr.html_url, "incident_id": incident_id, "file_patched": target_file_path}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"❌ Phase 5 (Git Execution) Failed: {str(e)}")
        return func.HttpResponse(f"Git branch execution barrier error: {str(e)}", status_code=500)