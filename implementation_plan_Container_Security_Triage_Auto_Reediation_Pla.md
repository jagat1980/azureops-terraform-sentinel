# Static & Dynamic Container Security Triage and Auto-Remediation Plan

This updated plan incorporates testing and auto-remediation for **static analyses** (container image vulnerability scans at rest/imaging) and **dynamic analyses** (runtime container anomalies and insecure configurations).

## Architectural Recommendations

### 1. Static Analysis (Imaging & Build Level)
* **Shift-Left Image Scanning**: Integrate image vulnerability scanners (e.g., Trivy, Grype, or Azure Defender for Containers) directly into the CI build pipeline.
* **Auto-Remediation Pattern**: When a static scan alert occurs, have the GitOps engine query the registry vulnerability report, identify out-of-date base images, and automatically propose a PR updating the base image reference (e.g., pinning a newer, patched tag in the Dockerfile or Terraform container definition).
* **Infrastructure Lockdown**: Restrict public network endpoints of registries (`azurerm_container_registry`) and enforce private link/IP restrictions to prevent untrusted image pulling.

### 2. Dynamic Analysis (Runtime & Execution Level)
* **Enforced Least Privilege**: Enforce container runtime security policies in Terraform using strict `security_profile` blocks (e.g. setting read-only root filesystems, blocking privilege escalation, and running as non-root).
* **Automated Threat Isolation**: Configure Event Grid to listen for runtime threat detection alerts (e.g., suspicious process spawning like `curl` inside a prod container, network scanning, or container breakouts).
* **Dynamic Remediation**: Define automated workflows to temporarily isolate the compromised container instance using updated network security rules (e.g. blocking egress/ingress) or terminating/re-spinning the container instance.

### 3. Open Policy Agent (OPA) & Industry Standards
* **OPA / Conftest Validation**: Integrate **OPA (Open Policy Agent)** or **Conftest** policies in the CI/CD pull request gate. Before code is merged, convert the Terraform plan to JSON (`terraform show -json tfplan`) and evaluate it against Rego policy definitions to verify that:
  - Containers are not configured to run as root (`run_as_non_root = true`).
  - Read-only root filesystem is enforced.
  - Public container registries are disallowed.
* **Industry Standards Alignment**:
  * **CIS Docker/Kubernetes Benchmarks**: Ensure all host, runtime, and network isolation configurations align with CIS compliance benchmarks.
  * **NIST SP 800-190 (Application Container Security Guide)**: Address the 5 core risk areas (Image, Registry, Orchestrator, Container, and Host OS) by ensuring image signing/trust is enforced and host access is minimized.

---

## Proposed Changes

### Infrastructure Configuration

#### [NEW] [main.tf](file:///c:/myailearn/projects/azureops-test-harness/modules/container/main.tf)
Create a new Terraform module representing:
1. **Static/Registry level**: An `azurerm_container_registry` with insecure access settings (representing vulnerable image storage).
2. **Dynamic/Runtime level**: An `azurerm_container_group` (Azure Container Instances) running a container with privileged mode or root-like execution configurations.

#### [MODIFY] [main.tf](file:///c:/myailearn/projects/azureops-test-harness/main.tf)
Register the new container module in the root orchestrator.

---

### Policy Engine Configuration

#### [MODIFY] [remediation_policies.json](file:///c:/myailearn/projects/azureops-test-harness/azureops-brain/remediation_policies.json)
Define specific remediation targets for container-related resources:
1. **Microsoft.ContainerRegistry**: Static scan remediation rules (e.g., locking down public access).
2. **Microsoft.ContainerInstance/containerGroups**: Dynamic/runtime container compliance rules (e.g., disabling privileged mode, setting read-only root filesystems, or enforcing resource limits).

---

### Test Simulation

#### [MODIFY] [test_all_payloads.py](file:///c:/myailearn/projects/azureops-test-harness/test_all_payloads.py)
Introduce new mock telemetry alerts covering:
1. **Static Analysis Alert (Imaging)**: An alert indicating that a vulnerability (e.g., critical CVE) was detected in a container image stored in the registry.
2. **Dynamic Analysis Alert (Runtime)**: An alert indicating anomalous runtime activity or insecure dynamic configuration (e.g., container running with full capabilities/privileged access).

---

## Verification Plan

### Manual Verification
1. Start the function app locally:
   ```powershell
   cd c:\myailearn\projects\azureops-test-harness\azureops-brain
   func start
   ```
2. Execute the updated simulation test runner:
   ```powershell
   python c:\myailearn\projects\azureops-test-harness\test_all_payloads.py
   ```
3. Verify that:
   - The static image registry vulnerability alert is triaged correctly and remediates public exposures.
   - The dynamic container runtime vulnerability alert triggers the policy engine to remediate runtime-level settings (e.g., disabling privileged mode).
