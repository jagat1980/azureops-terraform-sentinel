# App Service Plan (Free F1 Tier for Demo)
resource "azurerm_service_plan" "app_plan" {
  name                   = "asp-drift-test"
  resource_group_name    = var.resource_group_name
  location               = var.location
  os_type                = "Linux"
  sku_name               = "P1v3"
  worker_count           = 3
  zone_balancing_enabled = true
}

resource "azurerm_linux_web_app" "vulnerable_app" {
  # checkov:skip=CKV_AZURE_88: Azure Files mounting is intentionally omitted because this stateless app fixture has no file-share dependency.
  name                = "app-drift-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.app_plan.id

  https_only                                     = true
  public_network_access_enabled                  = false
  client_certificate_enabled                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                         = true
    health_check_path                 = "/health"
    health_check_eviction_time_in_min = 2
    http2_enabled                     = true
    ftps_state                        = "Disabled"
    minimum_tls_version               = "1.2"
    scm_minimum_tls_version           = "1.2"

    application_stack {
      python_version = "3.9"
    }
  }

  auth_settings {
    enabled                       = true
    default_provider              = "AzureActiveDirectory"
    issuer                        = var.azuread_issuer_url
    unauthenticated_client_action = "RedirectToLoginPage"

    active_directory {
      client_id = var.azuread_client_id
    }
  }

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  tags = {
    ComplianceRisk = "WebApp-Secure-Baseline"
  }
}
