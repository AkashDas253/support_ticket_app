## Support Ticket App

### Seed Schema and Data

```sql
-- 1. Create Schema and Tables
CREATE SCHEMA IF NOT EXISTS support_system;

CREATE TABLE IF NOT EXISTS support_system.tickets (
    ticket_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_system.ticket_messages (
    message_id VARCHAR(50) PRIMARY KEY,
    ticket_id VARCHAR(50) NOT NULL REFERENCES support_system.tickets(ticket_id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Insert Sample Data
INSERT INTO support_system.tickets (ticket_id, title, status, created_by, created_at)
VALUES 
    ('t-1001', 'Unable to connect to Lakebase cluster', 'open', 'alice@company.com', NOW() - INTERVAL '2 days'),
    ('t-1002', 'Pipeline execution failure in ETL job', 'in_progress', 'bob@company.com', NOW() - INTERVAL '1 day'),
    ('t-1003', 'Request for SQL warehouse access', 'resolved', 'charlie@company.com', NOW() - INTERVAL '3 days');

INSERT INTO support_system.ticket_messages (message_id, ticket_id, message_text, author, created_at)
VALUES 
    ('m-2001', 't-1001', 'I am receiving a connection timeout when initializing the DAL driver.', 'alice@company.com', NOW() - INTERVAL '2 days'),
    ('m-2002', 't-1001', 'Thanks for reaching out. We are verifying network routing and SSL settings.', 'support_agent@company.com', NOW() - INTERVAL '1 day 23 hours'),
    
    ('m-2003', 't-1002', 'The nightly ETL failed at task run_gold_tables with exit code 1.', 'bob@company.com', NOW() - INTERVAL '1 day'),
    ('m-2004', 't-1002', 'Reviewing cluster memory logs. Increasing driver node size to test.', 'support_agent@company.com', NOW() - INTERVAL '20 hours'),
    
    ('m-2005', 't-1003', 'Please grant read permissions on support_system schema to my role.', 'charlie@company.com', NOW() - INTERVAL '3 days'),
    ('m-2006', 't-1003', 'Permissions granted via Databricks Unity Catalog role mapping. Resolving.', 'support_agent@company.com', NOW() - INTERVAL '2 days 22 hours');
```

###  Priviledge Granted

```sql
-- 1. Grant schema usage privilege
GRANT USAGE ON SCHEMA support_system TO <db_role>;

-- 2. Grant privileges on all existing tables in the schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA support_system TO <db_role>;

-- 3. Ensure future tables created in this schema automatically grant privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA support_system 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <db_role>;

```