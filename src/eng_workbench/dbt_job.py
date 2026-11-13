"""Write dbt seeds and build the semantic models on DuckDB."""

import csv
import os
import subprocess
import sys
from pathlib import Path

from eng_workbench.synthetic import lab_records

ROOT = Path(__file__).resolve().parents[2]
DBT = ROOT / "dbt"


def write_seeds() -> None:
    records = lab_records()
    seeds = DBT / "seeds"
    seeds.mkdir(parents=True, exist_ok=True)
    tables = {
        "firmware_builds": records["builds"],
        "test_runs": records["runs"],
        "failures": records["failures"],
    }
    for name, rows in tables.items():
        path = seeds / f"{name}.csv"
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def dbt_executable() -> Path:
    name = "dbt.exe" if os.name == "nt" else "dbt"
    return Path(sys.executable).resolve().parent / name


def duckdb_path() -> Path:
    return DBT / "target" / "ridge.duckdb"


def run_dbt() -> int:
    write_seeds()
    binary = dbt_executable()
    if not binary.is_file():
        return 127
    completed = subprocess.run(
        [str(binary), "build", "--project-dir", str(DBT), "--profiles-dir", str(DBT)],
        check=False,
        cwd=str(DBT),
    )
    return completed.returncode
