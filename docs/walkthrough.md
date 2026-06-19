# Execution Walkthrough: Workspace Reorganization & Test Modularization

We have successfully restructured the `azureops-test-harness` workspace to separate concerns and establish a clean, industry-standard project layout. Each alert scenario has been moved into its own test file, and all infrastructure configurations have been relocated.

---

## 🛠️ New Workspace Layout

The repository has been restructured as follows:

```
azureops-test-harness/
├── .github/
│   └── workflows/
│       └── terraform.yml                  # Updated CI/CD Pipeline (targets ./terraform)
│
├── azureops-brain/                        # Azure Function App (Remediation Logic)
│   ├── sample_payloads/                   # Moved sample JSON alerts here
│   │   ├── Activity_log_Administrative_Sample_Alert.json
│   │   └── ...
│   ├── function_app.py
│   ├── host.json
│   ├── local.settings.json
│   ├── remediation_policies.json
│   └── requirements.txt
│
├── terraform/                             # Relocated Infrastructure Code
│   ├── modules/                           # Submodules (compute, database, network, storage)
│   ├── main.tf
│   ├── providers.tf
│   └── variables.tf
│
├── tests/                                 # Modular Test Harness
│   ├── config.py                          # Env loader, targets, & requests helper
│   ├── test_storage_activity_log.py       # Activity Log Alert (Sev3)
│   ├── test_storage_metric.py             # Transactions Metric Alert (Sev2)
│   ├── test_storage_service_health.py     # Service Health Alert (Sev1)
│   ├── test_storage_log_analytics.py      # Diagnostic Log Alert (Sev2)
│   ├── test_vm_cpu.py                     # VM CPU Threshold Alert (Sev2)
│   ├── test_storage_defender.py           # Defender Storage Alert (Sev0)
│   ├── test_nsg_exposure.py               # NSG Public Ports Alert (Sev1)
│   ├── test_sql_firewall.py               # SQL Firewall Rule Alert (Sev1)
│   └── run_all.py                         # Master sequential test runner
│
├── docs/                                  # Organized Documentation
│   ├── architecture/                      # Architectural presentations & specs
│   │   ├── azureops_gitops_architecture.md
│   │   └── ...
│   ├── deployment_guide.md
│   ├── solution.md
│   └── solution_review_and_hackathon_guide.md
│
├── keys/                                  # Deployment keys & metadata
├── .env                                   # Sourced credentials
├── .gitignore
└── test_all_payloads.py                   # Backward-compatible wrapper delegating to tests/run_all.py
```

---

## 🧪 Verification & Results

### 1. Local Terraform Initialization & Validation
We verified that running Terraform from the new `./terraform` directory works perfectly against the remote state backend:
* **Command**: `cd terraform; terraform init` and `terraform plan`
* **Output**: Successfully retrieved the remote state from Azure Blob Storage (`stdriftholt8j`).

### 2. Test Execution
We verified that both running the new modular tests and invoking the backward-compatibility wrapper succeed against the local Azure Function App:
* **Modular Runner**: `python tests/run_all.py`
* **Wrapper Runner**: `python test_all_payloads.py` (properly routes calls to the modular suite)
* **Log Output**:
```
[*] Running all modular tests against target triage endpoint: http://localhost:7071/api/swarm-triage

Executing: 1. Azure Monitor Activity Log Alert (Storage) ... -> Status Code: 200
Executing: 2. Azure Monitor Metric Alert (Storage) ... -> Status Code: 200
Executing: 3. Service Health Alert (Storage) ... -> Status Code: 200
Executing: 4. Log Analytics/Diagnostic Logging Alert (Storage) ... -> Status Code: 200
Executing: 5. CPU Threshold Alert (Compute/VM) ... -> Status Code: 200
Executing: 6. Microsoft Defender for Cloud Security Alert (Storage) ... -> Status Code: 200
Executing: 7. Network Security Group Public Port Rule Alert (Network) ... -> Status Code: 200
Executing: 8. SQL Server Firewall Open Alert (Database) ... -> Status Code: 200

=== Test Execution Summary ===
1. Azure Monitor Activity Log Alert (Storage) -> Status Code: 200
2. Azure Monitor Metric Alert (Storage) -> Status Code: 200
3. Service Health Alert (Storage) -> Status Code: 200
4. Log Analytics/Diagnostic Logging Alert (Storage) -> Status Code: 200
5. CPU Threshold Alert (Compute/VM) -> Status Code: 200
6. Microsoft Defender for Cloud Security Alert (Storage) -> Status Code: 200
7. Network Security Group Public Port Rule Alert (Network) -> Status Code: 200
8. SQL Server Firewall Open Alert (Database) -> Status Code: 200
```

### 3. CI/CD GitHub Actions Pipeline Validation
We created [Pull Request #92](https://github.com/jagat1980/azureops-terraform-sentinel/pull/92) to verify the modified `.github/workflows/terraform.yml` CI/CD pipeline:
* The pipeline initialized the `defaults.run.working-directory: ./terraform` setting correctly.
* The workflow run **`27562810865`** completed with a status of **`success`**, confirming syntax checks, formatting checks, and execution planning are fully operational with the new structure.

### 4. Renamed "Azure Sentinel" / "AzureOps Sentinel" to "CloudSecAIOps"
* **Solution Review & Hackathon Guide**: Renamed Microsoft "Azure Sentinel" to "CloudSecAIOps" (Line 89).
* **Architecture Specs**: Renamed project/engine name "AzureOps Sentinel" to "CloudSecAIOps" (Lines 1 & 4 of `docs/architecture/azureops_gitops_architecture.md`).
* **PPTX Slide Generator**: Renamed presentation title "AZUREOPS SENTINEL" to "CLOUDSECAIOPS" in `docs/architecture/generate_pptx.py`.
* **PowerPoint Presentation**: Re-executed `generate_pptx.py` to compile slide adjustments into `docs/architecture/azureops_gitops_architecture.pptx`.
* **GitHub Actions Run**: Triggered and verified successful completion of workflow run **`27563116288`** after push.

### 5. Production Environment Deployment (CloudSecAIOps-Prod)
We created a separate Terraform workspace `terraform-prod/` to deploy the remediation engine to production:
* **Resource Group**: Created `CloudSecAIOps-Prod` in region `centralindia`.
* **Storage Account**: Created standard LRS storage account for Function App package requirements.
* **App Service Plan**: Created a consumption plan (`Y1`).
* **Azure Key Vault**: Created `kv-cloudsecaiops-clq94w` to securely store `GITHUB_TOKEN` and `AZURE_OPENAI_KEY` as Key Vault Secrets.
* **Managed Identity**: Enabled a **System-Assigned Managed Identity** on the Linux Function App, granting it `Get` secret permissions in Key Vault. App Settings reference Key Vault secrets dynamically via `@Microsoft.KeyVault(...)` syntax.
* **Event Grid Integration**: Created an Event Grid System Topic (`egst-cloudsecaiops-prod`) in `rg-azureops-drift-test` matching the source scope. Created an Event Subscription (`egsub-cloudsecaiops-prod`) pointing to the Function App webhook endpoint including the auto-extracted host key.
* **Verification**: Run `python tests/run_all.py` against the production function endpoint. All 8 tests completed with **`Status Code 200`** and created PRs #94 to #101 on GitHub, validating Key Vault secrets resolution and end-to-end telemetry routing.
