import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import {
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { fetchStats } from '../../api/dashboard';
import type { DashboardStats } from '../../types';
import { CardSkeleton } from '../common/Skeleton';

export default function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchStats().then(setStats).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <CardSkeleton count={4} />;
  }

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日待审核"
            value={stats?.today_pending ?? 0}
            prefix={<ClockCircleOutlined />}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日高风险"
            value={stats?.today_high_risk ?? 0}
            prefix={<WarningOutlined />}
            styles={{ content: { color: '#cf1322' } }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日已处理"
            value={stats?.today_processed ?? 0}
            prefix={<CheckCircleOutlined />}
            styles={{ content: { color: '#3f8600' } }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="累计检测量"
            value={stats?.total_detected ?? 0}
            prefix={<DatabaseOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
}
