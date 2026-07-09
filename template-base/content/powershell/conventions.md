## PowerShell 7+ Conventions

### Mandatory Header

```powershell
#Requires -Version 7.0

using module "./MyModule.psm1"
using namespace System.IO
```

### Naming

```powershell
# Functions: Verb-Noun (approved verbs only)
function Get-UserById { }
function Set-UserEmail { }
function Test-DatabaseConnection { }

# Classes: PascalCase
class UserRepository { }

# Parameters: PascalCase
param([string]$UserName, [int]$MaxRetries = 3)

# Local variables: camelCase
$userId = 42
$connectionString = "..."

# Constants: PascalCase or UPPER_SNAKE_CASE
$script:MaxPageSize = 100
```

### Paths (Cross-Platform)

```powershell
# ✅ Good - Platform-agnostic
$configPath = [System.IO.Path]::Combine($PSScriptRoot, "config.json")
$outputDir  = [System.IO.Path]::Combine($PSScriptRoot, "output")

# ❌ Bad - Hardcoded separators
$configPath = "$PSScriptRoot\config.json"
$configPath = "$PSScriptRoot/config.json"
```

### Performance (C# methods over cmdlets)

```powershell
# ✅ Fast - C# methods
[System.IO.File]::Exists($path)
[System.IO.File]::ReadAllText($path)
[System.IO.Directory]::GetFiles($dir, "*.json")

# ✅ Fast - Generic collections
$list = [System.Collections.Generic.List[string]]::new()
$list.Add("item")

# ❌ Slow - PowerShell cmdlets for hot paths
Test-Path $path
Get-Content $path
$array += "item"   # Creates new array each time
```

### Null-Safe Arrays

```powershell
# ✅ Good - Always wrap in @() to prevent null
$files = @(Get-ChildItem $path -ErrorAction SilentlyContinue)
$count = @($items).Count  # Safe even if $items is $null
```

### Error Handling

```powershell
# ✅ Good
$ErrorActionPreference = "Stop"

try {
    $result = Invoke-RestMethod $url
}
catch [System.Net.WebException] {
    Write-Error "Network error: $_"
    throw
}
finally {
    # Cleanup
}
```

### Advanced Functions

```powershell
function Get-UserData {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [ValidateNotNullOrEmpty()]
        [string]$UserId
    )

    process {
        # implementation
    }
}
```

### Classes (OOP)

```powershell
class UserRepository {
    hidden [string]$_connectionString

    UserRepository([string]$connectionString) {
        $this._connectionString = $connectionString
    }

    [PSCustomObject] GetById([int]$id) {
        # implementation
        return $null
    }
}
```

### Testing (Pester 5+)

```powershell
BeforeAll {
    $scriptPath = [System.IO.Path]::Combine($PSScriptRoot, "..", "src", "utils.ps1")
    . $scriptPath
}

Describe "Get-UserById" {
    Context "When user exists" {
        It "Should return user object" {
            $result = Get-UserById -UserId "123"
            $result | Should -Not -BeNullOrEmpty
            $result.Name | Should -Be "John"
        }
    }

    Context "When user not found" {
        It "Should throw" {
            { Get-UserById -UserId "999" } | Should -Throw
        }
    }
}
```

---
