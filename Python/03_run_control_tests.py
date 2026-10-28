"""
Automated SOX Control Testing - Retail Banking
Step 4: Run the 5 control tests and write the exceptions report.

Run from the project folder:   python python/03_run_control_tests.py
Test from CSVs (no SQL):       python python/03_run_control_tests.py --csv-only

Output: output/SOX_Exceptions_Report.xlsx
  - Summary sheet: one row per control (population, exceptions, result)
  - One sheet per control listing every exception found
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

SERVER = r"localhost\MSSQLSERVER01"
DATABASE = "SOX_Testing"
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

AS_OF_DATE = date(2025, 12, 31)      # test period end
APPROVAL_THRESHOLD = 50_000          # Control 2
RECON_DAYS_ALLOWED = 5               # Control 4: business days after month-end
RECON_ON_TIME_TARGET = 0.95          # Control 4: 95% on time
SUSPENSE_MAX_DAYS = 30               # Control 5

TABLES = ["journal_entries", "hr_terminations", "user_access",
          "account_reconciliations", "suspense_items"]
DATE_COLS = ["entry_date", "termination_date", "last_login_date", "disabled_date",
             "period_end_date", "completed_date", "open_date", "cleared_date"]


# ---------- Load data ----------
def load_tables():
    """Read all 5 tables, from SQL Server or (with --csv-only) from the data folder."""
    if "--csv-only" in sys.argv:
        tables = {t: pd.read_csv(DATA_DIR / f"{t}.csv") for t in TABLES}
    else:
        import pyodbc
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
        )
        cur = conn.cursor()
        tables = {}
        for t in TABLES:
            cur.execute(f"SELECT * FROM {t}")
            cols = [c[0] for c in cur.description]
            tables[t] = pd.DataFrame.from_records(cur.fetchall(), columns=cols)
        conn.close()

    for df in tables.values():   # make sure date columns are real dates
        for col in DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
    return tables


# ---------- The 5 control tests ----------
# Each test returns (population_size, exceptions_dataframe)

def test_1_segregation_of_duties(t):
    je = t["journal_entries"]
    exceptions = je[je["preparer_id"] == je["approver_id"]]
    return len(je), exceptions


def test_2_approval_threshold(t):
    je = t["journal_entries"]
    population = je[je["amount"] > APPROVAL_THRESHOLD]
    exceptions = population[population["second_approver_id"].isna()]
    return len(population), exceptions


def test_3_terminated_user_access(t):
    hr, ua = t["hr_terminations"], t["user_access"]
    merged = ua.merge(hr, on="employee_id", how="inner")   # access rows for terminated staff
    exceptions = merged[merged["access_status"] == "Active"]
    return len(hr), exceptions


def test_4_reconciliation_timeliness(t):
    rc = t["account_reconciliations"].copy()
    rc["business_days_to_complete"] = np.busday_count(
        rc["period_end_date"].values.astype("datetime64[D]"),
        rc["completed_date"].values.astype("datetime64[D]"),
    )
    exceptions = rc[rc["business_days_to_complete"] > RECON_DAYS_ALLOWED]
    return len(rc), exceptions


def test_5_suspense_aging(t):
    si = t["suspense_items"].copy()
    population = si[si["cleared_date"].isna()].copy()       # open items at period end
    population["days_open"] = (pd.Timestamp(AS_OF_DATE) - population["open_date"]).dt.days
    exceptions = population[population["days_open"] > SUSPENSE_MAX_DAYS]
    return len(population), exceptions


CONTROLS = [
    (1, "Segregation of duties",     "High",   test_1_segregation_of_duties),
    (2, "Approval threshold",        "High",   test_2_approval_threshold),
    (3, "Terminated user access",    "High",   test_3_terminated_user_access),
    (4, "Reconciliation timeliness", "Medium", test_4_reconciliation_timeliness),
    (5, "Suspense account aging",    "Medium", test_5_suspense_aging),
]


# ---------- Run tests and build report ----------
def main():
    tables = load_tables()
    summary_rows, exception_sheets = [], {}

    for num, name, severity, test in CONTROLS:
        population, exceptions = test(tables)
        n_exc = len(exceptions)

        if num == 4:   # Control 4 passes on a % target, not zero exceptions
            on_time = 1 - n_exc / population if population else 1
            result = "Pass" if on_time >= RECON_ON_TIME_TARGET else "Fail"
            note = f"{on_time:.1%} on time (target {RECON_ON_TIME_TARGET:.0%})"
        else:
            result = "Pass" if n_exc == 0 else "Fail"
            note = ""

        summary_rows.append({
            "Control #": num, "Control name": name, "Population tested": population,
            "Exceptions": n_exc, "Result": result,
            "Severity if failed": severity if result == "Fail" else "",
            "Note": note,
        })
        exception_sheets[f"C{num} {name}"[:31]] = exceptions
        print(f"Control {num} - {name}: {population} tested, {n_exc} exceptions -> {result}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    report = OUTPUT_DIR / "SOX_Exceptions_Report.xlsx"
    with pd.ExcelWriter(report, engine="openpyxl") as xw:
        pd.DataFrame(summary_rows).to_excel(xw, sheet_name="Summary", index=False)
        for sheet, df in exception_sheets.items():
            out = df.copy()
            for col in out.select_dtypes("datetime").columns:
                out[col] = out[col].dt.date
            out.to_excel(xw, sheet_name=sheet, index=False)
        for ws in xw.book.worksheets:   # widen columns so the report is readable
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(width, 45)
    print(f"\nReport saved: {report}")


if __name__ == "__main__":
    main()
