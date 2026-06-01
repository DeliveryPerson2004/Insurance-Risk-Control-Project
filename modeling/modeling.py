## 保险欺诈风险控制 — XGBoost 建模流程 v4

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, TargetEncoder
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    f1_score, precision_recall_curve, average_precision_score,
    roc_auc_score, classification_report, confusion_matrix,
    roc_curve, precision_score, recall_score
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
import optuna
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置
# ============================================================
RUN_OPTUNA = True           # 是否运行超参数搜索（若已有最优参可关闭）
OPTUNA_TRIALS = 30          # Optuna 搜索轮数
RANDOM_STATE = 42

# ============================================================
# 数据加载
# ============================================================
DATA_DIR = "data/train_eval_test"

train_df = pd.read_csv(f"{DATA_DIR}/train.csv")
eval_df  = pd.read_csv(f"{DATA_DIR}/eval.csv")
test_df  = pd.read_csv(f"{DATA_DIR}/test.csv")

TARGET = 'FRAUD'
FEATURE_COLS = [c for c in train_df.columns if c != TARGET]

# 类别型特征列表
CAT_COLS = [
    'ICD10_CHAPTER', 'BH_PREFIX', 'BH_CATEGORY',
    'MBR_TYPE', 'BEN_TYPE', 'KIND_CODE', 'POCY_PLAN_DESC'
]
# 连续型特征 = 其余
CONT_COLS = [c for c in FEATURE_COLS if c not in CAT_COLS]

# 类别特征转为 category dtype（XGBoost 2.0+ 原生支持）
for col in CAT_COLS:
    if col in train_df.columns:
        train_df[col] = train_df[col].astype('category')
        eval_df[col] = eval_df[col].astype('category')
        test_df[col] = test_df[col].astype('category')

X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET]
X_eval,  y_eval  = eval_df[FEATURE_COLS],  eval_df[TARGET]
X_test,  y_test  = test_df[FEATURE_COLS],  test_df[TARGET]

scale_pos = (y_train == 0).sum() / (y_train == 1).sum()
print(f"训练: {len(X_train)} | 验证: {len(X_eval)} | 测试: {len(X_test)}")
print(f"FRAUD 占比: {y_train.mean()*100:.1f}% | scale_pos_weight = {scale_pos:.2f}")

### 3.2 基线模型评估

# ============================================================
# 基线模型
# ============================================================
# 准备 OHE 版本数据（LR 需要 one-hot）
ohe = OneHotEncoder(
    sparse_output=False, handle_unknown='ignore',
    max_categories=30,       # 高频类别 >30 的统一归为 infrequent
    min_frequency=50         # 出现 <50 次的归为 infrequent
)
cats_in_data = [c for c in CAT_COLS if c in X_train.columns]
ohe.fit(X_train[cats_in_data])
X_train_ohe = np.hstack([
    X_train[CONT_COLS].values,
    ohe.transform(X_train[cats_in_data])
])
X_eval_ohe = np.hstack([
    X_eval[CONT_COLS].values,
    ohe.transform(X_eval[cats_in_data])
])

baselines = {
    "LogisticRegression": LogisticRegression(
        max_iter=2000, class_weight='balanced', random_state=42),
    "RandomForest": RandomForestClassifier(
        n_estimators=100, class_weight='balanced',
        random_state=42, n_jobs=-1)
}

for name, model in baselines.items():
    if name == "LogisticRegression":
        X_tr, X_va = X_train_ohe, X_eval_ohe
    else:
        # RF 用 TargetEncoder 处理类别（比 OHE 更适合树模型）
        te = TargetEncoder(random_state=42)
        X_tr_cat = te.fit_transform(X_train[cats_in_data], y_train)
        X_tr = np.hstack([X_train[CONT_COLS].values, X_tr_cat])
        X_va_cat = te.transform(X_eval[cats_in_data])
        X_va = np.hstack([X_eval[CONT_COLS].values, X_va_cat])

    model.fit(X_tr, y_train)
    y_prob_va = model.predict_proba(X_va)[:, 1]
    y_pred_va = model.predict(X_va)
    auc = roc_auc_score(y_eval, y_prob_va)
    f1 = f1_score(y_eval, y_pred_va)
    print(f"{name:20s} -> AUC: {auc:.4f}, F1: {f1:.4f}")

### 3.3 XGBoost 超参数搜索（Optuna + 5折交叉验证）

# ============================================================
# Optuna 超参数搜索（在 v4 特征集上重新搜索）
# ============================================================
def objective(trial):
    params = {
        'objective':          'binary:logistic',
        'eval_metric':        'aucpr',
        'tree_method':        'hist',
        'enable_categorical': True,
        'random_state':       RANDOM_STATE,
        'verbosity':          0,
        'max_depth':          trial.suggest_int('max_depth', 3, 8),
        'learning_rate':      trial.suggest_float('learning_rate', 0.05, 0.3, log=True),
        'n_estimators':       trial.suggest_int('n_estimators', 200, 800, step=100),
        'min_child_weight':   trial.suggest_int('min_child_weight', 1, 10),
        'subsample':          trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree':   trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'reg_alpha':          trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda':         trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'gamma':              trial.suggest_float('gamma', 1e-8, 5.0, log=True),
        'scale_pos_weight':   scale_pos,
    }

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    f1_scores = []

    for train_idx, val_idx in skf.split(X_train, y_train):
        X_tr = X_train.iloc[train_idx]
        X_va = X_train.iloc[val_idx]
        y_tr = y_train.iloc[train_idx]
        y_va = y_train.iloc[val_idx]

        model = xgb.XGBClassifier(**params)
        model.fit(X_tr, y_tr, verbose=False)
        y_pred = model.predict(X_va)
        f1_scores.append(f1_score(y_va, y_pred))

    return np.mean(f1_scores)

if RUN_OPTUNA:
    print(f"运行 Optuna 超参数搜索 (n_trials={OPTUNA_TRIALS})...")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction='maximize', study_name='xgb_fraud_v4')
    study.optimize(objective, n_trials=OPTUNA_TRIALS, show_progress_bar=True)
    study_best_params = study.best_params
    print(f"Optuna 最优 CV-F1: {study.best_value:.4f}")
    print(f"最优参数: {study_best_params}")
else:
    # 预设最优参数（v3 时代的参数，仅在跳过 Optuna 时使用）
    print("跳过 Optuna，使用预设参数...")
    study_best_params = {
        'max_depth': 8, 'learning_rate': 0.18556987923828613,
        'n_estimators': 500, 'min_child_weight': 1,
        'subsample': 0.9091037598084464, 'colsample_bytree': 0.9394944423861904,
        'reg_alpha': 6.542532753339318e-08, 'reg_lambda': 0.30299230225704027,
        'gamma': 5.464607791727065e-08,
    }

### 3.4 最终模型训练（Early Stopping）

# ============================================================
# 训练最终模型（带早停）
# ============================================================
best_params = {
    'objective':          'binary:logistic',
    'eval_metric':        'aucpr',
    'tree_method':        'hist',
    'enable_categorical': True,
    'random_state':       RANDOM_STATE,
    'scale_pos_weight':   scale_pos,
    **study_best_params
}

final_model = xgb.XGBClassifier(
    early_stopping_rounds=50,
    **best_params
)
final_model.fit(
    X_train, y_train,
    eval_set=[(X_eval, y_eval)],      # 仅在验证集上早停
    verbose=50,
)

# 输出早停信息
results = final_model.evals_result()
best_iter = final_model.best_iteration
print(f"最佳迭代轮数: {best_iter}")

### 3.4b 概率校准（Isotonic Regression）

# ============================================================
# 概率校准 — 使 predict_proba 更接近真实概率
# ============================================================
# 在验证集上拟合 Isotonic 校准器
print("\n[校准] Isotonic Regression...")
y_prob_eval_raw = final_model.predict_proba(X_eval)[:, 1]

iso_calibrator = IsotonicRegression(y_min=0, y_max=1, out_of_bounds='clip')
iso_calibrator.fit(y_prob_eval_raw, y_eval)
print(f"  校准完成 (n_samples={len(y_prob_eval_raw)})")

# 包装函数：替代 CalibratedClassifierCV 的 predict_proba
class CalibratedModel:
    def __init__(self, base_model, calibrator):
        self.base_model = base_model
        self.calibrator = calibrator
    def predict_proba(self, X):
        raw = self.base_model.predict_proba(X)
        calibrated = self.calibrator.predict(raw[:, 1])
        calibrated = np.clip(calibrated, 0, 1)
        return np.column_stack([1 - calibrated, calibrated])

calibrated_model = CalibratedModel(final_model, iso_calibrator)

### 3.5 阈值优化（仅在验证集上）

# ============================================================
# 验证集阈值优化（使用校准后的概率）
# ============================================================
y_prob_val = calibrated_model.predict_proba(X_eval)[:, 1]

thresholds = np.arange(0.1, 0.9, 0.01)
metrics_val = []
for t in thresholds:
    y_t = (y_prob_val >= t).astype(int)
    metrics_val.append({
        'threshold':  t,
        'f1':         f1_score(y_eval, y_t),
        'precision':  precision_score(y_eval, y_t, zero_division=0),
        'recall':     recall_score(y_eval, y_t),
    })

metrics_val_df = pd.DataFrame(metrics_val)
best_idx = metrics_val_df['f1'].idxmax()
best_threshold = metrics_val_df.loc[best_idx, 'threshold']
print(f"验证集最优阈值: {best_threshold:.2f}, F1={metrics_val_df.loc[best_idx, 'f1']:.4f}")

# 阈值曲线
plt.figure(figsize=(8, 5))
for metric in ['f1', 'precision', 'recall']:
    plt.plot(metrics_val_df['threshold'], metrics_val_df[metric], label=metric.capitalize())
plt.axvline(best_threshold, color='r', linestyle='--', label=f'Best={best_threshold:.2f}')
plt.xlabel('Threshold'); plt.ylabel('Score')
plt.title('Validation Set Threshold Tuning'); plt.legend()
plt.tight_layout(); plt.savefig('modeling/plots/threshold_tuning.png', dpi=150); plt.close()


### 3.6 测试集评估 + 交叉验证稳健性

# ============================================================
# 测试集评估
# ============================================================
y_prob_test = calibrated_model.predict_proba(X_test)[:, 1]
y_pred_test = (y_prob_test >= best_threshold).astype(int)

print("=" * 60)
print(f"测试集分类报告 (threshold={best_threshold:.2f})")
print("=" * 60)
print(classification_report(y_test, y_pred_test, target_names=['Normal', 'Fraud']))

auc = roc_auc_score(y_test, y_prob_test)
pr_auc = average_precision_score(y_test, y_prob_test)
f1 = f1_score(y_test, y_pred_test)
print(f"ROC-AUC: {auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f}")

# 交叉验证稳健性评估（用不带 early_stopping 的模型）
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_model = xgb.XGBClassifier(**best_params)
cv_f1 = cross_val_score(cv_model, X_train, y_train, cv=cv, scoring='f1')
print(f"5-fold CV F1: {cv_f1.mean():.4f} +/- {cv_f1.std():.4f}")

# ============================================================
# CV vs Test 差距诊断
# ============================================================
cv_test_gap = cv_f1.mean() - f1
if abs(cv_test_gap) > 0.03:
    print(f"\nWARNING: CV vs Test F1 差距: {cv_test_gap:+.4f} (>0.03)")
    print("  可能原因: 1) 验证集与测试集分布差异  2) 模型轻微过拟合  3) 特征集与实际任务不完全匹配")

# 校准前后对比（各自用独立最优阈值）
y_prob_test_raw = final_model.predict_proba(X_test)[:, 1]
# 为原始预测单独搜索最优 F1 阈值
best_f1_raw, best_t_raw = 0, 0.5
for t in np.arange(0.1, 0.9, 0.01):
    f1_t = f1_score(y_test, (y_prob_test_raw >= t).astype(int))
    if f1_t > best_f1_raw:
        best_f1_raw, best_t_raw = f1_t, t
y_pred_test_raw = (y_prob_test_raw >= best_t_raw).astype(int)
f1_raw = f1_score(y_test, y_pred_test_raw)
print(f"\n概率校准效果:")
print(f"  原始模型: F1={f1_raw:.4f} (threshold={best_t_raw:.2f})")
print(f"  校准后:   F1={f1:.4f} (threshold={best_threshold:.2f})")

# 混淆矩阵
cm = confusion_matrix(y_test, y_pred_test)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal', 'Fraud'], yticklabels=['Normal', 'Fraud'])
plt.xlabel('Predicted'); plt.ylabel('Actual')
plt.title('Confusion Matrix')
plt.tight_layout(); plt.savefig('modeling/plots/confusion_matrix.png', dpi=150); plt.close()

# ROC 曲线
fpr, tpr, _ = roc_curve(y_test, y_prob_test)
plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, label=f'ROC-AUC = {auc:.4f}')
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('False Positive Rate'); plt.ylabel('True Positive Rate')
plt.title('ROC Curve'); plt.legend()
plt.tight_layout(); plt.savefig('modeling/plots/roc_curve.png', dpi=150); plt.close()

# PR 曲线
precision_c, recall_c, _ = precision_recall_curve(y_test, y_prob_test)
plt.figure(figsize=(6, 5))
plt.plot(recall_c, precision_c, label=f'PR-AUC = {pr_auc:.4f}')
plt.xlabel('Recall'); plt.ylabel('Precision')
plt.title('PR Curve'); plt.legend()
plt.tight_layout(); plt.savefig('modeling/plots/pr_curve.png', dpi=150); plt.close()

# 特征重要性（从原始 XGBoost 模型提取）
importance = final_model.feature_importances_
feat_imp = pd.Series(importance, index=FEATURE_COLS).sort_values(ascending=True)
top20 = feat_imp.tail(20)
plt.figure(figsize=(10, max(7, len(top20)*0.3)))
top20.plot(kind='barh')
plt.xlabel('Importance'); plt.title(f'XGBoost Feature Importance (Top {len(top20)})')
plt.tight_layout(); plt.savefig('modeling/plots/feature_importance.png', dpi=150); plt.close()

### 3.8 SHAP 可解释性分析

print("\n" + "=" * 60)
print("SHAP 可解释性分析")
print("=" * 60)

try:
    import shap
    print(f"  SHAP version: {shap.__version__}")

    # SHAP 计算量大，使用测试集子样本
    # XGBoost 原生支持 TreeExplainer，速度快
    n_shap = min(1000, len(X_test))
    X_shap_sample = X_test.sample(n=n_shap, random_state=RANDOM_STATE)

    # 确保类别列是 category dtype
    for col in CAT_COLS:
        if col in X_shap_sample.columns:
            X_shap_sample[col] = X_shap_sample[col].astype('category')

    explainer = shap.TreeExplainer(final_model)
    shap_values = explainer.shap_values(X_shap_sample)

    # --- SHAP Summary Plot ---
    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_values, X_shap_sample,
        max_display=20, show=False
    )
    plt.tight_layout()
    plt.savefig('modeling/plots/shap_summary.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] modeling/plots/shap_summary.png")

    # --- SHAP Bar Plot (mean |SHAP|) ---
    plt.figure(figsize=(8, 6))
    shap.summary_plot(
        shap_values, X_shap_sample,
        plot_type='bar', max_display=20, show=False
    )
    plt.tight_layout()
    plt.savefig('modeling/plots/shap_importance.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] modeling/plots/shap_importance.png")

    # --- 单个样本 Waterfall（展示一条高风险预测） ---
    if y_test.sum() > 0:
        fraud_idx = X_test.index[y_test == 1][0]
        X_single = X_test.loc[[fraud_idx]]
        for col in CAT_COLS:
            if col in X_single.columns:
                X_single[col] = X_single[col].astype('category')
        shap_single = explainer.shap_values(X_single)

        plt.figure(figsize=(10, 5))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_single[0],
                base_values=explainer.expected_value,
                data=X_single.iloc[0].values,
                feature_names=X_single.columns.tolist()
            ),
            max_display=15, show=False
        )
        plt.tight_layout()
        plt.savefig('modeling/plots/shap_waterfall.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] modeling/plots/shap_waterfall.png")

except ImportError:
    print("  SHAP 未安装，跳过。安装: pip install shap")

### 3.7 模型保存

joblib.dump({
    'base_model': final_model,           # 原始 XGBoost（用于特征重要性/SHAP）
    'calibrator': iso_calibrator,        # IsotonicRegression 校准器
    'threshold': best_threshold,
    'feature_cols': FEATURE_COLS,
    'cat_cols': CAT_COLS,
}, 'modeling/xgb_fraud_model.pkl')
print("模型已保存: modeling/xgb_fraud_model.pkl (含概率校准器)")

# 推理示例
print("""
推理方式:
  import joblib, numpy as np
  m = joblib.load('modeling/xgb_fraud_model.pkl')
  raw_prob = m['base_model'].predict_proba(X)[:, 1]
  calibrated_prob = m['calibrator'].predict(raw_prob)
  pred = (calibrated_prob >= m['threshold']).astype(int)
""")

