import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import warnings

warnings.filterwarnings("ignore")

# Module-level models (trained once on startup)
_supplier_delay_model = None
_stockout_model = None


def _generate_supplier_training_data(n_samples: int = 2000):
    """Generate synthetic supplier delay training data."""
    rng = np.random.RandomState(42)

    reliability = rng.uniform(0.5, 1.0, n_samples)
    avg_lead_time = rng.uniform(7, 180, n_samples)
    on_time_rate = rng.uniform(0.4, 1.0, n_samples)
    defect_rate = rng.uniform(0.001, 0.08, n_samples)
    days_since_audit = rng.uniform(0, 730, n_samples)

    X = np.column_stack([reliability, avg_lead_time, on_time_rate, defect_rate, days_since_audit])

    # Label: delayed if low reliability, low OTD, high defect, long since audit
    delay_score = (
        (1.0 - reliability) * 0.30
        + avg_lead_time / 180.0 * 0.15
        + (1.0 - on_time_rate) * 0.35
        + defect_rate / 0.08 * 0.10
        + days_since_audit / 730.0 * 0.10
    )
    noise = rng.normal(0, 0.08, n_samples)
    y = (delay_score + noise > 0.35).astype(int)

    return X, y


def _generate_stockout_training_data(n_samples: int = 2000):
    """Generate synthetic stockout prediction training data."""
    rng = np.random.RandomState(99)

    qty_on_hand = rng.randint(0, 50, n_samples).astype(float)
    avg_consumption = rng.uniform(0.1, 5.0, n_samples)
    lead_time_days = rng.uniform(7, 180, n_samples)
    qty_on_order = rng.randint(0, 20, n_samples).astype(float)
    reorder_point = rng.randint(1, 15, n_samples).astype(float)

    X = np.column_stack([qty_on_hand, avg_consumption, lead_time_days, qty_on_order, reorder_point])

    # Stockout in 30 days if (stock / daily_consumption) < 30 and no order imminent
    daily_consumption = avg_consumption / 30.0
    days_of_stock = np.where(daily_consumption > 0, qty_on_hand / daily_consumption, 9999)
    effective_days = days_of_stock + np.where(qty_on_order > 0, qty_on_order / np.maximum(daily_consumption, 0.001), 0)
    # Account for lead time risk
    stockout_risk = (effective_days < lead_time_days) | (qty_on_hand <= reorder_point)
    noise = rng.uniform(0, 1, n_samples) < 0.05  # 5% noise
    y = (stockout_risk ^ noise).astype(int)

    return X, y


def train_models():
    """Train both models on synthetic data. Called once at startup."""
    global _supplier_delay_model, _stockout_model

    # Supplier delay model
    X_sup, y_sup = _generate_supplier_training_data()
    _supplier_delay_model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42))
    ])
    _supplier_delay_model.fit(X_sup, y_sup)

    # Stockout model
    X_stock, y_stock = _generate_stockout_training_data()
    _stockout_model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=99))
    ])
    _stockout_model.fit(X_stock, y_stock)


def predict_supplier_delay_probability(supplier_features: dict) -> float:
    """
    Predict probability of supplier delay.

    Features:
        reliability_score: float (0-1)
        avg_lead_time: float (days)
        on_time_rate: float (0-1)
        defect_rate: float (0-1)
        days_since_audit: float (days)
    """
    if _supplier_delay_model is None:
        train_models()

    X = np.array([[
        supplier_features.get("reliability_score", 0.85),
        supplier_features.get("avg_lead_time", 30),
        supplier_features.get("on_time_rate", 0.90),
        supplier_features.get("defect_rate", 0.02),
        supplier_features.get("days_since_audit", 90),
    ]])
    prob = _supplier_delay_model.predict_proba(X)[0][1]
    return round(float(prob), 3)


def predict_stockout_probability(inventory_features: dict) -> float:
    """
    Predict probability of stockout within 30 days.

    Features:
        qty_on_hand: int
        avg_consumption: float (monthly)
        lead_time_days: float
        qty_on_order: int
        reorder_point: int
    """
    if _stockout_model is None:
        train_models()

    X = np.array([[
        inventory_features.get("qty_on_hand", 5),
        inventory_features.get("avg_consumption", 1.0),
        inventory_features.get("lead_time_days", 30),
        inventory_features.get("qty_on_order", 0),
        inventory_features.get("reorder_point", 3),
    ]])
    prob = _stockout_model.predict_proba(X)[0][1]
    return round(float(prob), 3)
