import { Skeleton as AntSkeleton, Card, Row, Col } from 'antd';

/** 模拟表格: 表头 + N 行 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Card>
      <AntSkeleton active title={{ width: '30%' }} paragraph={{ rows: 1 }} />
      {Array.from({ length: rows }, (_, i) => (
        <AntSkeleton
          key={i}
          active
          avatar={{ shape: 'square', size: 'small' }}
          paragraph={{ rows: 1 }}
          title={false}
        />
      ))}
    </Card>
  );
}

/** 模拟统计卡片: 1 行 × N 列 */
export function CardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <Row gutter={16}>
      {Array.from({ length: count }, (_, i) => (
        <Col key={i} span={6}>
          <Card>
            <AntSkeleton active paragraph={{ rows: 2 }} title={{ width: '60%' }} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}

/** 模拟详情页: 标题 + N 个信息卡片 */
export function DetailSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div>
      <AntSkeleton active paragraph={{ rows: 0 }} title={{ width: '40%' }} />
      {Array.from({ length: cards }, (_, i) => (
        <Card key={i} style={{ marginTop: 16 }}>
          <AntSkeleton active paragraph={{ rows: 3 }} title={{ width: '50%' }} />
        </Card>
      ))}
    </div>
  );
}

/** 模拟图表: 标题 + 占位区域 */
export function ChartSkeleton({ height = 220 }: { height?: number }) {
  return (
    <div>
      <AntSkeleton active paragraph={{ rows: 0 }} title={{ width: '40%' }} />
      <div
        style={{
          height,
          background: '#F5F3F0',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#A8A29E',
          marginTop: 8,
        }}
      >
        加载中...
      </div>
    </div>
  );
}
