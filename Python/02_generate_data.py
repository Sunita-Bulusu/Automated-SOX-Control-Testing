"""
Automated SOX Control Testing - Retail Banking
Step 3: Generate test data (with planted exceptions) and load it into SQL Server.

Run from the project folder:   python python/02_generate_data.py
Test without SQL Server:       python python/02_generate_data.py --csv-only

Data is synthetic. Exceptions are planted on purpose so the control tests
in Step 4 have something to catch. random.seed(42) keeps it the same every run.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)

SERVER = r"localhost\MSSQLSERVER01"
DATABASE = "SOX_Testing"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

YEAR_START, YEAR_END = date(2025, 1, 1), date(2025, 12, 31)
EMPLOYEES = [f"E{n:03d}" for n in range(1, 41)]
GL_ACCOUNTS = ["1010", "1200", "1450", "2100", "2300", "3100", "4000", "4100", "5200", "6100"]


def rand_date(start=YEAR_START, end=YEAR_END):
    return start + timedelta(days=random.randint(0, (end - start).days))


# ---------- Controls 1 & 2: journal_entries ----------
def make_journal_entries(n=150):
    rows = []
    for i in range(1, n + 1):
        preparer = random.choice(EMPLOYEES)
        approver = random.choice([e for e in EMPLOYEES if e != preparer])
        amount = round(random.choice([random.uniform(500, 49_999), random.uniform(50_000, 750_000)]), 2)
        second = random.choice([e for e in EMPLOYEES if e not in (preparer, approver)]) if amount > 50_000 else None
        rows.append({
            "je_id": f"JE{i:04d}", "entry_date": rand_date(), "gl_account": random.choice(GL_ACCOUNTS),
            "description": random.choice(["Accrual", "Fee reversal", "Loan interest adj", "Deposit correction", "Expense reclass"]),
            "amount": amount, "preparer_id": preparer, "approver_id": approver, "second_approver_id": second,
        })
    df = pd.DataFrame(rows)
    # Planted exceptions - Control 1: self-approval (4 rows)
    for idx in random.sample(range(n), 4):
        df.at[idx, "approver_id"] = df.at[idx, "preparer_id"]
    # Planted exceptions - Control 2: large entry with no second approver (3 rows)
    large = df.index[df["amount"] > 50_000].tolist()
    for idx in random.sample(large, 3):
        df.at[idx, "second_approver_id"] = None
    return df


# ---------- Control 3: hr_terminations + user_access ----------
def make_terminations_and_access():
    terminated = random.sample(EMPLOYEES, 12)
    hr = pd.DataFrame([{
        "employee_id": e, "employee_name": f"Employee {e[1:]}",
        "department": random.choice(["Retail Ops", "Deposits", "Lending", "Finance", "IT"]),
        "termination_date": rand_date(date(2025, 1, 1), date(2025, 11, 30)),
    } for e in terminated])

    systems = ["Core Banking", "GL System", "Loan Origination", "Online Banking Admin"]
    access, n = [], 1
    for e in EMPLOYEES:
        term = hr.loc[hr.employee_id == e, "termination_date"]
        term = term.iloc[0] if len(term) else None
        for s in random.sample(systems, 2):
            if term:
                status, disabled, last_login = "Disabled", term + timedelta(days=random.randint(0, 2)), term
            else:
                status, disabled, last_login = "Active", None, rand_date(date(2025, 11, 1))
            access.append({"access_id": f"UA{n:04d}", "employee_id": e, "system_name": s,
                           "access_status": status, "last_login_date": last_login, "disabled_date": disabled})
            n += 1
    ua = pd.DataFrame(access)
    # Planted exceptions - Control 3: terminated users still active (3 rows)
    term_rows = ua.index[ua["employee_id"].isin(terminated)].tolist()
    for idx in random.sample(term_rows, 3):
        ua.at[idx, "access_status"] = "Active"
        ua.at[idx, "disabled_date"] = None
    return hr, ua


# ---------- Control 4: account_reconciliations ----------
def make_reconciliations():
    rows, n = [], 1
    for m in range(1, 13):
        period_end = (pd.Timestamp(2025, m, 1) + pd.offsets.MonthEnd(0)).date()
        for acct in GL_ACCOUNTS:
            days = random.randint(1, 5)  # business days after month-end (on time)
            done = (pd.Timestamp(period_end) + pd.offsets.BDay(days)).date()
            prep, rev = random.sample(EMPLOYEES, 2)
            rows.append({"recon_id": f"RC{n:04d}", "gl_account": acct, "period_end_date": period_end,
                         "completed_date": done, "preparer_id": prep, "reviewer_id": rev})
            n += 1
    df = pd.DataFrame(rows)
    # Planted exceptions - Control 4: 8 late of 120 = 93.3% on time (fails the 95% target)
    for idx in random.sample(range(len(df)), 8):
        df.at[idx, "completed_date"] = (pd.Timestamp(df.at[idx, "period_end_date"])
                                        + pd.offsets.BDay(random.randint(7, 15))).date()
    return df


# ---------- Control 5: suspense_items ----------
def make_suspense(n=80):
    rows = []
    for i in range(1, n + 1):
        opened = rand_date(date(2025, 1, 1), date(2025, 12, 20))
        cleared = opened + timedelta(days=random.randint(1, 20))
        rows.append({"item_id": f"SI{i:04d}", "suspense_account": random.choice(["1900", "1910", "1920"]),
                     "open_date": opened, "cleared_date": cleared if cleared <= YEAR_END else None,
                     "amount": round(random.uniform(100, 25_000), 2),
                     "reason": random.choice(["Unmatched ACH", "Wire pending", "ATM imbalance", "Check misread"])})
    df = pd.DataFrame(rows)
    # Planted exceptions - Control 5: 5 items open more than 30 days at Dec 31, 2025
    for idx in random.sample(range(n), 5):
        df.at[idx, "open_date"] = rand_date(date(2025, 8, 1), date(2025, 11, 15))
        df.at[idx, "cleared_date"] = None
    return df


def load_to_sql(tables):
    import pyodbc
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
    )
    cur = conn.cursor()
    cur.fast_executemany = True
    for name, df in tables.items():
        cur.execute(f"DELETE FROM {name}")  # safe to re-run
        cols = ", ".join(df.columns)
        marks = ", ".join("?" * len(df.columns))
        data = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False)]
        cur.executemany(f"INSERT INTO {name} ({cols}) VALUES ({marks})", data)
        print(f"  {name}: {len(df)} rows loaded")
    conn.commit()
    conn.close()


def main():
    hr, ua = make_terminations_and_access()
    tables = {
        "journal_entries": make_journal_entries(),
        "hr_terminations": hr,
        "user_access": ua,
        "account_reconciliations": make_reconciliations(),
        "suspense_items": make_suspense(),
    }
    DATA_DIR.mkdir(exist_ok=True)
    for name, df in tables.items():
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)
    print(f"CSVs saved to {DATA_DIR}")

    if "--csv-only" not in sys.argv:
        load_to_sql(tables)
        print("All tables loaded into SQL Server.")


if __name__ == "__main__":
    main()
