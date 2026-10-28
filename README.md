# Automated SOX Control Testing – Retail Banking

Automated testing of five key SOX controls for a retail bank, using **SQL Server** for the data and **Python** for the tests. Every transaction in the population is tested (no sampling), every exception is written to an Excel report, and every failed control becomes a deficiency with a SOX classification, owner and remediation date.

> **Data note:** All data is synthetic. Exceptions were planted on purpose so each test has something to catch, which proves the tests work.

---

## What it does

| Step | File | What happens |
|---|---|---|
| 1. Test plan | `docs/SOX_Test_Plan.xlsx` | Defines each control, its objective, population, test logic, pass criteria and severity |
| 2. Database | `sql/01_create_tables.sql` | Creates the `SOX_Testing` database and its 5 tables in SQL Server |
| 3. Test data | `python/02_generate_data.py` | Generates the data with planted exceptions and loads it into SQL Server |
| 4. Control tests | `python/03_run_control_tests.py` | Runs the 5 tests and writes `output/SOX_Exceptions_Report.xlsx` |
| 5. Deficiency log | `python/04_build_deficiency_log.py` | Turns every failed control into a deficiency in `output/SOX_Deficiency_Log.xlsx` |

---

## The 5 controls

| # | Control | Type | Rule tested | Pass criteria | Severity |
|---|---|---|---|---|---|
| 1 | Segregation of duties | Preventive | Preparer is not the approver of a journal entry | 0 exceptions | High |
| 2 | Approval threshold | Preventive | Journal entries over $50,000 have a second approver | 0 exceptions | High |
| 3 | Terminated user access | Detective | Terminated employees have no active system access | 0 exceptions | High |
| 4 | Reconciliation timeliness | Detective | Reconciliations completed within 5 business days of month-end | 95% on time | Medium |
| 5 | Suspense account aging | Detective | No open suspense item older than 30 days at Dec 31, 2025 | 0 items over 30 days | Medium |

Test period: January 1 – December 31, 2025.

---

## Results

All 5 controls failed, and the exception counts match the planted data exactly.

| ID | Control | Exceptions | SOX classification | Owner | Remediation due |
|---|---|---|---|---|---|
| DEF-001 | Segregation of duties | 4 | Significant Deficiency | GL Accounting Manager | 2026-01-30 |
| DEF-002 | Approval threshold | 3 | Significant Deficiency | Financial Controller | 2026-01-30 |
| DEF-003 | Terminated user access | 3 | Significant Deficiency | IT Access Management Lead | 2026-01-30 |
| DEF-004 | Reconciliation timeliness | 8 | Control Deficiency | Reconciliation Team Lead | 2026-03-01 |
| DEF-005 | Suspense account aging | 5 | Control Deficiency | Operations Manager | 2026-03-01 |

**Classification rule:** a failed High-severity control is logged as a Significant Deficiency with 30 days to remediate; a failed Medium-severity control is a Control Deficiency with 60 days. Whether several Significant Deficiencies together amount to a Material Weakness is a judgment for management and the external auditors, so the script does not decide it.

Owners, root causes and due dates are illustrative; in practice they are agreed with each control owner.

![Exceptions report summary](Images/Screenshot%202026-10-28%20144250.png)

---

## Why automate

- **Full population:** every journal entry, user and reconciliation is tested, not a sample of 25–40.
- **Repeatable:** the same tests run in seconds every quarter.
- **Audit trail:** raw data → exceptions report → deficiency log, each step saved as a file.

---

## Project structure

```
Automated-SOX-Testing-Control/
├── docs/     SOX_Test_Plan.xlsx
├── sql/      01_create_tables.sql
├── python/   02_generate_data.py
│             03_run_control_tests.py
│             04_build_deficiency_log.py
├── data/     generated CSVs (created by step 3)
└── output/   SOX_Exceptions_Report.xlsx
              SOX_Deficiency_Log.xlsx
```

---

## How to run

**Requirements:** SQL Server with SSMS, ODBC Driver 17 for SQL Server, Python 3 with:

```
pip install pandas numpy pyodbc openpyxl
```

1. In SSMS, run `sql/01_create_tables.sql` to create the `SOX_Testing` database.
2. From the project folder, run:

```
python python\02_generate_data.py
python python\03_run_control_tests.py
python python\04_build_deficiency_log.py
```

The server name is set at the top of each Python script (`localhost\MSSQLSERVER01`); change it to match yours.

---

## Tools

SQL Server · SSMS · Python (pandas, NumPy, pyodbc, openpyxl) · Excel

## Author

**Sunita Bulusu** — 14+ years in financial operations, OTC derivatives settlements, and operational risk & control management.
Related project: [Regulatory Risk & Compliance Dashboard](https://github.com/Sunita-Bulusu/Regulatory-Risk-Compliance-Dashboard)
