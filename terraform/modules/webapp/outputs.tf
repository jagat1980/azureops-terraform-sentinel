output "webapp_url" {
  value       = "http://${azurerm_linux_web_app.vulnerable_app.default_hostname}"
  description = "The URL of the vulnerable web app"
}
