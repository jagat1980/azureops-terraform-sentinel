variable "resource_group_name" {
  type        = string
  description = "The name of the resource group"
}

variable "location" {
  type        = string
  description = "The Azure region to deploy to"
}

variable "unique_suffix" {
  type        = string
  description = "Unique suffix for globally unique names"
}
