"""原始 Excel (108列) → 30 特征 DataFrame (原始值，未缩放).

从 data/preprocessing.py 提取核心逻辑，去掉：
  - FRAUD 标签计算
  - train/eval/test 切分
  - winsor / log1p / StandardScaler（feature_transform.py 负责）
  - category dtype 转换（feature_transform.py 负责）
  - 缺失值标记 *_MISSING（feature_transform.py 的 transform_single 动态生成）

输出 30 列原始特征，下游由 feature_transform.py 完成剩余的 35 列变换。
"""

import logging
import pandas as pd
import numpy as np

from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

# 35 特征列（与模型训练时的 FEATURE_COLS 一致）
CATEGORICAL = [
    'ICD10_CHAPTER', 'BH_PREFIX', 'BH_CATEGORY',
    'MBR_TYPE', 'BEN_TYPE', 'KIND_CODE', 'POCY_PLAN_DESC',
]
CONTINUOUS = [
    'SUB_AMT', 'TOTAL_RECEIPT_AMT', 'ORG_PRES_AMT_VALUE', 'COPAY_PCT',
    'NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT',
    'DAYS_INCUR_TO_PAY', 'DAYS_RCV_TO_CLOSE',
    'DAYS_HOSPITALIZATION', 'DAYS_RCV_TO_PAY',
    'IS_INPATIENT', 'INCUR_MONTH', 'INCUR_DAYOFWEEK',
    'INCUR_QUARTER', 'INCUR_IS_WEEKEND',
    'PROV_LEVEL_ORDINAL', 'RECEIPT_TO_SUB_RATIO',
    'IS_NEW_INSURED', 'IS_LONGTERM_INSURED',
    'MBR_CLAIM_COUNT', 'MBR_AVG_SUB_AMT', 'MBR_UNIQUE_HOSPITALS',
]

AMOUNT_COLS = [
    'APP_AMT', 'BEN_SPEND', 'SUB_AMT', 'TOTAL_RECEIPT_AMT',
    'CL_SOCIAL_PAY_AMT', 'CL_OWNER_PAY_AMT', 'CL_SELF_CAT_PAY_AMT',
    'DED_AMT', 'PAY_AMT_USD', 'CWF_AMT_DAY',
]


def preprocess_raw_excel(df: pd.DataFrame) -> pd.DataFrame:
    """将原始 108 列 DataFrame 转换为 35 特征 DataFrame.

    入参 df 由调用方从 Excel 读入，列名已标准化（strip + uppercase）。
    返回的 DataFrame 包含 35 个特征列，值为原始值（未经 winsor/log/scaler）。
    """

    # ---- 1. 金额列清洗 ----
    for col in AMOUNT_COLS:
        if col not in df.columns:
            continue
        s = df[col].astype(str).str.replace('RMB', '', case=False, regex=False)
        s = s.str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
        s = s.str.strip().replace(['nan', 'NAN', 'None', '', 'NULL'], np.nan)
        df[col] = pd.to_numeric(s, errors='coerce')

    # ---- 2. 日期特征 ----
    date_cols_map = [
        ('INCUR_DATE_FROM', '_from'), ('INCUR_DATE_TO', '_to'),
        ('PAY_DATE', '_pay'), ('RCV_DATE', '_rcv'), ('FILE_CLOSE_DATE', '_close'),
    ]
    for col, name in date_cols_map:
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

    # 清理临时日期列
    for name in ['_from', '_to', '_pay', '_rcv', '_close']:
        if name in df.columns:
            del df[name]

    # ---- 3. ICD-10 章节映射 ----
    if 'DIAG_CODE' in df.columns:

        def _icd10_chapter(code):
            if pd.isna(code) or not isinstance(code, str):
                return 'UNKNOWN'
            c = code.strip().upper()[0]
            rest = code.strip().upper()[1:] if len(code) > 1 else ''

            if c in ('A', 'B'):    return 'INFECTIOUS'
            elif c == 'C':          return 'NEOPLASM'
            elif c == 'D':
                if rest and rest[0] in '01234': return 'NEOPLASM'
                return 'BLOOD'
            elif c == 'E':          return 'ENDOCRINE'
            elif c == 'F':          return 'MENTAL'
            elif c == 'G':          return 'NERVOUS'
            elif c == 'H':
                if rest and rest[0] in '0123456789': return 'EYE_EAR'
                return 'OTHER'
            elif c == 'I':          return 'CIRCULATORY'
            elif c == 'J':          return 'RESPIRATORY'
            elif c == 'K':          return 'DIGESTIVE'
            elif c == 'L':          return 'SKIN'
            elif c == 'M':          return 'MUSCULOSKELETAL'
            elif c == 'N':          return 'GENITOURINARY'
            elif c == 'O':          return 'PREGNANCY'
            elif c == 'P':          return 'PERINATAL'
            elif c == 'Q':          return 'CONGENITAL'
            elif c == 'R':          return 'SYMPTOMS'
            elif c in ('S', 'T'):   return 'INJURY'
            elif c == 'Z':          return 'FACTORS'
            else:                   return 'OTHER'

        df['ICD10_CHAPTER'] = df['DIAG_CODE'].apply(_icd10_chapter)

    # ---- 4. BEN_HEAD 拆分 ----
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

    # ---- 5. PROV_LEVEL 序数化 ----
    if 'PROV_LEVEL' in df.columns:
        order = {
            '一级': 1, '二级': 2, '三级': 3,
            '医保': 10, '非医保': 11,
            '未评级': 0, '卫生所': 1, '特需': 4,
        }
        df['PROV_LEVEL_ORDINAL'] = (
            df['PROV_LEVEL'].astype(str).str.upper().map(order).fillna(-1).astype(int)
        )

    # ---- 6. 类别特征标准化 ----
    if 'MBR_TYPE' in df.columns:
        df['MBR_TYPE'] = df['MBR_TYPE'].astype(str).str.upper().replace(
            ['NAN', 'NONE', 'NULL', ''], 'UNKNOWN'
        )
    if 'SCMA_OID_BEN_TYPE' in df.columns:
        df['BEN_TYPE'] = df['SCMA_OID_BEN_TYPE'].astype(str).str.upper()
    if 'KIND_CODE' in df.columns:
        df['KIND_CODE'] = df['KIND_CODE'].astype(str).str.upper()
    if 'POCY_PLAN_DESC' in df.columns:
        df['POCY_PLAN_DESC'] = (
            df['POCY_PLAN_DESC'].astype(str).str.upper()
            .replace(['NAN', 'NONE', 'NULL', ''], 'UNKNOWN')
        )

    # ---- 7. 数值列转换（SUB_AMT/TOTAL_RECEIPT_AMT 已在 step 1 转换，此处跳过） ----
    for col in ['NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT', 'COPAY_PCT',
                'ORG_PRES_AMT_VALUE']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ---- 8. 派生比率 ----
    if 'TOTAL_RECEIPT_AMT' in df.columns and 'SUB_AMT' in df.columns:
        df['RECEIPT_TO_SUB_RATIO'] = np.where(
            df['SUB_AMT'].fillna(0) > 0,
            df['TOTAL_RECEIPT_AMT'].fillna(0) / df['SUB_AMT'].clip(lower=1),
            0,
        )

    # ---- 9. 被保人特征 ----
    if 'NO_OF_YR' in df.columns:
        df['IS_NEW_INSURED'] = (df['NO_OF_YR'].fillna(0) <= 1).astype(int)
        df['IS_LONGTERM_INSURED'] = (df['NO_OF_YR'].fillna(0) >= 5).astype(int)

    # ---- 10. 被保人聚合特征 ----
    if 'MBR_NO' in df.columns:
        df['MBR_CLAIM_COUNT'] = df.groupby('MBR_NO')['MBR_NO'].transform('count')
        if 'SUB_AMT' in df.columns:
            df['MBR_AVG_SUB_AMT'] = df.groupby('MBR_NO')['SUB_AMT'].transform('mean')
        if 'PROV_CODE' in df.columns:
            df['MBR_UNIQUE_HOSPITALS'] = df.groupby('MBR_NO')['PROV_CODE'].transform('nunique')

    # ---- 11. 筛选 35 特征列 ----
    all_features = CATEGORICAL + CONTINUOUS
    available = [c for c in all_features if c in df.columns]
    missing = set(all_features) - set(available)

    if missing:
        raise AppException(
            f"预处理后缺少 {len(missing)} 个必需特征列: {sorted(missing)}",
            status_code=500,
        )

    logger.info("Preprocess done: %d rows, %d features", len(df), len(available))
    return df[available]
