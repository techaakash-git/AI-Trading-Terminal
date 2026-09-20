"""Phase 15 — Learning & Evaluation Engine services.

Python computes; the LLM only narrates. Signal recording and outcome
resolution are deterministic and walk-forward (never lookahead).
"""
from .signal_service import record_signal, get_signals, get_outcomes, get_signal_with_outcome
from .outcome_resolver import OutcomeResolver, evaluate_outcome
from .regime_service import latest_regime as get_regime
from .feedback_service import create_feedback as record_feedback, list_feedback as get_feedback
from .registry_service import (
    list_candidates as get_candidates, create_candidates as discover_candidates,
    set_candidate_validated as validate_candidate, promote_candidate,
    list_registry as get_registry, update_strategy_status as update_registry_status,
    list_training_runs as get_training_runs, record_training_run
)
from .performance import aggregate_performance as get_performance_summary

__all__ = [
    'record_signal', 'get_signals', 'get_outcomes', 'get_signal_with_outcome',
    'OutcomeResolver', 'evaluate_outcome',
    'get_regime',
    'record_feedback', 'get_feedback',
    'get_candidates', 'discover_candidates', 'validate_candidate', 'promote_candidate',
    'get_registry', 'update_registry_status', 'get_training_runs', 'record_training_run',
    'get_performance_summary'
]