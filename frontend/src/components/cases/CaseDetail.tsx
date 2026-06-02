import { Descriptions, Tag, Timeline } from 'antd';
import type { CaseDetailResponse } from '../../types';

const riskColorMap: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

// ---- 被保险人信息 ----
export function InsureeCard({ insuree }: { insuree: CaseDetailResponse['insuree'] }) {
  if (!insuree) return null;
  return (
    <Descriptions title="被保险人信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="被保险人ID">{insuree.insuree_id}</Descriptions.Item>
      <Descriptions.Item label="年龄">{insuree.age ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="性别">{insuree.gender ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="职业">{insuree.occupation ?? '-'}</Descriptions.Item>
    </Descriptions>
  );
}

// ---- 保单信息 ----
export function PolicyCard({ policy }: { policy: CaseDetailResponse['policy'] }) {
  if (!policy) return null;
  return (
    <Descriptions title="保单信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="保单号">{policy.policy_id}</Descriptions.Item>
      <Descriptions.Item label="保险类型">{policy.insurance_type ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="保额">
        {policy.insurance_amount != null ? `¥${policy.insurance_amount.toLocaleString()}` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="保费">
        {policy.premium != null ? `¥${policy.premium.toLocaleString()}` : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}

// ---- 理赔信息 ----
export function ClaimCard({ claim }: { claim: CaseDetailResponse['accident_claim'] }) {
  if (!claim) return null;
  return (
    <Descriptions title="理赔信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="事故日期">{claim.accident_date ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="事故类型">{claim.accident_type ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="理赔金额">
        {claim.claim_amount != null ? `¥${claim.claim_amount.toLocaleString()}` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="理赔日期">{claim.claim_date ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="是否欺诈">
        {claim.is_fraud != null ? (claim.is_fraud === true ? '欺诈' : '正常') : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="是否赔付">
        {claim.is_paid != null ? (claim.is_paid === true ? '已赔付' : '未赔付') : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}

// ---- 预测信息 ----
export function PredictionCard({ detail }: { detail: CaseDetailResponse }) {
  return (
    <Descriptions title="预测信息" column={2} bordered size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="欺诈概率">
        {`${(detail.fraud_prob * 100).toFixed(1)}%`}
      </Descriptions.Item>
      <Descriptions.Item label="原始概率">
        {detail.raw_prob != null ? `${(detail.raw_prob * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="风险等级">
        <Tag color={riskColorMap[detail.risk_level] || 'default'}>{detail.risk_level}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="阈值">
        {detail.threshold_used != null ? `${(detail.threshold_used * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="人工判定">
        {detail.manual_result ? (
          <Tag
            color={
              { pass: 'green', reject: 'red', investigate: 'blue' }[detail.manual_result] ||
              'default'
            }
          >
            {{ pass: '通过', reject: '拒绝', investigate: '调查中' }[detail.manual_result] ||
              detail.manual_result}
          </Tag>
        ) : (
          <Tag>待处理</Tag>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="检测时间">
        {detail.detect_time?.slice(0, 19) || '-'}
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
    <div style={{ marginBottom: 16 }}>
      <h4>特征贡献排名 (Top 10 SHAP)</h4>
      <Timeline
        items={sorted.map((item) => ({
          color: item.value >= 0 ? 'red' : 'green',
          children: (
            <span>
              <strong>{item.feature}</strong>: {item.value >= 0 ? '+' : ''}
              {item.value.toFixed(4)} {item.value >= 0 ? '(推高欺诈概率)' : '(降低欺诈概率)'}
            </span>
          ),
        }))}
      />
    </div>
  );
}

// ---- 审核历史 ----
export function HistoryTimeline({
  history,
}: {
  history: CaseDetailResponse['case_history'];
}) {
  if (!history || history.length === 0) {
    return (
      <div style={{ marginBottom: 16 }}>
        <h4>审核历史</h4>
        <p style={{ color: '#999' }}>暂无审核记录</p>
      </div>
    );
  }

  const resultColorMap: Record<string, string> = {
    pass: 'green',
    reject: 'red',
    investigate: 'blue',
  };
  const resultLabelMap: Record<string, string> = {
    pass: '通过',
    reject: '拒绝',
    investigate: '调查中',
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <h4>审核历史</h4>
      <Timeline
        items={history.map((item) => ({
          color: resultColorMap[item.manual_result ?? ''] || 'gray',
          children: (
            <div>
              <div>
                <strong>{item.reviewer_name ?? '系统'}</strong>
                {item.manual_result && (
                  <Tag
                    color={resultColorMap[item.manual_result] || 'default'}
                    style={{ marginLeft: 8 }}
                  >
                    {resultLabelMap[item.manual_result] || item.manual_result}
                  </Tag>
                )}
                <span style={{ marginLeft: 8, color: '#999', fontSize: 12 }}>
                  {item.operate_time?.slice(0, 19) || '-'}
                </span>
              </div>
              {item.remark && (
                <div style={{ marginTop: 4, color: '#666' }}>{item.remark}</div>
              )}
            </div>
          ),
        }))}
      />
    </div>
  );
}
