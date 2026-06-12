terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# 1. Linux Virtual Machine with Insecure Password Authentication (Drift Profile)
resource "azurerm_linux_virtual_machine" "vulnerable_vm" {
  name                            = "vm-drift-test"
  resource_group_name             = "rg-azureops-drift-test"
  location                        = "centralindia"
  size                            = "Standard_B1s"
  admin_username                  = "azureadmin"
  admin_password                  = "P@ssw0rd1234!"
  
  # DRIFT PROFILE: Password authentication is enabled instead of SSH keys
  disable_password_authentication = false

  network_interface_ids = [
    "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Network/networkInterfaces/nic-drift-test"
  ]

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
    ComplianceRisk = "Password-Authentication-Enabled"
    HeartbeatMonitoring = "Enabled"
  }
}

resource "azurerm_log_analytics_workspace" "vm_monitoring" {
  name                = "law-contoso-vm-monitoring"
  location            = "centralindia"
  resource_group_name = "rg-azureops-drift-test"
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_virtual_machine_extension" "azure_monitor_agent" {
  name                       = "AzureMonitorLinuxAgent"
  virtual_machine_id         = azurerm_linux_virtual_machine.vulnerable_vm.id
  publisher                  = "Microsoft.Azure.Monitor"
  type                       = "AzureMonitorLinuxAgent"
  type_handler_version       = "1.0"
  auto_upgrade_minor_version = true
}

resource "azurerm_monitor_data_collection_rule" "vm_heartbeat_dcr" {
  name                = "dcr-contoso-vm-heartbeat"
  location            = "centralindia"
  resource_group_name = "rg-azureops-drift-test"

  destinations {
    log_analytics {
      workspace_resource_id = azurerm_log_analytics_workspace.vm_monitoring.id
      name                  = "lawDestination"
    }
  }

  data_flow {
    streams      = ["Microsoft-Heartbeat"]
    destinations = ["lawDestination"]
  }

  data_sources {
    extension {
      name           = "heartbeatExtensionDataSource"
      streams        = ["Microsoft-Heartbeat"]
      extension_name = "Heartbeat"
    }
  }
}

resource "azurerm_monitor_data_collection_rule_association" "vm_heartbeat_assoc" {
  name                    = "assoc-contoso-vm-heartbeat"
  target_resource_id      = azurerm_linux_virtual_machine.vulnerable_vm.id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.vm_heartbeat_dcr.id
}