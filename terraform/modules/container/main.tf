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

# 1. Static Scan Level: Insecure Container Registry (Public Access Drift)
resource "azurerm_container_registry" "vulnerable_acr" {
  name                = "acrdrift${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Premium"
  admin_enabled       = false

  public_network_access_enabled = false
  quarantine_policy_enabled     = true
  retention_policy_in_days      = 7
  trust_policy_enabled          = true
  zone_redundancy_enabled       = true
  export_policy_enabled         = false
  data_endpoint_enabled         = true

  network_rule_bypass_option = "None"

  network_rule_set {
    default_action = "Deny"
  }

  georeplications {
    location                  = "southindia"
    regional_endpoint_enabled = true
    zone_redundancy_enabled   = true
    tags = {
      ComplianceRisk = "Geo-Replication-Enabled"
    }
  }

  tags = {
    ComplianceRisk = "Registry-Secure-Baseline"
  }
}

resource "azurerm_container_group" "vulnerable_aci" {
  # checkov:skip=CKV_AZURE_245: Azure currently does not support managed identity for container groups deployed into a virtual network; subnet isolation is prioritized here.
  name                = "aci-drift-${var.unique_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  ip_address_type     = "Private"
  os_type             = "Linux"
  subnet_ids          = [var.subnet_id]

  identity {
    type = "SystemAssigned"
  }

  container {
    name = "vulnerable-app"
    # DRIFT PROFILE: Vulnerable application base image with unpatched CVEs
    image  = "node:10-alpine"
    cpu    = "0.5"
    memory = "1.5"

    ports {
      port     = 80
      protocol = "TCP"
    }

    # Auto-Remediated: Disabled privileged access based on Azure Defender alert (ALT-1234567890)
    security {
      privilege_enabled = false
    }
  }

  tags = {
    ComplianceRisk = "Privileged-Container-Runtime-Enabled"
  }
}
