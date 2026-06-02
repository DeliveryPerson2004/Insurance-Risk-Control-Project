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

  // DualAxes expects two separate data arrays for left/right Y axes
  const columnData = data.map((d) => ({ date: d.date, total: d.total }));
  const lineData = data.map((d) => ({ date: d.date, fraud_rate: d.fraud_rate }));

  const config = {
    data: [columnData, lineData],
    // @ant-design/plots v2 不支持 geometryOptions；
    // xField / yField 放顶层会被 transformOptions 合并进 children 时覆盖 child 自己的 encode；
    // 因此直接在 children 中声明各 view 的 encode + axis + style，顶层不放 xField/yField。
    children: [
      {
        type: 'interval',
        encode: { x: 'date', y: 'total' },
        axis: { y: { title: '检测量' } },
        style: { fill: '#1677ff', maxWidth: 20 },
      },
      {
        type: 'line',
        encode: { x: 'date', y: 'fraud_rate' },
        axis: {
          y: {
            title: '欺诈率',
            labelFormatter: (v: number) => `${(v * 100).toFixed(0)}%`,
          },
        },
        style: { stroke: '#ff4d4f', lineWidth: 2 },
        point: { size: 3 },
        smooth: true,
      },
    ],
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
      {loading ? <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} /> : (
        <div style={{ height: 220 }}>
          <DualAxes {...config} autoFit />
        </div>
      )}
    </div>
  );
}
