import { useEffect, useRef, useState } from 'react';
import { Button, Space } from 'antd';
import { Chart } from '@antv/g2';
import { fetchTrend } from '../../api/dashboard';
import type { TrendItem } from '../../types';
import { ChartSkeleton } from '../common/Skeleton';

export default function RiskTrendChart() {
  const [data, setData] = useState<TrendItem[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<Chart | null>(null);

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

  // Render chart via @antv/g2 directly, avoiding @ant-design/charts DualAxes issues
  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    // Destroy previous chart
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const chart = new Chart({
      container: containerRef.current,
      autoFit: true,
      height: 220,
    });

    // Shared x-axis
    chart.data(data);

    // Left Y: column for daily total
    chart
      .interval()
      .encode('x', 'date')
      .encode('y', 'total')
      .axis('y', { title: '检测量' })
      .style('fill', '#4A5630');

    // Right Y: line for fraud rate
    chart
      .line()
      .encode('x', 'date')
      .encode('y', 'fraud_rate')
      .scale('y', { independent: true })
      .axis('y', {
        position: 'right',
        title: '欺诈率',
        labelFormatter: (v: number) => `${(v * 100).toFixed(0)}%`,
      })
      .style('stroke', '#DC2626')
      .style('lineWidth', 2);

    chart.render();
    chartRef.current = chart;

    return () => {
      chart.destroy();
      chartRef.current = null;
    };
  }, [data]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: '#292524' }}>检测量 & 欺诈率趋势</span>
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
      {loading ? (
        <ChartSkeleton height={220} />
      ) : (
        <div ref={containerRef} style={{ height: 220 }} />
      )}
    </div>
  );
}
