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

variable "subnet_id" {
  type = string
}

data "azurerm_client_config" "current" {}

resource "azurerm_mssql_server" "sql_server" {
  # checkov:skip=CKV_AZURE_113: SQL local admin remains enabled for break-glass access in this isolated test harness; Entra admin is configured for primary access.
  # checkov:skip=CKV2_AZURE_2: Express vulnerability assessment is enabled; external storage-backed VA requires environment-specific storage and secrets.
  name                                     = "sqlserver-drift-test"
  resource_group_name                      = var.resource_group_name
  location                                 = var.location
  version                                  = "12.0"
  administrator_login                      = "sqladmin"
  administrator_login_password             = "P@ssw0rd1234!"
  minimum_tls_version                      = "1.2"
  public_network_access_enabled            = false
  express_vulnerability_assessment_enabled = true

  identity {
    type = "SystemAssigned"
  }

  azuread_administrator {
    login_username              = "terraform-current-principal"
    object_id                   = data.azurerm_client_config.current.object_id
    tenant_id                   = data.azurerm_client_config.current.tenant_id
    azuread_authentication_only = false
  }
}

resource "azurerm_mssql_server_extended_auditing_policy" "sql_audit" {
  server_id              = azurerm_mssql_server.sql_server.id
  log_monitoring_enabled = true
  retention_in_days      = 91
}

resource "azurerm_private_endpoint" "sql_server" {
  name                = "pe-sql-drift-test"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "psc-sql-drift-test"
    private_connection_resource_id = azurerm_mssql_server.sql_server.id
    is_manual_connection           = false
    subresource_names              = ["sqlServer"]
  }
}
