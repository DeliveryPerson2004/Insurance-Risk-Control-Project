import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Typography,
  Spin,
  message,
} from 'antd';
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

const { Title, Paragraph } = Typography;

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CaseDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [adjudicating, setAdjudicating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [agentReport, setAgentReport] = useState<{
    report_text: string;
    model_used: string;
    generated_at: string;
  } | null>(detail?.agent_report || null);
  const [modalOpen, setModalOpen] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await fetchCaseDetail(Number(id));
      setDetail(data);
    } catch {
      message.error('加载案件详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (detail?.agent_report) {
      setAgentReport(detail.agent_report);
    }
  }, [detail]);

  const handleAnalyze = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const res = await analyzeCase(Number(id));
      if (res.fallback) {
        message.warning('AI 分析暂时不可用，请稍后重试');
      } else if (res.report) {
        setAgentReport({
          report_text: res.report,
          model_used: res.model_used || 'unknown',
          generated_at: new Date().toISOString(),
        });
        message.success(res.cached ? '命中缓存' : '分析报告已生成');
      }
    } catch {
      message.error('AI 分析请求失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAdjudicate = useCallback(
    async (values: { manual_result: 'pass' | 'reject' | 'investigate'; remark?: string }) => {
      if (!id) return;
      setAdjudicating(true);
      try {
        await adjudicateCase(Number(id), {
          manual_result: values.manual_result,
          remark: values.remark,
        });
        message.success('人工判定成功');
        setModalOpen(false);
        loadDetail();
      } catch {
        message.error('人工判定失败');
      } finally {
        setAdjudicating(false);
      }
    },
    [id, loadDetail],
  );

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!detail) {
    return <div>案件不存在</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/cases')}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <Title level={4} style={{ margin: 0 }}>
          案件详情 - {detail.policy_id}
        </Title>
        <Space style={{ marginLeft: 'auto' }}>
          <Button
            icon={<RobotOutlined />}
            onClick={handleAnalyze}
            loading={analyzing}
          >
            {agentReport ? '刷新 AI 分析' : 'AI 分析'}
          </Button>
          <Button
            type="primary"
            icon={<AuditOutlined />}
            onClick={() => setModalOpen(true)}
          >
            人工判定
          </Button>
        </Space>
      </div>

      {/* AI 分析报告 */}
      {agentReport && (
        <Card title="AI 分析报告" size="small" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap' }}>{agentReport.report_text}</div>
          <Paragraph type="secondary" style={{ marginTop: 8 }}>
            模型: {agentReport.model_used} | 生成时间: {agentReport.generated_at?.slice(0, 19)}
          </Paragraph>
        </Card>
      )}

      <Card style={{ marginBottom: 16 }}>
        <PredictionCard detail={detail} />
      </Card>

      <InsureeCard insuree={detail.insuree} />
      <PolicyCard policy={detail.policy} />
      <ClaimCard claim={detail.accident_claim} />

      <Card style={{ marginBottom: 16 }}>
        <ShapCard shapValues={detail.shap_values} />
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <HistoryTimeline history={detail.case_history} />
      </Card>

      <AdjudicateModal
        open={modalOpen}
        onOk={handleAdjudicate}
        onCancel={() => setModalOpen(false)}
        loading={adjudicating}
      />
    </div>
  );
}
