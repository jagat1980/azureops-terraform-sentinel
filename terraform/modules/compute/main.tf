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

variable "network_interface_id" {
  type = string
}

# 1. Linux Virtual Machine with Insecure Password Authentication (Drift Profile)
resource "azurerm_linux_virtual_machine" "vulnerable_vm" {
  name                            = "vm-drift-test"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  size                            = "Standard_B1s"
  admin_username                  = "azureadmin"
  disable_password_authentication = true

  network_interface_ids = [
    var.network_interface_id
  ]

  admin_ssh_key {
    username   = "azureadmin"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7exampleplaceholderkeyreplacewithvalidpublickey"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  tags = {
    ComplianceRisk = "Password-Authentication-Disabled"
  }
}