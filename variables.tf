variable "location" {
  type        = string
  description = "The target Azure primary region for the drift test harness."
  default     = "centralindia"
}

variable "resource_group_name" {
  type        = string
  description = "Isolated resource group name dedicated to the vulnerability simulation."
  default     = "rg-azureops-drift-test"
}

variable "storage_account_prefix" {
  type        = string
  description = "Base prefix for generating a unique global namespace storage account identifier."
  default     = "stdrift"
}