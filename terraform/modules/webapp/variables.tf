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

variable "azuread_client_id" {
  type        = string
  description = "Microsoft Entra application client ID used to enforce App Service authentication."
  default     = "00000000-0000-0000-0000-000000000000"
}

variable "azuread_issuer_url" {
  type        = string
  description = "Microsoft Entra issuer URL used by App Service authentication."
  default     = "https://sts.windows.net/00000000-0000-0000-0000-000000000000/"
}
