import { Descriptions, Timeline } from 'antd';
import type { CaseDetailResponse } from '../../types';

type FV = Record<string, unknown> | null;

function fvStr(fv: FV, key: string): string | null {
  const v = fv?.[key];
  if (v === null || v === undefined) return null;
  return String(v);
}

function fvNum(fv: FV, key: string): number | null {
  const v = fv?.[key];
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

// ---- 被保险人信息 ----
export function InsureeCard({ insuree, featureValues }: {
  insuree: CaseDetailResponse['insuree'];
  featureValues: FV;
}) {
  if (!insuree) return null;
  return (
    <Descriptions title="被保险人信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="被保险人ID">{insuree.insuree_id}</Descriptions.Item>
      <Descriptions.Item label="成员类型">{fvStr(featureValues, 'MBR_TYPE') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="是否新保户">
        {fvNum(featureValues, 'IS_NEW_INSURED') === 1 ? '是' : fvNum(featureValues, 'IS_NEW_INSURED') === 0 ? '否' : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="是否长期保户">
        {fvNum(featureValues, 'IS_LONGTERM_INSURED') === 1 ? '是（≥5年）' : fvNum(featureValues, 'IS_LONGTERM_INSURED') === 0 ? '否' : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="历史理赔次数">{fvNum(featureValues, 'MBR_CLAIM_COUNT') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="历史均赔金额">
        {fvNum(featureValues, 'MBR_AVG_SUB_AMT') != null ? `¥${fvNum(featureValues, 'MBR_AVG_SUB_AMT')!.toFixed(2)}` : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}

// ---- 保单信息 ----
export function PolicyCard({ policy, featureValues }: {
  policy: CaseDetailResponse['policy'];
  featureValues: FV;
}) {
  if (!policy) return null;
  return (
    <Descriptions title="保单信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="保单号">{policy.policy_id}</Descriptions.Item>
      <Descriptions.Item label="险种代码">{fvStr(featureValues, 'KIND_CODE') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="保单计划">{fvStr(featureValues, 'POCY_PLAN_DESC') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="投保年限">{fvNum(featureValues, 'NO_OF_YR') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="保单数">{fvNum(featureValues, 'POLICY_CNT') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="发票数">{fvNum(featureValues, 'INVOICE_CNT') ?? '-'}</Descriptions.Item>
    </Descriptions>
  );
}

// ---- 理赔信息 ----
export function ClaimCard({ claim, featureValues }: {
  claim: CaseDetailResponse['accident_claim'];
  featureValues: FV;
}) {
  if (!claim) return null;
  return (
    <Descriptions title="理赔信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="诊断大类">{fvStr(featureValues, 'ICD10_CHAPTER') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="受益类型">{fvStr(featureValues, 'BEN_TYPE') ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="理赔申请金额">
        {fvNum(featureValues, 'SUB_AMT') != null ? `¥${fvNum(featureValues, 'SUB_AMT')!.toFixed(2)}` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="住院天数">
        {fvNum(featureValues, 'DAYS_HOSPITALIZATION') != null ? `${fvNum(featureValues, 'DAYS_HOSPITALIZATION')} 天` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="是否住院">
        {fvNum(featureValues, 'IS_INPATIENT') === 1 ? '是' : fvNum(featureValues, 'IS_INPATIENT') === 0 ? '否' : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="就诊到赔付天数">
        {fvNum(featureValues, 'DAYS_INCUR_TO_PAY') != null ? `${fvNum(featureValues, 'DAYS_INCUR_TO_PAY')} 天` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="是否赔付">
        {claim.is_paid != null ? (claim.is_paid === true ? '已赔付' : '未赔付') :
          claim.claim_amount != null ? `¥${claim.claim_amount.toLocaleString()}` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="是否欺诈">
        {claim.is_fraud != null ? (
          <span style={{ fontWeight: 500, color: claim.is_fraud ? '#DC2626' : '#4A5630' }}>
            {claim.is_fraud ? '欺诈' : '正常'}
          </span>
        ) : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}

// ---- 预测信息 ----
export function PredictionCard({ detail }: { detail: CaseDetailResponse }) {
  const prob = detail.fraud_prob * 100;
  const pc = prob >= 70 ? '#DC2626' : prob >= 30 ? '#947008' : '#4A5630';
  const rl = detail.risk_level;
  const rc = rl === 'high' ? '#DC2626' : rl === 'medium' ? '#947008' : '#4A5630';
  const rlabel = rl === 'high' ? '高风险' : rl === 'medium' ? '中风险' : '低风险';

  const resultColor: Record<string, string> = { pass: '#4A5630', reject: '#DC2626', investigate: '#947008' };
  const resultLabel: Record<string, string> = { pass: '通过', reject: '拒绝', investigate: '调查中' };

  return (
    <Descriptions column={2} bordered size="small">
      <Descriptions.Item label="欺诈概率">
        <span style={{ fontWeight: 700, fontSize: 24, color: pc, fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
          {prob.toFixed(1)}%
        </span>
      </Descriptions.Item>
      <Descriptions.Item label="风险等级">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: rc, display: 'inline-block' }} />
          <span style={{ fontWeight: 500, color: rc }}>{rlabel}</span>
        </span>
      </Descriptions.Item>
      <Descriptions.Item label="原始概率">
        {detail.raw_prob != null ? `${(detail.raw_prob * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="阈值">
        {detail.threshold_used != null ? `${(detail.threshold_used * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="人工判定">
        {detail.manual_result ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: resultColor[detail.manual_result] || '#A8A29E', display: 'inline-block' }} />
            <span style={{ color: resultColor[detail.manual_result] || '#A8A29E', fontWeight: 500 }}>
              {resultLabel[detail.manual_result] || detail.manual_result}
            </span>
          </span>
        ) : (
          <span style={{ color: '#A8A29E', fontSize: 12 }}>待处理</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="检测时间">
        {detail.detect_time ? new Date(detail.detect_time).toLocaleString() : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}

// ---- SHAP 特征贡献排名 ----
export function ShapCard({ shapValues }: { shapValues: Record<string, number> | null }) {
  if (!shapValues || Object.keys(shapValues).length === 0) return null;

  const sorted = Object.entries(shapValues)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10);

  return (
    <Timeline
      items={sorted.map((item) => ({
        color: item.value >= 0 ? '#DC2626' : '#4A5630',
        children: (
          <span>
            <strong>{item.feature}</strong>: {item.value >= 0 ? '+' : ''}
            {item.value.toFixed(4)} {item.value >= 0 ? '(推高欺诈概率)' : '(降低欺诈概率)'}
          </span>
        ),
      }))}
    />
  );
}

// ---- 审核历史 ----
export function HistoryTimeline({
  history,
}: {
  history: CaseDetailResponse['case_history'];
}) {
  if (!history || history.length === 0) {
    return <p style={{ color: '#A8A29E' }}>暂无审核记录</p>;
  }

  const dotColor: Record<string, string> = {
    pass: '#4A5630',
    reject: '#DC2626',
    investigate: '#947008',
  };
  const resultLabelMap: Record<string, string> = {
    pass: '通过',
    reject: '拒绝',
    investigate: '调查中',
  };

  return (
    <Timeline
      items={history.map((item) => ({
        color: dotColor[item.manual_result ?? ''] || '#A8A29E',
        children: (
          <div>
            <div>
              <strong>{item.reviewer_name ?? '系统'}</strong>
              {item.manual_result && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginLeft: 8 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor[item.manual_result] || '#A8A29E', display: 'inline-block' }} />
                  <span style={{ color: dotColor[item.manual_result] || '#6B625D', fontWeight: 500, fontSize: 12 }}>
                    {resultLabelMap[item.manual_result] || item.manual_result}
                  </span>
                </span>
              )}
              <span style={{ marginLeft: 8, color: '#A8A29E', fontSize: 12 }}>
                {item.operate_time ? new Date(item.operate_time).toLocaleString() : '-'}
              </span>
            </div>
            {item.remark && (
              <div style={{ marginTop: 4, color: '#6B625D' }}>{item.remark}</div>
            )}
          </div>
        ),
      }))}
    />
  );
}
