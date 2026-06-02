"""DeepSeek Agent prompt 模板."""

SYSTEM_PROMPT = """你是一位资深的医疗保险欺诈调查员，拥有超过20年的行业经验。你的任务是对AI预测的案件进行深度分析，给出专业的风险评估报告。

## 报告格式要求

请使用 Markdown 格式，包含以下四个部分：

### 1. Summary（摘要）
用 2-3 句话概括案件的整体风险状况。

### 2. Risk Factors（风险因素）
列出 3-5 个关键风险因素，每个因素说明其影响方向和程度。

### 3. Recommendation（建议）
给出明确的审核建议：优先调查 / 常规审核 / 快速通过。

### 4. Key Evidence（关键证据）
引用 SHAP 特征分析中最重要的 3 个证据点。

## 注意事项
- 报告长度控制在 300-500 字
- 语言专业但易懂
- 不要给出"无法判断"的模糊结论
- 基于数据说话，不要臆测
"""


def build_user_prompt(case_context) -> str:
    """根据案件上下文构建用户消息."""
    lines = ["## 案件关键信息\n"]

    lines.append(f"- **案件 ID**: {case_context.case_id}")
    lines.append(f"- **欺诈概率**: {case_context.fraud_prob * 100:.1f}%")
    lines.append(f"- **风险等级**: {case_context.risk_level}")
    lines.append(f"- **判定阈值**: {case_context.threshold_used:.2f}")
    if case_context.claim_amount is not None:
        lines.append(f"- **理赔金额**: ¥{case_context.claim_amount:,.2f}")
    if case_context.icd10_chapter:
        lines.append(f"- **诊断大类**: {case_context.icd10_chapter}")

    if case_context.shap_top10:
        lines.append("\n## Top 10 SHAP 特征影响\n")
        for item in case_context.shap_top10[:10]:
            direction = "↑ 提高风险" if item.get("direction") == "+" else "↓ 降低风险"
            lines.append(
                f"- **{item['feature']}**: SHAP={item.get('shap_value', 0):.4f} ({direction}), "
                f"实际值={item.get('value', 'N/A')}"
            )

    lines.append("\n请根据以上信息生成专业的欺诈风险分析报告。")
    return "\n".join(lines)
