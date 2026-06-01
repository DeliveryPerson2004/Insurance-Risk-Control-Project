import type { ShapItem } from '../../types';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface Props {
  items: ShapItem[];
}

export default function ShapExplanation({ items }: Props) {
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14, color: '#666' }}>
        关键疑点特征（Top 10 SHAP）
      </div>
      {items.map((item, i) => (
        <div
          key={item.feature}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 0',
            borderBottom: i < items.length - 1 ? '1px solid #f0f0f0' : 'none',
            fontSize: 13,
          }}
        >
          <span style={{ flex: 1, fontWeight: 500 }}>{item.feature}</span>
          <span style={{ width: 60, textAlign: 'right', color: '#999' }}>
            {typeof item.value === 'number' ? item.value.toFixed(2) : item.value}
          </span>
          <span
            style={{
              width: 80,
              textAlign: 'right',
              fontWeight: 600,
              color: item.direction === '+' ? '#ff4d4f' : '#52c41a',
            }}
          >
            {item.direction === '+' ? (
              <ArrowUpOutlined style={{ marginRight: 2 }} />
            ) : (
              <ArrowDownOutlined style={{ marginRight: 2 }} />
            )}
            {item.shap_value.toFixed(3)}
          </span>
        </div>
      ))}
      <div style={{ marginTop: 8, fontSize: 11, color: '#999' }}>
        仅展示 Top 10 SHAP 特征，完整 35 特征值已存入数据库
      </div>
    </div>
  );
}
