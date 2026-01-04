DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_type') THEN
        CREATE TYPE account_type AS ENUM ('company', 'individual', 'loan');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS account (
    username VARCHAR(100) PRIMARY KEY,
    password VARCHAR(100) NOT NULL,
    type account_type NOT NULL
);

CREATE TABLE IF NOT EXISTS company (
    company_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    CONSTRAINT fk_company_account
        FOREIGN KEY (username) REFERENCES account(username)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS groups (
    group_id SERIAL PRIMARY KEY,         
    company_id INT NOT NULL,                          
    CONSTRAINT fk_group_company
        FOREIGN KEY (company_id) 
        REFERENCES company(company_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS individual (
    user_id SERIAL PRIMARY KEY,          
    group_id INT NOT NULL,              
    username VARCHAR(100) NOT NULL,     
    user_full_name VARCHAR(200),             
    CONSTRAINT fk_individual_group
        FOREIGN KEY (group_id) 
        REFERENCES groups(group_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_individual_account
        FOREIGN KEY (username) 
        REFERENCES account(username)
        ON DELETE CASCADE
);

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

Select * from individual;