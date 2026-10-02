-- Order procedures for the shop database
CREATE PROCEDURE dbo.SearchOrders @customer NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    SET @sql = 'SELECT * FROM [dbo].orders WHERE customer = ''' + @customer + '''';
    EXEC(@sql);
END
GO

CREATE PROCEDURE dbo.ArchiveOrders
AS
BEGIN
    BEGIN TRY
        DELETE FROM [dbo].orders WHERE status = 42;
    END TRY
    BEGIN CATCH
    END CATCH
END
GO

CREATE PROCEDURE dbo.OrderTotals
AS
BEGIN
    -- TODO: exclude refunds
    SELECT customer, SUM(total) FROM [dbo].orders WITH (NOLOCK) GROUP BY customer;
END
GO

CREATE PROCEDURE dbo.ResetPassword @login NVARCHAR(100), @password NVARCHAR(100)
AS
BEGIN
    PRINT 'New password for ' + @login + ': ' + @password;
    UPDATE [dbo].users SET password_hash = HASHBYTES('SHA2_256', @password) WHERE login = @login;
END
GO

GRANT SELECT ON [dbo].orders TO PUBLIC;
GO
