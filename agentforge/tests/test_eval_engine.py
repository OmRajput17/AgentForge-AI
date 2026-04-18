# agentforge/tests/test_eval_engine.py

import json
import pytest
from unittest.mock import patch
from dataclasses import asdict

from agentforge.eval_engine import EvalEngine, TriageEvalRecord, EVAL_FILE


# ---------------------------------------------------------------------------
# Fixture: redirect EVAL_FILE to a temp directory so tests never touch the
# real ~/.agentforge/evals.jsonl
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_eval_file(tmp_path):
    """Patch EVAL_FILE to a temporary path for every test."""
    fake_file = tmp_path / 'evals.jsonl'
    with patch('agentforge.eval_engine.EVAL_FILE', fake_file):
        yield fake_file


# ===========================================================================
# TriageEvalRecord dataclass
# ===========================================================================

class TestTriageEvalRecord:

    def test_fields_present(self):
        record = TriageEvalRecord(
            timestamp='2026-04-18T00:00:00',
            issue_number=42,
            issue_title='Bug in parser',
            predicted='high',
            ground_truth='high',
            correct=True,
            confidence=0.95,
            run_id='run-001',
        )
        d = asdict(record)
        assert d['issue_number'] == 42
        assert d['predicted'] == 'high'
        assert d['correct'] is True

    def test_ground_truth_none(self):
        record = TriageEvalRecord(
            timestamp='2026-04-18T00:00:00',
            issue_number=1,
            issue_title='Test',
            predicted='low',
            ground_truth=None,
            correct=None,
            confidence=0.5,
            run_id='run-002',
        )
        assert record.ground_truth is None
        assert record.correct is None


# ===========================================================================
# EvalEngine.log_triage
# ===========================================================================

class TestLogTriage:

    def test_log_creates_file_and_writes_record(self, _isolate_eval_file):
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=1,
            issue_title='First issue',
            predicted='High',
            confidence=0.9,
            run_id='run-1',
            ground_truth='high',
        )

        assert _isolate_eval_file.exists()
        lines = _isolate_eval_file.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data['issue_number'] == 1
        assert data['predicted'] == 'high'          # lowercased
        assert data['ground_truth'] == 'high'        # lowercased
        assert data['correct'] is True

    def test_log_without_ground_truth(self, _isolate_eval_file):
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=2,
            issue_title='No label issue',
            predicted='medium',
            confidence=0.6,
            run_id='run-1',
        )

        assert record.ground_truth is None
        assert record.correct is None

        data = json.loads(_isolate_eval_file.read_text(encoding='utf-8').strip())
        assert data['correct'] is None
        assert data['ground_truth'] is None

    def test_log_incorrect_prediction(self, _isolate_eval_file):
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=3,
            issue_title='Mismatch',
            predicted='low',
            confidence=0.4,
            run_id='run-1',
            ground_truth='critical',
        )

        assert record.correct is False

    def test_log_case_insensitive_comparison(self, _isolate_eval_file):
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=4,
            issue_title='Case test',
            predicted='HIGH',
            confidence=0.8,
            run_id='run-1',
            ground_truth='high',
        )

        assert record.correct is True
        assert record.predicted == 'high'

    def test_log_appends_multiple_records(self, _isolate_eval_file):
        engine = EvalEngine()
        for i in range(5):
            engine.log_triage(
                issue_number=i,
                issue_title=f'Issue {i}',
                predicted='medium',
                confidence=0.5,
                run_id='run-1',
            )

        lines = _isolate_eval_file.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 5

    def test_log_returns_record_instance(self, _isolate_eval_file):
        engine = EvalEngine()
        result = engine.log_triage(
            issue_number=10,
            issue_title='Return check',
            predicted='low',
            confidence=0.3,
            run_id='run-1',
        )

        assert isinstance(result, TriageEvalRecord)
        assert result.issue_number == 10
        assert result.run_id == 'run-1'

    def test_log_timestamp_is_utc_iso(self, _isolate_eval_file):
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=99,
            issue_title='Timestamp',
            predicted='low',
            confidence=0.1,
            run_id='run-ts',
        )

        # Should be a valid ISO 8601 timestamp with UTC offset info
        assert 'T' in record.timestamp
        assert '+00:00' in record.timestamp


# ===========================================================================
# EvalEngine.compute_metrics
# ===========================================================================

class TestComputeMetrics:

    def _seed_records(self, engine, records):
        """Helper to log multiple triage records at once."""
        for r in records:
            engine.log_triage(**r)

    def test_no_file_returns_message(self, _isolate_eval_file):
        engine = EvalEngine()
        # File doesn't exist yet (no log_triage calls)
        result = engine.compute_metrics()
        assert 'message' in result

    def test_no_ground_truth_returns_message(self, _isolate_eval_file):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1,
            issue_title='No label',
            predicted='high',
            confidence=0.9,
            run_id='run-1',
        )

        result = engine.compute_metrics()
        assert 'message' in result
        assert 'No verified records' in result['message']

    def test_perfect_accuracy(self, _isolate_eval_file):
        engine = EvalEngine()
        records = [
            dict(issue_number=1, issue_title='A', predicted='high',
                 confidence=0.9, run_id='run-1', ground_truth='high'),
            dict(issue_number=2, issue_title='B', predicted='low',
                 confidence=0.8, run_id='run-1', ground_truth='low'),
            dict(issue_number=3, issue_title='C', predicted='critical',
                 confidence=0.95, run_id='run-1', ground_truth='critical'),
        ]
        self._seed_records(engine, records)

        metrics = engine.compute_metrics()
        assert metrics['accuracy'] == 1.0
        assert metrics['total'] == 3
        assert metrics['per_label']['high']['precision'] == 1.0
        assert metrics['per_label']['high']['recall'] == 1.0

    def test_zero_accuracy(self, _isolate_eval_file):
        engine = EvalEngine()
        records = [
            dict(issue_number=1, issue_title='A', predicted='high',
                 confidence=0.9, run_id='run-1', ground_truth='low'),
            dict(issue_number=2, issue_title='B', predicted='low',
                 confidence=0.8, run_id='run-1', ground_truth='high'),
        ]
        self._seed_records(engine, records)

        metrics = engine.compute_metrics()
        assert metrics['accuracy'] == 0.0
        assert metrics['per_label']['high']['precision'] == 0.0
        assert metrics['per_label']['high']['recall'] == 0.0

    def test_mixed_accuracy(self, _isolate_eval_file):
        engine = EvalEngine()
        records = [
            dict(issue_number=1, issue_title='A', predicted='high',
                 confidence=0.9, run_id='run-1', ground_truth='high'),
            dict(issue_number=2, issue_title='B', predicted='high',
                 confidence=0.7, run_id='run-1', ground_truth='low'),
            dict(issue_number=3, issue_title='C', predicted='low',
                 confidence=0.6, run_id='run-1', ground_truth='low'),
        ]
        self._seed_records(engine, records)

        metrics = engine.compute_metrics()
        assert metrics['total'] == 3
        assert metrics['accuracy'] == round(2 / 3, 3)

        # high: predicted=[1,2], actual=[1] → TP=1, precision=0.5, recall=1.0
        assert metrics['per_label']['high']['precision'] == 0.5
        assert metrics['per_label']['high']['recall'] == 1.0

        # low: predicted=[3], actual=[2,3] → TP=1, precision=1.0, recall=0.5
        assert metrics['per_label']['low']['precision'] == 1.0
        assert metrics['per_label']['low']['recall'] == 0.5

    def test_filter_by_run_id(self, _isolate_eval_file):
        engine = EvalEngine()
        records = [
            dict(issue_number=1, issue_title='A', predicted='high',
                 confidence=0.9, run_id='run-A', ground_truth='high'),
            dict(issue_number=2, issue_title='B', predicted='low',
                 confidence=0.8, run_id='run-B', ground_truth='high'),
        ]
        self._seed_records(engine, records)

        metrics_a = engine.compute_metrics(run_id='run-A')
        assert metrics_a['total'] == 1
        assert metrics_a['accuracy'] == 1.0
        assert metrics_a['run_id'] == 'run-A'

        metrics_b = engine.compute_metrics(run_id='run-B')
        assert metrics_b['total'] == 1
        assert metrics_b['accuracy'] == 0.0
        assert metrics_b['run_id'] == 'run-B'

    def test_run_id_all_when_not_filtered(self, _isolate_eval_file):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-1', ground_truth='high',
        )

        metrics = engine.compute_metrics()
        assert metrics['run_id'] == 'all'

    def test_labels_without_predictions_have_zero_precision(self, _isolate_eval_file):
        """Labels that were never predicted should have precision=0, recall=0."""
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-1', ground_truth='high',
        )

        metrics = engine.compute_metrics()
        # 'medium' was never predicted or ground-truthed
        assert metrics['per_label']['medium']['precision'] == 0.0
        assert metrics['per_label']['medium']['recall'] == 0.0


# ===========================================================================
# EvalEngine.print_report
# ===========================================================================

class TestPrintReport:

    def test_print_report_no_file(self, _isolate_eval_file, capsys):
        engine = EvalEngine()
        engine.print_report()
        captured = capsys.readouterr()
        assert 'No eval file found' in captured.out

    def test_print_report_no_verified(self, _isolate_eval_file, capsys):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-1',
        )
        engine.print_report()
        captured = capsys.readouterr()
        assert 'No verified records' in captured.out

    def test_print_report_with_data(self, _isolate_eval_file, capsys):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-1', ground_truth='high',
        )
        engine.log_triage(
            issue_number=2, issue_title='B', predicted='low',
            confidence=0.8, run_id='run-1', ground_truth='low',
        )

        engine.print_report()
        captured = capsys.readouterr()

        assert 'Eval Report' in captured.out
        assert 'Total: 2' in captured.out
        assert 'Accuracy: 100.0%' in captured.out
        assert 'precision' in captured.out
        assert 'recall' in captured.out

    def test_print_report_with_run_id(self, _isolate_eval_file, capsys):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-X', ground_truth='high',
        )

        engine.print_report(run_id='run-X')
        captured = capsys.readouterr()
        assert 'run-X' in captured.out


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:

    def test_empty_string_ground_truth_is_not_none(self, _isolate_eval_file):
        """Empty string ground_truth should still trigger comparison (not skip)."""
        engine = EvalEngine()
        record = engine.log_triage(
            issue_number=1,
            issue_title='Edge',
            predicted='high',
            confidence=0.5,
            run_id='run-edge',
            ground_truth='',
        )
        # ground_truth="" != predicted="high", so correct should be False
        assert record.correct is False
        assert record.ground_truth == ''

    def test_nonexistent_run_id_returns_message(self, _isolate_eval_file):
        engine = EvalEngine()
        engine.log_triage(
            issue_number=1, issue_title='A', predicted='high',
            confidence=0.9, run_id='run-1', ground_truth='high',
        )

        result = engine.compute_metrics(run_id='nonexistent')
        assert 'message' in result

    def test_init_creates_parent_dir(self, tmp_path):
        """Ensure __init__ creates the parent directory if missing."""
        fake_file = tmp_path / 'subdir' / 'evals.jsonl'
        with patch('agentforge.eval_engine.EVAL_FILE', fake_file):
            engine = EvalEngine()
            assert fake_file.parent.exists()
