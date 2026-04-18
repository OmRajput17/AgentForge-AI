# agentforge/eval_engine.py

import json
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Literal

EVAL_FILE = Path.home() / '.agentforge' / 'evals.jsonl'

SeverityLabel = Literal['low', 'medium', 'high', 'critical']

@dataclass
class TriageEvalRecord:
    timestamp: str
    issue_number: int
    issue_title: str
    predicted: SeverityLabel
    ground_truth: SeverityLabel | None
    correct: bool | None
    confidence: float
    run_id: str

class EvalEngine:
    '''
    Logs triage predictions and computes precision/recall.
    Writes to ~/.agentforge/evals.jsonl (one JSON per line).
    Ground truth is optional — logs predictions even without labels.
    '''

    def __init__(self):
        EVAL_FILE.parent.mkdir(exist_ok=True)


    def log_triage(
        self, 
        issue_number: int,
        issue_title: str,
        predicted: str,
        confidence: float,
        run_id: str,
        ground_truth: str | None = None
        ) -> TriageEvalRecord:

        correct = None
        if ground_truth is not None:
            correct = (predicted.lower() == ground_truth.lower())

        record = TriageEvalRecord(
            timestamp= datetime.now(timezone.utc).isoformat(),
            issue_number= issue_number,
            issue_title= issue_title,
            predicted= predicted.lower(),
            ground_truth= ground_truth.lower() if ground_truth is not None else None,
            correct= correct,
            confidence= confidence,
            run_id= run_id,
        )

        with open(EVAL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(record)) + '\n')
        
        return record

    def compute_metrics(self, run_id: str | None = None) -> dict:
        '''
        Compute precision, recall, accuracy for verified predictions.
        If run_id provided, filters to that run only.
        '''

        if not EVAL_FILE.exists():
            return {'message': 'No eval file found. Run log_triage() first.'}

        records = []

        with open(EVAL_FILE, encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)

                if run_id and r['run_id'] != run_id:
                    continue
            
                if r['correct'] is not None:
                    records.append(r)

        if not records:
            return {'message': 'No verified records yet. Add ground_truth labels to measure accuracy.'}

        labels = ['critical', 'high', 'medium', 'low']
            
        total = len(records)
        correct = sum(1 for r in records if r['correct'])
        accuracy = correct / total

        per_label = {}

        for label in labels:
            predicted_pos = [r for r in records if r['predicted'] == label]
            actual_pos = [r for r in records if r.get('ground_truth') == label]
            tp = sum(
                1 for r in records
                if r['predicted'] == label and r.get('ground_truth') == label
            )

            precision = tp / len(predicted_pos) if predicted_pos else 0.0
            recall = tp / len(actual_pos) if actual_pos else 0.0

            per_label[label] = {'precision': round(precision, 3), 'recall': round(recall, 3)}


        return {
            'total': total,
            'accuracy': round(accuracy, 3),
            'per_label': per_label,
            'run_id': run_id or 'all'
        }

    def print_report(self, run_id: str | None = None):
        metrics= self.compute_metrics(run_id)
        if 'message' in metrics:
            print(metrics['message'])
            return 
        print(f'\nEval Report -- {metrics["run_id"]}')
        print(f'Total: {metrics["total"]} | Accuracy: {metrics["accuracy"] * 100:.1f}%')

        for label, m in metrics['per_label'].items():
            print(f'{label:<10} precision = {m["precision"]:.3f} recall = {m["recall"]:.3f}')