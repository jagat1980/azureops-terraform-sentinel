import azure.functions as func
import logging
import json
import os
from openai import AzureOpenAI
from github import Github

# Initialize the Azure Functions Python V2 Programming Model
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

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
    # PHASE 1: Cognitive Triage (Normalize polymorphic alert schemas)
    # -----------------------------------------------------------------
    try:
        ai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-05-01-preview"
        )

        triage_prompt = f"""
        You are an advanced cloud security triage engine. Analyze the incoming unparsed Azure cloud alert payload.
        Locate any unique correlation identifiers (like alertId, id, trackingId, name). Map that value to 'incident_id'. If missing, synthesize a unique tracking code.
        Locate the compromised or target asset name and map it to 'target_resource'.
        Identify the explicit security vulnerability or policy drift and map it to 'vulnerability'.
        
        Output ONLY a strict, flat JSON dictionary containing these exact keys: 'incident_id', 'target_resource', 'vulnerability'.
        
        Alert Payload:
        {json.dumps(req_body)}
        """

        triage_response = ai_client.chat.completions.create(
            model=os.getenv("OPENAI_DEPLOYMENT_NAME"),
            messages=[{"role": "user", "content": triage_prompt}],
            response_format={"type": "json_object"}
        )
        
        normalized_alert = json.loads(triage_response.choices[0].message.content)
        incident_id = normalized_alert.get("incident_id", "INC-GENERIC")
        target_asset = normalized_alert.get("target_resource", "UnknownAsset")
        vulnerability = normalized_alert.get("vulnerability", "Security Policy Drift Detected")
        
        logging.info(f"🧠 AI Normalized Event -> ID: {incident_id} | Asset: {target_asset}")
    except Exception as e:
        logging.error(f"❌ Phase 1 (Triage) Failed: {str(e)}")
        return func.HttpResponse(f"Triage processing failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 2: Source File Retrieval (Connect to Git Monorepo context)
    # -----------------------------------------------------------------
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        # Fetches dynamically from your App Settings env variables (e.g., "your-username/azureops-test-harness")
        repo_path = os.getenv("GITHUB_REPO") 
        repo = g.get_repo(repo_path) 
        
        target_file_path = "modules/storage/main.tf"
        file_content = repo.get_contents(target_file_path, ref="main")
        raw_tf_code = file_content.decoded_content.decode("utf-8")
        logging.info(f"📂 Git Context Fetched: Successfully read '{target_file_path}' from repository branch 'main'.")
    except Exception as e:
        logging.error(f"❌ Phase 2 (Git Connection) Failed: {str(e)}")
        return func.HttpResponse(f"Git retrieval failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 3: Generative HCL Patching (Surgically adjust state)
    # -----------------------------------------------------------------
    try:
        patch_prompt = f"""
        You are an automated DevSecOps patch engineer specialized in HashiCorp Terraform HCL.
        Vulnerability Metric: {vulnerability}
        Target Vulnerable Asset: {target_asset}
        
        Review this current Terraform file content:
        ```hcl
        {raw_tf_code}
        ```
        
        Surgically rewrite this code to mitigate the vulnerability. 
        - Fix container_access_type properties to ensure they are explicitly set to "private".
        - Do NOT alter any random string resource structures, provider definitions, or resource group scopes.
        - Ensure all original syntax blocks remain fully valid.
        
        Return ONLY the updated raw configuration file text. Do not include markdown ticks (```hcl), explanations, or notes.
        """

        patch_response = ai_client.chat.completions.create(
            model=os.getenv("OPENAI_DEPLOYMENT_NAME"),
            messages=[{"role": "user", "content": patch_prompt}]
        )
        corrected_tf_code = patch_response.choices[0].message.content.strip()
        
        # Clean up any accidental markdown wrappers if returned by the LLM
        if corrected_tf_code.startswith("```"):
            corrected_tf_code = corrected_tf_code.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    except Exception as e:
        logging.error(f"❌ Phase 3 (HCL Patching) Failed: {str(e)}")
        return func.HttpResponse(f"Generative patching failure: {str(e)}", status_code=500)

    # -----------------------------------------------------------------
    # PHASE 4: Cognitive PR Copywriting & Git Branch Commit Pipeline
    # -----------------------------------------------------------------
    try:
        new_branch = f"secops-swarm-fix-{incident_id.lower().replace(' ', '-')}"
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
        
        Include sections for: '#### 🚨 Security Risk Analysis', '#### 🛠 Automated Remediation Patch', and '#### 🔍 Peer Validation Guidance'.
        Keep the tone highly technical and precise for SRE review.
        """
        
        pr_doc_response = ai_client.chat.completions.create(
            model=os.getenv("OPENAI_DEPLOYMENT_NAME"),
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
            body=json.dumps({"status": "PR_CREATED", "url": pr.html_url, "incident_id": incident_id}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"❌ Phase 4 (Git Execution) Failed: {str(e)}")
        return func.HttpResponse(f"Git branch execution barrier error: {str(e)}", status_code=500)