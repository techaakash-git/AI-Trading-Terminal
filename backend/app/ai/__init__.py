"""AI boundary: the LLM narrates pre-computed data; it never calculates.
Phase 15 adds the sklearn-backed evaluators (still summarizing only data the
deterministic engine produced)."""
from .provider import AIProvider
from .ml_engine import SignalClassifier, RegimeDetector, ExpectancyModel

provider = AIProvider()

__all__ = ['AIProvider', 'provider', 'SignalClassifier', 'RegimeDetector',
           'ExpectancyModel']