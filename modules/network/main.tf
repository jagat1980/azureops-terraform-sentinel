terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# 1. Network Security Group with Open Management Ports (Drift Profile)
resource "azurerm_network_security_group" "vulnerable_nsg" {
  name                = "nsg-landingzone-drift"
  location            = "centralindia"
  resource_group_name = "rg-azureops-drift-test"

  # DRIFT PROFILE: Allows SSH inbound from corporate network
  security_rule {
    name                       = "allow-ssh-public"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  # DRIFT PROFILE: Allows RDP inbound from corporate network
  security_rule {
    name                       = "allow-rdp-public"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  tags = {
    ComplianceRisk = "Public-Management-Ports"
  }
}