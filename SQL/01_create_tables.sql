Create Database SOX_TESTING;

CREATE TABLE journal_entries (
    je_id               VARCHAR(10)    PRIMARY KEY,
    entry_date          DATE           NOT NULL,
    gl_account          VARCHAR(10)    NOT NULL,
    description         VARCHAR(100),
    amount              DECIMAL(15,2)  NOT NULL,
    preparer_id         VARCHAR(10)    NOT NULL,
    approver_id         VARCHAR(10),
    second_approver_id  VARCHAR(10)
);
CREATE TABLE hr_terminations (
    employee_id         VARCHAR(10)    PRIMARY KEY,
    employee_name       VARCHAR(50)    NOT NULL,
    department          VARCHAR(50),
    termination_date    DATE           NOT NULL
);

CREATE TABLE user_access (
    access_id           VARCHAR(10)    PRIMARY KEY,
    employee_id         VARCHAR(10)    NOT NULL,
    system_name         VARCHAR(50)    NOT NULL,
    access_status       VARCHAR(10)    NOT NULL,
    last_login_date     DATE,
    disabled_date       DATE
);
CREATE TABLE account_reconciliations (
    recon_id            VARCHAR(10)    PRIMARY KEY,
    gl_account          VARCHAR(10)    NOT NULL,
    period_end_date     DATE           NOT NULL,
    completed_date      DATE,
    preparer_id         VARCHAR(10),
    reviewer_id         VARCHAR(10)
);


CREATE TABLE suspense_items (
    item_id             VARCHAR(10)    PRIMARY KEY,
    suspense_account    VARCHAR(10)    NOT NULL,
    open_date           DATE           NOT NULL,
    cleared_date        DATE,                      -- NULL = still open
    amount              DECIMAL(15,2)  NOT NULL,
    reason              VARCHAR(100)
);