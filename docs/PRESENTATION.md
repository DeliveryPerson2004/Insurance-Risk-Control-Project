# 医保理赔欺诈检测系统 — 技术讲解脚本

> 面向老师的深度技术介绍，涵盖模型原理、推理机制、特征工程、架构设计。不涉及页面和功能展示。

---

## 一、为什么要做概率校准：原始概率 vs 欺诈概率

XGBoost 输出的 `predict_proba` 是一个"原始概率"（raw probability），但**树模型的原始概率并不可靠**。原因：

- 决策树天然倾向于输出极端值（接近 0 或接近 1），即"过度自信"
- 不同决策路径上的样本量不同，叶子节点的概率估计方差很大
- 评估指标 AUC 只关心排序能力（"这个案子比那个案子更像欺诈吗？"），不关心概率值本身是否准确

**解决方案**：在 XGBoost 之后串联一个 **IsotonicRegression（保序回归）** 校准器。

```
推理流程（3 步）:

  输入 35 特征
      │
      ▼
  ┌─────────────────────┐
  │ Step 1: XGBoost     │  输出: raw_prob (原始概率)
  │ predict_proba(X)    │  问题: 未校准，偏极端
  └─────────┬───────────┘
            │ raw_prob
            ▼
  ┌─────────────────────┐
  │ Step 2: Isotonic     │  输入: raw_prob (单个数)
  │ Regression 校准       │  输出: fraud_prob (校准后)
  │ calibrator(raw_prob) │  效果: 更接近真实概率
  └─────────┬───────────┘
            │ fraud_prob
            ▼
  ┌─────────────────────┐
  │ Step 3: 阈值判定     │  fraud_prob ≥ 0.7 → high
  │                     │  fraud_prob ≥ 0.36 → medium
  │                     │  fraud_prob < 0.36 → low
  └─────────────────────┘
```

**为什么 IsotonicRegression 而非 Platt Scaling？** Platt 假设数据服从 sigmoid 分布，对树模型并不适用。Isotonic 不需要分布假设，仅仅保证"预测值更高的样本，真实标签为正的概率也更高"（单调性约束）。

**校验效果**：校准前 F1=0.83，校准后 F1=0.85，阈值从 0.42 优化至 0.36。

---

## 二、双阈值风险等级的设计逻辑

风险等级使用**两个不同的阈值**，这不是简单的"三等分"：

| 等级 | 阈值条件 | 含义 |
|------|---------|------|
| **高风险** | fraud_prob ≥ **0.7** | 业务决策阈值：欺诈概率极高，必须人工优先审核 |
| **中风险** | fraud_prob ≥ **0.36** (模型最优阈值) | 模型认为可疑，但置信度不足，建议人工复核 |
| **低风险** | fraud_prob < 0.36 | 模型判断为正常案件，自动放行 |

**为什么 0.7 是业务阈值而 0.36 是模型阈值？**

- **0.36**：在验证集上搜索使 F1 最大的阈值，是模型的最优二分类边界。低于此值的案件模型判断为正常。这个值低于 0.5（直观的"一半一半"）是因为训练数据严重不平衡（欺诈占比仅约 5%），正负样本的 scale_pos_weight 调整后的自然结果。

- **0.7**：是业务规则，而非模型最优。目的是减少误报对正常用户的影响——只有模型几乎确定是欺诈时，才会标为"高风险"触发紧急审核流程。中风险区域（0.36~0.7）的案子人工复查即可。

这是一种保守的审慎风控策略：宁可漏掉一些边缘欺诈（中风险不自动拦截），也不能把正常用户的理赔标为高风险导致信任危机。

---

## 三、108 列 → 35 特征的完整转换链路

### 3.1 训练阶段 vs 推理阶段

特征工程分为两段，分别在不同阶段执行：

**离线训练段**（`data/preprocessing.py`，只跑一次）：
```
原始 108 列 Excel → 清洗 + 特征衍生 → 35 特征 CSV → 训练模型
```

**在线推理段**（两个 Service 配合，每次调用）：

```
用户输入 27 字段 / 原始 108 列 Excel
    │
    ▼
┌──────────────────────────────────────┐
│ preprocess_service.py (108 → 30)     │  ← 新模块，从离线脚本提取
│  金额清洗: "RMB 144.2" → 144.2       │
│  ICD-10 编码映射: S62.601 → INJURY  │
│    含 D 系编码修正 (D00-D48=肿瘤)     │
│  BEN_HEAD 拆分: S-JCF → SOCIAL + JCF │
│  PROV_LEVEL 序数化: 三级→3, 医保→10  │
│  被保人聚合: GROUP BY MBR_NO         │
│  日期派生: INCUR_DATE → DAYS_* 等    │
└──────────────┬───────────────────────┘
               │ 30 特征 (raw 值，未缩放)
               ▼
┌──────────────────────────────────────┐
│ feature_transform.py (30 → 35)       │  ← 7 步管线
│  0. 缺失标记: BASE_MISSING 自动生成   │
│  1. category dtype 转换              │
│  2. 连续值中位数填充                  │
│  3. Winsorize (1%-99% 截尾)          │
│  4. log1p 偏态校正                   │
│  5. StandardScaler 标准化            │
│  6. 按 FEATURE_COLS 排序列            │
└──────────────┬───────────────────────┘
               │ 35 特征 (scaled 值，可推理)
               ▼
          model_service.predict()
```

### 3.2 特征工程的版本演化：数据泄漏修复

欺诈检测的特征工程有一个致命陷阱—— **数据泄漏**：

| 版本 | 特征数 | 问题 |
|------|--------|------|
| v1 | 12 | 含 4 个泄漏特征 |
| v2 | 29 | 移除了 `MAN_REJ_COUNT`（人工拒赔次数——理赔后才产生），扩充特征 |
| v3 | 27 | 进一步移除 10 个金额泄漏特征（如 `PAY_AMT_USD_BIN`、`REJECTED_AMT`） |
| v4 | **35** | 修复 ICD-10 D 系编码 Bug（D00-D48 之前被错误分类为血液病→修正为肿瘤），新增 5 个缺失值标记特征 |

**核心原则**：训练时只能使用**赔付决定之前**已知的信息。任何在赔付之后才产生的字段（如拒赔原因、实付金额）如果参与了训练，模型就会学到"因为被拒赔了所以是欺诈"这种因果倒置的错误。这叫做**目标泄漏**，会导致训练 AUC 虚高但在真实环境中毫无预测能力。

---

## 四、35 个特征详解

### 4.1 7 个类别特征

| 特征 | 来源 | 举例 |
|------|------|------|
| `ICD10_CHAPTER` | DIAG_CODE → ICD-10 大类映射 | INJURY（损伤）、NEOPLASM（肿瘤）、RESPIRATORY（呼吸系统）等 22 类 |
| `BH_PREFIX` | BEN_HEAD 前缀 | SOCIAL（社保）、NON_SOCIAL（非社保）、100PCT（全额）等 6 类 |
| `BH_CATEGORY` | BEN_HEAD 后缀 | JCF、YPF、GHF（不同医保目录分类）等 10 类 |
| `MBR_TYPE` | 被保人类型 | Applicant、Employee、Dependent 等 |
| `BEN_TYPE` | 给付类型 | BENEFIT_TYPE_OP（门诊）、BENEFIT_TYPE_IP（住院） |
| `KIND_CODE` | 险种代码 | 70P、HSP 等 |
| `POCY_PLAN_DESC` | 保单计划描述 | 标准化后取 uppercase，UNKNOWN 填充缺失 |

### 4.2 23 个连续特征

| 类别 | 特征 | 说明 |
|------|------|------|
| 金额类 (4) | SUB_AMT, TOTAL_RECEIPT_AMT, ORG_PRES_AMT_VALUE, COPAY_PCT | 发票金额、处方金额、共付比例 |
| 保单类 (3) | NO_OF_YR, POLICY_CNT, INVOICE_CNT | 投保年限、保单数、发票数 |
| 日期派生 (8) | DAYS_INCUR_TO_PAY, DAYS_RCV_TO_CLOSE, DAYS_HOSPITALIZATION, DAYS_RCV_TO_PAY, IS_INPATIENT, INCUR_MONTH, INCUR_DAYOFWEEK, INCUR_QUARTER, INCUR_IS_WEEKEND | 就诊距赔付天数、住院天数、是否住院、就诊月份/星期/季度/周末 |
| 机构类 (1) | PROV_LEVEL_ORDINAL | 医院等级（一级→1，三级→3，医保定点→10） |
| 比率类 (1) | RECEIPT_TO_SUB_RATIO | 发票金额/处方金额，异常比例暗示虚开发票 |
| 客户画像 (2) | IS_NEW_INSURED, IS_LONGTERM_INSURED | 是否新投保（≤1年）、是否长期投保（≥5年） |
| 被保人聚合 (3) | MBR_CLAIM_COUNT, MBR_AVG_SUB_AMT, MBR_UNIQUE_HOSPITALS | 同一被保人的历史理赔次数、均次金额、就诊医院数 |
| 缺失标记 (5) | TOTAL_RECEIPT_AMT_MISSING 等 | 关键字段是否存在缺失——缺失本身就是信号 |

### 4.3 为什么被保人聚合特征是关键

同一被保人的历史理赔行为模式是欺诈检测的最强信号之一：

- 单一被保人在短时间内多次理赔（`MBR_CLAIM_COUNT` 高）→ 可疑
- 同一被保人频繁在不同医院就诊（`MBR_UNIQUE_HOSPITALS` 高）→ 需关注
- 同一被保人每次理赔金额异常接近（`MBR_AVG_SUB_AMT` 特殊模式）→ 可能是套保

这是从"单次理赔"上升到"行为模式"的关键跨越——是 v4 版本相比 v1-v3 最大的特征工程提升。

---

## 五、XGBoost 模型的技术细节

### 5.1 为什么选 XGBoost

| 对比维度 | XGBoost | 逻辑回归 | 随机森林 |
|---------|---------|---------|---------|
| 非线性关系捕捉 | 强（树模型天然） | 弱（线性边界） | 强 |
| 类别特征处理 | 原生支持 `enable_categorical` | 需要 OneHot | 需要 TargetEncoder |
| 正则化 | L1 + L2 双重 | 仅 L2 | 无内置 |
| 不平衡数据 | scale_pos_weight 配置 | class_weight | class_weight |
| 训练速度 | GPU 加速、直方图算法 | 快 | n_jobs 并行 |
| SHAP 可解释性 | TreeExplainer 精确，速度快 | KernelExplainer 近似，极慢 | TreeExplainer |

**选择 XGBoost 的核心原因**：在表格数据上表现最优 + **Tree SHAP 的可解释性最高效且精确**——这对风控系统的合规性至关重要。

### 5.2 超参数搜索

使用 **Optuna + 5 折分层交叉验证**（`StratifiedKFold`），以 F1 为目标函数搜索：

- `max_depth`: 3-8（控制树深度，防过拟合）
- `n_estimators`: 200-800（树的数量）
- `scale_pos_weight`: 根据训练集正负样本比自动计算（值≈20）
- 正则化参数: `reg_alpha` (L1), `reg_lambda` (L2), `gamma`（分裂最小损失）

Early Stopping: 验证集上连续 50 轮不提升则停止。

### 5.3 模型性能

| 指标 | 值 | 含义 |
|------|-----|------|
| ROC-AUC | 0.9934 | 排序能力极强，模型几乎不会把欺诈排在正常案件后面 |
| 5-fold CV F1 | 交叉验证均值 ± 标准差 | 模型在不同数据划分上表现稳定 |
| 最优阈值 | 0.36 | 验证集 F1 最大的分类边界 |

**AUC 0.9934 是否过拟合？** 5 折 CV 回答了这个问题——如果 CV 标准差很小且与测试集 F1 差距 <0.03，说明泛化能力良好。训练中明确检查了 CV vs Test 的 F1 差距。

---

## 六、SHAP 可解释性：模型为什么说这个案子是欺诈

### 6.1 为什么需要可解释性

理赔风控场景下，"概率高所以拒赔"是不可接受的。审核员、被保人、监管部门都有权知道**哪个特征起了决定性作用**。SHAP（SHapley Additive exPlanations）基于博弈论中的 Shapley 值，公平分配每个特征对预测结果的贡献。

### 6.2 TreeExplainer 的技术优势

XGBoost 使用 `TreeExplainer` 而非通用的 `KernelExplainer`：

- **速度**：TreeExplainer 遍历树结构 O(TLD²)（T=树数, L=叶子数, D=深度），比 KernelExplainer 快 1000+ 倍
- **精确性**：对树模型有解析解，不需要采样近似
- **输出**：每个特征一个 SHAP 值（正→推高欺诈概率，负→降低欺诈概率），取绝对值 Top 10 展示

### 6.3 SHAP 失效的容错处理

在推理代码中 SHAP 是 try-catch 包裹的：计算失败时不阻塞主流程，回退为空列表。同时模块级缓存了 `_explainer` 单例，首次推理时才惰性构建。

---

## 七、为什么用异步架构

### 7.1 同步 vs 异步的选择

```
同步模式:
  POST /api/predict/batch (大文件)
    → 上传文件 [2s]
    → 逐行推理 1000 条 [60s]
    → 返回结果 [2s]
  HTTP 连接保持 64 秒，超时风险极高，前端白屏等待

异步模式:
  POST /api/predict/batch (大文件)
    → 上传文件 + 创建任务 [0.3s]
    → 立即返回 task_id
  Celery Worker 后台处理 [60s]
  前端轮询 GET /status，显示进度条
  HTTP 连接 0.3 秒即释放
```

### 7.2 技术选型

| 组件 | 选择 | 原因 |
|------|------|------|
| 任务队列 | Celery + Redis | Python 生态最成熟，文档丰富 |
| 后端框架 | FastAPI | 原生异步（async/await），性能接近 Node.js |
| ORM | SQLAlchemy 2.0 Async | 异步驱动 asyncpg，连接池复用 |
| 数据库 | PostgreSQL 16 | JSONB 存储特征值/SHAP，无需额外 NoSQL |

### 7.3 Celery 与 SQLAlchemy Async 的坑

Celery Worker 是同步进程，但推理需要异步数据库操作。解决方案：`asyncio.run()` 在 Worker 内部创建临时事件循环执行异步代码。同时 `engine.dispose()` 在每次任务执行前清理上一轮的连接池，避免 asyncpg 的 "another operation is in progress" 错误。Worker 使用 `--pool=solo --without-mingle` 跳过集群同步以减少 Windows 上的启动延迟。

---

## 八、7 张数据表的设计逻辑

```
user_info ──────────────────────────────────────┐
  (用户表: 认证 + RBAC)                          │
                                                 │
insuree_info ────┐                               │
  (被保人)        │ 1:N                           │
                 ▼                               │
policy_info ─────┐                               │
  (保单)          │ 1:N                           │
                 ▼                               │
accident_claim_info ─┐                           │
  (理赔事故)          │ 1:1                       │
                      ▼                          │
fraud_detect_result ──┬── model_info             │
  (检测结果, JSONB)    │    (模型元信息)           │
  feature_values      │                          │
  shap_values         │ 1:N                      │
  agent_report        ▼                          │
                      │                  case_history
                      └──────────────→ (审核记录, FK user_id)
                                          manual_result
                                          remark
```

关键设计：
- `fraud_detect_result` 用 JSONB 原样存储 35 个特征值和 SHAP 值，保证**预测可复现**——无论模型后续如何升级，历史预测结果不变
- `case_history` 独立建表，每次人工判定追加一条记录，完整追溯审核链路
- `accident_claim_info.is_fraud` 仅用于训练数据回填时的真实标签，系统运行中产生的新案件该字段为 NULL——因为真实世界没有即时标签

---

## 九、安全与认证设计

### 9.1 双 Token 无感刷新

```
登录 → access_token (15min) + refresh_token (7天)
         │                      │
         │ 请求时携带             │ access_token 过期时
         │                       │ 自动用 refresh_token 换取新 access_token
         │                       │
         ▼                       ▼
     正常请求              Axios 拦截器自动处理，用户无感知
```

前端 axios 的响应拦截器实现了一个请求队列：当多个请求同时遇到 401 时，只有第一个请求触发 refresh，其余排队等待，refresh 成功后一起重试。

### 9.2 RBAC 角色设计

`UserRole(str, Enum)` 继承自 `str`，直接参与 JWT 序列化，无需 `.value` 转换。双角色体系：

- **admin**：首个注册用户自动获得，可管理用户和上传数据
- **reviewer**：后续注册用户默认获得，仅可使用预测和案件管理

前后端双重验证：后端 `require_admin` 依赖注入 + 前端 `AdminRoute` 路由守卫。

---

## 十、总结：技术亮点

1. **3 步推理链**：原始概率 → IsotonicRegression 校准 → 双阈值判定，解决树模型概率不可靠问题
2. **数据泄漏防护**：4 个版本迭代，从 12 特征演化到 35 特征，严格排除赔付后信息
3. **特征分层处理**：离线预处理（108→35，含 groupby 聚合）和在线变换（7 步管线）解耦
4. **SHAP 可解释性**：基于博弈论的公平归因 + TreeExplainer 精确高效 + 惰性单例 + 故障容错
5. **异步架构**：Celery 处理长任务 + Redis 进度追踪 + 前端轮询，避免 HTTP 超时
6. **JSONB 存储**：特征值和 SHAP 值原样保留，预测结果跨模型版本可复现
7. **双 Token 认证**：15min/7day 两级过期 + 请求队列化自动刷新
8. **WSL2 + Docker**：开发与生产环境统一，一键部署
