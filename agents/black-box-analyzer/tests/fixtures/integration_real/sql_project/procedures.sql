CREATE PROCEDURE CreateUser(IN p_email VARCHAR(255), IN p_display_name VARCHAR(100))
BEGIN
    INSERT INTO users (email, display_name) VALUES (p_email, p_display_name);
END;

CREATE OR ALTER PROCEDURE DeactivateUser(IN p_user_id INT)
BEGIN
    UPDATE users SET is_active = 0 WHERE id = p_user_id;
END;
