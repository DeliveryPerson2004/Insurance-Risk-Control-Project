import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, App } from 'antd';
import { DetailSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';
import {
  ArrowLeftOutlined,
  AuditOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import {
  InsureeCard,
  PolicyCard,
  ClaimCard,
  PredictionCard,
  ShapCard,
  HistoryTimeline,
} from '../components/cases/CaseDetail';
import AdjudicateModal from '../components/cases/AdjudicateModal';
import { fetchCaseDetail, adjudicateCase } from '../api/cases';
import { analyzeCase } from '../api/agent';
import type { CaseDetailResponse } from '../types';

export default function CaseDetailPage() {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CaseDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [adjudicating, setAdjudicating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [agentReport, setAgentReport] = useState<{
    report_text: string; model_used: string; generated_at: string;
  } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await fetchCaseDetail(Number(id));
      setDetail(data);
    } catch { message.error('加载案件详情失败'); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  useEffect(() => {
    if (detail?.agent_report) setAgentReport(detail.agent_report);
  }, [detail]);

  const handleAnalyze = useCallback(async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const isRefresh = !!agentReport;
      const res = await analyzeCase(Number(id), isRefresh);
      if (res.fallback) { message.warning('AI 分析暂时不可用，请稍后重试'); }
      else if (res.report) {
        setAgentReport({
          report_text: res.report,
          model_used: res.model_used || 'unknown',
          generated_at: new Date().toISOString(),
        });
        message.success(res.cached ? '命中缓存' : '分析报告已生成');
      }
    } catch { message.error('AI 分析请求失败'); }
    finally { setAnalyzing(false); }
  }, [id, agentReport]);

  const handleAdjudicate = useCallback(async (values: { manual_result: 'pass' | 'reject' | 'investigate'; remark?: string }) => {
    if (!id) return;
    setAdjudicating(true);
    try {
      await adjudicateCase(Number(id), { manual_result: values.manual_result, remark: values.remark });
      message.success('人工判定成功');
      setModalOpen(false);
      loadDetail();
    } catch { message.error('人工判定失败'); }
    finally { setAdjudicating(false); }
  }, [id, loadDetail]);

  if (loading) return <DetailSkeleton cards={4} />;
  if (!detail) return <EmptyState description="案件不存在" />;

  const riskLabel = detail.risk_level === 'high' ? '高风险' : detail.risk_level === 'medium' ? '中风险' : '低风险';
  const riskColor = detail.risk_level === 'high' ? '#DC2626' : detail.risk_level === 'medium' ? '#947008' : '#4A5630';

  return (
    <div>
      {/* 顶部导航 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/cases')}
          type="text"
          style={{ color: '#6B625D', marginRight: 8, marginTop: 2 }}
        />
        <div style={{ flex: 1 }}>
          <h2 style={{ marginBottom: 4 }}>
            案件 {detail.policy_id}
          </h2>
          <p style={{ color: '#6B625D', fontSize: 13, margin: 0 }}>
            创建于 {detail.detect_time ? new Date(detail.detect_time).toLocaleString() : '-'}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginLeft: 12 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: riskColor, display: 'inline-block' }} />
              <span style={{ color: riskColor, fontWeight: 500 }}>{riskLabel}</span>
            </span>
          </p>
        </div>
        <Space>
          <Button icon={<RobotOutlined />} onClick={handleAnalyze} loading={analyzing}>
            {agentReport ? '刷新 AI 分析' : 'AI 分析'}
          </Button>
          <Button type="primary" icon={<AuditOutlined />} onClick={() => setModalOpen(true)}>
            人工判定
          </Button>
        </Space>
      </div>

      {/* AI 分析报告 */}
      {agentReport && (
        <Card title="AI 分析报告" size="small" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', color: '#44403C' }}>{agentReport.report_text}</div>
          <p style={{ color: '#A8A29E', fontSize: 12, marginTop: 8 }}>
            模型: {agentReport.model_used} | 生成时间: {new Date(agentReport.generated_at).toLocaleString()}
          </p>
        </Card>
      )}

      {/* 概览 */}
      <Card style={{ marginBottom: 16 }} title="预测概览">
        <PredictionCard detail={detail} />
      </Card>

      {/* 详细特征 */}
      <InsureeCard insuree={detail.insuree} featureValues={detail.feature_values} />
      <PolicyCard policy={detail.policy} featureValues={detail.feature_values} />
      <ClaimCard claim={detail.accident_claim} featureValues={detail.feature_values} />

      {/* SHAP 解释 */}
      <Card style={{ marginBottom: 16 }} title="SHAP 特征贡献">
        <ShapCard shapValues={detail.shap_values} />
      </Card>

      {/* 审核历史 */}
      <Card style={{ marginBottom: 16 }} title="审核历史">
        <HistoryTimeline history={detail.case_history} />
      </Card>

      {/* 判定弹窗 */}
      <AdjudicateModal
        open={modalOpen}
        onOk={handleAdjudicate}
        onCancel={() => setModalOpen(false)}
        loading={adjudicating}
      />
    </div>
  );
}
