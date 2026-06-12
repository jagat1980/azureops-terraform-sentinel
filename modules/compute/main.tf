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

  identity {
    type = "SystemAssigned"
  }

  tags = {
    ComplianceRisk = "Password-Authentication-Enabled"
  }
}

resource "azurerm_monitor_data_collection_rule" "vm_heartbeat_dcr" {
  name                = "dcr-vm-heartbeat"
  resource_group_name = "rg-azureops-drift-test"
  location            = "centralindia"

  destinations {
    azure_monitor_metrics {
      name = "heartbeatMetricsDestination"
    }
  }

  data_flow {
    streams      = ["Microsoft-Heartbeat"]
    destinations = ["heartbeatMetricsDestination"]
  }

  data_sources {
    performance_counter {
      name                          = "heartbeatDataSource"
      streams                       = ["Microsoft-Heartbeat"]
      sampling_frequency_in_seconds = 60
      counter_specifiers            = ["\\Heartbeat"]
    }
  }
}

resource "azurerm_monitor_data_collection_rule_association" "vm_heartbeat_assoc" {
  name                    = "dcra-vm-heartbeat"
  target_resource_id      = azurerm_linux_virtual_machine.vulnerable_vm.id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.vm_heartbeat_dcr.id
}