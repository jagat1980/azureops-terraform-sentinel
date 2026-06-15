output "nic_id" {
  value       = azurerm_network_interface.drift_nic.id
  description = "The ID of the network interface for the vulnerable virtual machine."
}
