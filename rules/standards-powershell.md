---
paths:
  - "**/*.ps1"
  - "**/*.psm1"
  - "**/*.psd1"
---

# PowerShell Coding Standards

Company standards for PowerShell 7+ development with performance optimization and OOP patterns.

**Last Updated**: 2026-03-05

---

## Version Requirement

### MANDATORY: PowerShell 7.0+

**All scripts MUST start with**:
```powershell
#Requires -Version 7.0
```

**Why**:
- Consistent behavior across team
- Access to modern features (.NET Core/5+)
- Better performance than Windows PowerShell 5.1
- Cross-platform compatibility (Windows, Linux, macOS)

---

## Cross-Platform Compatibility

### CRITICAL: Always Use Platform-Agnostic Path Operations

**❌ NEVER use path separators directly**:
```powershell
# ❌ Bad - Platform-specific (breaks on Linux/macOS)
$path = "C:\repos\api\src"
$fullPath = "$baseDir\subfolder\file.txt"
$fullPath = $baseDir + "\" + $subfolder
```

**✅ ALWAYS use [System.IO.Path] methods**:
```powershell
# ✅ Good - Cross-platform (works on Windows/Linux/macOS)
$path = [System.IO.Path]::Combine("C:", "repos", "api", "src")
$fullPath = [System.IO.Path]::Combine($baseDir, "subfolder", "file.txt")
$fullPath = [System.IO.Path]::Combine($baseDir, $subfolder, "file.txt")
```

**Why**:
- `[System.IO.Path]::Combine()` automatically uses the correct separator (`\` on Windows, `/` on Linux/macOS)
- No need to worry about mixing `/` and `\`
- Code works identically on all platforms
- Future-proof for containerized environments

**Additional path operations**:
```powershell
# Get directory name (parent directory)
$parent = [System.IO.Path]::GetDirectoryName($fullPath)

# Get filename
$filename = [System.IO.Path]::GetFileName($fullPath)

# Get extension
$ext = [System.IO.Path]::GetExtension($fullPath)  # Returns ".txt"

# Get filename without extension
$nameOnly = [System.IO.Path]::GetFileNameWithoutExtension($fullPath)

# Check if path is rooted (absolute)
$isAbsolute = [System.IO.Path]::IsPathRooted($path)

# Get full path (resolves relative paths)
$absolutePath = [System.IO.Path]::GetFullPath($relativePath)
```

### Platform Detection (When Necessary)

```powershell
# Detect OS (PowerShell 7+)
$IsWindowsOS = $IsWindows -or ($PSVersionTable.PSVersion.Major -le 5)
$IsMacOS = $PSVersionTable.OS -match "Darwin"
$IsLinuxOS = $PSVersionTable.OS -match "Linux"

# Platform-specific logic (use sparingly)
if ($IsWindowsOS) {
    # Windows-specific code
} elseif ($IsMacOS) {
    # macOS-specific code
} elseif ($IsLinuxOS) {
    # Linux-specific code
}
```

**Best Practice**: Avoid platform-specific code when possible. Use .NET methods that work cross-platform.

---

## Approved Verbs

### Use PowerShell Approved Verbs Only

**Check available verbs**: `Get-Verb`

**✅ Approved verbs**:
- **Get** - Retrieve data
- **Set** - Modify data
- **Test** - Validate condition (return bool)
- **New** - Create new resource
- **Remove** - Delete resource
- **Initialize** - Set up initial state
- **Invoke** - Execute operation
- **Add** - Add to collection
- **Clear** - Remove all items
- **Update** - Modify existing resource

**❌ Avoid non-approved verbs**:
- ❌ `Ensure` → Use `Test` or `Initialize`
- ❌ `Validate` → Use `Test`
- ❌ `Configure` → Use `Set` or `Initialize`
- ❌ `Apply` → Use `Update` or `Set`
- ❌ `Drop` → Use `Remove`
- ❌ `Seed` → Use `Import` or `Initialize`

**Examples**:

```powershell
# ❌ Bad
function Ensure-Database { }
function Drop-AllTables { }
function Seed-Database { }
function Apply-Migrations { }

# ✅ Good
function Test-DatabaseExists { }
function Remove-AllTables { }
function Import-DatabaseSeedData { }
function Update-DatabaseSchema { }
```

---

## Performance Optimization

### Use C# Methods Instead of Cmdlets

**Why**: C# methods are 10-100x faster than PowerShell cmdlets for common operations.

#### String Operations

```powershell
# ❌ Slow - PowerShell cmdlet
$result = $string | Select-String -Pattern "regex"
$lower = $string.ToLower()  # Actually calls .NET, this is OK

# ✅ Fast - C# methods
$result = [regex]::Match($string, "pattern")
$lower = $string.ToLower()
$upper = $string.ToUpper()
$contains = $string.Contains("substring")
$startsWith = $string.StartsWith("prefix")
$endsWith = $string.EndsWith(".txt")
```

#### File Operations

```powershell
# ❌ Slow - PowerShell cmdlets
Test-Path $filePath
Get-Content $filePath
Set-Content $filePath -Value $content

# ✅ Fast - C# methods
[System.IO.File]::Exists($filePath)
[System.IO.File]::ReadAllText($filePath)
[System.IO.File]::WriteAllText($filePath, $content)
[System.IO.File]::ReadAllLines($filePath)
[System.IO.File]::WriteAllLines($filePath, $lines)

# ✅ Even faster for large files - Streams
$stream = [System.IO.File]::OpenRead($filePath)
$reader = [System.IO.StreamReader]::new($stream)
try {
    while ($null -ne ($line = $reader.ReadLine())) {
        # Process line
    }
}
finally {
    $reader.Dispose()
    $stream.Dispose()
}
```

#### Directory Operations

```powershell
# ❌ Slow
Test-Path $directoryPath
Get-ChildItem $directoryPath
New-Item -ItemType Directory -Path $directoryPath

# ✅ Fast
[System.IO.Directory]::Exists($directoryPath)
[System.IO.Directory]::GetFiles($directoryPath, "*.txt")
[System.IO.Directory]::GetDirectories($directoryPath)
[System.IO.Directory]::CreateDirectory($directoryPath)
```

#### Path Operations

```powershell
# ❌ Slow
Join-Path $path1 $path2
Split-Path $path -Parent

# ✅ Fast
[System.IO.Path]::Combine($path1, $path2)
[System.IO.Path]::GetDirectoryName($path)
[System.IO.Path]::GetFileName($path)
[System.IO.Path]::GetExtension($path)
[System.IO.Path]::GetFileNameWithoutExtension($path)
```

#### Collections

```powershell
# ❌ Slow - Array concatenation
$array = @()
foreach ($item in $items) {
    $array += $item  # Creates new array each time
}

# ✅ Fast - Generic List
$list = [System.Collections.Generic.List[string]]::new()
foreach ($item in $items) {
    $list.Add($item)  # O(1) operation
}

# ✅ Fast - StringBuilder for strings
$sb = [System.Text.StringBuilder]::new()
foreach ($line in $lines) {
    $sb.AppendLine($line) | Out-Null
}
$result = $sb.ToString()
```

#### Null-Safe Array Handling

**CRITICAL: Always ensure arrays are never null to avoid `.Count` and `.Length` errors**

```powershell
# ❌ Bad - Can return $null
function Get-Items {
    $items = Get-ChildItem -ErrorAction SilentlyContinue
    return [string[]]$items  # Can be $null if empty
}

$results = Get-Items
$results.Count  # ❌ ERROR if $null

# ✅ Good - Guarantees array (never null)
function Get-Items {
    $items = Get-ChildItem -ErrorAction SilentlyContinue
    return [string[]]@($items)  # Always returns array, even if empty
}

$results = Get-Items
$results.Count  # ✅ Works - returns 0 if empty

# ✅ Pattern 1: Force array conversion with @()
$services = @([ServiceDiscovery]::GetAllServices())  # Guarantees array
$files = @(Get-ChildItem $path -ErrorAction SilentlyContinue)  # Array even if empty
$count = @($items).Count  # Safe .Count access

# ✅ Pattern 2: [array] cast for [ref] parameters
function Get-Items {
    param([ref]$OutputArray)

    $items = Get-ChildItem -ErrorAction SilentlyContinue
    $OutputArray.Value = [array]@($items)  # Force array cast
}

$items = $null
Get-Items -OutputArray ([ref]$items)
$items.Count  # ✅ Works - returns 0 if empty
```

**Why**:
- `@()` forces conversion to array, turning `$null` into `@()` (empty array)
- `.Count` and `.Length` on `$null` throw errors, but work on empty arrays
- Prevents defensive `if ($null -ne $result)` checks everywhere
- Makes code more robust and predictable

**Best Practice**:
```powershell
# ❌ Avoid - Requires null checks
function Get-Services {
    $services = [ServiceDiscovery]::GetAllServiceNames($path)
    return $services  # Can be $null
}

$services = Get-Services
if ($null -ne $services) {  # ❌ Defensive check needed
    foreach ($service in $services) { }
}

# ✅ Prefer - No null checks needed
function Get-Services {
    $services = [ServiceDiscovery]::GetAllServiceNames($path)
    return @($services)  # ✅ Guarantees array
}

$services = Get-Services  # Always array, never null
foreach ($service in $services) { }  # ✅ Works even if empty
```

#### JSON Operations

```powershell
# ❌ Slow
$json = ConvertTo-Json $object -Depth 10
$object = ConvertFrom-Json $json

# ✅ Fast (PowerShell 7+)
$json = [System.Text.Json.JsonSerializer]::Serialize($object)
$object = [System.Text.Json.JsonSerializer]::Deserialize($json, [MyClass])
```

---

## Object-Oriented Programming

### Use Classes and Modules

#### CRITICAL: using module for Parse-Time Type Resolution

**ALWAYS use `using module` at the top of files** (before any code):

```powershell
#Requires -Version 7.0

# ============================================================================
# CRITICAL: using module MUST be at the very top (parse-time, not runtime)
# ============================================================================
using module "./logging/Logger.psm1"
using module "./context/RattlerContext.psm1"
using namespace System.IO
using namespace System.Collections.Generic

# Now classes are available for type hints
class MyClass {
    [Logger]$Logger  # Type resolved at parse-time
    [RattlerContext]$Context

    MyClass() {
        $this.Logger = [Logger]::GetInstance()
        $this.Context = [RattlerContext]::GetInstance()
    }
}
```

**Why `using module` vs Import-Module**:
- `using module` - Parse-time resolution (types available immediately)
- `Import-Module` - Runtime resolution (types NOT available for type hints)
- **Always prefer `using module`** for classes and type hints

**Order matters**:
```powershell
#Requires -Version 7.0

# 1. using module (parse-time types)
using module "./BaseClass.psm1"

# 2. using namespace (aliases)
using namespace System.IO
using namespace System.Collections.Generic

# 3. Class definitions
class MyClass : BaseClass { }

# 4. Function definitions
function Get-Something { }
```

---

### Base Classes for Shared Functionality

**Pattern: Universal base class (like Unity's MonoBehaviour)**

```powershell
#Requires -Version 7.0
using module "./logging/Logger.psm1"
using module "./context/AppContext.psm1"

<#
.SYNOPSIS
    BaseClass - Universal base for all application classes
.DESCRIPTION
    Provides automatic dependency injection (Logger, Context) for all derived classes.
    Zero duplication - inherit once, use everywhere.
#>

class BaseClass {
    # ========================================================================
    # STATIC PROPERTIES (Shared across all instances)
    # ========================================================================

    # Logger instance (available in ALL classes)
    static [Logger] $Logger

    # Application context (available in ALL classes)
    static [AppContext] $Context

    # Initialization flag
    hidden static [bool] $Initialized = $false

    # ========================================================================
    # STATIC METHODS
    # ========================================================================

    <#
    .SYNOPSIS
        Initialize core dependencies (Logger, Context)
    .DESCRIPTION
        Lazy loads singleton instances. Called automatically before first use.
        Idempotent - safe to call multiple times.
    #>
    static [void] Initialize() {
        if ([BaseClass]::Initialized) { return }

        [BaseClass]::Logger = [Logger]::GetInstance()
        [BaseClass]::Context = [AppContext]::GetInstance()
        [BaseClass]::Initialized = $true
    }
}

# Usage: All classes inherit Logger and Context automatically
class UserService : BaseClass {
    [void] CreateUser([string]$name) {
        # Logger available via inheritance
        [BaseClass]::Logger.Info("Creating user: $name")

        # Context available via inheritance
        $dbPath = [BaseClass]::Context.DatabasePath
    }
}

class OrderService : BaseClass {
    [void] ProcessOrder([int]$orderId) {
        # Zero setup - Logger and Context already available
        [BaseClass]::Logger.Info("Processing order: $orderId")
        $apiUrl = [BaseClass]::Context.ApiEndpoint
    }
}
```

**Benefits**:
- **Zero duplication** - Write dependency setup once
- **Automatic injection** - All classes get Logger, Context, etc.
- **Unity-like API** - Familiar pattern for game developers
- **Easy to extend** - Add new shared dependencies in one place

---

### Static Utility Classes

**Pattern: Utility class with only static members (cannot be instantiated)**

```powershell
#Requires -Version 7.0
using module "../BaseClass.psm1"

<#
.SYNOPSIS
    DirectoryManager - Safe directory operations
.DESCRIPTION
    Static utility class with no instance members.
    Prevents instantiation with hidden constructor.
#>

class DirectoryManager {
    # Hidden constructor prevents instantiation
    hidden DirectoryManager() {
        throw "DirectoryManager is a static utility class and cannot be instantiated"
    }

    <#
    .SYNOPSIS
        Initialize a directory, creating it if necessary
    .PARAMETER Path
        Path to the directory
    .PARAMETER Description
        Description for logging (e.g., "temporary files")
    .OUTPUTS
        Boolean - true if directory exists or was created
    .EXAMPLE
        [DirectoryManager]::Initialize("C:\temp\logs", "log directory")
    #>
    static [bool] Initialize([string]$Path, [string]$Description) {
        if ([string]::IsNullOrWhiteSpace($Path)) {
            throw "Path cannot be null or empty"
        }

        try {
            # Check if already exists
            if ([System.IO.Directory]::Exists($Path)) {
                [BaseClass]::Logger.Verbose("Directory already exists: $Path")
                return $true
            }

            # Create with -Force (creates parent directories automatically)
            $null = New-Item -ItemType Directory -Path $Path -Force -ErrorAction Stop
            [BaseClass]::Logger.Verbose("Created $Description : $Path")
            return $true
        }
        catch {
            [BaseClass]::Logger.Error("Failed to create $Description at $Path : $_")
            return $false
        }
    }

    <#
    .SYNOPSIS
        Check if directory is empty
    .PARAMETER Path
        Path to check
    .OUTPUTS
        Boolean - true if directory is empty or doesn't exist
    #>
    static [bool] IsEmpty([string]$Path) {
        if (-not [System.IO.Directory]::Exists($Path)) {
            return $true
        }

        $items = [System.IO.Directory]::GetFileSystemEntries($Path)
        return $items.Count -eq 0
    }

    <#
    .SYNOPSIS
        Remove directory forcefully
    .PARAMETER Path
        Path to remove
    .PARAMETER Description
        Description for logging
    .OUTPUTS
        Boolean - true if removed or doesn't exist
    #>
    static [bool] RemoveForce([string]$Path, [string]$Description) {
        if (-not [System.IO.Directory]::Exists($Path)) {
            [BaseClass]::Logger.Verbose("Directory doesn't exist: $Path")
            return $true
        }

        try {
            Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
            [BaseClass]::Logger.Verbose("Removed $Description : $Path")
            return $true
        }
        catch {
            [BaseClass]::Logger.Error("Failed to remove $Description at $Path : $_")
            return $false
        }
    }
}

# Usage: Static methods only, no instance creation
[DirectoryManager]::Initialize("C:\temp\logs", "log directory")
if ([DirectoryManager]::IsEmpty("C:\temp\cache")) {
    [DirectoryManager]::RemoveForce("C:\temp\cache", "cache directory")
}

# ❌ This will throw an error (cannot instantiate)
# $manager = [DirectoryManager]::new()
```

**Why static utility classes**:
- **No state** - Pure utility functions
- **No instantiation** - Prevents accidental misuse
- **Better IntelliSense** - `[ClassName]::` shows all methods
- **Thread-safe** - No shared instance state

---

### Singleton Pattern

**Pattern: Single instance with GetInstance()**

```powershell
#Requires -Version 7.0

<#
.SYNOPSIS
    Logger - Singleton logging service
.DESCRIPTION
    Provides centralized logging with single instance across application.
#>

class Logger {
    # ========================================================================
    # SINGLETON IMPLEMENTATION
    # ========================================================================

    # Static instance (shared across all access)
    hidden static [Logger] $Instance

    # Lock object for thread-safe initialization
    hidden static [object] $Lock = [object]::new()

    # ========================================================================
    # INSTANCE PROPERTIES
    # ========================================================================

    [string]$LogLevel = "Info"
    [string]$LogFile

    # ========================================================================
    # CONSTRUCTOR (hidden - prevents direct instantiation)
    # ========================================================================

    hidden Logger() {
        $this.LogFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "app.log")
    }

    # ========================================================================
    # STATIC METHODS
    # ========================================================================

    <#
    .SYNOPSIS
        Get the singleton Logger instance
    .DESCRIPTION
        Thread-safe lazy initialization. Creates instance on first call.
    .OUTPUTS
        Logger - The singleton instance
    .EXAMPLE
        $logger = [Logger]::GetInstance()
        $logger.Info("Hello world")
    #>
    static [Logger] GetInstance() {
        if ($null -eq [Logger]::Instance) {
            # Thread-safe initialization
            [System.Threading.Monitor]::Enter([Logger]::Lock)
            try {
                if ($null -eq [Logger]::Instance) {
                    [Logger]::Instance = [Logger]::new()
                }
            }
            finally {
                [System.Threading.Monitor]::Exit([Logger]::Lock)
            }
        }

        return [Logger]::Instance
    }

    # ========================================================================
    # INSTANCE METHODS
    # ========================================================================

    [void] Info([string]$message) {
        $this.Log("INFO", $message)
    }

    [void] Warning([string]$message) {
        $this.Log("WARN", $message)
    }

    [void] Error([string]$message) {
        $this.Log("ERROR", $message)
    }

    hidden [void] Log([string]$level, [string]$message) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logEntry = "[$timestamp] [$level] $message"

        Write-Host $logEntry
        Add-Content -Path $this.LogFile -Value $logEntry
    }
}

# Usage: Always access via GetInstance()
$logger = [Logger]::GetInstance()
$logger.Info("Application started")
$logger.Warning("Low memory")
$logger.Error("Database connection failed")

# ❌ Don't do this (constructor is hidden)
# $logger = [Logger]::new()
```

**Benefits**:
- **Single instance** - Guaranteed across entire application
- **Lazy initialization** - Created only when first accessed
- **Thread-safe** - Safe for concurrent access
- **Global access** - Available anywhere via `GetInstance()`

---

### Define Classes

```powershell
#Requires -Version 7.0

class DatabaseConnection {
    [string]$Server
    [string]$Database
    [int]$Timeout = 30

    # Constructor
    DatabaseConnection([string]$server, [string]$database) {
        $this.Server = $server
        $this.Database = $database
    }

    # Methods
    [string] GetConnectionString() {
        return "Server=$($this.Server);Database=$($this.Database);Timeout=$($this.Timeout)"
    }

    [bool] TestConnection() {
        # Implementation
        return $true
    }
}

class SqlRepository {
    [DatabaseConnection]$Connection

    SqlRepository([DatabaseConnection]$connection) {
        $this.Connection = $connection
    }

    [object[]] ExecuteQuery([string]$query) {
        # Implementation
        return @()
    }
}
```

**Benefits**:
- Type safety
- IntelliSense support
- Better code organization
- Reusable components

---

## Module Structure

### Organize Code with Modules

**Structure**:
```
MyModule/
├── MyModule.psd1              # Module manifest
├── MyModule.psm1              # Main module file
├── Classes/
│   ├── DatabaseConnection.ps1
│   └── SqlRepository.ps1
├── Public/
│   ├── Get-User.ps1
│   └── Set-User.ps1
└── Private/
    └── ConvertTo-SqlParameter.ps1
```

**MyModule.psm1**:
```powershell
#Requires -Version 7.0
using namespace System.IO
using namespace System.Data.SqlClient

# Import classes
. $PSScriptRoot\Classes\DatabaseConnection.ps1
. $PSScriptRoot\Classes\SqlRepository.ps1

# Import private functions
Get-ChildItem "$PSScriptRoot\Private\*.ps1" | ForEach-Object {
    . $_.FullName
}

# Import and export public functions
Get-ChildItem "$PSScriptRoot\Public\*.ps1" | ForEach-Object {
    . $_.FullName
    Export-ModuleMember -Function $_.BaseName
}

# Export classes
Export-ModuleMember -Function * -Alias *
```

**MyModule.psd1**:
```powershell
@{
    ModuleVersion = '1.0.0'
    RootModule = 'MyModule.psm1'
    PowerShellVersion = '7.0'
    FunctionsToExport = @('Get-User', 'Set-User')
    ClassesToExport = @('DatabaseConnection', 'SqlRepository')
}
```

---

## Development Principles

### Apply Universal Best Practices

**All PowerShell code must follow**:

**TDD (Test-Driven Development)**:
- Write tests before implementation
- Use Pester 5+ for unit and integration tests
- Aim for ≥ 80% code coverage
- Tests must be fast, isolated, and deterministic

**DDD (Domain-Driven Design)**:
- Model the domain with rich domain entities
- Use ubiquitous language (same terms as business)
- Separate domain logic from infrastructure
- Organize by domain concepts, not technical layers
- Keep domain models pure (no database/UI concerns)

**DRY (Don't Repeat Yourself)**:
- Extract common logic into functions/classes
- Create reusable modules for shared functionality
- Use inheritance and composition to avoid duplication
- **Use helper functions for repeated operations**
- **Use base classes for shared behavior**
- **Use static utility classes for common operations**

**OOP (Object-Oriented Programming)**:
- Use classes for complex data structures
- Encapsulate behavior with methods
- Apply inheritance for shared behavior
- Use interfaces (abstract classes) for contracts

**SOLID Principles**:
1. **Single Responsibility** - One class/function, one purpose
2. **Open-Closed** - Open for extension, closed for modification
3. **Liskov Substitution** - Derived classes must be substitutable
4. **Interface Segregation** - Small, focused interfaces
5. **Dependency Inversion** - Depend on abstractions, not concretions

**Design Patterns to Use**:
- **Repository Pattern** - Abstract data access
- **Factory Pattern** - Object creation
- **Strategy Pattern** - Interchangeable algorithms
- **Singleton Pattern** - Single instance (use sparingly)
- **Builder Pattern** - Complex object construction

**Example - Domain-Driven Design**:
```powershell
#Requires -Version 7.0

# Domain Entity (rich model with business logic)
class Order {
    [int]$Id
    [string]$CustomerName
    [Collections.Generic.List[OrderItem]]$Items
    [OrderStatus]$Status
    [datetime]$CreatedAt

    Order([string]$customerName) {
        $this.CustomerName = $customerName
        $this.Items = [Collections.Generic.List[OrderItem]]::new()
        $this.Status = [OrderStatus]::Draft
        $this.CreatedAt = [datetime]::Now
    }

    # Business logic in domain model
    [void] AddItem([string]$productName, [decimal]$price, [int]$quantity) {
        if ($quantity -le 0) {
            throw "Quantity must be positive"
        }
        $item = [OrderItem]::new($productName, $price, $quantity)
        $this.Items.Add($item)
    }

    [decimal] GetTotal() {
        $total = 0
        foreach ($item in $this.Items) {
            $total += $item.GetSubtotal()
        }
        return $total
    }

    [void] Submit() {
        if ($this.Items.Count -eq 0) {
            throw "Cannot submit empty order"
        }
        $this.Status = [OrderStatus]::Submitted
    }

    [bool] CanBeCancelled() {
        return $this.Status -in @([OrderStatus]::Draft, [OrderStatus]::Submitted)
    }
}

class OrderItem {
    [string]$ProductName
    [decimal]$Price
    [int]$Quantity

    OrderItem([string]$productName, [decimal]$price, [int]$quantity) {
        $this.ProductName = $productName
        $this.Price = $price
        $this.Quantity = $quantity
    }

    [decimal] GetSubtotal() {
        return $this.Price * $this.Quantity
    }
}

enum OrderStatus {
    Draft
    Submitted
    Paid
    Shipped
    Delivered
    Cancelled
}

# Domain Service (when logic spans multiple entities)
class OrderPricingService {
    [decimal] CalculateTotalWithTax([Order]$order, [decimal]$taxRate) {
        $subtotal = $order.GetTotal()
        return $subtotal * (1 + $taxRate)
    }

    [decimal] ApplyDiscount([Order]$order, [decimal]$discountPercent) {
        if ($discountPercent -lt 0 -or $discountPercent -gt 100) {
            throw "Invalid discount percentage"
        }
        $total = $order.GetTotal()
        return $total * (1 - ($discountPercent / 100))
    }
}

# Repository (infrastructure concern, separated from domain)
class IOrderRepository {
    [Order] GetById([int]$id) { throw "Not implemented" }
    [void] Save([Order]$order) { throw "Not implemented" }
}
```

**Example - Repository Pattern**:
```powershell
#Requires -Version 7.0

# Interface (abstract base class)
class IUserRepository {
    [object[]] GetAll() { throw "Not implemented" }
    [object] GetById([int]$id) { throw "Not implemented" }
    [void] Add([object]$user) { throw "Not implemented" }
}

# Implementation
class SqlUserRepository : IUserRepository {
    [DatabaseConnection]$Connection

    SqlUserRepository([DatabaseConnection]$connection) {
        $this.Connection = $connection
    }

    [object[]] GetAll() {
        return $this.Connection.ExecuteQuery("SELECT * FROM Users")
    }

    [object] GetById([int]$id) {
        $query = "SELECT * FROM Users WHERE Id = $id"
        return $this.Connection.ExecuteQuery($query)[0]
    }

    [void] Add([object]$user) {
        $query = "INSERT INTO Users (Name, Email) VALUES ('$($user.Name)', '$($user.Email)')"
        $this.Connection.ExecuteNonQuery($query)
    }
}

# Usage - Depend on abstraction
function Get-UserList {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [IUserRepository]$Repository
    )

    return $Repository.GetAll()
}
```

**Example - Strategy Pattern**:
```powershell
#Requires -Version 7.0

# Strategy interface
class ICompressionStrategy {
    [byte[]] Compress([byte[]]$data) { throw "Not implemented" }
    [byte[]] Decompress([byte[]]$data) { throw "Not implemented" }
}

# Concrete strategies
class GzipCompression : ICompressionStrategy {
    [byte[]] Compress([byte[]]$data) {
        # GZip implementation
        return $data
    }
    [byte[]] Decompress([byte[]]$data) {
        return $data
    }
}

class ZipCompression : ICompressionStrategy {
    [byte[]] Compress([byte[]]$data) {
        # ZIP implementation
        return $data
    }
    [byte[]] Decompress([byte[]]$data) {
        return $data
    }
}

# Context
class FileArchiver {
    [ICompressionStrategy]$Strategy

    FileArchiver([ICompressionStrategy]$strategy) {
        $this.Strategy = $strategy
    }

    [void] ArchiveFile([string]$path) {
        $data = [System.IO.File]::ReadAllBytes($path)
        $compressed = $this.Strategy.Compress($data)
        [System.IO.File]::WriteAllBytes("$path.archive", $compressed)
    }
}
```

---

## Avoid Code Duplication (DRY Principle)

### CRITICAL: Extract Repeated Logic

**❌ Bad - Duplicated code**:
```powershell
function Deploy-ServiceA {
    Write-Host "Starting deployment..."
    $tempDir = Join-Path $env:TEMP "deploy-a"
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Host "Deployment complete"
}

function Deploy-ServiceB {
    Write-Host "Starting deployment..."
    $tempDir = Join-Path $env:TEMP "deploy-b"
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Host "Deployment complete"
}
```

**✅ Good - Extract common logic into helper**:
```powershell
# Helper function - reusable
function Initialize-TempDirectory {
    param([string]$Name)

    $tempDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), $Name)

    if ([System.IO.Directory]::Exists($tempDir)) {
        Remove-Item $tempDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    return $tempDir
}

# Usage - no duplication
function Deploy-ServiceA {
    Write-Host "Starting deployment..."
    $tempDir = Initialize-TempDirectory "deploy-a"
    Write-Host "Deployment complete"
}

function Deploy-ServiceB {
    Write-Host "Starting deployment..."
    $tempDir = Initialize-TempDirectory "deploy-b"
    Write-Host "Deployment complete"
}
```

---

### Extract Common Patterns into Functions

**❌ Bad - Repeated error handling**:
```powershell
function Get-UserData {
    param([int]$UserId)

    try {
        $data = Invoke-RestMethod "https://api.com/users/$UserId"
        return $data
    }
    catch {
        Write-Error "Failed to get user $UserId : $_"
        return $null
    }
}

function Get-OrderData {
    param([int]$OrderId)

    try {
        $data = Invoke-RestMethod "https://api.com/orders/$OrderId"
        return $data
    }
    catch {
        Write-Error "Failed to get order $OrderId : $_"
        return $null
    }
}
```

**✅ Good - Extract HTTP helper**:
```powershell
# Generic HTTP helper
function Invoke-ApiRequest {
    param(
        [string]$Endpoint,
        [string]$EntityType
    )

    try {
        $data = Invoke-RestMethod $Endpoint
        return $data
    }
    catch {
        Write-Error "Failed to get $EntityType : $_"
        return $null
    }
}

# Usage - no duplication
function Get-UserData {
    param([int]$UserId)
    return Invoke-ApiRequest -Endpoint "https://api.com/users/$UserId" -EntityType "user $UserId"
}

function Get-OrderData {
    param([int]$OrderId)
    return Invoke-ApiRequest -Endpoint "https://api.com/orders/$OrderId" -EntityType "order $OrderId"
}
```

---

### Use Base Classes for Shared Behavior

**❌ Bad - Duplicated validation logic**:
```powershell
class User {
    [string]$Name
    [string]$Email

    [bool] ValidateName() {
        if ([string]::IsNullOrWhiteSpace($this.Name)) {
            return $false
        }
        if ($this.Name.Length -lt 2) {
            return $false
        }
        return $true
    }

    [bool] ValidateEmail() {
        if ([string]::IsNullOrWhiteSpace($this.Email)) {
            return $false
        }
        return $this.Email -match "^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$"
    }
}

class Customer {
    [string]$CompanyName
    [string]$ContactEmail

    [bool] ValidateCompanyName() {
        if ([string]::IsNullOrWhiteSpace($this.CompanyName)) {
            return $false
        }
        if ($this.CompanyName.Length -lt 2) {
            return $false
        }
        return $true
    }

    [bool] ValidateContactEmail() {
        if ([string]::IsNullOrWhiteSpace($this.ContactEmail)) {
            return $false
        }
        return $this.ContactEmail -match "^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$"
    }
}
```

**✅ Good - Extract validation to base class**:
```powershell
# Base class with shared validation
class EntityBase {
    [bool] ValidateString([string]$value, [int]$minLength) {
        if ([string]::IsNullOrWhiteSpace($value)) {
            return $false
        }
        return $value.Length -ge $minLength
    }

    [bool] ValidateEmail([string]$email) {
        if ([string]::IsNullOrWhiteSpace($email)) {
            return $false
        }
        return $email -match "^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$"
    }
}

# Derived classes - no duplication
class User : EntityBase {
    [string]$Name
    [string]$Email

    [bool] Validate() {
        return $this.ValidateString($this.Name, 2) -and $this.ValidateEmail($this.Email)
    }
}

class Customer : EntityBase {
    [string]$CompanyName
    [string]$ContactEmail

    [bool] Validate() {
        return $this.ValidateString($this.CompanyName, 2) -and $this.ValidateEmail($this.ContactEmail)
    }
}
```

---

### Use Static Utility Classes for Common Operations

**❌ Bad - Duplicated file operations**:
```powershell
function Process-ConfigFile {
    $configPath = Join-Path $PSScriptRoot "config.json"
    if (Test-Path $configPath) {
        $content = Get-Content $configPath -Raw
        return $content | ConvertFrom-Json
    }
    return $null
}

function Process-SettingsFile {
    $settingsPath = Join-Path $PSScriptRoot "settings.json"
    if (Test-Path $settingsPath) {
        $content = Get-Content $settingsPath -Raw
        return $content | ConvertFrom-Json
    }
    return $null
}
```

**✅ Good - Static utility class**:
```powershell
class FileHelper {
    hidden FileHelper() {
        throw "FileHelper is a static utility class"
    }

    static [PSCustomObject] ReadJson([string]$FilePath) {
        if (-not [System.IO.File]::Exists($FilePath)) {
            return $null
        }

        $content = [System.IO.File]::ReadAllText($FilePath)
        return [System.Text.Json.JsonSerializer]::Deserialize($content, [PSCustomObject])
    }

    static [bool] WriteJson([string]$FilePath, [object]$Data) {
        try {
            $json = [System.Text.Json.JsonSerializer]::Serialize($Data)
            [System.IO.File]::WriteAllText($FilePath, $json)
            return $true
        }
        catch {
            return $false
        }
    }
}

# Usage - no duplication
function Process-ConfigFile {
    $configPath = [System.IO.Path]::Combine($PSScriptRoot, "config.json")
    return [FileHelper]::ReadJson($configPath)
}

function Process-SettingsFile {
    $settingsPath = [System.IO.Path]::Combine($PSScriptRoot, "settings.json")
    return [FileHelper]::ReadJson($settingsPath)
}
```

---

### Use Advanced Functions with Pipeline Support

**❌ Bad - Separate functions for single/multiple items**:
```powershell
function Convert-UserToJson {
    param([object]$User)
    return $User | ConvertTo-Json -Depth 5
}

function Convert-UsersToJson {
    param([object[]]$Users)
    return $Users | ConvertTo-Json -Depth 5
}
```

**✅ Good - Single function with pipeline support**:
```powershell
function Convert-UserToJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [object]$User
    )

    process {
        return $User | ConvertTo-Json -Depth 5
    }
}

# Usage - works for single or multiple
$user | Convert-UserToJson
$users | Convert-UserToJson
```

---

## Testing with Pester

### Write Tests for All Functions

**Structure**:
```
MyModule/
├── MyModule.psm1
├── Tests/
│   ├── Unit/
│   │   ├── DatabaseConnection.Tests.ps1
│   │   └── SqlRepository.Tests.ps1
│   └── Integration/
│       └── DatabaseModule.Tests.ps1
```

**Unit Test Example**:
```powershell
#Requires -Version 7.0

BeforeAll {
    using module ../MyModule.psm1
}

Describe "DatabaseConnection" {
    Context "Constructor" {
        It "Should create connection with valid parameters" {
            $connection = [DatabaseConnection]::new("localhost", "testdb")

            $connection.Server | Should -Be "localhost"
            $connection.Database | Should -Be "testdb"
            $connection.Timeout | Should -Be 30
        }
    }

    Context "GetConnectionString" {
        It "Should return valid connection string" {
            $connection = [DatabaseConnection]::new("localhost", "testdb")

            $result = $connection.GetConnectionString()

            $result | Should -Match "Server=localhost"
            $result | Should -Match "Database=testdb"
        }
    }

    Context "TestConnection" {
        It "Should return true for valid connection" {
            $connection = [DatabaseConnection]::new("localhost", "testdb")

            $result = $connection.TestConnection()

            $result | Should -Be $true
        }
    }
}
```

**Integration Test Example**:
```powershell
#Requires -Version 7.0

BeforeAll {
    using module ../MyModule.psm1

    # Setup test database
    $script:connection = [DatabaseConnection]::new("localhost", "testdb")
}

Describe "SqlRepository Integration Tests" {
    Context "ExecuteQuery" {
        It "Should retrieve users from database" {
            $repository = [SqlRepository]::new($script:connection)

            $users = $repository.ExecuteQuery("SELECT * FROM Users")

            $users | Should -Not -BeNullOrEmpty
            $users[0].Id | Should -BeOfType [int]
        }
    }
}

AfterAll {
    # Cleanup test database
}
```

---

## Best Practices

### Error Handling

```powershell
#Requires -Version 7.0

function Get-UserData {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [int]$UserId
    )

    try {
        $ErrorActionPreference = 'Stop'

        # Use C# for performance
        $data = [System.IO.File]::ReadAllText("users/$UserId.json")
        return [System.Text.Json.JsonSerializer]::Deserialize($data, [PSCustomObject])
    }
    catch [System.IO.FileNotFoundException] {
        Write-Error "User $UserId not found"
        return $null
    }
    catch {
        Write-Error "Failed to load user data: $_"
        throw
    }
}
```

### Parameter Validation

```powershell
#Requires -Version 7.0

function New-DatabaseConnection {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Server,

        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Database,

        [ValidateRange(1, 300)]
        [int]$Timeout = 30
    )

    return [DatabaseConnection]::new($Server, $Database)
}
```

### Advanced Functions

```powershell
#Requires -Version 7.0

function Test-DatabaseExists {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [string]$DatabaseName
    )

    process {
        # Use C# for performance
        $query = "SELECT 1 FROM sys.databases WHERE name = '$DatabaseName'"
        $result = Invoke-SqlQuery -Query $query
        return $null -ne $result
    }
}
```

---

## Pipeline Optimization

### Avoid Unnecessary Pipeline Operations

```powershell
# ❌ Slow - Multiple pipeline operations
$result = Get-ChildItem | Where-Object { $_.Extension -eq '.txt' } | ForEach-Object { $_.Name }

# ✅ Fast - C# LINQ-style
$files = [System.IO.Directory]::GetFiles($path, "*.txt")
$result = $files | ForEach-Object { [System.IO.Path]::GetFileName($_) }

# ✅ Even faster - Pure C#
$files = [System.IO.Directory]::GetFiles($path, "*.txt")
$result = $files.ForEach({ [System.IO.Path]::GetFileName($_) })
```

---

## Naming Conventions

### Functions

```powershell
# ✅ Good - Approved verb, clear noun
function Get-UserById { }
function Set-UserEmail { }
function Test-EmailFormat { }
function New-UserAccount { }
function Remove-UserSession { }
```

### Classes

```powershell
# ✅ Good - PascalCase, descriptive
class UserRepository { }
class EmailValidator { }
class SqlConnectionFactory { }
```

### Variables

```powershell
# ✅ Good - camelCase for local, PascalCase for params
$userId = 123
$connectionString = "..."

[Parameter()]
[string]$ServerName
```

---

## Examples

### Complete Module Example

**DatabaseModule.psm1**:
```powershell
#Requires -Version 7.0
using namespace System.Data.SqlClient
using namespace System.Collections.Generic

class DatabaseConnection {
    [string]$ConnectionString

    DatabaseConnection([string]$server, [string]$database) {
        $this.ConnectionString = "Server=$server;Database=$database;Integrated Security=true"
    }

    [List[PSCustomObject]] ExecuteQuery([string]$query) {
        $results = [List[PSCustomObject]]::new()

        $connection = [SqlConnection]::new($this.ConnectionString)
        try {
            $connection.Open()
            $command = [SqlCommand]::new($query, $connection)
            $reader = $command.ExecuteReader()

            while ($reader.Read()) {
                $row = @{}
                for ($i = 0; $i -lt $reader.FieldCount; $i++) {
                    $row[$reader.GetName($i)] = $reader.GetValue($i)
                }
                $results.Add([PSCustomObject]$row)
            }
        }
        finally {
            $connection.Close()
        }

        return $results
    }
}

function Get-DatabaseUsers {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [DatabaseConnection]$Connection
    )

    return $Connection.ExecuteQuery("SELECT * FROM Users")
}

Export-ModuleMember -Function Get-DatabaseUsers
```

**Usage**:
```powershell
#Requires -Version 7.0
using module .\DatabaseModule.psm1

$connection = [DatabaseConnection]::new("localhost", "mydb")
$users = Get-DatabaseUsers -Connection $connection
```

---

## References

- [PowerShell Approved Verbs](https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands)
- [PowerShell Classes](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_classes)
- [.NET API Browser](https://learn.microsoft.com/en-us/dotnet/api/)

---

**These standards apply to all PowerShell development.**
