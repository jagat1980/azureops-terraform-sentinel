terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# Explicitly defining the mandatory features block in the same file
provider "azurerm" {
  features {}
}

# 1. Random ID Generation
resource "random_string" "unique_id" {
  length  = 6
  special = false
  upper   = false
}

# 2. Resource Group Creation (Central India)
resource "azurerm_resource_group" "drift_test" {
  name     = "rg-azureops-drift-test"
  location = "centralindia"
  tags = {
    Environment = "Harness-Testing"
    ManagedBy   = "Terraform"
    SecurityLog = "Drift-Simulation"
  }
}

# 3. Storage Account with Explicit Public Opt-In Disabled
resource "azurerm_storage_account" "vulnerable_storage" {
  name                     = "stdrift${random_string.unique_id.result}"
  resource_group_name      = azurerm_resource_group.drift_test.name
  location                 = azurerm_resource_group.drift_test.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # Security fix: Prevent nested child assets from being public
  allow_nested_items_to_be_public = false

  min_tls_version            = "TLS1_2"
  https_traffic_only_enabled = true

  tags = {
    ComplianceRisk = "Intentional-Drift"
  }
}

# 4. Private Access Container
resource "azurerm_storage_container" "anonymous_container" {
  name               = "azure-webjobs-hosts"
  storage_account_id = azurerm_storage_account.vulnerable_storage.id

  # Security fix: Disable anonymous public access
  container_access_type = "private"
}