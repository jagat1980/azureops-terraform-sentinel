# Retrieve client config for deployer identity
data "azurerm_client_config" "current" {}

# Random suffix for unique naming
resource "random_string" "unique" {
  length  = 6
  special = false
  upper   = false
}

# 1. Resource Group
resource "azurerm_resource_group" "prod" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Environment = "Production"
    Project     = "CloudSecAIOps"
    ManagedBy   = "Terraform"
  }
}

# 2. Function App Storage Account
resource "azurerm_storage_account" "func_store" {
  name                     = "stcloudsecaiops${random_string.unique.result}"
  resource_group_name      = azurerm_resource_group.prod.name
  location                 = azurerm_resource_group.prod.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 3. App Service Plan (Consumption Plan)
resource "azurerm_service_plan" "func_plan" {
  name                = "asp-cloudsecaiops-prod"
  resource_group_name = azurerm_resource_group.prod.name
  location            = azurerm_resource_group.prod.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# 4. Azure Key Vault
resource "azurerm_key_vault" "kv" {
  name                        = "kv-cloudsecaiops-${random_string.unique.result}"
  location                    = azurerm_resource_group.prod.location
  resource_group_name         = azurerm_resource_group.prod.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"
}

# 5. Access Policy for Deployer (to write secrets)
resource "azurerm_key_vault_access_policy" "deployer_access" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# 6. Key Vault Secrets
resource "azurerm_key_vault_secret" "github_token" {
  name         = "github-token"
  value        = var.GITHUB_TOKEN
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.deployer_access]
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "azure-openai-key"
  value        = var.AZURE_OPENAI_KEY
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.deployer_access]
}

# 7. Linux Function App (secured with SystemAssigned Managed Identity)
resource "azurerm_linux_function_app" "triage_func" {
  name                = "func-cloudsecaiops-prod-${random_string.unique.result}"
  resource_group_name = azurerm_resource_group.prod.name
  location            = azurerm_resource_group.prod.location

  storage_account_name       = azurerm_storage_account.func_store.name
  storage_account_access_key = azurerm_storage_account.func_store.primary_access_key
  service_plan_id            = azurerm_service_plan.func_plan.id

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    GITHUB_REPO              = var.GITHUB_REPO
    AZURE_OPENAI_ENDPOINT    = var.AZURE_OPENAI_ENDPOINT
    OPENAI_DEPLOYMENT_NAME   = var.OPENAI_DEPLOYMENT_NAME
    
    # Key Vault references for sensitive settings
    GITHUB_TOKEN             = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.github_token.id})"
    AZURE_OPENAI_KEY         = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_key.id})"
  }
}

# 8. Access Policy for Function App Managed Identity (to read secrets)
resource "azurerm_key_vault_access_policy" "func_access" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.triage_func.identity[0].principal_id

  secret_permissions = [
    "Get",
  ]
}

# 9. Host Keys Data Source (to extract webhook code)
data "azurerm_function_app_host_keys" "keys" {
  name                = azurerm_linux_function_app.triage_func.name
  resource_group_name = azurerm_linux_function_app.triage_func.resource_group_name
  depends_on          = [azurerm_linux_function_app.triage_func]
}

# 10. Event Grid System Topic for rg-azureops-drift-test Resource Group
resource "azurerm_eventgrid_system_topic" "sys_topic" {
  name                   = "egst-cloudsecaiops-prod"
  resource_group_name    = "rg-azureops-drift-test"
  location               = "global" # Control plane events are global
  source_resource_id     = "/subscriptions/${var.subscription_id}/resourceGroups/rg-azureops-drift-test"
  topic_type             = "Microsoft.Resources.ResourceGroups"
}

# 11. Event Grid Subscription routing to Function Webhook
resource "azurerm_eventgrid_system_topic_event_subscription" "event_sub" {
  name                = "egsub-cloudsecaiops-prod"
  resource_group_name = "rg-azureops-drift-test"
  system_topic        = azurerm_eventgrid_system_topic.sys_topic.name

  webhook_endpoint {
    url = "https://${azurerm_linux_function_app.triage_func.default_hostname}/api/swarm-triage?code=${data.azurerm_function_app_host_keys.keys.default_function_key}"
  }
}
