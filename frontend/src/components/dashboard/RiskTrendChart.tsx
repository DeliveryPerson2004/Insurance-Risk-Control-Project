import { useEffect, useState } from 'react';
import { Button, Space, Spin } from 'antd';
import { DualAxes } from '@ant-design/charts';
import { fetchTrend } from '../../api/dashboard';
import type { TrendItem } from '../../types';

export default function RiskTrendChart() {
  const [data, setData] = useState<TrendItem[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTrend(days)
      .then(setData)
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchTrend(days).then(setData).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, [days]);

  const config = {
    data: [data, data],
    xField: 'date',
    yField: ['total', 'fraud_rate'],
    geometryOptions: [
      { geometry: 'column', color: '#1677ff' },
      {
        geometry: 'line',
        color: '#ff4d4f',
        lineStyle: { lineWidth: 2 },
        point: { size: 3 },
      },
    ],
    yAxis: {
      total: { title: { text: '检测量' } },
      fraud_rate: {
        title: { text: '欺诈率' },
        label: { formatter: (v: string) => `${(parseFloat(v) * 100).toFixed(0)}%` },
      },
    },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: '#666' }}>检测量 & 欺诈率趋势</span>
        <Space>
          {[7, 30, 90].map((d) => (
            <Button
              key={d}
              size="small"
              type={days === d ? 'primary' : 'default'}
              onClick={() => setDays(d)}
            >
              {d}天
            </Button>
          ))}
        </Space>
      </div>
      {loading ? <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} /> : <DualAxes {...config} height={220} />}
    </div>
  );
}
