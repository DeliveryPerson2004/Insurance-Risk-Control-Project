整体流程
两个 Excel (76,911行×108列)
        ↓
   字段筛选 → 47列
        ↓
   数据清洗 → 金额/日期/类别
        ↓
   特征工程 → 衍生10+个新特征
        ↓
   标签构造 → FRAUD (13.09%)
        ↓
   标准化+编码 → 全数值
        ↓
   三阶段特征选择 → 12个特征
        ↓
   建模数据集 (76,911×13)
1. 合并去重
两个文件字段完全一样，直接 concat → 76,911 行，0 重复。

2. 字段筛选（108→47）
不是随便筛的，按你的字段说明文档分了类：

类别	保留	举例
金额	7个	PAY_AMT_USD、BEN_SPEND、REJECTED_AMT…
付款结构	6个	社保支付、自费、免赔额…
诊断	5个	DIAG_CODE、BEN_HEAD、CODES…
医院	4个	PROV_LEVEL、PROV_DEPT…
理赔状态	3个	CL_LINE_STATUS、RJ_CODE_LIST…
时间	5个	出险日期、划账日期…
保单/ID/其他	17个	MBR_TYPE、KIND_CODE…
丢掉的 61 列是像 PAYEE_LAST_NAME、CRT_USER、BARCODE 这种和人名/操作日志/条形码相关的，跟欺诈预测无关。

3. 数据清洗
金额列：去掉 RMB 前缀、千分位逗号 → 转数值。数据里 APP_AMT、BEN_SPEND 这些列存的是字符串格式。

日期列：Excel 序列号 → datetime，然后提取时间差特征（后面说）。

类别列：统一大写，NaN 标准化。特别注意 KIND_CODE 这个字段——它混了数字代码（7100014）和中文标签（员工、退休），所以拆成了 KIND_CODE_NUM（数值）+ KIND_CODE_IS_NUMERIC（标记）。

PROV_LEVEL：医院等级做了有序编码（三级=3 > 二级=2 > 一级=1），医保/非医保单独编码。

4. 缺失值处理
删了 3 个缺失太高的：

PROV_DEPT（科室）83.8% 缺失
FILE_CLOSE_DATE（结案日期）63.5%
DAYS_RCV_TO_CLOSE（收件→结案天数，父列缺失导致）
其余数值用中位数填充，类别用众数填充。

5. 特征工程（重点）
这是比原版 v2 增强最多的部分：

BEN_HEAD 拆解（福利项目里有隐含的社保信息）：

S-YPF  → 前缀=S（社保内） + 类别=YPF（药品费）
F-GHF  → 前缀=F（非社保） + 类别=GHF（挂号费）
100PF-YPF → 前缀=100P（100%赔付）
拆出 3 个新特征：BH_PREFIX、BH_CATEGORY、BH_COMBO

ICD-10 疾病编码分组（不是用原始 J06.900，太细了）：

J06.900 → ICD10_CHAPTER=J_RESPIRATORY（呼吸系统）
K30.x00 → ICD10_CHAPTER=K_DIGESTIVE（消化系统）
20 个粗粒度类别，比 1661 个原始疾病编码好建模得多。

时间差特征：

DAYS_INCUR_TO_PAY：出险到划账多少天（拖越久越可疑？）
DAYS_HOSPITALIZATION：住院天数
IS_INPATIENT：是否住院（>0天=住院）
6. 标签构造——这是核心修正
FRAUD = (有拒赔码) AND (实际支付 == 0)
关键区别：RJ_CODE_LIST 里混了三类代码——

🔴 CL_REJ_CODE（系统拒赔，如 R530=疑似欺诈）
🔴 MAN_REJ_CODE（人工拒赔，如 T180=人工审核拒赔）
🟡 CL_WARN_CODE（警告而已，如 W055=还没发缴费通知）
原版错误：把所有有 WARN_CODE 且零支付的都标成欺诈 → 70% 的"欺诈率"（明显荒谬）

修正后：只看真正的拒赔码（REJ_CODE + MAN_REJ_CODE）∩ 零支付 → 13.09%，合理多了。

然后删掉 RJ_CODE_LIST 和 CODES 原始列（防止标签泄漏），但保留了统计特征：

WARN_CODE_COUNT、REJ_CODE_COUNT、MAN_REJ_COUNT
HAS_WARN_CODE、HAS_REJ_CODE
7. 标准化 + 编码
数值 → StandardScaler（均值0方差1）
类别 → LabelEncoder
SUB_AMT、PAY_AMT_USD → 5分箱（减少极端值影响）
高偏度特征 → log1p 变换
8. 三阶段特征选择
过滤法(Variance + KBest) → 嵌入法(RandomForest) → 包装法(RFE)
       48个                     25→13个               13→12个
最终保留的 12 个特征及重要性：

特征	重要性	解读
BEN_SPEND	34.1%	福利扣减金额——最大单一预测因子
APP_AMT	22.5%	申请赔付金额
PAY_AMT_USD_BIN	16.5%	实际支付分箱（零支付直接触发FRAUD）
CL_LINE_STATUS	8.4%	理赔条状态（AC/RJ）
MAN_REJ_COUNT	6.3%	人工拒赔码数量
DAYS_INCUR_TO_PAY	2.1%	出险到划账天数
其余6个	<2%	日期、金额、保单等
反思
有一点可以看看：MAN_REJ_COUNT 排第5，说明人工拒赔码数量本身就是一个强信号——但这东西跟标签有相关性是正常的（因为 FRAUD 就是基于拒赔码构造的）。不过我们只用了计数，没直接用 _HAS_R530 这种具体码，所以不算完全的数据泄漏。

另外 Date 类特征（INCUR_DATE_FROM、PAY_DATE、RCV_DATE）都进了 Top 12，说明时间维度确实对欺诈检测有意义——可能某些时段集中爆发。