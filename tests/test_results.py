"""Tests for results.py — ResultsManager."""

import csv
import json
from pathlib import Path

import pytest

from crawler import DiscoveryResult
from results import ResultsManager
from validator import ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_discovery(
    domain="example.gov",
    http_outcome="success",
    http_status=200,
    file_format="publiccode.yml",
    file_url="https://example.gov/publiccode.yml",
    redirect_chain=None,
    final_url="https://example.gov/publiccode.yml",
    error_message=None,
    response_time_ms=120.0,
):
    """Return a minimal DiscoveryResult for testing."""
    return DiscoveryResult(
        domain=domain,
        http_outcome=http_outcome,
        http_status=http_status,
        file_format=file_format,
        file_url=file_url,
        redirect_chain=redirect_chain or [],
        final_url=final_url,
        error_message=error_message,
        response_time_ms=response_time_ms,
    )


def _make_validation(
    yaml_valid=True,
    spec_valid=False,
    useful=False,
    usefulness_score=30,
    yaml_error=None,
    spec_errors=None,
    spec_warnings=None,
    usefulness_issues=None,
):
    """Return a minimal ValidationResult for testing."""
    return ValidationResult(
        yaml_valid=yaml_valid,
        spec_valid=spec_valid,
        useful=useful,
        usefulness_score=usefulness_score,
        yaml_error=yaml_error,
        spec_errors=spec_errors or [],
        spec_warnings=spec_warnings or [],
        usefulness_issues=usefulness_issues or [],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manager():
    """Return a fresh ResultsManager."""
    return ResultsManager()


# ---------------------------------------------------------------------------
# add_result
# ---------------------------------------------------------------------------

class TestAddResult:
    """Tests for ResultsManager.add_result."""

    def test_increments_total_domains(self, manager):
        """Each add_result call increments total_domains."""
        manager.add_result(_make_discovery())
        manager.add_result(_make_discovery(domain="other.gov"))
        assert manager.stats["total_domains"] == 2

    def test_result_stored_in_list(self, manager):
        """Results are stored and retrievable."""
        manager.add_result(_make_discovery())
        assert len(manager.results) == 1
        assert manager.results[0]["domain"] == "example.gov"

    def test_with_validation_yaml_valid_counted(self, manager):
        """yaml_valid stat incremented when validation yaml_valid=True."""
        manager.add_result(_make_discovery(), _make_validation(yaml_valid=True))
        assert manager.stats["yaml_valid"] == 1

    def test_with_validation_spec_valid_counted(self, manager):
        """spec_valid stat incremented when validation spec_valid=True."""
        manager.add_result(
            _make_discovery(), _make_validation(yaml_valid=True, spec_valid=True)
        )
        assert manager.stats["spec_valid"] == 1

    def test_with_validation_useful_counted(self, manager):
        """useful stat incremented when validation useful=True."""
        manager.add_result(
            _make_discovery(),
            _make_validation(yaml_valid=True, spec_valid=True, useful=True)
        )
        assert manager.stats["useful"] == 1

    def test_files_discovered_on_success_outcome(self, manager):
        """files_discovered incremented when http_outcome='success'."""
        manager.add_result(
            _make_discovery(http_outcome="success"),
            _make_validation(yaml_valid=True)
        )
        assert manager.stats["files_discovered"] == 1

    def test_not_found_outcome_counted(self, manager):
        """not_found stat incremented for 'not_found' outcome."""
        manager.add_result(_make_discovery(http_outcome="not_found"))
        assert manager.stats["not_found"] == 1

    def test_error_outcome_counted(self, manager):
        """errors stat incremented for error-type outcomes."""
        for outcome in ["error", "timeout", "ssl_error", "connection_error"]:
            manager.add_result(_make_discovery(http_outcome=outcome))
        assert manager.stats["errors"] == 4

    def test_without_validation_defaults(self, manager):
        """Result without validation has yaml_valid=False and score=0."""
        manager.add_result(_make_discovery())
        r = manager.results[0]
        assert r["yaml_valid"] is False
        assert r["usefulness_score"] == 0

    def test_long_yaml_error_truncated(self, manager):
        """yaml_error longer than 100 chars is truncated with ellipsis."""
        long_error = "E" * 150
        manager.add_result(
            _make_discovery(),
            _make_validation(yaml_valid=False, yaml_error=long_error)
        )
        stored = manager.results[0]["yaml_error"]
        assert len(stored) <= 100
        assert stored.endswith("...")

    def test_spec_errors_joined_with_semicolon(self, manager):
        """spec_errors list is joined with ';'."""
        validation = _make_validation(
            yaml_valid=True,
            spec_errors=["error one", "error two"]
        )
        manager.add_result(_make_discovery(), validation)
        assert manager.results[0]["spec_errors"] == "error one;error two"

    def test_redirect_chain_joined_with_semicolon(self, manager):
        """redirect_chain list is joined with ';'."""
        d = _make_discovery(
            redirect_chain=["https://a.gov", "https://b.gov"]
        )
        manager.add_result(d)
        assert manager.results[0]["redirect_chain"] == "https://a.gov;https://b.gov"

    def test_empty_redirect_chain_is_empty_string(self, manager):
        """Empty redirect_chain is stored as empty string."""
        manager.add_result(_make_discovery())
        assert manager.results[0]["redirect_chain"] == ""


# ---------------------------------------------------------------------------
# save_csv
# ---------------------------------------------------------------------------

class TestSaveCsv:
    """Tests for ResultsManager.save_csv."""

    def test_csv_file_created(self, manager, tmp_path):
        """CSV file is created when results exist."""
        manager.add_result(_make_discovery())
        out = str(tmp_path / "out.csv")
        manager.save_csv(out)
        assert Path(out).exists()

    def test_csv_has_correct_headers(self, manager, tmp_path):
        """CSV file contains expected column headers."""
        manager.add_result(_make_discovery())
        out = str(tmp_path / "out.csv")
        manager.save_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        assert "domain" in headers
        assert "yaml_valid" in headers
        assert "usefulness_score" in headers

    def test_csv_contains_data_row(self, manager, tmp_path):
        """CSV file contains the expected data row."""
        manager.add_result(_make_discovery(domain="test.gov"))
        out = str(tmp_path / "out.csv")
        manager.save_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["domain"] == "test.gov"

    def test_csv_no_results_does_not_crash(self, manager, tmp_path):
        """No results: save_csv logs a warning and does not raise."""
        out = str(tmp_path / "out.csv")
        manager.save_csv(out)  # should not raise
        assert not Path(out).exists()

    def test_csv_multiple_rows(self, manager, tmp_path):
        """Multiple add_result calls produce multiple CSV rows."""
        for i in range(3):
            manager.add_result(_make_discovery(domain=f"domain{i}.gov"))
        out = str(tmp_path / "out.csv")
        manager.save_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# save_json
# ---------------------------------------------------------------------------

class TestSaveJson:
    """Tests for ResultsManager.save_json."""

    def test_json_file_created(self, manager, tmp_path):
        """JSON file is created when results exist."""
        manager.add_result(_make_discovery())
        out = str(tmp_path / "out.json")
        manager.save_json(out)
        assert Path(out).exists()

    def test_json_structure(self, manager, tmp_path):
        """JSON output has 'metadata' and 'results' keys."""
        manager.add_result(_make_discovery())
        out = str(tmp_path / "out.json")
        manager.save_json(out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert "metadata" in data
        assert "results" in data
        assert data["metadata"]["total_results"] == 1

    def test_json_no_results_does_not_crash(self, manager, tmp_path):
        """No results: save_json logs a warning and does not crash."""
        out = str(tmp_path / "out.json")
        manager.save_json(out)  # should not raise


# ---------------------------------------------------------------------------
# save_checkpoint / load_checkpoint
# ---------------------------------------------------------------------------

class TestCheckpoint:
    """Tests for save_checkpoint and load_checkpoint."""

    def test_save_and_load_roundtrip(self, manager, tmp_path):
        """Saved checkpoint index is correctly loaded back."""
        ckpt = str(tmp_path / "ckpt.json")
        manager.add_result(_make_discovery())
        manager.save_checkpoint(ckpt, 42)
        loaded = manager.load_checkpoint(ckpt)
        assert loaded == 42

    def test_load_missing_checkpoint_returns_zero(self, manager, tmp_path):
        """Missing checkpoint file returns index 0."""
        ckpt = str(tmp_path / "nonexistent.json")
        assert manager.load_checkpoint(ckpt) == 0

    def test_load_corrupt_checkpoint_returns_zero(self, manager, tmp_path):
        """Corrupt JSON in checkpoint returns index 0."""
        ckpt = str(tmp_path / "bad.json")
        Path(ckpt).write_text("NOT VALID JSON {{{{")
        result = manager.load_checkpoint(ckpt)
        assert result == 0

    def test_checkpoint_contains_stats(self, manager, tmp_path):
        """Saved checkpoint includes current stats."""
        ckpt = str(tmp_path / "ckpt.json")
        manager.save_checkpoint(ckpt, 5)
        with open(ckpt, encoding="utf-8") as f:
            data = json.load(f)
        assert "stats" in data
        assert data["last_processed_index"] == 5


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------

class TestPrintSummary:
    """Tests for print_summary."""

    def test_print_summary_runs_without_error(self, manager, capsys):
        """print_summary does not raise even with zero results."""
        manager.print_summary()
        captured = capsys.readouterr()
        assert "PUBLICCODE.YML DISCOVERY SUMMARY" in captured.out

    def test_print_summary_shows_counts(self, manager, capsys):
        """print_summary reflects added results."""
        manager.add_result(_make_discovery(http_outcome="not_found"))
        manager.print_summary()
        captured = capsys.readouterr()
        assert "1" in captured.out

    def test_discovery_rate_shown_when_results_exist(self, manager, capsys):
        """Discovery rate line is shown when total_domains > 0."""
        manager.add_result(
            _make_discovery(http_outcome="success"),
            _make_validation(yaml_valid=True)
        )
        manager.print_summary()
        captured = capsys.readouterr()
        assert "Discovery rate" in captured.out

    def test_quality_rate_shown_when_files_found(self, manager, capsys):
        """Quality rate is shown when at least one file was discovered."""
        manager.add_result(
            _make_discovery(http_outcome="success"),
            _make_validation(yaml_valid=True, spec_valid=True, useful=True)
        )
        manager.print_summary()
        captured = capsys.readouterr()
        assert "Quality rate" in captured.out


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    """Tests for generate_report."""

    def test_report_file_created(self, manager, tmp_path):
        """generate_report creates ANALYSIS_REPORT.md in output_dir."""
        manager.add_result(_make_discovery())
        manager.generate_report(str(tmp_path))
        report = tmp_path / "ANALYSIS_REPORT.md"
        assert report.exists()

    def test_report_contains_sections(self, manager, tmp_path):
        """Generated report contains expected section headings."""
        manager.add_result(_make_discovery())
        manager.generate_report(str(tmp_path))
        content = (tmp_path / "ANALYSIS_REPORT.md").read_text(encoding="utf-8")
        assert "Executive Summary" in content
        assert "Methodology" in content
        assert "Key Findings" in content
        assert "Limitations" in content

    def test_report_includes_stats(self, manager, tmp_path):
        """Report includes domain count from stats."""
        manager.add_result(_make_discovery())
        manager.generate_report(str(tmp_path))
        content = (tmp_path / "ANALYSIS_REPORT.md").read_text(encoding="utf-8")
        assert "1" in content  # total_domains


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    """Tests for get_stats."""

    def test_initial_stats(self, manager):
        """Initial stats are all zero."""
        stats = manager.get_stats()
        for key in [
            "total_domains", "files_discovered", "yaml_valid",
            "spec_valid", "useful", "not_found", "errors"
        ]:
            assert stats[key] == 0

    def test_stats_returns_copy(self, manager):
        """get_stats returns a copy, not the internal dict."""
        stats = manager.get_stats()
        stats["total_domains"] = 999
        assert manager.stats["total_domains"] == 0
