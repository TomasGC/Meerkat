-- PostgreSQL stored procedures and triggers

CREATE OR REPLACE PROCEDURE sp_CreateUser(
    IN p_email VARCHAR(255),
    IN p_name VARCHAR(255),
    IN p_age INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO users (email, name, age, created_at)
    VALUES (p_email, p_name, p_age, NOW());
END;
$$;

CREATE OR REPLACE FUNCTION fn_GetUserByEmail(
    p_email VARCHAR(255)
)
RETURNS TABLE(id INT, email VARCHAR, name VARCHAR, age INT)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.name, u.age
    FROM users u
    WHERE u.email = p_email;
END;
$$;

CREATE OR REPLACE FUNCTION fn_CalculateDiscount(
    p_amount DECIMAL(10,2),
    p_percentage DECIMAL(5,2)
)
RETURNS DECIMAL(10,2)
LANGUAGE plpgsql
AS $$
DECLARE
    v_discount DECIMAL(10,2);
BEGIN
    v_discount := p_amount * (p_percentage / 100);
    RETURN v_discount;
END;
$$;

CREATE TRIGGER tr_UpdateTimestamp
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_UpdateTimestamp();

CREATE TRIGGER tr_ValidateEmail
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_ValidateEmail();
