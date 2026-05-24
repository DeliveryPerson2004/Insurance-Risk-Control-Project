# 保险欺诈风险控制 - 机器学习建模方案

## 修订历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 | - | 12 特征，含 4 个泄漏特征 |
| v2 | 2026-05-11 | 移除 4 个泄漏特征，扩充至 29 个语义特征 |
| **v3** | **2026-05-11** | **移除 10 个金额泄漏特征，最终 27 个纯语义特征** |

---

## 一、泄漏特征发现与修复

### v1 → v2 修复
| 被移除 | 原因 |
|--------|------|
| `MAN_REJ_COUNT` | 人工拒赔码计数 → 96.68% 欺诈 |
| `PAY_AMT_USD_BIN` | 支付金额分箱（BIN=0 → 65.36% 欺诈） |
| `REJECTED_AMT` | 拒赔金额，与标签高度相关 |
| `SCMA_OID_CL_LINE_STATUS` | 理赔状态（RJ → 84.81% 欺诈） |

### v2 → v3 修复（本次关键发现）
v2 模型 AUC 高达 0.9997，经排查发现 APP_AMT 和 BEN_SPEND 仍泄漏标签：
- **所有 FRAUD=1 案件在原始数据中 APP_AMT = 0, BEN_SPEND = 0**
- 零支付案件的金额字段被系统统一填为 0，成为 PAY_AMT_USD 的「分身」
- 进一步扫描发现以下金额字段同样存在泄漏：

| 字段 | FRAUD=1 中为零比例 | 判定 |
|------|-------------------|------|
| `APP_AMT` | 100% | **泄漏** |
| `BEN_SPEND` | 100% | **泄漏** |
| `CL_THIRD_PARTY_PAY_AMT` | 100% | **泄漏** |
| `CWF_AMT_DAY` | 95.3% | **泄漏** |
| `CL_SELF_CAT_PAY_AMT` | 87.5% | **泄漏** |
| `DED_AMT` | 76.5% | **泄漏** |
| `CL_SOCIAL_PAY_AMT` | 72.7% | **泄漏** |
| `CL_OWNER_PAY_AMT` | 60.2% | **泄漏** |
| `SOCIAL_PAY_RATIO` | 基于嫌疑似特征 | **派生泄漏** |
| `OWNER_PAY_RATIO` | 基于嫌疑似特征 | **派生泄漏** |

### 真正安全的金额特征（pre-payment）
| 字段 | FRAUD=1 中为零比例 | 说明 |
|------|-------------------|------|
| `SUB_AMT` | 6.7% | 发票金额 — 理赔申请时提交 |
| `TOTAL_RECEIPT_AMT` | 8.6% | 收据总额 — 来自医院 |
| `ORG_PRES_AMT_VALUE` | 14.5% | 处方原始价值 — 与赔付无关 |

---

## 二、最终特征集（27 个，v3）

### 连续型特征（20 个）

| 特征名 | 说明 | 来源 |
|--------|------|------|
| `SUB_AMT` | 发票金额 | 安全金额 |
| `TOTAL_RECEIPT_AMT` | 收据总额 | 安全金额 |
| `ORG_PRES_AMT_VALUE` | 处方金额 | 安全金额 |
| `COPAY_PCT` | 自负比例（%） | 保单条款 |
| `NO_OF_YR` | 投保年数 | 保单信息 |
| `POLICY_CNT` | 保单数量 | 保单信息 |
| `INVOICE_CNT` | 发票数量 | 理赔信息 |
| `DAYS_INCUR_TO_PAY` | 出险→划账天数 | 日期派生 |
| `DAYS_RCV_TO_CLOSE` | 收件→结案天数 | 日期派生 |
| `DAYS_HOSPITALIZATION` | 住院天数（0=门诊） | 日期派生 |
| `DAYS_RCV_TO_PAY` | 收件→划账天数 | 日期派生 |
| `IS_INPATIENT` | 是否住院（0/1） | 日期派生 |
| `INCUR_MONTH` | 出险月份（1-12） | 日期派生 |
| `INCUR_DAYOFWEEK` | 出险星期（0=周一） | 日期派生 |
| `INCUR_QUARTER` | 出险季度（1-4） | 日期派生 |
| `INCUR_IS_WEEKEND` | 是否周末就诊 | 日期派生 |
| `PROV_LEVEL_ORDINAL` | 医院等级 | 医院信息 |
| `RECEIPT_TO_SUB_RATIO` | 收据金额/发票金额 | 派生怕 |
| `IS_NEW_INSURED` | 是否新投保（≤1年） | 客户画像 |
| `IS_LONGTERM_INSURED` | 是否长期投保（≥5年） | 客户画像 |

### 类别型特征（7 个）

| 特征名 | 类别数 | 说明 |
|--------|--------|------|
| `ICD10_CHAPTER` | 20 | ICD-10 疾病大类 |
| `BH_PREFIX` | 6 | 福利社保分类 |
| `BH_CATEGORY` | 10 | 福利细分类别 |
| `MBR_TYPE` | 4 | 被保人类型 |
| `BEN_TYPE` | 17 | 福利类型 |
| `KIND_CODE` | 29 | 险种代码 |
| `POCY_PLAN_DESC` | 606 | 保单计划描述 |

---

## 三、运行方式

### 环境

```bash
uv pip install xgboost>=2.0.0 scikit-learn>=1.3.0 optuna pandas matplotlib seaborn joblib imbalanced-learn
```

### 文件结构

```
Insurance-Risk-Control-Project/
├── preprocessing.py              # 数据预处理（从原始 Excel 生成 train/eval/test）
├── modeling.py                   # 完整建模流程
├── xgb_fraud_model.pkl           # 训练好的模型
├── pyproject.toml                # 依赖管理
├── Data/train_eval_test/
│   ├── train.csv                 # 训练集 46,146 条
│   ├── eval.csv                  # 验证集 15,382 条
│   ├── test.csv                  # 测试集 15,383 条
│   └── README.md                 # 本文件
├── threshold_tuning.png          # 阈值优化曲线
├── confusion_matrix.png          # 混淆矩阵
├── roc_curve.png                 # ROC 曲线
├── pr_curve.png                  # PR 曲线
└── feature_importance.png        # 特征重要性 Top 20
```

### 运行建模

```bash
python modeling.py
```

脚本流程：数据加载 → 基线(LR+RF) → 最终模型(XGBoost+早停) → 阈值优化 → 测试集评估 → CV稳健性 → 图表输出 → 模型保存

---

## 四、最终结果

| 指标 | 值 |
|------|-----|
| **ROC-AUC** | 0.9904 |
| **PR-AUC** | 0.9283 |
| **F1 Score** | 0.8680 |
| **Precision (Fraud)** | 0.80 |
| **Recall (Fraud)** | 0.95 |
| **5-fold CV F1** | 0.9114 ± 0.0052 |
| **最优阈值** | 0.35 |

### 基线与消融

| 模型 | AUC | F1 |
|------|-----|-----|
| LogisticRegression | 0.8946 | 0.5545 |
| RandomForest | 0.9945 | 0.9053 |
| **XGBoost** | **0.9904** | **0.8680** |

### 输出图表说明

| 图表 | 含义 |
|------|------|
| `threshold_tuning.png` | F1/Precision/Recall 随阈值变化曲线，标注最优 F1 点。当前最优阈值 0.35 |
| `confusion_matrix.png` | 测试集混淆矩阵。真负/假正/假负/真正 |
| `roc_curve.png` | ROC 曲线，AUC 越接近 1 越好。反映了模型对正负样本的整体排序能力 |
| `pr_curve.png` | PR 曲线，适合不平衡数据集评估。关注 Precision 在高 Recall 区间的表现 |
| `feature_importance.png` | XGBoost 特征重要性 Top 20，帮助理解哪些特征对预测贡献最大 |

### 模型文件

`xgb_fraud_model.pkl`（1.6 MB）：joblib 格式，包含模型、最优阈值、特征列名、类别列名。加载方式：

```python
import joblib
m = joblib.load('xgb_fraud_model.pkl')
model = m['model']        # XGBClassifier
threshold = m['threshold'] # 0.35
```

---

## 五、结果解读

- **Recall 0.95**：100 个真实欺诈案件能抓到 95 个，漏网率 5%，业务上可接受
- **Precision 0.80**：模型标记为「欺诈」的案件中 80% 是真的，20% 是误报。需要人工复核。
- **CV F1 0.9114 ± 0.0052**：模型稳定性好，方差极低
- 相比含泄漏的 v2（AUC 0.9997），v3 下降约 0.01，但这是**诚实的分**，代表模型真正从疾病/时间/医院/保单模式中学到了欺诈信号，而非作弊

### 已知局限

1. **特征工程已较保守**：所有金额相关字段经过两次排查，仅保留 3 个 pre-payment 安全字段
2. **未做 Optuna 重搜参**：当前使用 v2 的最优参（`max_depth=8, lr=0.186, n_estimators=500`），在新特征集上重新搜参可能还有小幅提升
3. **POCY_PLAN_DESC (606 类)**：高基数类别特征，XGBoost `enable_categorical` 原生支持，但在 LR 中需要额外处理
4. **SHAP 分析**：未包含在当前运行中（耗时较长），可独立运行分析

---

## 六、技术细节

- **标准化**：StandardScaler 仅在训练集上 fit，验证/测试集使用相同 scaler
- **划分策略**：`train_test_split(stratify=y)`，三轮 (60:40 → 20:20)
- **缺失值**：连续列用中位数填充，类别列填充 'UNKNOWN'
- **异常值**：Winsorize (1%-99%) + 偏度 >1 的对数变换
- **类别编码**：XGBoost 用 `enable_categorical=True` 原生处理；LR 用 OneHotEncoder (max_categories=30)；RF 用 TargetEncoder
- **早停**：`early_stopping_rounds=50`，基于验证集 AUC-PR

---

## 七、特征泄漏检查清单（后续参考）

任何新加入的数值型特征，建议先跑一遍：

```python
# 检查欺诈案件中特征值为零的比例
f0 = df[df['FRAUD']==0]['NEW_FEATURE']
f1 = df[df['FRAUD']==1]['NEW_FEATURE']
pct_zero = (f1 == 0).mean() * 100
if pct_zero > 50:
    print(f"WARNING: {pct_zero:.0f}% of fraud cases have NEW_FEATURE=0 — SUSPICIOUS")
```

**判定标准**：>90% 为泄漏，50-90% 为高嫌疑，<50% 通常安全（视具体领域而定）。
