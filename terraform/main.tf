
# 1. Random ID Generation (Root Level)
resource "random_string" "unique_id" {
  length  = 6
  special = false
  upper   = false
}

# 2. Resource Group Creation (Root Level)
resource "azurerm_resource_group" "drift_test" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Environment = "Harness-Testing"
    ManagedBy   = "Terraform"
    SecurityLog = "Drift-Simulation"
  }
}

# 3. Module Orchestration
module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.drift_test.name
  location            = azurerm_resource_group.drift_test.location
  unique_suffix       = random_string.unique_id.result
}

module "network" {
  source              = "./modules/network"
  resource_group_name = azurerm_resource_group.drift_test.name
  location            = azurerm_resource_group.drift_test.location
}

module "compute" {
  source               = "./modules/compute"
  resource_group_name  = azurerm_resource_group.drift_test.name
  location             = azurerm_resource_group.drift_test.location
  network_interface_id = module.network.nic_id
}

module "database" {
  source              = "./modules/database"
  resource_group_name = azurerm_resource_group.drift_test.name
  location            = azurerm_resource_group.drift_test.location
}

module "container" {
  source              = "./modules/container"
  resource_group_name = azurerm_resource_group.drift_test.name
  location            = azurerm_resource_group.drift_test.location
  unique_suffix       = random_string.unique_id.result
}

# 4. State Migration Blocks
moved {
  from = azurerm_storage_account.vulnerable_storage
  to   = module.storage.azurerm_storage_account.vulnerable_storage
}

moved {
  from = azurerm_storage_container.anonymous_container
  to   = module.storage.azurerm_storage_container.anonymous_container
}
