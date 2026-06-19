# App Service Plan (Free F1 Tier for Demo)
resource "azurerm_service_plan" "app_plan" {
  name                = "asp-drift-test"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "F1"
}

# Vulnerable Web App
resource "azurerm_linux_web_app" "vulnerable_app" {
  name                = "app-drift-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.app_plan.id

  # Missing HTTPS Only (DAST/SAST test point)
  https_only = false

  site_config {
    always_on = false
    application_stack {
      python_version = "3.9"
    }
  }

  tags = {
    ComplianceRisk = "Vulnerable-App-Demo"
  }
}
