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

resource "azurerm_virtual_network" "drift_vnet" {
  name                = "vnet-drift-test"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_subnet" "drift_subnet" {
  name                 = "subnet-drift-test"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.drift_vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_interface" "drift_nic" {
  name                = "nic-drift-test"
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.drift_subnet.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_network_interface_security_group_association" "nic_nsg_assoc" {
  network_interface_id      = azurerm_network_interface.drift_nic.id
  network_security_group_id = azurerm_network_security_group.vulnerable_nsg.id
}

# 1. Network Security Group with Open Management Ports (Drift Profile)
resource "azurerm_network_security_group" "vulnerable_nsg" {
  name                = "nsg-landingzone-drift"
  location            = var.location
  resource_group_name = var.resource_group_name


  # DRIFT PROFILE: Allows SSH inbound from corporate network
  security_rule {
    name                       = "allow-ssh-public"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  # DRIFT PROFILE: Allows RDP inbound from corporate network
  security_rule {
    name                       = "allow-rdp-public"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  tags = {
    ComplianceRisk = "Public-Management-Ports"
  }
}