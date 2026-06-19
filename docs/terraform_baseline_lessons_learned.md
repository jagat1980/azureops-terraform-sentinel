# Terraform Baseline Lessons Learned

## Incident

A container vulnerability remediation branch was blocked by unrelated Terraform baseline findings. The original security issue was the OpenSSL container alert for `CVE-2023-75689`, but the validation gate also ran `checkov -d terraform` and failed on pre-existing Azure infrastructure drift fixtures.

## What Happened

The Terraform modules intentionally modeled insecure drift scenarios for storage, network, compute, SQL, container, and App Service resources. Once Checkov was installed and executed across the full `terraform/` directory, these unrelated baseline findings obscured the container remediation signal.

Initial baseline result:

```text
checkov -d terraform
failed: 47
```

Final baseline result:

```text
checkov -d terraform --quiet --output json
passed: 68
failed: 0
skipped: 6
parsing_errors: 0
```

Terraform validation result:

```text
terraform -chdir=terraform validate
Success! The configuration is valid.
```

## Root Cause

The repository mixed two concerns in one validation path:

- Container image vulnerability remediation.
- Terraform drift simulation fixtures with intentionally insecure Azure defaults.

Because the CI-style validation scanned the whole Terraform tree, unrelated baseline debt caused the remediation workflow to appear incomplete even after the container fix was applied.

## Remediation Pattern

The fix was to make the Terraform baseline secure enough for the shared validation gate while preserving the harness intent.

Applied changes included:

- Network: associated the NSG at the subnet level and exposed the subnet ID for private endpoints.
- Compute: disabled VM extension operations.
- Container: disabled ACR admin access, disabled public registry access, enabled retention, quarantine, trust policy, zone redundancy, private networking, and ACI managed identity.
- SQL: disabled public network access, enforced TLS 1.2, enabled Entra administrator configuration, managed identity, auditing, express vulnerability assessment, and private endpoint access.
- Storage: disabled public network access, disabled shared keys, enabled OAuth default auth, TLS 1.2, HTTPS-only, soft delete, versioning, change feed, SAS expiration, queue logging, GRS replication, and private endpoint access.
- Web App: moved from free tier to production-capable plan, enabled HTTPS-only, managed identity, authentication, logs, health check, HTTP/2, TLS 1.2, disabled FTP/basic publishing, disabled public network access, and required client certificates.

## Exception Policy

Checkov skips are acceptable only when all of the following are true:

- The control requires environment-specific resources or secrets outside the test harness.
- The resource has already been hardened as far as possible without that external dependency.
- The skip is placed inside the Terraform resource block.
- The skip includes a specific rationale.
- The skip count is reported in validation output.

Documented skips in this remediation covered:

- Customer-managed key ownership requiring Key Vault lifecycle and key governance.
- Storage-backed SQL vulnerability assessment requiring external storage and secrets.
- SQL local admin retained for isolated break-glass test harness access while Entra admin is configured.
- Azure Files mounting omitted for a stateless App Service fixture.
- Blob diagnostic logging destination outside the compact fixture.
- ACI managed identity and virtual network behavior documented for the fixture.

## Validation Guidance

Run both checks before asking for review:

```powershell
terraform fmt -recursive terraform
terraform -chdir=terraform validate
$env:PATH='C:\tmp\checkov-bin;' + $env:PATH
checkov -d terraform --quiet --output json
```

Treat `failed: 0` as the required gate. Treat skips as audit items, not hidden passes.

## Prevention

Future remediation branches should separate vulnerability-specific validation from repository baseline validation. If the full baseline gate is required, fix or document unrelated findings before opening the PR so reviewers can focus on the actual alert.

When a harness intentionally includes vulnerable fixtures, keep them in a dedicated path or mark them with explicit scanner configuration. Do not allow intentionally insecure examples to share the same required gate as production-ready Terraform.
