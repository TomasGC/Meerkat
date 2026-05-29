---
paths:
  - "**/*.sql"
  - "**/StoredProcedures/**/*.sql"
---

# SQL Server Standards

T-SQL best practices for Microsoft SQL Server.

---

## Stored Procedures

```sql
-- ✅ Good - Use parameters, error handling
CREATE PROCEDURE dbo.usp_GetUserOrders
    @UserId INT,
    @StartDate DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        SELECT o.OrderId, o.Total, o.CreatedAt
        FROM dbo.Orders o
        WHERE o.UserId = @UserId
          AND (@StartDate IS NULL OR o.CreatedAt >= @StartDate)
        ORDER BY o.CreatedAt DESC;
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END
GO
```

---

## Naming Conventions

```sql
-- ✅ Good - Consistent naming
-- Tables: PascalCase, plural
CREATE TABLE dbo.Users (...);
CREATE TABLE dbo.Orders (...);

-- Stored procedures: usp_ prefix
CREATE PROCEDURE dbo.usp_CreateUser ...
CREATE PROCEDURE dbo.usp_GetUserById ...

-- Functions: fn_ prefix
CREATE FUNCTION dbo.fn_CalculateTax ...

-- Views: vw_ prefix
CREATE VIEW dbo.vw_ActiveUsers ...

-- Indexes: idx_table_column
CREATE INDEX idx_Users_Email ON dbo.Users(Email);
```

---

## Transactions

```sql
-- ✅ Good - Explicit transactions with error handling
BEGIN TRANSACTION;
BEGIN TRY
    INSERT INTO dbo.Users (Email, Name) VALUES (@Email, @Name);
    SET @UserId = SCOPE_IDENTITY();

    INSERT INTO dbo.Accounts (UserId, Balance) VALUES (@UserId, 0.00);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH
```

---

## Indexing

```sql
-- ✅ Good - Clustered index on primary key
CREATE TABLE dbo.Users (
    UserId INT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    Email NVARCHAR(255) NOT NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- ✅ Good - Non-clustered indexes for queries
CREATE NONCLUSTERED INDEX idx_Users_Email
ON dbo.Users(Email)
INCLUDE (Name, CreatedAt);

-- ✅ Good - Filtered index
CREATE NONCLUSTERED INDEX idx_ActiveUsers
ON dbo.Users(Email)
WHERE IsActive = 1;
```

---

## Data Types

```sql
-- ✅ Good - Appropriate types
CREATE TABLE dbo.Orders (
    OrderId BIGINT IDENTITY(1,1) PRIMARY KEY,
    UserId BIGINT NOT NULL,
    Total DECIMAL(18, 2) NOT NULL,           -- DECIMAL for money
    Status NVARCHAR(50) NOT NULL,
    Metadata NVARCHAR(MAX),                   -- JSON data
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- ❌ Bad - Wrong types
CREATE TABLE dbo.Orders (
    OrderId INT,                              -- Too small
    Total FLOAT,                              -- Precision issues
    CreatedAt DATETIME                        -- Less precise than DATETIME2
);
```

---

## Performance

```sql
-- ✅ Good - Use SET NOCOUNT ON
CREATE PROCEDURE dbo.usp_UpdateUser
AS
BEGIN
    SET NOCOUNT ON;
    -- Your queries
END

-- ✅ Good - Use table variables for small datasets
DECLARE @UserIds TABLE (UserId INT);
INSERT INTO @UserIds SELECT UserId FROM dbo.Users WHERE IsActive = 1;

-- ✅ Good - Use temp tables for large datasets
CREATE TABLE #ActiveUsers (
    UserId INT PRIMARY KEY,
    Email NVARCHAR(255)
);
INSERT INTO #ActiveUsers SELECT UserId, Email FROM dbo.Users WHERE IsActive = 1;
CREATE INDEX idx_Temp ON #ActiveUsers(Email);
```

---

**Write efficient T-SQL for SQL Server.**
