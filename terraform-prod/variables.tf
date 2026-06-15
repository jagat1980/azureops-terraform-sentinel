variable "location" {
  type        = string
  description = "The target Azure primary region for the production resources."
  default     = "centralindia"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name dedicated to the production CloudSecAIOps engine."
  default     = "CloudSecAIOps-Prod"
}

variable "GITHUB_TOKEN" {
  type        = string
  description = "GitHub Personal Access Token for PR generation."
  sensitive   = true
}

variable "GITHUB_REPO" {
  type        = string
  description = "Target GitHub repository in owner/name format."
  default     = "jagat1980/azureops-terraform-sentinel"
}

variable "AZURE_OPENAI_ENDPOINT" {
  type        = string
  description = "Azure OpenAI Service Endpoint URL."
}

variable "AZURE_OPENAI_KEY" {
  type        = string
  description = "Azure OpenAI Service API Key."
  sensitive   = true
}

variable "OPENAI_DEPLOYMENT_NAME" {
  type        = string
  description = "Azure OpenAI model deployment name."
  default     = "gpt-5.4"
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID."
  default     = "d78af5f4-5d2d-4141-a725-2088437da0ca"
}
