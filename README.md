# 医保欺诈风险控制项目 (Insurance-Risk-Control)

基于机器学习的医疗保险理赔欺诈检测系统。

## 项目结构

```
rgzn-class/
├── README.md
├── .gitignore
│
├── docs/                             # 📄 项目文档
│   ├── requirements-analysis.md      # 需求分析文档
│   ├── requirements-analysis.html
│   └── ppt/                          # 课程配套PPT
│
├── data/                             # 🔧 数据处理 & 特征工程
│   ├── raw/                          # 原始数据（Excel，不入库）
│   ├── preprocessing.py              # 特征工程脚本（v4）
│   └── train_eval_test/              # 训练/验证/测试集（6:2:2）
│       ├── README.md                 # 特征说明 & 版本演进
│       ├── train.csv / eval.csv / test.csv
│
├── modeling/                         # 🤖 模型训练
│   ├── modeling.py                   # XGBoost 建模脚本
│   ├── xgb_fraud_model.pkl           # 训练好的模型（不入库）
│   └── plots/                        # 评估可视化（含 SHAP）
│
├── backend/                          # 🖥 FastAPI REST API 后端（待构建）
├── frontend/                         # 🎨 React + TypeScript Web 前端（待构建）
│
└── images/                           # 项目图片
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 特征工程 | Python, pandas, scikit-learn |
| 模型 | XGBoost + Optuna + 交叉验证 |
| 后端 | FastAPI + SQLAlchemy + Celery（待构建） |
| 前端 | React + TypeScript + Ant Design（待构建） |

## 最终模型性能 (v4)

| 指标 | 值 |
|------|-----|
| **ROC-AUC** | 0.9934 |
| **PR-AUC** | 0.9487 |
| **F1 Score** | 0.8835 |
| **Precision (Fraud)** | 0.87 |
| **Recall (Fraud)** | 0.89 |
| **5-fold CV F1** | 0.9259 ± 0.0037 |
| **最优阈值** | 0.36 |

## 快速开始

### 环境

```bash
uv sync          # 一键安装所有依赖
```

### 运行特征工程

```bash
# 1. 将原始 Excel 文件放入 data/raw/
# 2. 运行
uv run python data/preprocessing.py
```

### 运行建模

```bash
uv run python modeling/modeling.py
```

### 加载模型推理

```python
import joblib, numpy as np
m = joblib.load('modeling/xgb_fraud_model.pkl')
raw = m['base_model'].predict_proba(X)[:, 1]       # XGBoost 原始概率
prob = m['calibrator'].predict(raw)                 # Isotonic 校准后概率
pred = (prob >= m['threshold']).astype(int)         # threshold = 0.36
```
