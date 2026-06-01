#!/usr/bin/env python3
"""
医疗保险理赔 · 去泄漏特征工程 v4（白名单方式）

修复记录:
  v1: 12 特征，含 4 个泄漏特征
  v2: 移除 MAN_REJ_COUNT/PAY_AMT_USD_BIN/REJECTED_AMT/SCMA_OID_CL_LINE_STATUS，扩充至 29 特征
  v3: 移除 10 个金额泄漏特征，最终 27 个纯语义特征
  v4: 修复 ICD-10 D系编码分类Bug (D00-D48应为肿瘤而非血液病)、添加缺失值标记特征、
      清理冗余金额清洗代码、统一 BH_PREFIX 命名
"""

import pandas as pd
import numpy as np
import sys, os, warnings
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')
RANDOM_STATE = 42
FILE1 = 'data/raw/data-14-01.xlsx'
FILE2 = 'data/raw/data-18-01.xlsx'
OUTPUT_DIR = 'data/train_eval_test'

print("=" * 60)
print("医疗保险理赔 · 去泄漏特征工程 v4")
print("=" * 60)

# ============================
# 1. 加载
# ============================
print("\n[1] Loading...")
df1 = pd.read_excel(FILE1, dtype=str)
df2 = pd.read_excel(FILE2, dtype=str)
df = pd.concat([df1, df2], axis=0, ignore_index=True)
df.columns = df.columns.str.strip().str.upper()
df = df.drop_duplicates()
print(f"  {df.shape[0]} rows, {df.shape[1]} cols")
del df1, df2

# ============================
# 2. 金额列清洗
# ============================
print("\n[2] Cleaning amounts...")
for col in ['APP_AMT','BEN_SPEND','SUB_AMT','TOTAL_RECEIPT_AMT',
            'CL_SOCIAL_PAY_AMT','CL_OWNER_PAY_AMT','CL_SELF_CAT_PAY_AMT',
            'DED_AMT','PAY_AMT_USD','CWF_AMT_DAY']:
    if col in df.columns:
        s = df[col].astype(str).str.replace('RMB','',case=False,regex=False)
        s = s.str.replace(',','',regex=False).str.replace(' ','',regex=False)
        s = s.str.strip().replace(['nan','NAN','None','','NULL'], np.nan)
        df[col] = pd.to_numeric(s, errors='coerce')

# ============================
# 3. 日期特征
# ============================
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

# ============================
# 4. FRAUD 标签
# ============================
print("\n[4] FRAUD label...")
has_cl = df['RJ_CODE_LIST'].str.contains(r'CL_REJ_CODE_', na=False, regex=True).astype(int)
has_man = df['RJ_CODE_LIST'].str.contains(r'MAN_REJ_CODE_', na=False, regex=True).astype(int)
zero_pay = (df['PAY_AMT_USD'].fillna(-1) == 0).astype(int)
df['FRAUD'] = (((has_cl == 1) | (has_man == 1)) & (zero_pay == 1)).astype(int)
print(f"  FRAUD=1: {df['FRAUD'].sum()} ({df['FRAUD'].mean()*100:.1f}%)")

# ============================
# 5. 语义特征
# ============================
print("\n[5] Feature engineering...")

# ICD-10 (修复 D系/H系分类: D00-D48→NEOPLASM, D50-D89→BLOOD, H00-H95→EYE_EAR)
if 'DIAG_CODE' in df.columns:
    def icd10_chapter(code):
        """ICD-10 编码→大类章节"""
        if pd.isna(code) or not isinstance(code, str):
            return 'UNKNOWN'
        c = code.strip().upper()[0]
        rest = code.strip().upper()[1:] if len(code) > 1 else ''

        if c in ('A', 'B'):
            return 'INFECTIOUS'
        elif c == 'C':
            return 'NEOPLASM'
        elif c == 'D':
            # D00-D48 = 肿瘤, D50-D89 = 血液病
            if rest and rest[0] in '01234':
                return 'NEOPLASM'
            else:
                return 'BLOOD'
        elif c == 'E':
            return 'ENDOCRINE'
        elif c == 'F':
            return 'MENTAL'
        elif c == 'G':
            return 'NERVOUS'
        elif c == 'H':
            # H00-H95 = 眼/耳, 其他 = OTHER
            if rest and rest[0] in '0123456789':
                return 'EYE_EAR'
            return 'OTHER'
        elif c == 'I':
            return 'CIRCULATORY'
        elif c == 'J':
            return 'RESPIRATORY'
        elif c == 'K':
            return 'DIGESTIVE'
        elif c == 'L':
            return 'SKIN'
        elif c == 'M':
            return 'MUSCULOSKELETAL'
        elif c == 'N':
            return 'GENITOURINARY'
        elif c == 'O':
            return 'PREGNANCY'
        elif c == 'P':
            return 'PERINATAL'
        elif c == 'Q':
            return 'CONGENITAL'
        elif c == 'R':
            return 'SYMPTOMS'
        elif c in ('S', 'T'):
            return 'INJURY'
        elif c == 'Z':
            return 'FACTORS'
        else:
            return 'OTHER'
    df['ICD10_CHAPTER'] = df['DIAG_CODE'].apply(icd10_chapter)

# BEN_HEAD
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

# Hospital level
if 'PROV_LEVEL' in df.columns:
    order = {'一级':1,'二级':2,'三级':3,'医保':10,'非医保':11,'未评级':0,'卫生所':1,'特需':4}
    df['PROV_LEVEL_ORDINAL'] = df['PROV_LEVEL'].astype(str).str.upper().map(order).fillna(-1).astype(int)

# Member type
if 'MBR_TYPE' in df.columns:
    df['MBR_TYPE'] = df['MBR_TYPE'].astype(str).str.upper().replace(['NAN','NONE','NULL',''],'UNKNOWN')

# Benefit type
if 'SCMA_OID_BEN_TYPE' in df.columns:
    df['BEN_TYPE'] = df['SCMA_OID_BEN_TYPE'].astype(str).str.upper()

# Insurance kind
if 'KIND_CODE' in df.columns:
    df['KIND_CODE'] = df['KIND_CODE'].astype(str).str.upper()

# Policy plan description
if 'POCY_PLAN_DESC' in df.columns:
    df['POCY_PLAN_DESC'] = df['POCY_PLAN_DESC'].astype(str).str.upper().replace(['NAN','NONE','NULL',''],'UNKNOWN')

# Count cols
for col in ['NO_OF_YR','POLICY_CNT','INVOICE_CNT']:
    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

# Ratio
if 'COPAY_PCT' in df.columns: df['COPAY_PCT'] = pd.to_numeric(df['COPAY_PCT'], errors='coerce')

# Derived ratios (using safe pre-payment amounts only)
if 'TOTAL_RECEIPT_AMT' in df.columns and 'SUB_AMT' in df.columns:
    df['RECEIPT_TO_SUB_RATIO'] = np.where(df['SUB_AMT'].fillna(0) > 0,
        df['TOTAL_RECEIPT_AMT'].fillna(0) / df['SUB_AMT'].clip(lower=1), 0)

# Insured age
if 'NO_OF_YR' in df.columns:
    df['IS_NEW_INSURED'] = (df['NO_OF_YR'].fillna(0) <= 1).astype(int)
    df['IS_LONGTERM_INSURED'] = (df['NO_OF_YR'].fillna(0) >= 5).astype(int)

print("  Features generated")

# ============================
# 5b. 被保人聚合特征
# ============================
print("\n[5b] Member-level aggregation features...")

member_features_added = []
if 'MBR_NO' in df.columns:
    # 5b-1: 每被保人理赔次数
    mbr_claim_cnt = df.groupby('MBR_NO').size().rename('MBR_CLAIM_COUNT')
    df = df.join(mbr_claim_cnt, on='MBR_NO')
    member_features_added.append('MBR_CLAIM_COUNT')

    # 5b-2: 每被保人平均发票金额
    if 'SUB_AMT' in df.columns:
        df['SUB_AMT'] = pd.to_numeric(df['SUB_AMT'], errors='coerce')
        mbr_avg_sub = df.groupby('MBR_NO')['SUB_AMT'].mean().rename('MBR_AVG_SUB_AMT')
        df = df.join(mbr_avg_sub, on='MBR_NO')
        member_features_added.append('MBR_AVG_SUB_AMT')

    # 5b-3: 每被保人就诊医院数
    if 'PROV_CODE' in df.columns:
        mbr_hosp_cnt = df.groupby('MBR_NO')['PROV_CODE'].nunique().rename('MBR_UNIQUE_HOSPITALS')
        df = df.join(mbr_hosp_cnt, on='MBR_NO')
        member_features_added.append('MBR_UNIQUE_HOSPITALS')

    print(f"  Added: {member_features_added}")
else:
    print("  MBR_NO not found, skipping")

# ============================
# 6. Feature whitelist
# ============================
print("\n[6] Selecting features...")

CATEGORICAL = ['ICD10_CHAPTER','BH_PREFIX','BH_CATEGORY','MBR_TYPE','BEN_TYPE','KIND_CODE','POCY_PLAN_DESC']
CONTINUOUS = [
    # === Safe pre-payment amount features ===
    'SUB_AMT','TOTAL_RECEIPT_AMT','ORG_PRES_AMT_VALUE','COPAY_PCT',
    # === Policy info ===
    'NO_OF_YR','POLICY_CNT','INVOICE_CNT',
    # === Date-derived ===
    'DAYS_INCUR_TO_PAY','DAYS_RCV_TO_CLOSE','DAYS_HOSPITALIZATION','DAYS_RCV_TO_PAY',
    'IS_INPATIENT','INCUR_MONTH','INCUR_DAYOFWEEK','INCUR_QUARTER','INCUR_IS_WEEKEND',
    # === Hospital level ===
    'PROV_LEVEL_ORDINAL',
    # === Derived ratios ===
    'RECEIPT_TO_SUB_RATIO',
    # === Customer profile ===
    'IS_NEW_INSURED','IS_LONGTERM_INSURED',
    # === Member-level aggregates (v4) ===
    'MBR_CLAIM_COUNT','MBR_AVG_SUB_AMT','MBR_UNIQUE_HOSPITALS',
]

# Only keep columns that exist
CATEGORICAL = [c for c in CATEGORICAL if c in df.columns]
CONTINUOUS = [c for c in CONTINUOUS if c in df.columns]

# Build final dataframe
keep = CATEGORICAL + CONTINUOUS + ['FRAUD']
df = df[keep].copy()

print(f"  Categorical: {len(CATEGORICAL)} {CATEGORICAL}")
print(f"  Continuous:  {len(CONTINUOUS)}")

# ============================
# 6b. 缺失值标记特征
# ============================
print("\n[6b] Missing value indicators...")

# 对含缺失值的连续特征，创建缺失标记
new_missing_cols = []
for col in CONTINUOUS:
    if col in df.columns and df[col].isnull().any():
        miss_flag = f'{col}_MISSING'
        df[miss_flag] = df[col].isnull().astype(int)
        new_missing_cols.append(miss_flag)

# 也检查类别特征
for col in CATEGORICAL:
    if col in df.columns and df[col].isnull().any():
        miss_flag = f'{col}_MISSING'
        df[miss_flag] = df[col].isnull().astype(int)
        new_missing_cols.append(miss_flag)

if new_missing_cols:
    print(f"  Added: {new_missing_cols}")
else:
    print("  No missing values to flag")

# ============================
# 7. Clean & encode
# ============================
print("\n[7] Cleaning & encoding...")

# Fill categorical
for col in CATEGORICAL:
    df[col] = df[col].fillna('UNKNOWN').astype(str).astype('category')

# Fill continuous
for col in CONTINUOUS:
    df[col] = pd.to_numeric(df[col], errors='coerce')
    med = df[col].median()
    df[col] = df[col].fillna(med if not pd.isna(med) else 0)

# Winsorize (skip binary/time/ordinal)
skip_winsor = {'IS_INPATIENT','INCUR_MONTH','INCUR_DAYOFWEEK','INCUR_QUARTER',
               'INCUR_IS_WEEKEND','IS_NEW_INSURED','IS_LONGTERM_INSURED',
               'PROV_LEVEL_ORDINAL','COPAY_PCT','NO_OF_YR','POLICY_CNT','INVOICE_CNT'}
for col in CONTINUOUS:
    if col not in skip_winsor and df[col].nunique() > 10:
        lo, hi = df[col].quantile(0.01), df[col].quantile(0.99)
        df[col] = df[col].clip(lo, hi)

# Log transform skewed
for col in CONTINUOUS:
    if col not in skip_winsor and df[col].nunique() > 10:
        skew = df[col].skew()
        if abs(skew) > 1:
            mn = df[col].min()
            df[col] = np.log1p(df[col] - mn + 1)

# ============================
# 8. Split 6:2:2 + scale
# ============================
print("\n[8] Split & scale...")

y = df['FRAUD']
X = df.drop(columns=['FRAUD'])

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.4, random_state=RANDOM_STATE, stratify=y)
X_eval, X_test, y_eval, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=RANDOM_STATE, stratify=y_temp)

print(f"  Train: {len(X_train)} ({len(X_train)/len(df)*100:.0f}%)")
print(f"  Eval:  {len(X_eval)} ({len(X_eval)/len(df)*100:.0f}%)")
print(f"  Test:  {len(X_test)} ({len(X_test)/len(df)*100:.0f}%)")

# Scale continuous on training data
scaler = StandardScaler()
CONTINUOUS_EXISTING = [c for c in CONTINUOUS if c in X_train.columns]

if CONTINUOUS_EXISTING:
    X_train_cont = pd.DataFrame(
        scaler.fit_transform(X_train[CONTINUOUS_EXISTING]),
        columns=CONTINUOUS_EXISTING, index=X_train.index)
    X_eval_cont = pd.DataFrame(
        scaler.transform(X_eval[CONTINUOUS_EXISTING]),
        columns=CONTINUOUS_EXISTING, index=X_eval.index)
    X_test_cont = pd.DataFrame(
        scaler.transform(X_test[CONTINUOUS_EXISTING]),
        columns=CONTINUOUS_EXISTING, index=X_test.index)

    X_train = X_train.drop(columns=CONTINUOUS_EXISTING).join(X_train_cont)
    X_eval = X_eval.drop(columns=CONTINUOUS_EXISTING).join(X_eval_cont)
    X_test = X_test.drop(columns=CONTINUOUS_EXISTING).join(X_test_cont)

# Save
os.makedirs(OUTPUT_DIR, exist_ok=True)
pd.concat([X_train, y_train.rename('FRAUD')], axis=1).to_csv(f'{OUTPUT_DIR}/train.csv', index=False)
pd.concat([X_eval, y_eval.rename('FRAUD')], axis=1).to_csv(f'{OUTPUT_DIR}/eval.csv', index=False)
pd.concat([X_test, y_test.rename('FRAUD')], axis=1).to_csv(f'{OUTPUT_DIR}/test.csv', index=False)

total_features = len(CATEGORICAL) + len(CONTINUOUS_EXISTING)
print(f"\n{'='*60}")
print(f"Done! {total_features} features (cat:{len(CATEGORICAL)} + cont:{len(CONTINUOUS_EXISTING)})")
print(f"Train: {len(X_train)}, Eval: {len(X_eval)}, Test: {len(X_test)}")
print(f"FRAUD: {y_train.sum()}({y_train.mean()*100:.1f}%) / {y_eval.sum()}({y_eval.mean()*100:.1f}%) / {y_test.sum()}({y_test.mean()*100:.1f}%)")
print(f"Saved to {OUTPUT_DIR}/")
print("=" * 60)
