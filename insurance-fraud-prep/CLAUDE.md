# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: insurance-fraud-prep

## Project Overview

Insurance claim fraud detection preprocessing pipeline implemented as a single Jupyter notebook (`all_data.ipynb`). The pipeline processes Chinese medical insurance claims data (76,911 records), constructs a binary fraud label, and performs feature selection to produce a modeling-ready dataset.

All comments and domain terminology are in Simplified Chinese. The data originates from a Chinese medical insurance system with RMB-denominated fields.

## Running the Notebook

```bash
# Install dependencies
pip install pandas numpy scikit-learn openpyxl

# Run all cells
jupyter nbconvert --to notebook --execute all_data.ipynb
```

The notebook requires two source Excel files (`data-14-01.xlsx`, `data-18-01.xlsx`) which are **not included** in this repository.

## Dependencies

- pandas, numpy, scikit-learn (preprocessing, imputation, feature selection, RandomForestClassifier)
- openpyxl (for reading .xlsx files)

## Pipeline Architecture

The notebook is a sequential 22-cell pipeline with these stages:

1. **Data Loading** (Cells 1-2): Load two Excel files (108 columns each), concatenate, deduplicate → 76,911 rows
2. **Column Selection** (Cell 3): Keep 47 core columns across groups: claim amounts, payment structure, diagnosis, hospital, claim status, insured person, policy, time features
3. **Cleaning** (Cells 4-7): Strip "RMB" from currency columns, parse dates (derive `DAYS_FROM_INCUR_TO_PAY`), normalize categorical strings, convert count/percentage fields to numeric
4. **Missing Values & Outliers** (Cells 8-10): Drop constant columns and >60% missing columns, impute (median for numeric, mode for categorical, days-since-epoch for dates), winsorize at 1st/99th percentile
5. **Label Construction** (Cell 11): Binary `FRAUD` label = (has rejection code R530 or T180) AND (zero payment). Creates `HAS_R530`, `HAS_T180`, `IS_ZERO_PAY` helper features. **Immediately drops `RJ_CODE_LIST` and `CODES` to prevent data leakage.**
6. **Feature Engineering** (Cells 12-15): Bin `SUB_AMT`/`PAY_AMT_USD` into 5 quantile bins, log1p transform on 11 skewed features, StandardScaler on continuous numerics, LabelEncoder on remaining categoricals
7. **Feature Selection** (Cells 18-21): Drop 9 ID columns → filter (variance threshold 0.01 + SelectKBest top 20) → embedded (RandomForest importance, SelectFromModel at median) → wrapper (RFE, skipped if ≤10 features already)
8. **Output** (Cells 17, 22): `preprocessed_data.csv` (47 columns) and `data_for_modeling.csv` (10 features + FRAUD label)

## Key Design Decisions

- **Fraud definition**: Claims with rejection codes R530/T180 and zero payment are labeled fraud (73% of data — highly imbalanced)
- **Feature engineering order**: Binning happens before log transform; label encoding is last after all numeric transformations
- **Data leakage prevention**: Source columns used for label construction (`RJ_CODE_LIST`, `CODES`) are dropped immediately after label creation
- **No train/test split**: The notebook outputs a single dataset; splitting and model training are downstream tasks

## Output Files

| File | Shape | Description |
|------|-------|-------------|
| `preprocessed_data.csv` | 76,911 × 47 | Full preprocessed dataset with all features |
| `data_for_modeling.csv` | 76,911 × 11 | Final 10 selected features + `FRAUD` label |

## Final Selected Features

`APP_AMT`, `REJECTED_AMT`, `COPAY_PCT`, `PROV_LEVEL`, `POCY_PLAN_DESC`, `KIND_CODE`, `CWF_AMT_DAY`, `HAS_R530`, `HAS_T180`, `IS_ZERO_PAY`
