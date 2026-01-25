"""
Port Congestion Model Training Script
=====================================
Trains a LightGBM model to predict port waiting times.

Run from project root:
    python scripts/train_model.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import os
import sys
import json

warnings.filterwarnings('ignore')

# Setup paths relative to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')

# Add src to path for imports
sys.path.insert(0, SRC_DIR)

print("=" * 60)
print("PORT CONGESTION PREDICTION MODEL TRAINING")
print("=" * 60)
print(f"Project root: {PROJECT_ROOT}")

# Check for required packages
try:
    import lightgbm as lgb
    print("[OK] LightGBM imported")
except ImportError:
    print("[ERROR] LightGBM not installed. Run: pip install lightgbm")
    exit(1)

try:
    import joblib
    print("[OK] Joblib imported")
except ImportError:
    print("[ERROR] Joblib not installed. Run: pip install joblib")
    exit(1)

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    print("[OK] Scikit-learn imported")
except ImportError:
    print("[ERROR] Scikit-learn not installed. Run: pip install scikit-learn")
    exit(1)

try:
    import shap
    HAS_SHAP = True
    print("[OK] SHAP imported")
except ImportError:
    HAS_SHAP = False
    print("[WARN] SHAP not installed. SHAP analysis will be skipped. Run: pip install shap")

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving plots
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
    print("[OK] Matplotlib imported")
except ImportError:
    HAS_MATPLOTLIB = False
    print("[WARN] Matplotlib not installed. Plots will be skipped.")

# Local imports
from ml.feature_engineering import FeatureEngineer
from ml.holiday_calendar import HolidayCalendar
print("[OK] Local modules imported")

# ============================================================================
# 1. DATA LOADING
# ============================================================================
print("\n" + "-" * 60)
print("1. LOADING DATA")
print("-" * 60)

print("Loading port activity data (this may take a moment)...")
activity_df = pd.read_csv(os.path.join(RAW_DATA_DIR, 'Daily_Port_Activity_Data_and_Trade_Estimates.csv'))
print(f"   Loaded {len(activity_df):,} rows")

ports_df = pd.read_csv(os.path.join(DATA_DIR, 'PortWatch_ports_database.csv'))
print(f"   Loaded {len(ports_df):,} ports")

# Target port IDs
TARGET_PORTS = {
    'port1069': 'Qingdao',
    'port1105': 'Rizhao',
    'port339': 'Fangcheng',
    'port1266': 'Caofeidian',
    'port777': 'Mundra',
    'port1367': 'Vizag',
}

# Filter to target ports
target_df = activity_df[activity_df['portid'].isin(TARGET_PORTS.keys())].copy()
target_df['date'] = pd.to_datetime(target_df['date'])
target_df = target_df.sort_values(['portid', 'date'])

print(f"   Filtered to {len(target_df):,} rows for target ports")
print(f"   Date range: {target_df['date'].min().date()} to {target_df['date'].max().date()}")

# Show data per port
print("\n   Rows per port:")
for port_id, port_name in TARGET_PORTS.items():
    count = len(target_df[target_df['portid'] == port_id])
    print(f"      {port_name}: {count:,} rows")

# ============================================================================
# 2. FEATURE ENGINEERING
# ============================================================================
print("\n" + "-" * 60)
print("2. FEATURE ENGINEERING")
print("-" * 60)

feature_engineer = FeatureEngineer(os.path.join(DATA_DIR, 'PortWatch_ports_database.csv'))

# Create target variable and features for each port
all_features = []

for port_id, port_name in TARGET_PORTS.items():
    port_data = target_df[target_df['portid'] == port_id].copy()
    port_data = port_data.sort_values('date')

    # Create delay_days target
    port_data['delay_days'] = feature_engineer.create_target_variable(port_data, port_id)

    # Full feature engineering
    features_df = feature_engineer.engineer_features(port_data, port_id, include_target=True)
    all_features.append(features_df)

    mean_delay = features_df['delay_days'].mean()
    print(f"   {port_name}: {len(features_df):,} rows, mean delay = {mean_delay:.2f} days")

training_df = pd.concat(all_features, ignore_index=True)
print(f"\n   Total training data: {len(training_df):,} rows")

# ============================================================================
# 3. TRAIN/VAL/TEST SPLIT
# ============================================================================
print("\n" + "-" * 60)
print("3. PREPARING TRAIN/VAL/TEST SPLITS")
print("-" * 60)

training_df['date'] = pd.to_datetime(training_df['date'])

# Time-based splits
train_mask = training_df['date'] < '2024-01-01'
val_mask = (training_df['date'] >= '2024-01-01') & (training_df['date'] < '2024-07-01')
test_mask = training_df['date'] >= '2024-07-01'

train_df = training_df[train_mask].dropna(subset=['delay_days'])
val_df = training_df[val_mask].dropna(subset=['delay_days'])
test_df = training_df[test_mask].dropna(subset=['delay_days'])

print(f"   Train: {len(train_df):,} rows ({train_df['date'].min().date()} to {train_df['date'].max().date()})")
print(f"   Val:   {len(val_df):,} rows ({val_df['date'].min().date()} to {val_df['date'].max().date()})")
print(f"   Test:  {len(test_df):,} rows ({test_df['date'].min().date()} to {test_df['date'].max().date()})")

# Prepare feature matrices
feature_cols = feature_engineer.get_feature_columns()
available_features = [c for c in feature_cols if c in training_df.columns]
print(f"\n   Using {len(available_features)} features")

X_train = train_df[available_features].fillna(0)
y_train = train_df['delay_days']

X_val = val_df[available_features].fillna(0)
y_val = val_df['delay_days']

X_test = test_df[available_features].fillna(0)
y_test = test_df['delay_days']

print(f"   X_train shape: {X_train.shape}")
print(f"   X_val shape: {X_val.shape}")
print(f"   X_test shape: {X_test.shape}")

# ============================================================================
# 4. MODEL TRAINING
# ============================================================================
print("\n" + "-" * 60)
print("4. TRAINING LIGHTGBM MODEL")
print("-" * 60)

params = {
    'objective': 'regression',
    'metric': ['mae', 'rmse'],
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_data_in_leaf': 100,
    'verbose': -1,
    'seed': 42,
}

train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

print("   Training model (early stopping enabled)...")
model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, val_data],
    valid_names=['train', 'val'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=100)
    ]
)

print(f"\n   Best iteration: {model.best_iteration}")

# ============================================================================
# 5. MODEL EVALUATION
# ============================================================================
print("\n" + "-" * 60)
print("5. MODEL EVALUATION")
print("-" * 60)

# Make predictions
y_train_pred = model.predict(X_train)
y_val_pred = model.predict(X_val)
y_test_pred = model.predict(X_test)

def calculate_metrics(y_true, y_pred, name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    within_1_day = np.mean(np.abs(y_true - y_pred) <= 1) * 100
    within_2_days = np.mean(np.abs(y_true - y_pred) <= 2) * 100

    print(f"\n   {name} Metrics:")
    print(f"      MAE: {mae:.3f} days")
    print(f"      RMSE: {rmse:.3f} days")
    print(f"      Within 1 day: {within_1_day:.1f}%")
    print(f"      Within 2 days: {within_2_days:.1f}%")

    return {'mae': mae, 'rmse': rmse, 'within_1_day': within_1_day, 'within_2_days': within_2_days}

train_metrics = calculate_metrics(y_train, y_train_pred, "Training")
val_metrics = calculate_metrics(y_val, y_val_pred, "Validation")
test_metrics = calculate_metrics(y_test, y_test_pred, "Test")

# Check target metrics
print("\n" + "=" * 60)
print("TARGET METRICS CHECK (Test Set)")
print("=" * 60)

checks = [
    ("MAE < 1.5 days", test_metrics['mae'] < 1.5, test_metrics['mae']),
    ("RMSE < 2.0 days", test_metrics['rmse'] < 2.0, test_metrics['rmse']),
    ("Within 1 day > 60%", test_metrics['within_1_day'] > 60, test_metrics['within_1_day']),
    ("Within 2 days > 80%", test_metrics['within_2_days'] > 80, test_metrics['within_2_days']),
]

for check_name, passed, value in checks:
    status = "PASS" if passed else "FAIL"
    print(f"   [{status}] {check_name}: {value:.2f}")

# Per-port metrics
print("\n   Per-Port Test Metrics:")
for port_id, port_name in TARGET_PORTS.items():
    port_mask = test_df['portid'] == port_id
    if port_mask.sum() > 0:
        port_y_test = y_test[port_mask]
        port_y_pred = y_test_pred[port_mask]
        mae = mean_absolute_error(port_y_test, port_y_pred)
        print(f"      {port_name}: MAE = {mae:.2f} days")

# ============================================================================
# 6. FEATURE IMPORTANCE
# ============================================================================
print("\n" + "-" * 60)
print("6. FEATURE IMPORTANCE (Top 10)")
print("-" * 60)

importance_df = pd.DataFrame({
    'feature': available_features,
    'importance': model.feature_importance(importance_type='gain')
}).sort_values('importance', ascending=False)

for i, row in importance_df.head(10).iterrows():
    print(f"   {row['feature']}: {row['importance']:.0f}")

# ============================================================================
# 6.5 SHAP ANALYSIS (Required by Datathon for Explainability)
# ============================================================================
print("\n" + "-" * 60)
print("6.5. SHAP EXPLAINABILITY ANALYSIS")
print("-" * 60)

shap_values_dict = {}

if HAS_SHAP and HAS_MATPLOTLIB:
    print("   Computing SHAP values (this may take a moment)...")

    # Use a sample of training data for SHAP analysis (for efficiency)
    sample_size = min(1000, len(X_train))
    X_sample = X_train.sample(n=sample_size, random_state=42)

    # Create SHAP explainer for LightGBM
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Calculate mean absolute SHAP values for each feature
    mean_shap = np.abs(shap_values).mean(axis=0)
    shap_importance = pd.DataFrame({
        'feature': available_features,
        'mean_shap': mean_shap
    }).sort_values('mean_shap', ascending=False)

    print("\n   SHAP Feature Importance (Top 10):")
    for i, row in shap_importance.head(10).iterrows():
        print(f"      {row['feature']}: {row['mean_shap']:.4f}")

    # Store SHAP values for model_info.json
    shap_values_dict = {
        'shap_feature_importance': {
            row['feature']: float(row['mean_shap'])
            for _, row in shap_importance.iterrows()
        },
        'sample_size': sample_size,
    }

    # Create and save SHAP summary plot
    print("\n   Generating SHAP summary plot...")
    try:
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_sample, feature_names=available_features, show=False)
        plt.tight_layout()

        shap_plot_path = os.path.join(MODELS_DIR, 'shap_summary.png')
        plt.savefig(shap_plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   SHAP plot saved to: {shap_plot_path}")

        # Also create a bar plot for cleaner visualization
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, X_sample, feature_names=available_features,
                          plot_type="bar", show=False)
        plt.tight_layout()

        shap_bar_path = os.path.join(MODELS_DIR, 'shap_importance_bar.png')
        plt.savefig(shap_bar_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   SHAP bar plot saved to: {shap_bar_path}")

    except Exception as e:
        print(f"   [WARN] Could not save SHAP plot: {e}")

else:
    print("   [SKIP] SHAP analysis requires 'shap' and 'matplotlib' packages")
    print("   To enable: pip install shap matplotlib")

# ============================================================================
# 7. SAVE MODEL
# ============================================================================
print("\n" + "-" * 60)
print("7. SAVING MODEL")
print("-" * 60)

os.makedirs(MODELS_DIR, exist_ok=True)

model_path = os.path.join(MODELS_DIR, 'port_delay_v1.joblib')
joblib.dump(model, model_path)
print(f"   Model saved to: {model_path}")

# Save model info
model_info = {
    'model_version': 'v1',
    'training_date': datetime.now().isoformat(),
    'features': available_features,
    'target_ports': TARGET_PORTS,
    'best_iteration': model.best_iteration,
    'test_metrics': {
        'mae': float(test_metrics['mae']),
        'rmse': float(test_metrics['rmse']),
        'within_1_day_pct': float(test_metrics['within_1_day']),
        'within_2_days_pct': float(test_metrics['within_2_days']),
    },
    'gain_feature_importance': {
        row['feature']: float(row['importance'])
        for _, row in importance_df.iterrows()
    },
}

# Add SHAP values if available
if shap_values_dict:
    model_info['shap_analysis'] = shap_values_dict
    model_info['shap_plot_path'] = os.path.join(MODELS_DIR, 'shap_summary.png')

model_info_path = os.path.join(MODELS_DIR, 'model_info.json')
with open(model_info_path, 'w') as f:
    json.dump(model_info, f, indent=2)
print(f"   Model info saved to: {model_info_path}")

# Verify model loads correctly
loaded_model = joblib.load(model_path)
test_pred = loaded_model.predict(X_test[:5])
print(f"   Model verification: OK (sample predictions: {test_pred[:3].round(2)})")

# ============================================================================
# 8. TEST PREDICTOR CLASS
# ============================================================================
print("\n" + "-" * 60)
print("8. TESTING PREDICTOR CLASS")
print("-" * 60)

from ml.port_congestion_predictor import PortCongestionPredictor

predictor = PortCongestionPredictor(
    model_path=model_path,
    data_path=os.path.join(RAW_DATA_DIR, 'Daily_Port_Activity_Data_and_Trade_Estimates.csv'),
    port_database_path=os.path.join(DATA_DIR, 'PortWatch_ports_database.csv')
)

print(f"   Model available: {predictor.is_model_available()}")

test_ports = ['Qingdao', 'Rizhao', 'Mundra', 'Vizag']
test_date = '2026-03-15'

print(f"\n   Predictions for {test_date}:")
for port in test_ports:
    result = predictor.predict(port, test_date)
    print(f"      {port}: {result.predicted_delay_days:.1f} days "
          f"[{result.confidence_lower:.1f}-{result.confidence_upper:.1f}] "
          f"({result.congestion_level})")

print("\n" + "=" * 60)
print("TRAINING COMPLETE!")
print("=" * 60)
print(f"\nModel saved to: {model_path}")
print("Use with:")
print("  from src.ml import PortCongestionPredictor")
print(f"  predictor = PortCongestionPredictor('{model_path}')")
print("  delay = predictor.get_delay_for_voyage('Qingdao', '2026-03-15')")
