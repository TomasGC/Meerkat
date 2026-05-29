---
paths:
  - "**/*.tf"
  - "**/*.tfvars"
---

# Terraform Standards

Infrastructure as Code best practices for Terraform.

---

## File Structure

```
terraform/
├── main.tf              # Main resources
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── versions.tf          # Provider versions
├── backend.tf           # Remote state config
├── terraform.tfvars     # Variable values (gitignored)
└── modules/
    └── network/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

---

## Naming Conventions

```hcl
# ✅ Good - Descriptive, snake_case
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.environment}"
  location = var.location
}

resource "azurerm_virtual_network" "app_network" {
  name                = "vnet-${var.project}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.0.0.0/16"]
}
```

---

## Variables

```hcl
# variables.tf
variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "vm_size" {
  description = "Virtual machine size"
  type        = string
  default     = "Standard_B2s"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
```

---

## Modules

```hcl
# ✅ Good - Reusable module
module "network" {
  source = "./modules/network"

  project     = var.project
  environment = var.environment
  location    = var.location
  cidr_block  = "10.0.0.0/16"

  tags = merge(var.tags, {
    Module = "network"
  })
}

# Use module outputs
resource "azurerm_virtual_machine" "app" {
  subnet_id = module.network.subnet_id
  # ...
}
```

---

## State Management

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "sttfstate"
    container_name       = "tfstate"
    key                  = "myapp.terraform.tfstate"
  }
}

# ✅ Always use remote state
# ❌ Never commit .tfstate files
```

---

## Security

```hcl
# ✅ Good - Use variables for secrets
variable "database_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

# ❌ Bad - Hardcoded secrets
resource "azurerm_sql_server" "main" {
  administrator_login_password = "P@ssw0rd123!"  # Never do this
}

# ✅ Good - Reference from Key Vault
data "azurerm_key_vault_secret" "db_password" {
  name         = "database-password"
  key_vault_id = azurerm_key_vault.main.id
}
```

---

## Best Practices

```hcl
# ✅ Good - Use data sources for existing resources
data "azurerm_resource_group" "existing" {
  name = "rg-shared-resources"
}

# ✅ Good - Use locals for computed values
locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  name_prefix = "${var.project}-${var.environment}"
}

resource "azurerm_storage_account" "main" {
  name                = "${local.name_prefix}storage"
  tags                = local.common_tags
  # ...
}

# ✅ Good - Use count/for_each for multiple resources
resource "azurerm_subnet" "app" {
  for_each = toset(["web", "app", "data"])

  name                 = "subnet-${each.key}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet("10.0.0.0/16", 8, index(["web", "app", "data"], each.key))]
}
```

---

**Manage infrastructure consistently and securely.**
