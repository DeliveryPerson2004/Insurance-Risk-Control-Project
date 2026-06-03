import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import {
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { fetchStats } from '../../api/dashboard';
import type { DashboardStats } from '../../types';
import { CardSkeleton } from '../common/Skeleton';

const CARD_STYLE: CSSProperties = {
  background: '#FFFFFF',
  border: '1px solid #E7E5E2',
  borderRadius: 6,
  padding: '16px 20px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const titleStyle: CSSProperties = { fontSize: 12, color: '#6B625D', fontWeight: 400 };

export default function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {}).finally(() => setLoading(false));
    const interval = setInterval(() => { fetchStats().then(setStats).catch(() => {}); }, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <CardSkeleton count={4} />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>待审核</div>
        <div style={{ fontSize: 32, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <ClockCircleOutlined style={{ fontSize: 18, color: '#6B625D', marginRight: 8 }} />
          {stats?.today_pending ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE, borderLeft: '3px solid #DC2626' }}>
        <div style={titleStyle}>高风险</div>
        <div style={{ fontSize: 32, fontWeight: 600, color: '#DC2626', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <WarningOutlined style={{ fontSize: 18, color: '#DC2626', marginRight: 8 }} />
          {stats?.today_high_risk ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>已处理</div>
        <div style={{ fontSize: 28, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <CheckCircleOutlined style={{ fontSize: 16, color: '#4A5630', marginRight: 8 }} />
          {stats?.today_processed ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>累计检测量</div>
        <div style={{ fontSize: 28, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <DatabaseOutlined style={{ fontSize: 16, color: '#6B625D', marginRight: 8 }} />
          {stats?.total_detected ?? 0}
        </div>
      </div>
    </div>
  );
}
