"""
Automated SOX Control Testing - Retail Banking
Step 5: Build the deficiency log from the Step 4 exceptions report.

Run from the project folder:   python python/04_build_deficiency_log.py
Input:  output/SOX_Exceptions_Report.xlsx   (created by Step 4)
Output: output/SOX_Deficiency_Log.xlsx
  - Deficiency_Log sheet: one row per FAILED control, with SOX classification,
    owner, root cause, remediation plan and due date
"""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
REPORT_IN = OUTPUT_DIR / "SOX_Exceptions_Report.xlsx"
LOG_OUT = OUTPUT_DIR / "SOX_Deficiency_Log.xlsx"

IDENTIFIED_DATE = date(2025, 12, 31)       # same test period end as Step 4

# Severity from Step 4 -> SOX classification and days allowed to remediate
SOX_CLASSIFICATION = {
    "High":   ("Significant Deficiency", 30),
    "Medium": ("Control Deficiency", 60),
}

# Owner, likely root cause and remediation action for each control
CONTROL_DETAILS = {
    1: ("GL Accounting Manager",
        "System allows preparer to approve own journal entry",
        "Configure system to block self-approval; review all self-approved entries"),
    2: ("Financial Controller",
        "No system enforcement of second approval above $50K",
        "Add workflow rule requiring second approver for entries over $50K"),
    3: ("IT Access Management Lead",
        "HR termination feed not linked to access removal",
        "Automate access removal from HR feed; disable the flagged accounts now"),
    4: ("Reconciliation Team Lead",
        "Month-end workload exceeds team capacity",
        "Add recon deadline tracker and escalation at day 4"),
    5: ("Operations Manager",
        "No aging review or escalation for suspense items",
        "Weekly aging review; escalate items open over 30 days"),
}


def main():
    summary = pd.read_excel(REPORT_IN, sheet_name="Summary")
    failed = summary[summary["Result"] == "Fail"]

    rows = []
    for i, r in enumerate(failed.itertuples(index=False), start=1):
        num = r[0]                                   # Control #
        severity = r[5]                              # Severity if failed
        classification, days = SOX_CLASSIFICATION[severity]
        owner, root_cause, action = CONTROL_DETAILS[num]
        rows.append({
            "Deficiency ID": f"DEF-{i:03d}",
            "Control #": num,
            "Control name": r[1],
            "Exceptions": r[3],
            "Population tested": r[2],
            "Risk severity": severity,
            "SOX classification": classification,
            "Root cause": root_cause,
            "Remediation action": action,
            "Owner": owner,
            "Identified date": IDENTIFIED_DATE,
            "Remediation due date": IDENTIFIED_DATE + timedelta(days=days),
            "Status": "Open",
        })

    log = pd.DataFrame(rows)
    with pd.ExcelWriter(LOG_OUT, engine="openpyxl") as xw:
        log.to_excel(xw, sheet_name="Deficiency_Log", index=False)
        ws = xw.book["Deficiency_Log"]
        for col in ws.columns:                       # widen columns so it's readable
            width = max(len(str(c.value or "")) for c in col) + 2
            ws.column_dimensions[col[0].column_letter].width = min(width, 60)

    print(f"{len(log)} deficiencies logged")
    print(log[["Deficiency ID", "Control name", "SOX classification",
               "Owner", "Remediation due date"]].to_string(index=False))
    print(f"\nLog saved: {LOG_OUT}")


if __name__ == "__main__":
    main()
