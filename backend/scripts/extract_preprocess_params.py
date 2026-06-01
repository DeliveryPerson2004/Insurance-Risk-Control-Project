#!/usr/bin/env python3
"""
提取预处理参数 → backend/app/services/preprocess_params.json

Phase 2 的 feature_transform.py 需要这些参数，用于对单条输入执行
与训练数据完全相同的 winsor/log/scale/encode 变换。

运行方式: uv run python backend/scripts/extract_preprocess_params.py
"""

import json
import os
import warnings
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

FILE1 = 'data/raw/data-14-01.xlsx'
FILE2 = 'data/raw/data-18-01.xlsx'
OUTPUT_PATH = 'backend/app/services/preprocess_params.json'

print("=" * 60)
print("提取预处理参数")
print("=" * 60)

# ---- 1. 加载 ----
print("\n[1] Loading raw data...")
df1 = pd.read_excel(FILE1, dtype=str)
df2 = pd.read_excel(FILE2, dtype=str)
df = pd.concat([df1, df2], axis=0, ignore_index=True)
df.columns = df.columns.str.strip().str.upper()
df = df.drop_duplicates()
print(f"  {df.shape[0]} rows, {df.shape[1]} cols")
del df1, df2

# ---- 2. 金额清洗 ----
print("\n[2] Cleaning amounts...")
for col in ['APP_AMT','BEN_SPEND','SUB_AMT','TOTAL_RECEIPT_AMT',
            'CL_SOCIAL_PAY_AMT','CL_OWNER_PAY_AMT','CL_SELF_CAT_PAY_AMT',
            'DED_AMT','PAY_AMT_USD','CWF_AMT_DAY']:
    if col in df.columns:
        s = df[col].astype(str).str.replace('RMB','',case=False,regex=False)
        s = s.str.replace(',','',regex=False).str.replace(' ','',regex=False)
        s = s.str.strip().replace(['nan','NAN','None','','NULL'], np.nan)
        df[col] = pd.to_numeric(s, errors='coerce')

# ---- 3. 日期特征 ----
print("\n[3] Date features...")
for col, name in [('INCUR_DATE_FROM','_from'),('INCUR_DATE_TO','_to'),
                  ('PAY_DATE','_pay'),('RCV_DATE','_rcv'),('FILE_CLOSE_DATE','_close')]:
    if col in df.columns:
        df[name] = pd.to_datetime(df[col], errors='coerce')

if '_from' in df.columns and '_pay' in df.columns:
    df['DAYS_INCUR_TO_PAY'] = (df['_pay'] - df['_from']).dt.days
if '_rcv' in df.columns and '_close' in df.columns:
    df['DAYS_RCV_TO_CLOSE'] = (df['_close'] - df['_rcv']).dt.days
if '_to' in df.columns and '_from' in df.columns:
    df['DAYS_HOSPITALIZATION'] = (df['_to'] - df['_from']).dt.days
    df['IS_INPATIENT'] = (df['DAYS_HOSPITALIZATION'] > 0).astype(int)
if '_from' in df.columns:
    df['INCUR_MONTH'] = df['_from'].dt.month.astype(int)
    df['INCUR_DAYOFWEEK'] = df['_from'].dt.dayofweek.astype(int)
    df['INCUR_QUARTER'] = df['_from'].dt.quarter.astype(int)
    df['INCUR_IS_WEEKEND'] = (df['INCUR_DAYOFWEEK'] >= 5).astype(int)
if '_rcv' in df.columns and '_pay' in df.columns:
    df['DAYS_RCV_TO_PAY'] = (df['_pay'] - df['_rcv']).dt.days

for name in ['_from','_to','_pay','_rcv','_close']:
    if name in df.columns: del df[name]

# ---- 4. ICD10 分类 ----
if 'DIAG_CODE' in df.columns:
    def icd10_chapter(code):
        if pd.isna(code) or not isinstance(code, str):
            return 'UNKNOWN'
        c = code.strip().upper()[0]
        rest = code.strip().upper()[1:] if len(code) > 1 else ''
        if c in ('A', 'B'): return 'INFECTIOUS'
        elif c == 'C': return 'NEOPLASM'
        elif c == 'D':
            if rest and rest[0] in '01234': return 'NEOPLASM'
            else: return 'BLOOD'
        elif c == 'E': return 'ENDOCRINE'
        elif c == 'F': return 'MENTAL'
        elif c == 'G': return 'NERVOUS'
        elif c == 'H':
            if rest and rest[0] in '0123456789': return 'EYE_EAR'
            return 'OTHER'
        elif c == 'I': return 'CIRCULATORY'
        elif c == 'J': return 'RESPIRATORY'
        elif c == 'K': return 'DIGESTIVE'
        elif c == 'L': return 'SKIN'
        elif c == 'M': return 'MUSCULOSKELETAL'
        elif c == 'N': return 'GENITOURINARY'
        elif c == 'O': return 'PREGNANCY'
        elif c == 'P': return 'PERINATAL'
        elif c == 'Q': return 'CONGENITAL'
        elif c == 'R': return 'SYMPTOMS'
        elif c in ('S', 'T'): return 'INJURY'
        elif c == 'Z': return 'FACTORS'
        else: return 'OTHER'
    df['ICD10_CHAPTER'] = df['DIAG_CODE'].apply(icd10_chapter)

# ---- 5. BEN_HEAD / PROV_LEVEL / MBR_TYPE / etc ----
if 'BEN_HEAD' in df.columns:
    bh = df['BEN_HEAD'].fillna('').astype(str)
    df['BH_PREFIX'] = 'OTHER'
    df.loc[bh.str.startswith('S-'), 'BH_PREFIX'] = 'SOCIAL'
    df.loc[bh.str.startswith('F-'), 'BH_PREFIX'] = 'NON_SOCIAL'
    df.loc[bh.str.startswith('NS-'), 'BH_PREFIX'] = 'NS'
    df.loc[bh.str.startswith('NF-'), 'BH_PREFIX'] = 'NF'
    df.loc[bh.str.startswith('100P'), 'BH_PREFIX'] = '100PCT'
    df['BH_CATEGORY'] = bh.str.extract(r'[-]?(YPF|GHF|JCF|ZLF|CJF|ZYF|ZFYP|SSF|CLF|CWF)$')
    df['BH_CATEGORY'] = df['BH_CATEGORY'].fillna('OTHER')

if 'PROV_LEVEL' in df.columns:
    order = {'一级':1,'二级':2,'三级':3,'医保':10,'非医保':11,'未评级':0,'卫生所':1,'特需':4}
    df['PROV_LEVEL_ORDINAL'] = df['PROV_LEVEL'].astype(str).str.upper().map(order).fillna(-1).astype(int)
if 'MBR_TYPE' in df.columns:
    df['MBR_TYPE'] = df['MBR_TYPE'].astype(str).str.upper().replace(['NAN','NONE','NULL',''],'UNKNOWN')
if 'SCMA_OID_BEN_TYPE' in df.columns:
    df['BEN_TYPE'] = df['SCMA_OID_BEN_TYPE'].astype(str).str.upper()
if 'KIND_CODE' in df.columns:
    df['KIND_CODE'] = df['KIND_CODE'].astype(str).str.upper()
if 'POCY_PLAN_DESC' in df.columns:
    df['POCY_PLAN_DESC'] = df['POCY_PLAN_DESC'].astype(str).str.upper().replace(['NAN','NONE','NULL',''],'UNKNOWN')

for col in ['NO_OF_YR','POLICY_CNT','INVOICE_CNT']:
    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
if 'COPAY_PCT' in df.columns: df[col] = pd.to_numeric(df['COPAY_PCT'], errors='coerce')

if 'TOTAL_RECEIPT_AMT' in df.columns and 'SUB_AMT' in df.columns:
    df['RECEIPT_TO_SUB_RATIO'] = np.where(df['SUB_AMT'].fillna(0) > 0,
        df['TOTAL_RECEIPT_AMT'].fillna(0) / df['SUB_AMT'].clip(lower=1), 0)
if 'NO_OF_YR' in df.columns:
    df['IS_NEW_INSURED'] = (df['NO_OF_YR'].fillna(0) <= 1).astype(int)
    df['IS_LONGTERM_INSURED'] = (df['NO_OF_YR'].fillna(0) >= 5).astype(int)

# ---- 6. 成员聚合 ----
if 'MBR_NO' in df.columns:
    mbr_claim_cnt = df.groupby('MBR_NO').size().rename('MBR_CLAIM_COUNT')
    df = df.join(mbr_claim_cnt, on='MBR_NO')
    if 'SUB_AMT' in df.columns:
        df['SUB_AMT'] = pd.to_numeric(df['SUB_AMT'], errors='coerce')
        mbr_avg_sub = df.groupby('MBR_NO')['SUB_AMT'].mean().rename('MBR_AVG_SUB_AMT')
        df = df.join(mbr_avg_sub, on='MBR_NO')
    if 'PROV_CODE' in df.columns:
        mbr_hosp_cnt = df.groupby('MBR_NO')['PROV_CODE'].nunique().rename('MBR_UNIQUE_HOSPITALS')
        df = df.join(mbr_hosp_cnt, on='MBR_NO')

# ---- 7. 特征筛选 ----
CATEGORICAL = ['ICD10_CHAPTER','BH_PREFIX','BH_CATEGORY','MBR_TYPE','BEN_TYPE','KIND_CODE','POCY_PLAN_DESC']
CONTINUOUS = [
    'SUB_AMT','TOTAL_RECEIPT_AMT','ORG_PRES_AMT_VALUE','COPAY_PCT',
    'NO_OF_YR','POLICY_CNT','INVOICE_CNT',
    'DAYS_INCUR_TO_PAY','DAYS_RCV_TO_CLOSE','DAYS_HOSPITALIZATION','DAYS_RCV_TO_PAY',
    'IS_INPATIENT','INCUR_MONTH','INCUR_DAYOFWEEK','INCUR_QUARTER','INCUR_IS_WEEKEND',
    'PROV_LEVEL_ORDINAL',
    'RECEIPT_TO_SUB_RATIO',
    'IS_NEW_INSURED','IS_LONGTERM_INSURED',
    'MBR_CLAIM_COUNT','MBR_AVG_SUB_AMT','MBR_UNIQUE_HOSPITALS',
]

CATEGORICAL = [c for c in CATEGORICAL if c in df.columns]
CONTINUOUS = [c for c in CONTINUOUS if c in df.columns]

# ---- 8. 缺失标记 ----
new_missing_cols = []
for col in CONTINUOUS + CATEGORICAL:
    if col in df.columns and df[col].isnull().any():
        miss_flag = f'{col}_MISSING'
        df[miss_flag] = df[col].isnull().astype(int)
        new_missing_cols.append(miss_flag)

MISSING_COLS = new_missing_cols

# ---- 9. 填充 + Winsorize + Log（在原始连续值上） ----
print("\n[9] Capturing fill values, winsor bounds, log params...")

# 9a. 填充类别特征
for col in CATEGORICAL:
    df[col] = df[col].fillna('UNKNOWN').astype(str).astype('category')

# 9b. 填充连续特征并记录中位数
fill_values = {}
for col in CONTINUOUS:
    df[col] = pd.to_numeric(df[col], errors='coerce')
    med = df[col].median()
    if pd.isna(med):
        med = 0.0
    fill_values[col] = float(med)
    df[col] = df[col].fillna(med)

# 9c. Winsorize（跳过分类型/二元/时间特征）
skip_winsor = {'IS_INPATIENT','INCUR_MONTH','INCUR_DAYOFWEEK','INCUR_QUARTER',
               'INCUR_IS_WEEKEND','IS_NEW_INSURED','IS_LONGTERM_INSURED',
               'PROV_LEVEL_ORDINAL','COPAY_PCT','NO_OF_YR','POLICY_CNT','INVOICE_CNT'}
winsor_bounds = {}
for col in CONTINUOUS:
    if col not in skip_winsor and df[col].nunique() > 10:
        lo, hi = float(df[col].quantile(0.01)), float(df[col].quantile(0.99))
        winsor_bounds[col] = [lo, hi]
        df[col] = df[col].clip(lo, hi)

# 9d. Log transform
log_params = {}
for col in CONTINUOUS:
    if col not in skip_winsor and df[col].nunique() > 10:
        skew = df[col].skew()
        if abs(skew) > 1:
            mn = float(df[col].min())
            log_params[col] = {"min": mn, "skew": float(skew)}
            df[col] = np.log1p(df[col] - mn + 1)

# ---- 10. StandardScaler（仅在非类别、非缺失标记的特征上） ----
print("\n[10] Fitting StandardScaler...")
scaler = StandardScaler()
cont_existing = [c for c in CONTINUOUS if c in df.columns]
if cont_existing:
    scaler.fit(df[cont_existing])

scaler_params = {}
for i, col in enumerate(cont_existing):
    scaler_params[col] = {
        "mean": float(scaler.mean_[i]),
        "std": float(scaler.scale_[i]),
    }

# ---- 11. 构建最终特征顺序 ----
ALL_FEATURES = cont_existing + CATEGORICAL + MISSING_COLS
print(f"\n  特征总数: {len(ALL_FEATURES)} (cont:{len(cont_existing)} + cat:{len(CATEGORICAL)} + missing:{len(MISSING_COLS)})")

# ---- 12. 保存 ----
params = {
    "cat_cols": CATEGORICAL,
    "cont_cols": cont_existing,
    "missing_cols": MISSING_COLS,
    "feature_cols": ALL_FEATURES,
    "fill_values": fill_values,
    "winsor_bounds": winsor_bounds,
    "skip_winsor": list(skip_winsor),
    "log_params": log_params,
    "scaler_params": scaler_params,
    "n_features": len(ALL_FEATURES),
    "description": "训练时提取的预处理参数。Phase 2 feature_transform.py 对单条输入执行相同变换。",
}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(params, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 参数已保存至: {OUTPUT_PATH}")
print(f"  cat_cols:      {len(CATEGORICAL)}")
print(f"  cont_cols:     {len(cont_existing)}")
print(f"  missing_cols:  {len(MISSING_COLS)}")
print(f"  winsor_bounds: {len(winsor_bounds)} cols")
print(f"  log_params:    {len(log_params)} cols")
print(f"  scaler_params: {len(scaler_params)} cols")
print(f"  total features: {len(ALL_FEATURES)}")
