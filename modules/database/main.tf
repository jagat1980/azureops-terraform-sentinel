terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# 1. SQL Server Configuration
resource "azurerm_mssql_server" "sql_server" {
  name                         = "sqlserver-drift-test"
  resource_group_name          = "rg-azureops-drift-test"
  location                     = "centralindia"
  version                      = "12.0"
  administrator_login          = "sqladmin"
  administrator_login_password = "P@ssw0rd1234!"
}

# 2. SQL Firewall Rule Exposing Database Publicly (Drift Profile)
resource "azurerm_mssql_firewall_rule" "vulnerable_fw" {
  name             = "AllowAllInternet"
  server_id        = azurerm_mssql_server.sql_server.id
  
  # DRIFT PROFILE: Exposes database to the entire public internet
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}
