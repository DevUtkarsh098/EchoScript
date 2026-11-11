variable "cost_approval_reference" {
  type        = string
  default     = ""
  description = "Owner's explicit approval reference for docs/jenkins-aws-design.md; never populate automatically."
}

variable "approved_account_budget_usd" {
  type        = number
  default     = 0
  description = "Explicitly approved account-wide budget, including the existing application."
}

variable "verified_budget_email" {
  type        = string
  default     = ""
  description = "Verified account billing/contact email, confirmed using the developer's own Identity Center access."
}

variable "ubuntu_ami_id" {
  type        = string
  description = "Pinned Canonical Ubuntu 24.04 amd64 AMI verified in us-west-2 before the approved plan."
  validation {
    condition     = can(regex("^ami-[a-f0-9]{8,17}$", var.ubuntu_ami_id))
    error_message = "Supply a pinned AMI ID; no automatic AMI replacements."
  }
}

variable "availability_zone" {
  type    = string
  default = "us-west-2a"
}

variable "agent_desired_state" {
  type        = string
  default     = "stopped"
  description = "Agents are stopped by default to match the cost estimate. Coordinate running jobs before changing this value."
  validation {
    condition     = contains(["running", "stopped"], var.agent_desired_state)
    error_message = "Use running or stopped."
  }
}

variable "enable_disposable_test_host" {
  type        = bool
  default     = false
  description = "Enable only after the separate one-off AWS test allowance is approved; test Ansible here before production hosts."
}

variable "application_role_policies" {
  type        = map(string)
  default     = {}
  description = "Five reviewed JSON policies from ci/iam/render.py using confirmed live application/backend metadata. No static credentials."
}
