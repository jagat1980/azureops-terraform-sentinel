output "resource_group_name" {
  value       = azurerm_resource_group.prod.name
  description = "The Resource Group name where resources are deployed."
}

output "function_app_name" {
  value       = azurerm_linux_function_app.triage_func.name
  description = "The Azure Function App name."
}

output "function_app_hostname" {
  value       = azurerm_linux_function_app.triage_func.default_hostname
  description = "The Azure Function App hostname."
}

output "key_vault_name" {
  value       = azurerm_key_vault.kv.name
  description = "The Azure Key Vault name."
}

output "webhook_endpoint_url" {
  value       = "https://${azurerm_linux_function_app.triage_func.default_hostname}/api/swarm-triage?code=${data.azurerm_function_app_host_keys.keys.default_function_key}"
  description = "The Event Grid Webhook integration URL (including authorization key)."
  sensitive   = true
}
