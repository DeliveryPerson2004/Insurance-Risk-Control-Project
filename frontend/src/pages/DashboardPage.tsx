import { useEffect, useState } from 'react';
import StatsCards from '../components/dashboard/StatsCards';
import RiskTrendChart from '../components/dashboard/RiskTrendChart';
import HighRiskTable from '../components/dashboard/HighRiskTable';

function DateHeader() {
  const [dateStr, setDateStr] = useState('');
  useEffect(() => {
    const today = new Date();
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    setDateStr(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')} · ${weekdays[today.getDay()]}`);
  }, []);
  return <span style={{ color: '#A8A29E' }}>{dateStr}</span>;
}

export default function DashboardPage() {
  return (
    <div>
      <h2>Dashboard</h2>
      <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 24 }}>
        欺诈检测概览 · <DateHeader />
      </p>

      {/* 核心区: 趋势图 60% + 右侧 4 卡片 40% */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <div style={{
          flex: '60%',
          background: '#FFFFFF',
          border: '1px solid #E7E5E2',
          borderRadius: 6,
          padding: '20px 24px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }}>
          <RiskTrendChart />
        </div>
        <div style={{ flex: '40%' }}>
          <StatsCards />
        </div>
      </div>

      {/* 高风险表格 — 全宽 */}
      <div>
        <HighRiskTable />
      </div>
    </div>
  );
}
