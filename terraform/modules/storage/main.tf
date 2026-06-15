terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}


variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "unique_suffix" {
  type = string
}

# 1. Storage Account with Explicit Public Opt-In Enabled
resource "azurerm_storage_account" "vulnerable_storage" {
  name                     = "stdrift${var.unique_suffix}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # DRIFT PROFILE: Allows nested child assets to bypass private settings
  allow_nested_items_to_be_public = false
  
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true

  tags = {
    ComplianceRisk = "Intentional-Drift"
  }
}

# 4. Public Anonymous Access Container
resource "azurerm_storage_container" "anonymous_container" {
  name               = "azure-webjobs-hosts"
  storage_account_id = azurerm_storage_account.vulnerable_storage.id
  
  # DRIFT PROFILE: Exposes full listing access anonymously to the internet
  container_access_type = "private"
}