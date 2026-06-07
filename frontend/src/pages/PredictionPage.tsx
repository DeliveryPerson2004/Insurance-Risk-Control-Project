import { useState } from 'react';
import { App, Card } from 'antd';
import PredictionForm from '../components/predict/PredictionForm';
import RiskGauge from '../components/predict/RiskGauge';
import ShapExplanation from '../components/predict/ShapExplanation';
import { postSinglePredict } from '../api/predict';
import type { PredictSingleResponse } from '../types';

export default function PredictionPage() {
  const { message } = App.useApp();
  const [result, setResult] = useState<PredictSingleResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: Record<string, any>) => {
    setLoading(true);
    try {
      const res = await postSinglePredict(values as any);
      setResult(res);
      message.success('预测完成');
    } catch {
      message.error('预测失败，请检查输入');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>单条预测</h2>
      <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 24 }}>
        理赔风险评估 · 填写以下字段后提交，即刻返回欺诈概率
      </p>

      <PredictionForm onResult={handleSubmit} loading={loading} />

      {result && (
        <Card style={{ marginTop: 24 }} title="预测结果">
          <div style={{
            marginBottom: 16,
            padding: '10px 16px',
            background: '#F5F3F0',
            borderRadius: 6,
            fontSize: 13,
            color: '#44403C',
          }}>
            保单号：<strong style={{ color: '#292524' }}>{result.policy_id}</strong>
          </div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
            <div style={{ flex: '240px 0 0' }}>
              <RiskGauge
                fraudProb={result.fraud_prob}
                riskLevel={result.risk_level}
                threshold={result.threshold_used}
              />
            </div>
            <div style={{ flex: 1 }}>
              <ShapExplanation items={result.shap_top10} />
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
