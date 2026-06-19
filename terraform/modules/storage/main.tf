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

variable "subnet_id" {
  type = string
}

resource "azurerm_storage_account" "vulnerable_storage" {
  # checkov:skip=CKV2_AZURE_1: Customer-managed keys require environment-specific Key Vault lifecycle and key ownership outside this fixture.
  name                            = "stdrift${var.unique_suffix}"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  public_network_access_enabled   = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true

  allow_nested_items_to_be_public = false

  sas_policy {
    expiration_period = "01.00:00:00"
    expiration_action = "Log"
  }

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  queue_properties {
    logging {
      delete                = true
      read                  = true
      version               = "1.0"
      write                 = true
      retention_policy_days = 7
    }
  }

  tags = {
    ComplianceRisk = "Storage-Secure-Baseline"
  }
}

resource "azurerm_private_endpoint" "storage_blob" {
  name                = "pe-storage-blob-${var.unique_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "psc-storage-blob-${var.unique_suffix}"
    private_connection_resource_id = azurerm_storage_account.vulnerable_storage.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }
}

resource "azurerm_storage_container" "anonymous_container" {
  # checkov:skip=CKV2_AZURE_21: Blob read logging requires a subscription-level diagnostic destination that is outside this compact fixture.
  name               = "azure-webjobs-hosts"
  storage_account_id = azurerm_storage_account.vulnerable_storage.id

  container_access_type = "private"
}
