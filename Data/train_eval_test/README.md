# 保险欺诈风险控制 - XGBoost 模型训练方案

## 一、环境依赖

```bash
uv pip install xgboost>=2.0.0 scikit-learn>=1.3.0 optuna>=3.4.0 pandas>=2.0.0 matplotlib>=3.7.0 seaborn>=0.12.0 joblib>=1.3.0
```

---

## 二、数据概况

| 项目 | 说明 |
|------|------|
| 训练样本数 | 46,146 条 |
| 验证集 / 测试集 | 各约 20%（见 train_eval_test 目录划分） |
| 特征数量 | 12 个 |
| 目标变量 | `FRAUD`（二分类：0=正常, 1=欺诈） |
| 欺诈比例 | 6,041 条 (13.1%)，正常 40,105 条 (86.9%) |
| 类别不平衡比 | 约 6.6 : 1 |

### 特征说明

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `APP_AMT` | 连续型（已标准化） | 申请金额 |
| `BEN_SPEND` | 连续型（已标准化） | 福利消费金额 |
| `REJECTED_AMT` | 连续型（已标准化） | 拒付金额 |
| `DED_AMT` | 连续型（已标准化） | 免赔额 |
| `SCMA_OID_CL_LINE_STATUS` | 分类型（4 类：0/1/2/3） | 索赔行状态 |
| `POCY_PLAN_DESC` | 分类型（5 类） | 保单计划描述 |
| `INCUR_DATE_FROM` | 连续型（已标准化） | 费用发生日期 |
| `PAY_DATE` | 连续型（已标准化） | 支付日期 |
| `RCV_DATE` | 连续型（已标准化） | 收件日期 |
| `DAYS_INCUR_TO_PAY` | 连续型（已标准化） | 费用发生到支付的天数 |
| `MAN_REJ_COUNT` | 连续型（已标准化） | 人工拒付次数 |
| `PAY_AMT_USD_BIN` | 有序分类（5 档：0-4） | 支付金额分箱 |

---

## 三、完整代码方案

### 3.1 数据加载与准备

```python
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    f1_score, precision_recall_curve, average_precision_score,
    roc_auc_score, classification_report, confusion_matrix,
    roc_curve, precision_score, recall_score
)
from sklearn.model_selection import StratifiedKFold
import optuna
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. 数据加载
# ============================================================
DATA_DIR = "Data/train_eval_test"

train_df = pd.read_csv(f"{DATA_DIR}/train.csv")
eval_df  = pd.read_csv(f"{DATA_DIR}/eval.csv")
test_df  = pd.read_csv(f"{DATA_DIR}/test.csv")

FEATURE_COLS = [
    'APP_AMT', 'BEN_SPEND', 'REJECTED_AMT', 'DED_AMT',
    'SCMA_OID_CL_LINE_STATUS', 'POCY_PLAN_DESC',
    'INCUR_DATE_FROM', 'PAY_DATE', 'RCV_DATE',
    'DAYS_INCUR_TO_PAY', 'MAN_REJ_COUNT', 'PAY_AMT_USD_BIN'
]
TARGET = 'FRAUD'

X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET]
X_eval,  y_eval  = eval_df[FEATURE_COLS],  eval_df[TARGET]
X_test,  y_test  = test_df[FEATURE_COLS],  test_df[TARGET]

# 计算类别不平衡权重
scale_pos = (y_train == 0).sum() / (y_train == 1).sum()
print(f"训练集: {len(X_train)} 条, 验证集: {len(X_eval)} 条, 测试集: {len(X_test)} 条")
print(f"scale_pos_weight = {scale_pos:.2f}")
```

### 3.2 超参数搜索（Optuna）

**什么是超参数搜索？**

超参数是模型训练前需要人工设定的配置项（如树的最大深度、学习率等），它们不能通过梯度下降自动学习。超参数搜索就是在预设的候选范围内，自动尝试不同的超参数组合，通过交叉验证选出在验证集上表现最优的配置。常用方法包括网格搜索、随机搜索和贝叶斯搜索。这里使用 **Optuna**（贝叶斯搜索框架），它能根据历史试验结果智能选择下一组参数，比随机搜索更高效。

```python
# ============================================================
# 2. Optuna 超参数搜索
# ============================================================
def objective(trial):
    """Optuna 目标函数：以验证集 F1-Score 为优化目标"""
    params = {
        'objective':        'binary:logistic',
        'eval_metric':      'aucpr',          # 用 PR-AUC 作为内部评估
        'tree_method':      'hist',
        'random_state':     42,
        'verbosity':        0,

        # --- 搜索空间 ---
        'max_depth':        trial.suggest_int('max_depth', 3, 10),
        'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators':     trial.suggest_int('n_estimators', 100, 1000, step=50),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'subsample':        trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha':        trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda':       trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'gamma':            trial.suggest_float('gamma', 1e-8, 5.0, log=True),
        'scale_pos_weight': scale_pos,
    }

    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_eval, y_eval)],
        verbose=False,
    )

    y_pred = model.predict(X_eval)
    return f1_score(y_eval, y_pred)

# 运行搜索（默认 100 轮试验）
study = optuna.create_study(direction='maximize', study_name='xgb_fraud')
study.optimize(objective, n_trials=100, show_progress_bar=True)

print(f"\n最优 F1-Score: {study.best_value:.4f}")
print(f"最优参数: {study.best_params}")
```

### 3.3 模型训练（使用最优参数 + Early Stopping）

```python
# ============================================================
# 3. 用最优参数训练最终模型
# ============================================================
best_params = {
    'objective':        'binary:logistic',
    'eval_metric':      'aucpr',
    'tree_method':      'hist',
    'random_state':     42,
    'scale_pos_weight': scale_pos,
    **study.best_params,          # 合并 Optuna 搜索到的最优参数
}

best_model = xgb.XGBClassifier(**best_params)
best_model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_eval, y_eval)],
    verbose=50,
)

# 保存模型
joblib.dump(best_model, 'xgb_fraud_model.pkl')
print("模型已保存: xgb_fraud_model.pkl")
```

### 3.4 评估方法

```python
# ============================================================
# 4. 在测试集上全面评估
# ============================================================
y_prob  = best_model.predict_proba(X_test)[:, 1]   # 欺诈概率
y_pred  = best_model.predict(X_test)                # 默认阈值 0.5

# --- 4.1 分类报告 ---
print("=" * 60)
print("分类报告 (threshold=0.5)")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=['正常', '欺诈']))

# --- 4.2 核心指标 ---
f1     = f1_score(y_test, y_pred)
pr_auc = average_precision_score(y_test, y_prob)
roc    = roc_auc_score(y_test, y_prob)
prec   = precision_score(y_test, y_pred)
rec    = recall_score(y_test, y_pred)

print(f"F1-Score : {f1:.4f}")
print(f"PR-AUC   : {pr_auc:.4f}")
print(f"ROC-AUC  : {roc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall   : {rec:.4f}")

# --- 4.3 混淆矩阵 ---
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['正常', '欺诈'], yticklabels=['正常', '欺诈'])
plt.xlabel('预测值')
plt.ylabel('真实值')
plt.title('混淆矩阵')
plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=150)
plt.show()

# --- 4.4 ROC 曲线 ---
fpr, tpr, _ = roc_curve(y_test, y_prob)
plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, label=f'ROC-AUC = {roc:.4f}')
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('假正率 (FPR)')
plt.ylabel('真正率 (TPR)')
plt.title('ROC 曲线')
plt.legend()
plt.tight_layout()
plt.savefig('roc_curve.png', dpi=150)
plt.show()

# --- 4.5 PR 曲线 ---
precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_prob)
plt.figure(figsize=(6, 5))
plt.plot(recall_curve, precision_curve, label=f'PR-AUC = {pr_auc:.4f}')
plt.xlabel('召回率 (Recall)')
plt.ylabel('精确率 (Precision)')
plt.title('PR 曲线')
plt.legend()
plt.tight_layout()
plt.savefig('pr_curve.png', dpi=150)
plt.show()

# --- 4.6 特征重要性 ---
importance = best_model.feature_importances_
feat_imp = pd.Series(importance, index=FEATURE_COLS).sort_values(ascending=True)
plt.figure(figsize=(8, 5))
feat_imp.plot(kind='barh')
plt.xlabel('重要性')
plt.title('XGBoost 特征重要性')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150)
plt.show()
```

### 3.5 阈值优化

```python
# ============================================================
# 5. 阈值优化：寻找最优分类阈值
# ============================================================
# 默认阈值 0.5 不一定最优，根据业务需求调整：
#   - 偏重召回率（减少漏检）→ 降低阈值
#   - 偏重精确率（减少误报）→ 提高阈值

thresholds = np.arange(0.1, 0.9, 0.01)
results = []
for t in thresholds:
    y_t = (y_prob >= t).astype(int)
    results.append({
        'threshold': t,
        'f1':        f1_score(y_test, y_t),
        'precision': precision_score(y_test, y_t, zero_division=0),
        'recall':    recall_score(y_test, y_t),
    })

result_df = pd.DataFrame(results)

# 找到 F1 最优阈值
best_idx = result_df['f1'].idxmax()
best_threshold = result_df.loc[best_idx, 'threshold']
print(f"最优 F1 阈值: {best_threshold:.2f}")
print(f"  F1={result_df.loc[best_idx, 'f1']:.4f}, "
      f"Precision={result_df.loc[best_idx, 'precision']:.4f}, "
      f"Recall={result_df.loc[best_idx, 'recall']:.4f}")

# 可视化阈值与指标的关系
plt.figure(figsize=(8, 5))
plt.plot(result_df['threshold'], result_df['f1'], label='F1')
plt.plot(result_df['threshold'], result_df['precision'], label='Precision')
plt.plot(result_df['threshold'], result_df['recall'], label='Recall')
plt.axvline(best_threshold, color='r', linestyle='--', label=f'最优阈值={best_threshold:.2f}')
plt.xlabel('分类阈值')
plt.ylabel('指标值')
plt.title('阈值 vs F1 / Precision / Recall')
plt.legend()
plt.tight_layout()
plt.savefig('threshold_tuning.png', dpi=150)
plt.show()

# 用最优阈值重新输出结果
y_pred_opt = (y_prob >= best_threshold).astype(int)
print("\n" + "=" * 60)
print(f"分类报告 (threshold={best_threshold:.2f})")
print("=" * 60)
print(classification_report(y_test, y_pred_opt, target_names=['正常', '欺诈']))
```

---

## 四、关键超参数说明

| 超参数 | 含义 | 搜索范围 | 影响 |
|--------|------|----------|------|
| `max_depth` | 树的最大深度 | 3-10 | 越深越复杂，易过拟合 |
| `learning_rate` | 学习率（步长） | 0.01-0.3 | 越小越稳健，需配合更多树 |
| `n_estimators` | 树的数量 | 100-1000 | 越多越强，配合 Early Stopping |
| `min_child_weight` | 叶节点最小权重和 | 1-10 | 越大越保守 |
| `subsample` | 行采样比例 | 0.6-1.0 | <1 可减少过拟合 |
| `colsample_bytree` | 列采样比例 | 0.6-1.0 | <1 可减少过拟合 |
| `reg_alpha` | L1 正则化 | 1e-8-10 | 越大越保守 |
| `reg_lambda` | L2 正则化 | 1e-8-10 | 越大越保守 |
| `gamma` | 分裂最小增益 | 1e-8-5 | 越大越保守 |
| `scale_pos_weight` | 正样本权重 | ≈6.63 | 处理类别不平衡 |

---

## 五、运行流程

```
1. 安装依赖    uv pip install xgboost scikit-learn optuna pandas matplotlib seaborn joblib
2. 超参数搜索  运行 3.2 节 → 输出最优参数（约 5-15 分钟）
3. 模型训练    运行 3.3 节 → 输出 xgb_fraud_model.pkl
4. 模型评估    运行 3.4 节 → 输出指标、混淆矩阵、ROC/PR 曲线、特征重要性
5. 阈值优化    运行 3.5 节 → 输出最优阈值和优化后的分类报告
```
