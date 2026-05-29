---
paths:
  - "**/*.sql"
  - "**/migrations/**/*"
---

# PostgreSQL Standards

SQL best practices for PostgreSQL databases.

---

## Query Style

```sql
-- ✅ Good - Uppercase keywords, readable
SELECT u.id, u.email, u.created_at
FROM users u
INNER JOIN orders o ON u.id = o.user_id
WHERE u.active = TRUE
  AND o.status = 'completed'
ORDER BY u.created_at DESC
LIMIT 100;

-- ❌ Bad - Lowercase, hard to read
select u.id,u.email from users u inner join orders o on u.id=o.user_id where u.active=true;
```

---

## Parameterized Queries

```sql
-- ✅ Good - Use parameters (prevents SQL injection)
-- Application code:
-- query = "SELECT * FROM users WHERE email = $1"
-- db.Query(query, email)

-- ❌ Bad - String concatenation (SQL injection risk)
-- query = "SELECT * FROM users WHERE email = '" + email + "'"
```

---

## Indexing

```sql
-- ✅ Good - Index frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status_created ON orders(status, created_at);

-- ✅ Good - Unique constraint as index
CREATE UNIQUE INDEX idx_users_email_unique ON users(email);

-- ✅ Good - Partial index for specific conditions
CREATE INDEX idx_active_users ON users(email) WHERE active = TRUE;

-- ✅ Good - Analyze index usage
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'john@example.com';
```

---

## Transactions

```sql
-- ✅ Good - Use transactions for data consistency
BEGIN;

INSERT INTO users (email, name) VALUES ('john@example.com', 'John');
INSERT INTO accounts (user_id, balance) VALUES (currval('users_id_seq'), 0.00);

COMMIT;

-- ✅ Good - Rollback on error
BEGIN;
INSERT INTO orders (user_id, total) VALUES (123, 99.99);
-- If error occurs
ROLLBACK;
```

---

## Migrations

```sql
-- ✅ Good - Reversible migrations
-- Migration: 001_create_users.up.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- Migration: 001_create_users.down.sql
DROP INDEX IF EXISTS idx_users_email;
DROP TABLE IF EXISTS users;
```

---

## Data Types

```sql
-- ✅ Good - Appropriate data types
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    total NUMERIC(10, 2) NOT NULL,      -- Use NUMERIC for money
    status VARCHAR(50) NOT NULL,
    metadata JSONB,                      -- Use JSONB for flexible data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ❌ Bad - Wrong types
CREATE TABLE orders (
    id INT,                              -- Too small, no auto-increment
    user_id INT,                         -- No foreign key
    total FLOAT,                         -- Precision issues with money
    status TEXT,                         -- No constraint
    metadata TEXT                        -- Can't query JSON efficiently
);
```

---

## Constraints

```sql
-- ✅ Good - Enforce data integrity
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    age INT CHECK (age >= 18),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'banned')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ✅ Good - Foreign keys with actions
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

---

## Performance

```sql
-- ✅ Good - Use EXISTS instead of IN for large datasets
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.id
);

-- ❌ Slower - IN with subquery
SELECT * FROM users u
WHERE u.id IN (SELECT user_id FROM orders);

-- ✅ Good - LIMIT for pagination
SELECT * FROM users
ORDER BY created_at DESC
LIMIT 20 OFFSET 40;

-- ✅ Good - Use CTEs for readability
WITH active_users AS (
    SELECT id, email FROM users WHERE active = TRUE
),
recent_orders AS (
    SELECT user_id, COUNT(*) as order_count
    FROM orders
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT au.email, COALESCE(ro.order_count, 0) as orders
FROM active_users au
LEFT JOIN recent_orders ro ON au.id = ro.user_id;
```

---

**Write efficient, secure PostgreSQL queries.**
