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

# 1. Static Scan Level: Insecure Container Registry (Public Access Drift)
resource "azurerm_container_registry" "vulnerable_acr" {
  name                     = "acrdrift${var.unique_suffix}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  sku                      = "Premium"
  admin_enabled            = true
  
  # DRIFT PROFILE: Registry is accessible to the public internet
  public_network_access_enabled = true

  tags = {
    ComplianceRisk = "Public-Registry-Access-Enabled"
  }
}

# 2. Dynamic Scan Level: Insecure Runtime Container Group (Privileged & Root Execution)
resource "azurerm_container_group" "vulnerable_aci" {
  name                = "aci-drift-${var.unique_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  ip_address_type     = "Public"
  os_type             = "Linux"

  container {
    name   = "webserver"
    image  = "mcr.microsoft.com/azuredocs/aci-helloworld:latest"
    cpu    = "0.5"
    memory = "1.5"

    ports {
      port     = 80
      protocol = "TCP"
    }

    # DRIFT PROFILE: Container runs with privileged root-like access (violates least privilege)
    security_profile {
      privileged = true
    }
  }

  tags = {
    ComplianceRisk = "Privileged-Container-Runtime-Enabled"
  }
}
