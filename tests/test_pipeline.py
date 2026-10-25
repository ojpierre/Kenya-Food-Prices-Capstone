from pathlib import Path
import pytest
from src.main import run_pipeline


def test_full_pipeline_run(tmp_path: Path):
    db_file = (tmp_path / "pipeline_test.db").as_posix()
    db_url = f"sqlite:///{db_file}"

    summary = run_pipeline(mode="replace", use_benchmark=True, database_url=db_url)

    assert summary["mode"] == "replace"
    assert summary["raw_rows"] == 9600
    assert summary["cleaned_rows"] == 9600
    assert summary["fact_rows"] == 9600
    assert summary["dq_status"] == "PASSED"
    assert summary["dq_passed_checks"] == 8
