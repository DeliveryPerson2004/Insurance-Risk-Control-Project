import { useState } from 'react';
import { message, Row, Col, Card, Button, Input } from 'antd';
import PredictionForm from '../components/predict/PredictionForm';
import RiskGauge from '../components/predict/RiskGauge';
import ShapExplanation from '../components/predict/ShapExplanation';
import { postSinglePredict } from '../api/predict';
import type { PredictSingleResponse } from '../types';

export default function PredictionPage() {
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
      <PredictionForm onResult={handleSubmit} loading={loading} />

      {result && (
        <Card style={{ marginTop: 24 }}>
          <Row gutter={24} align="top">
            <Col flex="240px">
              <RiskGauge
                fraudProb={result.fraud_prob}
                riskLevel={result.risk_level}
                threshold={result.threshold_used}
              />
            </Col>
            <Col flex="auto">
              <ShapExplanation items={result.shap_top10} />
            </Col>
            <Col flex="160px">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, marginBottom: 16, color: '#666' }}>审核判定</div>
                <Button
                  type="primary"
                  style={{ background: '#52c41a', borderColor: '#52c41a', width: '100%', marginBottom: 8 }}
                >
                  通过
                </Button>
                <Button
                  danger
                  style={{ width: '100%', marginBottom: 8 }}
                >
                  拒绝
                </Button>
                <Button
                  style={{ background: '#faad14', borderColor: '#faad14', color: '#fff', width: '100%', marginBottom: 12 }}
                >
                  待调查
                </Button>
                <Input.TextArea rows={3} placeholder="备注（可选）" />
              </div>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}
