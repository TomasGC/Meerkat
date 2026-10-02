CREATE OR REPLACE FUNCTION fetch_report(p_id int)
RETURNS text AS $$
BEGIN
    RETURN (SELECT body FROM reports WHERE id = p_id);
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'report failed: %', SQLERRM;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION find_orders(p_table text, p_customer text)
RETURNS SETOF record AS $$
BEGIN
    RETURN QUERY EXECUTE 'SELECT * FROM ' || p_table || ' WHERE customer = ' || quote_literal(p_customer);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION purge_orders()
RETURNS void AS $$
BEGIN
    DELETE FROM orders WHERE status = 42;
EXCEPTION
    WHEN OTHERS THEN
        NULL;
END;
$$ LANGUAGE plpgsql;

GRANT ALL ON orders TO reporting;

SELECT dblink_connect('host=replica dbname=shop user=report password=changeme');
