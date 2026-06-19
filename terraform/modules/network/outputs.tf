output "nic_id" {
  value       = azurerm_network_interface.drift_nic.id
  description = "The ID of the network interface for the vulnerable virtual machine."
}

output "subnet_id" {
  value       = azurerm_subnet.drift_subnet.id
  description = "The ID of the secured subnet used by private platform endpoints."
}
