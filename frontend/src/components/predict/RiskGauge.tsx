import { Typography } from 'antd';

const { Text, Title } = Typography;

interface Props {
  fraudProb: number;
  riskLevel: 'high' | 'medium' | 'low';
  threshold: number;
}

const LEVEL_CONFIG = {
  high: { color: '#ff4d4f', label: '高风险' },
  medium: { color: '#faad14', label: '中等风险' },
  low: { color: '#52c41a', label: '低风险' },
};

export default function RiskGauge({ fraudProb, riskLevel, threshold }: Props) {
  const pct = fraudProb; // 0-1
  const angle = -180 + pct * 180; // SVG 半圆：-180° → 0°
  const cfg = LEVEL_CONFIG[riskLevel];

  // 指针端点坐标
  const cx = 100, cy = 100, r = 80;
  const rad = (angle * Math.PI) / 180;
  const nx = cx + r * Math.cos(rad);
  const ny = cy + r * Math.sin(rad);

  // Helper to map probability → x position on the arc
  const probToX = (prob: number) => 10 + prob * 180;

  return (
    <div style={{ textAlign: 'center', padding: '16px 0' }}>
      <svg width="220" height="120" viewBox="0 0 200 110">
        {/* 半圆背景色段 */}
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#52c41a" />
            <stop offset="36%" stopColor="#52c41a" />
            <stop offset="36%" stopColor="#faad14" />
            <stop offset="70%" stopColor="#faad14" />
            <stop offset="70%" stopColor="#ff4d4f" />
            <stop offset="100%" stopColor="#ff4d4f" />
          </linearGradient>
        </defs>
        <path
          d="M 10 100 A 90 90 0 0 1 190 100"
          fill="none"
          stroke="url(#gaugeGrad)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        {/* 指针 */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke="#333"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r="4" fill="#333" />
        {/* 刻度标签 */}
        <text x={probToX(0)} y="112" fontSize="9" fill="#999" textAnchor="middle">0</text>
        <text x={probToX(threshold)} y="112" fontSize="9" fill="#999" textAnchor="middle">{threshold.toFixed(2)}</text>
        <text x={probToX(0.5)} y="112" fontSize="9" fill="#999" textAnchor="middle">0.5</text>
        <text x={probToX(0.7)} y="112" fontSize="9" fill="#999" textAnchor="middle">0.7</text>
        <text x={probToX(1.0)} y="112" fontSize="9" fill="#999" textAnchor="middle">1.0</text>
      </svg>
      <div style={{ marginTop: -8 }}>
        <Title level={3} style={{ color: cfg.color, marginBottom: 0 }}>
          {cfg.label}
        </Title>
        <Text strong style={{ fontSize: 20, color: cfg.color }}>
          {(fraudProb * 100).toFixed(1)}%
        </Text>
        <br />
        <Text type="secondary" style={{ fontSize: 11 }}>
          阈值 {threshold} | 校准后概率
        </Text>
      </div>
    </div>
  );
}
