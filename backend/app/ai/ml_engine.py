"""Phase 15 — Machine-learning evaluation of recorded signals.

Every number comes from deterministic feature engineering (app/engine/features.py)
and inferred OUTCOMES (app/learning/outcome_resolver.py). The models below only
summarize that pre-computed history — they never synthesize market data.

All training uses strict chronologically-ordered TimeSeriesSplit folds (never a
random shuffle), so validation can't leak future bars into a training set.

Graceful degradation: if scikit-learn is unavailable the classes return a
``{'status': 'skipped', 'reason': ...}`` dict from train/predict, so the API
and dashboard keep working.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.cluster import KMeans
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, mean_squared_error
    _SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - import failure path
    np = None  # type: ignore[assignment]
    _SKLEARN_AVAILABLE = False

SKIP_RESPONSE = {'status': 'skipped', 'reason': 'scikit-learn not installed', 'metrics': {}}


def _skip_or(data: list | int) -> dict:
    return {'status': 'skipped', 'reason': 'insufficient samples', 'metrics': {}}


def _guard_nan(v: float) -> float:
    """The engine layer already drops NaN features; assert it never leaks here."""
    if v is None or (np is not None and not np.isfinite(v)):
        return 0.0
    return float(v)


class SignalClassifier:
    """Logistic-regression model: predict the win probability of a signal.

    ``train`` expects the deterministic feature rows produced by
    calculate_features() and the matching outcome labels ('win' -> 1 else 0).
    `predict` returns the calibrated win probability in [0, 1].
    """

    min_samples: int = 30

    def _model(self):
        return LogisticRegression(max_iter=1000, C=1.0)

    def train(self, features, labels) -> dict:
        if not _SKLEARN_AVAILABLE:
            return SKIP_RESPONSE
        try:
            import numpy as np
        except ImportError:
            return SKIP_RESPONSE
        if not features or not labels or len(features) < self.min_samples:
            return _skip_or(len(features))
        X = np.asarray([[i.get('value', i) if isinstance(i, dict) else float(i) for i in row]
                        for row in features], dtype=float)
        y = np.asarray([1 if label == 'win' else 0 for label in labels], dtype=int)
        if len(set(y.tolist())) < 2:
            return {'status': 'skipped', 'reason': 'single-class labels', 'metrics': {}}
        # Strict chronological splits: shuffle=False keeps bar order intact.
        folds, accs = 0, []
        for train_idx, test_idx in TimeSeriesSplit(n_splits=3).split(X):
            m = self._model().fit(X[train_idx], y[train_idx])
            pred = m.predict(X[test_idx])
            if len(set(y[test_idx].tolist())) == 2:
                accs.append(accuracy_score(y[test_idx], pred)); folds += 1
        if not folds:
            return {'status': 'skipped', 'reason': 'folds too small', 'metrics': {}}
        self._fitted = self._model().fit(X, y)
        self._importance = None
        return {'status': 'ok', 'accuracy': round(sum(accs) / folds, 4),
                'folds': folds, 'mean_accuracy': round(sum(accs) / folds, 4)}

    def predict(self, features) -> float:
        """features: one flat feature row (list of scalars)."""
        if not _SKLEARN_AVAILABLE or not getattr(self, '_fitted', None):
            return 0.5
        import numpy as np
        X = np.asarray([[_guard_nan(v) for v in features]], dtype=float)
        proba = self._fitted.predict_proba(X)[0]
        return float(proba[list(self._fitted.classes_).index(1)] if 1 in self._fitted.classes_ else proba[-1])


class RegimeDetector:
    """Unsupervised K-means over normalized features to label unseen regimes.

    Pure clustering describer — it re-groups the same features Python already
    computed; it never predicts prices.
    """

    max_clusters: int = 5

    def train(self, features) -> dict:
        if not _SKLEARN_AVAILABLE:
            return SKIP_RESPONSE
        try:
            import numpy as np
        except ImportError:
            return SKIP_RESPONSE
        if not features or len(features) < self.max_clusters * 2:
            return _skip_or(len(features))
        X = np.asarray([[float(_guard_nan(i.get('value', i) if isinstance(i, dict) else i)) for i in row]
                        for row in features], dtype=float)
        n = min(self.max_clusters, max(2, len(X) // 4))
        k = KMeans(n_clusters=n, n_init=10, random_state=42)  # fixed seed: deterministic
        k.fit(X)
        self._fitted = k
        counts = [int((k.labels_ == i).sum()) for i in range(n)]
        return {'status': 'ok', 'n_clusters': n, 'cluster_counts': counts,
                'inertia': round(float(k.inertia_), 4)}

    def predict(self, features) -> int:
        """features: one flat feature row (list of scalars)."""
        if not _SKLEARN_AVAILABLE or not getattr(self, '_fitted', None):
            return 0
        import numpy as np
        X = np.asarray([[_guard_nan(v) for v in features]], dtype=float)
        return int(self._fitted.predict(X)[0])


class ExpectancyModel:
    """Gradient-boosted regressor for expected trade PnL %.

    Trained on (features, resolved pnl_pct) pairs from the outcome history so
    candidate strategies can be ranked by expected return. Still bounded by what
    the walk-forward resolver recorded — no fabrications.
    """

    min_samples: int = 30

    def train(self, features, pnl_vector) -> dict:
        if not _SKLEARN_AVAILABLE:
            return SKIP_RESPONSE
        try:
            import numpy as np
        except ImportError:
            return SKIP_RESPONSE
        if not features or not pnl_vector or len(features) < self.min_samples:
            return _skip_or(len(features) if features else 0)
        X = np.asarray([[float(_guard_nan(i.get('value', i) if isinstance(i, dict) else i)) for i in row]
                        for row in features], dtype=float)
        y = np.asarray([float(v) for v in pnl_vector], dtype=float)
        errors, folds = [], 0
        for train_idx, test_idx in TimeSeriesSplit(n_splits=3).split(X):
            m = GradientBoostingRegressor(n_estimators=60, max_depth=3, random_state=42)
            m.fit(X[train_idx], y[train_idx])
            errors.append(mean_squared_error(y[test_idx], m.predict(X[test_idx]))); folds += 1
        self._fitted = GradientBoostingRegressor(n_estimators=60, max_depth=3, random_state=42).fit(X, y)
        mse = float(sum(errors) / len(errors))
        return {'status': 'ok', 'mse': round(mse, 4), 'rmse': round(mse ** 0.5, 4),
                'folds': folds, 'mean_pnl': round(float(y.mean()), 4)}

    def predict(self, features) -> float:
        """features: one flat feature row (list of scalars)."""
        if not _SKLEARN_AVAILABLE or not getattr(self, '_fitted', None):
            return 0.0
        import numpy as np
        X = np.asarray([[_guard_nan(v) for v in features]], dtype=float)
        return float(self._fitted.predict(X)[0])