CREATE TRIGGER users_audit_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO users_audit (user_id, action) VALUES (NEW.id, 'insert');
END;
