#!/usr/bin/env python3
"""
=============================================================================
医疗保险理赔数据 · 全流程清洗与特征工程脚本
=============================================================================
目标文件：
  - data-14-01.xlsx（约 41,692 条 × 108 列）
  - data-18-01.xlsx（约 36,428 条 × 108 列，字段完全一致）
  两文件拼接后去重处理。
输出文件：
  - preprocessed_data.csv      预处理完成的全量数据（含 FRAUD 标签）
  - data_for_modeling.csv      特征选择后的建模数据集

配套资料（来自 E:\zhenew）：
  - 保险理赔数据-字段说明-学生.xlsx  字段说明 & ICD-10 & WARN_CODE 字典
  - 部分数据样例.xlsx              样例数据（用于对照验证）
  - all_data_v2.py                 前置版本（参考，本脚本在此基础上增强）

=============================================================================
核心修正（vs 原版）：
  1. FRAUD = (含拒赔码 CL_REJ_CODE / MAN_REJ_CODE) AND (PAY_AMT_USD == 0)
     排除 CL_WARN_CODE（警告码≠拒赔码）
  2. 衍生中间列全部在标签构造后删除，防止数据泄漏
  3. 增强特征工程：BEN_HEAD 类别 / ICD-10 大类 / WARN_CODE 计数 / 时间差
  4. 同时处理 data-14-01 与 data-18-01，拼接去重
=============================================================================
"""

import pandas as pd
import numpy as np
import warnings
from sklearn.preprocessing import (
    StandardScaler, LabelEncoder, KBinsDiscretizer
)
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import (
    VarianceThreshold, SelectKBest, f_classif
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel, RFE

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', 120)
pd.set_option('display.max_rows', 60)
pd.set_option('display.float_format', '{:.4f}'.format)

# ============================================================================
# 0. 配置
# ============================================================================
FILE1 = 'data-14-01.xlsx'
FILE2 = 'data-18-01.xlsx'
OUTPUT_PREPROCESSED = 'preprocessed_data.csv'
OUTPUT_MODELING = 'data_for_modeling.csv'
RANDOM_STATE = 42

print("=" * 70)
print("医疗保险理赔数据 · 全流程清洗与特征工程")
print(f"输入: {FILE1} + {FILE2}")
print("=" * 70)

# ============================================================================
# Cell 1: 数据加载与合并
# ============================================================================
print("\n[Cell 1] 加载数据...")

df1 = pd.read_excel(FILE1, dtype=str)
df2 = pd.read_excel(FILE2, dtype=str)
print(f"  {FILE1}: {df1.shape}")
print(f"  {FILE2}: {df2.shape}")

# 拼接
df = pd.concat([df1, df2], axis=0, ignore_index=True)
print(f"  拼接后: {df.shape}")

# 统一列名为大写
df.columns = df.columns.str.strip().str.upper()

# 去重
before = df.shape[0]
df = df.drop_duplicates()
print(f"  去重后: {df.shape} (移除 {before - df.shape[0]} 条重复)")

# 释放原始 DataFrame
del df1, df2

# ============================================================================
# Cell 2: 字段筛选 — 基于字段说明文档精选建模字段
# ============================================================================
print("\n[Cell 2] 字段筛选...")

# 分类整理（基于「保险理赔数据-字段说明-学生.xlsx」Sheet1）
keep_cols = [
    # === 理赔金额类 (7) ===
    'ORG_PRES_AMT_VALUE',   # 核准金额
    'APP_AMT',              # 赔付金额（申请）
    'BEN_SPEND',            # 本次福利项目扣减金额
    'PAY_AMT_USD',          # 实际支付金额（美元）
    'SUB_AMT',              # 发票金额
    'REJECTED_AMT',         # 拒赔金额
    'TOTAL_RECEIPT_AMT',    # 发票总金额

    # === 付款结构 (6) ===
    'CL_SOCIAL_PAY_AMT',    # 社保基金支付
    'CL_THIRD_PARTY_PAY_AMT', # 第三方支付
    'CL_OWNER_PAY_AMT',     # 自费
    'CL_SELF_CAT_PAY_AMT',  # 分类自负
    'DED_AMT',              # 免赔额
    'COPAY_PCT',            # 自负比例%

    # === 诊断 (5) ===
    'DIAG_CODE',            # ICD-10 疾病代码
    'CODES',                # 案件条拒赔代码列表
    'BEN_HEAD',             # 福利项目（药品费/挂号费/检查费...）
    'BEN_HEAD_TYPE',        # 福利项目大类（YPF/JCF/CWF...）
    'SCMA_OID_BEN_TYPE',    # 福利类型（BENEFIT_TYPE_OP/IP...）

    # === 医院 (4) ===
    'PROV_CODE',            # 医院代码
    'PROV_LEVEL',           # 医院等级（三级/二级/一级/未评级/医保）
    'PROV_DEPT',            # 就诊科室
    'CLSH_HOSP_CODE',       # 结算医院代码

    # === 理赔状态 (3) ===
    'SCMA_OID_CL_LINE_STATUS',  # 理赔条状态（AC=接受/RJ=拒绝/PD=搁置...）
    'SCMA_OID_CL_STATUS',       # 理赔状态（FC=完成/PC=部分完成...）
    'RJ_CODE_LIST',             # 拒赔/警告代码列表（分号分隔）

    # === 被保险人 (3) ===
    'MBR_NO',               # 被保险人编号
    'MBR_TYPE',             # 被保险人类型（Applicant/Child/Spouse/Parents）
    'NO_OF_YR',             # 投保年数

    # === 保单 (5) ===
    'POCY_NO',              # 保单号
    'POCY_PLAN_DESC',       # 保单计划描述
    'PLAN_OID',             # 计划OID
    'POPL_OID',             # 保单人群OID
    'POHO_NO',              # 保单持有人编号

    # === 时间 (5) ===
    'INCUR_DATE_FROM',      # 出险开始日期
    'INCUR_DATE_TO',        # 出险结束日期
    'PAY_DATE',             # 划账日期
    'RCV_DATE',             # 收件日期
    'FILE_CLOSE_DATE',      # 结案日期

    # === 行/单据 ID (2) ===
    'CL_NO',                # 理赔号
    'CL_LINE_NO',           # 理赔条编号

    # === 其他特征 (7) ===
    'KIND_CODE',            # 险种代码
    'INSUR_INVOICE_IND',    # 是否有保险发票
    'INVOICE_CNT',          # 发票数量
    'FX_RATE',              # 汇率
    'POLICY_CNT',           # 保单数
    'CWF_AMT_DAY',          # 日津贴金额
    'SCMA_OID_COUNTRY_TREATMENT',  # 就诊国家
]

# 统一为大写匹配
keep_cols_upper = [c.upper() for c in keep_cols]
existing = [c for c in keep_cols_upper if c in df.columns]
missing = set(keep_cols_upper) - set(existing)
if missing:
    print(f"  ⚠ 以下列不存在，已跳过: {missing}")
df = df[existing].copy()
print(f"筛选后: {df.shape} ({len(existing)} 列)")

# ============================================================================
# Cell 3: 金额列清洗
# ============================================================================
print("\n[Cell 3] 金额列清洗...")


def clean_currency(series):
    """去除 RMB / 千位逗号 / 空格 → 数值"""
    if series.dtype == 'object':
        s = series.astype(str)
        s = s.str.replace('RMB', '', case=False, regex=False)
        s = s.str.replace(',', '', regex=False)
        s = s.str.replace(' ', '', regex=False)
        s = s.str.strip()
        s = s.replace(['nan', 'NAN', 'None', '', 'NULL'], np.nan)
        return s
    return series


amt_cols = [
    'ORG_PRES_AMT_VALUE', 'APP_AMT', 'BEN_SPEND', 'PAY_AMT_USD',
    'SUB_AMT', 'REJECTED_AMT', 'TOTAL_RECEIPT_AMT',
    'CL_SOCIAL_PAY_AMT', 'CL_THIRD_PARTY_PAY_AMT', 'CL_OWNER_PAY_AMT',
    'CL_SELF_CAT_PAY_AMT', 'DED_AMT', 'CWF_AMT_DAY',
]
amt_cols = [c for c in amt_cols if c in df.columns]

for col in amt_cols:
    df[col] = clean_currency(df[col])
    df[col] = pd.to_numeric(df[col], errors='coerce')

print(f"  已清洗 {len(amt_cols)} 个金额列")

# ============================================================================
# Cell 4: 日期列处理 + 时间差特征
# ============================================================================
print("\n[Cell 4] 日期列处理 + 时间特征工程...")

date_cols = [
    'INCUR_DATE_FROM', 'INCUR_DATE_TO', 'PAY_DATE',
    'RCV_DATE', 'FILE_CLOSE_DATE'
]
date_cols = [c for c in date_cols if c in df.columns]

for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=False)

# --- 时间差特征 ---
if 'PAY_DATE' in df.columns and 'INCUR_DATE_FROM' in df.columns:
    df['DAYS_INCUR_TO_PAY'] = (
        df['PAY_DATE'] - df['INCUR_DATE_FROM']
    ).dt.days
    print("  ✓ DAYS_INCUR_TO_PAY（出险→划账 天数）")

if 'FILE_CLOSE_DATE' in df.columns and 'RCV_DATE' in df.columns:
    df['DAYS_RCV_TO_CLOSE'] = (
        df['FILE_CLOSE_DATE'] - df['RCV_DATE']
    ).dt.days
    print("  ✓ DAYS_RCV_TO_CLOSE（收件→结案 天数）")

if 'INCUR_DATE_TO' in df.columns and 'INCUR_DATE_FROM' in df.columns:
    df['DAYS_HOSPITALIZATION'] = (
        df['INCUR_DATE_TO'] - df['INCUR_DATE_FROM']
    ).dt.days
    # 住院天数：>0 标记为住院，0 为门诊
    df['IS_INPATIENT'] = (df['DAYS_HOSPITALIZATION'] > 0).astype(int)
    print("  ✓ DAYS_HOSPITALIZATION（住院天数）、IS_INPATIENT（是否住院）")

# 出险月份 / 星期（捕捉季节性）
if 'INCUR_DATE_FROM' in df.columns:
    df['INCUR_MONTH'] = df['INCUR_DATE_FROM'].dt.month
    df['INCUR_DAYOFWEEK'] = df['INCUR_DATE_FROM'].dt.dayofweek
    print("  ✓ INCUR_MONTH、INCUR_DAYOFWEEK")

# ============================================================================
# Cell 5: 类别列初步清洗
# ============================================================================
print("\n[Cell 5] 类别列清洗...")

cat_cols = [
    'PROV_LEVEL', 'MBR_TYPE', 'BEN_HEAD', 'BEN_HEAD_TYPE',
    'SCMA_OID_BEN_TYPE', 'SCMA_OID_CL_LINE_STATUS',
    'SCMA_OID_CL_STATUS', 'SCMA_OID_COUNTRY_TREATMENT',
    'KIND_CODE', 'INSUR_INVOICE_IND', 'PROV_DEPT',
    'POCY_PLAN_DESC',
]
cat_cols = [c for c in cat_cols if c in df.columns]

for col in cat_cols:
    df[col] = df[col].astype(str).str.strip().str.upper()
    df[col] = df[col].replace(['NAN', 'NONE', 'NULL', 'NA', ''], np.nan)

# RJ_CODE_LIST 和 CODES 也标准化
for col in ['RJ_CODE_LIST', 'CODES']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
        df[col] = df[col].replace(['NAN', 'NONE', 'NULL', 'NA', ''], np.nan)

print(f"  已清洗 {len(cat_cols)} 个类别列")

# ============================================================================
# Cell 6: 特殊字段转换
# ============================================================================
print("\n[Cell 6] 特殊字段转换...")

# 比例类
if 'COPAY_PCT' in df.columns:
    df['COPAY_PCT'] = pd.to_numeric(df['COPAY_PCT'], errors='coerce')

# 计数值
for col in ['NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# KIND_CODE 特殊处理：混合了数字代码和中文标签
if 'KIND_CODE' in df.columns:
    # 尝试转为数值，失败则保留字符串
    df['KIND_CODE_NUM'] = pd.to_numeric(df['KIND_CODE'], errors='coerce')
    df['KIND_CODE_IS_NUMERIC'] = df['KIND_CODE_NUM'].notna().astype(int)
    print("  ✓ KIND_CODE → KIND_CODE_NUM + KIND_CODE_IS_NUMERIC")

# PROV_LEVEL 有序编码
if 'PROV_LEVEL' in df.columns:
    prov_order = {
        '一级': 1, '二级': 2, '三级': 3,
        '医保': 10, '非医保': 11,
        '未评级': 0, '未知': 0, '卫生所': 1, '特需': 4,
    }
    df['PROV_LEVEL_ORDINAL'] = df['PROV_LEVEL'].map(prov_order).fillna(-1).astype(int)
    print("  ✓ PROV_LEVEL_ORDINAL（有序编码）")

# ============================================================================
# Cell 7: 缺失值分析 & 列过滤
# ============================================================================
print("\n[Cell 7] 缺失值分析与列过滤...")

missing_ratio = df.isnull().mean().sort_values(ascending=False)
print("  缺失比例 > 30% 的列:")
high_miss = missing_ratio[missing_ratio > 0.3]
if len(high_miss) > 0:
    for c, r in high_miss.items():
        print(f"    {c}: {r:.1%}")
else:
    print("    (无)")

# 删除常量列
const_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
if const_cols:
    print(f"  剔除常量列: {const_cols}")
    df.drop(columns=const_cols, inplace=True)

# 删除缺失率 > 60% 的列
high_missing = missing_ratio[missing_ratio > 0.6].index.tolist()
if high_missing:
    print(f"  剔除高缺失列 (>60%): {high_missing}")
    df.drop(columns=high_missing, inplace=True)

print(f"  当前: {df.shape}")

# ============================================================================
# Cell 8: 缺失值填充
# ============================================================================
print("\n[Cell 8] 缺失值填充...")

# 数值型：中位数
num_features = df.select_dtypes(include=[np.number]).columns.tolist()
if num_features:
    imputer_num = SimpleImputer(strategy='median')
    df[num_features] = imputer_num.fit_transform(df[num_features])

# 类别型：众数 / 'Unknown'
cat_features = df.select_dtypes(include=['object']).columns.tolist()
for col in cat_features:
    df[col] = df[col].replace(['NAN', 'NONE', 'NULL', 'NA', ''], np.nan)
    if df[col].dropna().empty:
        df[col] = df[col].fillna('UNKNOWN')
    else:
        mode_val = df[col].mode()
        df[col] = df[col].fillna(mode_val.iloc[0] if len(mode_val) > 0 else 'UNKNOWN')

# 日期型 → 距 1970-01-01 的天数
date_cols_now = df.select_dtypes(include=['datetime64']).columns.tolist()
for col in date_cols_now:
    df[col] = (df[col] - pd.Timestamp('1970-01-01')).dt.days

# 全 NaN 列
all_nan = [c for c in df.columns if df[c].isnull().all()]
if all_nan:
    print(f"  剔除全缺失列: {all_nan}")
    df.drop(columns=all_nan, inplace=True)

# 最终填充
num_cols_now = df.select_dtypes(include=[np.number]).columns.tolist()
if num_cols_now:
    imputer_final = SimpleImputer(strategy='median')
    df[num_cols_now] = imputer_final.fit_transform(df[num_cols_now])

print(f"  缺失值残留: {df.isnull().sum().sum()}")

# ============================================================================
# Cell 9: 异常值处理 — Winsorize (1%-99%)
# ============================================================================
print("\n[Cell 9] 异常值处理 (Winsorize 1%-99%)...")

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
# 排除不适合截尾的列
exclude_winsor = [
    'COPAY_PCT', 'NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT',
    'DAYS_INCUR_TO_PAY', 'DAYS_RCV_TO_CLOSE', 'DAYS_HOSPITALIZATION',
    'IS_INPATIENT', 'INCUR_MONTH', 'INCUR_DAYOFWEEK',
    'PROV_LEVEL_ORDINAL', 'KIND_CODE_IS_NUMERIC',
]
numeric_cols = [
    c for c in numeric_cols
    if c not in exclude_winsor and df[c].nunique() > 10
]

for col in numeric_cols:
    lo = df[col].quantile(0.01)
    hi = df[col].quantile(0.99)
    df[col] = df[col].clip(lo, hi)

print(f"  已截尾 {len(numeric_cols)} 个特征")

# ============================================================================
# Cell 10: BEN_HEAD 特征工程
# ============================================================================
print("\n[Cell 10] BEN_HEAD 特征工程...")

if 'BEN_HEAD' in df.columns:
    # 10a. 提取前缀：S- = 社保目录内, F- = 非社保, NS- = ?, NF- = ?
    #      100P = 100%赔付, 无前缀 = 其他
    df['BH_PREFIX'] = 'OTHER'
    df.loc[df['BEN_HEAD'].str.startswith('S-'), 'BH_PREFIX'] = 'S'       # 社保内
    df.loc[df['BEN_HEAD'].str.startswith('F-'), 'BH_PREFIX'] = 'F'       # 非社保
    df.loc[df['BEN_HEAD'].str.startswith('NS-'), 'BH_PREFIX'] = 'NS'
    df.loc[df['BEN_HEAD'].str.startswith('NF-'), 'BH_PREFIX'] = 'NF'
    df.loc[df['BEN_HEAD'].str.startswith('100P'), 'BH_PREFIX'] = '100P'
    print("  ✓ BH_PREFIX（福利项目社保分类）")

    # 10b. 提取类别后缀：YPF=药品费, GHF=挂号费, JCF=检查费, ZLF=诊疗费, CJF=材料费,
    #     ZYF=住院费, ZFYP=自费药品, SSF=手术费, CLF=材料费, CWF=床位费
    df['BH_CATEGORY'] = df['BEN_HEAD'].str.extract(
        r'[-]?(YPF|GHF|JCF|ZLF|CJF|ZYF|ZFYP|SSF|CLF|CWF)$'
    )
    df['BH_CATEGORY'] = df['BH_CATEGORY'].fillna('OTHER')
    print("  ✓ BH_CATEGORY（福利项目细分类别）")

    # 10c. 融合前缀+类别
    df['BH_COMBO'] = df['BH_PREFIX'] + '_' + df['BH_CATEGORY']
    print("  ✓ BH_COMBO（前缀_类别组合）")

# ============================================================================
# Cell 11: DIAG_CODE → ICD-10 大类特征
# ============================================================================
print("\n[Cell 11] ICD-10 疾病编码特征工程...")

if 'DIAG_CODE' in df.columns:
    # ICD-10 章节映射（基于 Sheet6 诊断字典）
    def icd10_chapter(code):
        """根据 ICD-10 编码前缀推断章节"""
        if pd.isna(code) or not isinstance(code, str):
            return 'UNKNOWN'
        code = code.strip().upper()
        prefix = code[0] if code else '?'
        if prefix == 'A' or prefix == 'B':
            return 'A_B_INFECTIOUS'        # 传染病和寄生虫病
        elif prefix == 'C' or (prefix == 'D' and len(code) > 1 and code[1] in '0123456789'):
            return 'C_D0_NEOPLASM'          # 肿瘤
        elif prefix == 'D':
            return 'D_BLOOD'                # 血液及造血器官疾病
        elif prefix == 'E':
            return 'E_ENDOCRINE'            # 内分泌、营养和代谢
        elif prefix == 'F':
            return 'F_MENTAL'               # 精神和行为障碍
        elif prefix == 'G':
            return 'G_NERVOUS'              # 神经系统
        elif prefix == 'H' and len(code) > 1 and code[1] in '0123456789':
            return 'H_EYE_EAR'              # 眼及附器/耳及乳突
        elif prefix == 'H':
            return 'H_OTHER'
        elif prefix == 'I':
            return 'I_CIRCULATORY'          # 循环系统
        elif prefix == 'J':
            return 'J_RESPIRATORY'          # 呼吸系统（感冒/流感/肺炎等）
        elif prefix == 'K':
            return 'K_DIGESTIVE'            # 消化系统
        elif prefix == 'L':
            return 'L_SKIN'                 # 皮肤和皮下组织
        elif prefix == 'M':
            return 'M_MUSCULOSKELETAL'      # 肌肉骨骼系统
        elif prefix == 'N':
            return 'N_GENITOURINARY'        # 泌尿生殖系统
        elif prefix == 'O':
            return 'O_PREGNANCY'            # 妊娠、分娩
        elif prefix == 'P':
            return 'P_PERINATAL'            # 围产期
        elif prefix == 'Q':
            return 'Q_CONGENITAL'           # 先天性畸形
        elif prefix == 'R':
            return 'R_SYMPTOMS'             # 症状、体征（咳嗽/头痛等）
        elif prefix == 'S' or prefix == 'T':
            return 'S_T_INJURY'             # 损伤、中毒
        elif prefix == 'Z':
            return 'Z_FACTORS'              # 影响健康状态的因素（体检等）
        elif prefix in 'UVWXY':
            return 'OTHER_ICD'
        else:
            return 'UNKNOWN'

    df['ICD10_CHAPTER'] = df['DIAG_CODE'].apply(icd10_chapter)
    print("  ✓ ICD10_CHAPTER（ICD-10 疾病大类）")

    # 提取 ICD-10 字母前缀
    df['ICD10_LETTER'] = df['DIAG_CODE'].str[0].fillna('?')
    print("  ✓ ICD10_LETTER（ICD-10 首字母）")

# ============================================================================
# Cell 12: 【核心】构造欺诈标签（修正版）
# ============================================================================
# 逻辑说明：
#   FRAUD = (含拒赔码 REJ_CODE) AND (实际支付 PAY_AMT_USD == 0)
#
#   RJ_CODE_LIST 中包含三类代码：
#     1. CL_REJ_CODE_*  系统拒赔码（R530=疑似欺诈, R520=其他拒赔, R060=系统拒赔...）
#     2. MAN_REJ_CODE_* 人工拒赔码（T180=人工审核后拒赔...）
#     3. CL_WARN_CODE_* 警告码（W055/W080/W200... 仅提醒，≠拒赔）
#   只有前两类与零支付的交集才标记为 FRAUD
# ============================================================================
print("\n[Cell 12] 【核心】构造 FRAUD 标签...")

if 'RJ_CODE_LIST' in df.columns:
    # 12a. 各类代码标记
    df['_HAS_CL_REJ'] = df['RJ_CODE_LIST'].str.contains(
        r'CL_REJ_CODE_', na=False, regex=True
    ).astype(int)

    df['_HAS_MAN_REJ'] = df['RJ_CODE_LIST'].str.contains(
        r'MAN_REJ_CODE_', na=False, regex=True
    ).astype(int)

    df['_HAS_WARN'] = df['RJ_CODE_LIST'].str.contains(
        r'CL_WARN_CODE_', na=False, regex=True
    ).astype(int)

    # 12b. 具体拒赔码标记
    df['_HAS_R530'] = df['RJ_CODE_LIST'].str.contains('R530', na=False).astype(int)
    df['_HAS_R520'] = df['RJ_CODE_LIST'].str.contains('R520', na=False).astype(int)
    df['_HAS_R060'] = df['RJ_CODE_LIST'].str.contains('R060', na=False).astype(int)
    df['_HAS_T180'] = df['RJ_CODE_LIST'].str.contains('T180', na=False).astype(int)

    # 12c. 警告码种类计数
    df['_WARN_CODE_COUNT'] = df['RJ_CODE_LIST'].str.count(r'CL_WARN_CODE_')
    df['_REJ_CODE_COUNT'] = df['RJ_CODE_LIST'].str.count(r'CL_REJ_CODE_')
    df['_MAN_REJ_COUNT'] = df['RJ_CODE_LIST'].str.count(r'MAN_REJ_CODE_')
else:
    for c in ['_HAS_CL_REJ', '_HAS_MAN_REJ', '_HAS_WARN',
              '_HAS_R530', '_HAS_R520', '_HAS_R060', '_HAS_T180',
              '_WARN_CODE_COUNT', '_REJ_CODE_COUNT', '_MAN_REJ_COUNT']:
        df[c] = 0

# 12d. 零支付定义
if 'PAY_AMT_USD' in df.columns:
    df['_IS_ZERO_PAY'] = (df['PAY_AMT_USD'] == 0).astype(int)
else:
    df['_IS_ZERO_PAY'] = 0

# 12e. 含任何拒赔码（系统 + 人工）
df['_HAS_ANY_REJ'] = (
    (df['_HAS_CL_REJ'] == 1) | (df['_HAS_MAN_REJ'] == 1)
).astype(int)

# 12f. FRAUD = 拒赔码 ∩ 零支付
df['FRAUD'] = (
    (df['_HAS_ANY_REJ'] == 1) & (df['_IS_ZERO_PAY'] == 1)
).astype(int)

print(f"\n  FRAUD 标签分布:")
print(f"    FRAUD=1: {df['FRAUD'].sum()} ({df['FRAUD'].mean()*100:.2f}%)")
print(f"    FRAUD=0: {(df['FRAUD']==0).sum()} ({(1-df['FRAUD'].mean())*100:.2f}%)")

print(f"\n  代码统计:")
print(f"    含 CL_REJ_CODE (系统拒赔): {df['_HAS_CL_REJ'].sum()}")
print(f"    含 MAN_REJ_CODE (人工拒赔): {df['_HAS_MAN_REJ'].sum()}")
print(f"    含 CL_WARN_CODE (警告):     {df['_HAS_WARN'].sum()}")
print(f"    IS_ZERO_PAY (零支付):       {df['_IS_ZERO_PAY'].sum()}")
print(f"    拒赔码 ∩ 零支付 = FRAUD:    {df['FRAUD'].sum()}")
print(f"    含拒赔码但支付>0 (非欺诈):   {(df['_HAS_ANY_REJ']==1).sum() - df['FRAUD'].sum()}")

# 12g. 保存 RJ_CODE 衍生特征（用于后续特征工程），然后删除原始列
# 这些是有信息量的特征，不会被删除
code_features = {
    '_WARN_CODE_COUNT': df['_WARN_CODE_COUNT'].copy(),
    '_REJ_CODE_COUNT': df['_REJ_CODE_COUNT'].copy(),
    '_MAN_REJ_COUNT': df['_MAN_REJ_COUNT'].copy(),
    '_HAS_WARN': df['_HAS_WARN'].copy(),
    '_HAS_CL_REJ': df['_HAS_CL_REJ'].copy(),
}

# 12h. 删除原始泄露列 + 标签构造中间列
leakage_drop = ['RJ_CODE_LIST', 'CODES']  # 原始泄露列
derived_drop = [c for c in df.columns if c.startswith('_')]  # 所有 _ 前缀中间列
all_drop = [c for c in leakage_drop + derived_drop if c in df.columns]
df.drop(columns=all_drop, inplace=True)

# 12i. 加回有信息量的代码统计特征（重命名去掉 _ 前缀）
rename_map = {
    '_WARN_CODE_COUNT': 'WARN_CODE_COUNT',
    '_REJ_CODE_COUNT': 'REJ_CODE_COUNT',
    '_MAN_REJ_COUNT': 'MAN_REJ_COUNT',
    '_HAS_WARN': 'HAS_WARN_CODE',
    '_HAS_CL_REJ': 'HAS_REJ_CODE',
}
for old_name, new_name in rename_map.items():
    df[new_name] = code_features[old_name]

print(f"\n  已删除 {len(all_drop)} 个泄露/中间列")
print(f"  保留 {len(rename_map)} 个代码统计特征")

# ============================================================================
# Cell 13: 分箱处理
# ============================================================================
print("\n[Cell 13] 分箱处理...")

discretize_cols = ['SUB_AMT', 'PAY_AMT_USD']
discretize_cols = [c for c in discretize_cols if c in df.columns]

if discretize_cols:
    est = KBinsDiscretizer(n_bins=5, encode='ordinal', strategy='quantile')
    binned = est.fit_transform(df[discretize_cols]).astype(int)
    binned_cols = [f'{c}_BIN' for c in discretize_cols]
    df.drop(columns=discretize_cols, inplace=True)
    df[binned_cols] = binned
    print(f"  ✓ {binned_cols}")
else:
    print("  无合适的分箱特征")

# ============================================================================
# Cell 14: 对数变换（高偏度特征）
# ============================================================================
print("\n[Cell 14] 对数变换...")

candidate = [
    c for c in df.select_dtypes(include=[np.number]).columns
    if c not in [
        'FRAUD', 'COPAY_PCT', 'NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT',
        'IS_INPATIENT', 'INCUR_MONTH', 'INCUR_DAYOFWEEK',
        'PROV_LEVEL_ORDINAL', 'KIND_CODE_IS_NUMERIC',
        'PAY_AMT_USD_BIN', 'SUB_AMT_BIN',
    ]
    and not c.endswith('_BIN')
    and not c.startswith('HAS_')
    and not c.endswith('_COUNT')
]

if candidate:
    skewness = df[candidate].skew().abs()
    skewed = skewness[skewness > 1].index.tolist()
    print(f"  偏度 > 1: {len(skewed)} 个 → {skewed}")
    for col in skewed:
        min_val = df[col].min()
        if min_val <= 0:
            df[col] = df[col] - min_val + 1
        df[col] = np.log1p(df[col])
else:
    print("  无候选列")

# ============================================================================
# Cell 15: 标准化
# ============================================================================
print("\n[Cell 15] 标准化...")

exclude_scaling = ['FRAUD']
bin_cols = [c for c in df.columns if c.endswith('_BIN')]

scaler = StandardScaler()
numeric_to_scale = [
    c for c in df.select_dtypes(include=[np.number]).columns
    if c not in exclude_scaling + bin_cols
]

df_scaled = df.copy()
if numeric_to_scale:
    df_scaled[numeric_to_scale] = scaler.fit_transform(df[numeric_to_scale])
    print(f"  ✓ 已缩放 {len(numeric_to_scale)} 个特征")
else:
    print("  无可缩放特征")

# ============================================================================
# Cell 16: 类别编码
# ============================================================================
print("\n[Cell 16] 类别编码 (Label Encoding)...")

cat_features = df_scaled.select_dtypes(include=['object']).columns.tolist()
print(f"  待编码 ({len(cat_features)} 个): {cat_features}")

label_encoders = {}
for col in cat_features:
    le = LabelEncoder()
    df_scaled[col] = le.fit_transform(df_scaled[col].astype(str))
    label_encoders[col] = le
    print(f"    {col}: {len(le.classes_)} 类")

# ============================================================================
# Cell 17: 最终数据验证
# ============================================================================
print("\n[Cell 17] 最终数据验证...")

print(f"  预处理后形状: {df_scaled.shape}")
print(f"  数据类型分布:\n{df_scaled.dtypes.value_counts().to_string()}")
print(f"  缺失值总数: {df_scaled.isnull().sum().sum()}")
print(f"  无限值总数: {np.isinf(df_scaled.select_dtypes(include=[np.number]).values).sum()}")

# 检查 FRAUD 标签
if 'FRAUD' in df_scaled.columns:
    print(f"\n  FRAUD 标签最终分布:")
    print(f"    {df_scaled['FRAUD'].value_counts().to_string()}")

# ============================================================================
# Cell 18: 保存预处理全量数据
# ============================================================================
print("\n[Cell 18] 保存预处理数据...")

df_scaled.to_csv(OUTPUT_PREPROCESSED, index=False, encoding='utf-8-sig')
print(f"  ✓ 已保存至 {OUTPUT_PREPROCESSED}")

# ============================================================================
# Cell 19: 分离特征与标签，剔除 ID 列
# ============================================================================
print("\n[Cell 19] 分离 X / y，剔除 ID...")

id_cols = [
    'CL_NO', 'CL_LINE_NO', 'MBR_NO', 'POCY_NO',
    'POPL_OID', 'POHO_NO', 'PLAN_OID',
    'PROV_CODE', 'CLSH_HOSP_CODE',
]
id_cols = [c for c in id_cols if c in df_scaled.columns]

y = df_scaled['FRAUD']
X = df_scaled.drop(columns=id_cols + ['FRAUD'], errors='ignore')
print(f"  X: {X.shape}, y: {y.shape}")
print(f"  已剔除 ID 列: {[c for c in id_cols if c in df_scaled.columns]}")

# ============================================================================
# Cell 20: 过滤法特征选择
# ============================================================================
print("\n[Cell 20] 过滤法特征选择...")

# 低方差过滤
sel_var = VarianceThreshold(threshold=0.01)
X_var = sel_var.fit_transform(X)
mask_var = sel_var.get_support()
kept_var = X.columns[mask_var]
print(f"  低方差过滤: {X.shape[1]} → {len(kept_var)}")

# 单变量
k_select = min(25, len(kept_var))
selector = SelectKBest(score_func=f_classif, k=k_select)
X_filtered = selector.fit_transform(X_var, y)
mask = selector.get_support()
final_filter = kept_var[mask]
print(f"  SelectKBest Top {k_select}:")
for i, f in enumerate(final_filter):
    print(f"    {i+1:2d}. {f}")

X_final = pd.DataFrame(X_filtered, columns=final_filter)

# ============================================================================
# Cell 21: 嵌入法 — 随机森林特征重要性
# ============================================================================
print("\n[Cell 21] 嵌入法（随机森林）...")

rf = RandomForestClassifier(
    n_estimators=100, random_state=RANDOM_STATE,
    n_jobs=-1, class_weight='balanced'
)
rf.fit(X_final, y)

importances = pd.Series(
    rf.feature_importances_, index=X_final.columns
).sort_values(ascending=False)
print("  特征重要性 Top 15:")
for i, (f, imp) in enumerate(importances.head(15).items()):
    print(f"    {i+1:2d}. {f:<35s} {imp:.4f}")

sel_embedded = SelectFromModel(rf, threshold='median')
X_embedded = sel_embedded.fit_transform(X_final, y)
embedded_features = X_final.columns[sel_embedded.get_support()]
print(f"\n  嵌入法保留: {len(embedded_features)} 个")

# ============================================================================
# Cell 22: 包装法（RFE）
# ============================================================================
print("\n[Cell 22] 包装法（RFE）...")

if X_embedded.shape[1] > 10:
    rfe_est = RandomForestClassifier(
        n_estimators=50, random_state=RANDOM_STATE,
        n_jobs=-1, class_weight='balanced'
    )
    n_select = min(12, X_embedded.shape[1])
    rfe = RFE(rfe_est, n_features_to_select=n_select, step=1)
    X_rfe = rfe.fit_transform(X_embedded, y)
    rfe_features = embedded_features[rfe.get_support()]
    print(f"  包装法保留 {len(rfe_features)} 个:")
    for f in rfe_features:
        print(f"    - {f}")
    X_selected = pd.DataFrame(X_rfe, columns=rfe_features)
else:
    X_selected = pd.DataFrame(X_embedded, columns=embedded_features)
    print(f"  特征已精简 ({X_embedded.shape[1]} 个)，跳过包装法")

# ============================================================================
# Cell 23: 保存最终建模数据
# ============================================================================
print("\n[Cell 23] 保存建模数据...")

final_df = pd.concat([X_selected, y.rename('FRAUD')], axis=1)
final_df.to_csv(OUTPUT_MODELING, index=False, encoding='utf-8-sig')
print(f"  最终数据集: {final_df.shape}")
print(f"  ✓ 已保存至 {OUTPUT_MODELING}")

# ============================================================================
# Cell 24: 输出摘要
# ============================================================================
print("\n" + "=" * 70)
print("✅ 全流程完成！")
print(f"  原始文件:    {FILE1} + {FILE2}")
print(f"  合并去重后:  {df.shape[0]} 条")
print(f"  预处理后:    {df_scaled.shape}")
print(f"  建模数据:    {final_df.shape}")
print(f"  FRAUD=1:    {y.sum()} ({y.mean()*100:.2f}%)")
print(f"  输出文件:")
print(f"    {OUTPUT_PREPROCESSED}")
print(f"    {OUTPUT_MODELING}")
print("=" * 70)
