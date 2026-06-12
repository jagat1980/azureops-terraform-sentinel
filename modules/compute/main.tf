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
  }
}

resource "azurerm_monitor_metric_alert" "high_cpu_alert" {
  name                = "INC-Gen2Alert"
  resource_group_name = "rg-azureops-drift-test"
  scopes              = [azurerm_linux_virtual_machine.vulnerable_vm.id]
  description         = "Alert when VM CPU utilization exceeds threshold"
  severity            = 2
  enabled             = true
  frequency           = "PT5M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachines"
    metric_name      = "Percentage CPU"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }
}