# tests/test_eval_engine.py
import pytest, json
from pathlib import Path
from unittest.mock import patch
from agentforge.eval_engine import EvalEngine
 
@pytest.fixture
def tmp_eval(tmp_path, monkeypatch):
    eval_file = tmp_path / 'evals.jsonl'
    monkeypatch.setattr('agentforge.eval_engine.EVAL_FILE', eval_file)
    return EvalEngine()
 
def test_logs_prediction(tmp_eval):
    r = tmp_eval.log_triage(1, 'Login crash', 'critical', 0.95, 'run1')
    assert r.predicted == 'critical'
    assert r.correct is None  # no ground truth yet
 
def test_logs_with_ground_truth(tmp_eval):
    r = tmp_eval.log_triage(2, 'Button color', 'low', 0.9, 'run1', ground_truth='low')
    assert r.correct == True
 
def test_compute_accuracy(tmp_eval):
    tmp_eval.log_triage(1, 'Crash', 'critical', 0.95, 'run1', ground_truth='critical')
    tmp_eval.log_triage(2, 'Color', 'low', 0.9, 'run1', ground_truth='high')  # wrong
    metrics = tmp_eval.compute_metrics(run_id='run1')
    assert metrics['total'] == 2
    assert metrics['accuracy'] == 0.5
 
def test_precision_recall(tmp_eval):
    # 2 true positives, 1 false positive, 1 false negative for 'critical'
    tmp_eval.log_triage(1, 'A', 'critical', 0.9, 'r', ground_truth='critical')
    tmp_eval.log_triage(2, 'B', 'critical', 0.85, 'r', ground_truth='critical')
    tmp_eval.log_triage(3, 'C', 'critical', 0.7, 'r', ground_truth='high')   # FP
    tmp_eval.log_triage(4, 'D', 'high', 0.8, 'r', ground_truth='critical')   # FN
    m = tmp_eval.compute_metrics('r')
    assert m['per_label']['critical']['precision'] == pytest.approx(0.667, abs=0.01)
    assert m['per_label']['critical']['recall'] == pytest.approx(0.667, abs=0.01)
