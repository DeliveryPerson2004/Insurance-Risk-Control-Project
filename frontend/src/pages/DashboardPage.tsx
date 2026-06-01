import { Card, Col, Row } from 'antd';
import StatsCards from '../components/dashboard/StatsCards';
import RiskTrendChart from '../components/dashboard/RiskTrendChart';
import HighRiskTable from '../components/dashboard/HighRiskTable';

export default function DashboardPage() {
  return (
    <div>
      <h2>仪表盘</h2>
      <StatsCards />
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={15}>
          <Card>
            <RiskTrendChart />
          </Card>
        </Col>
        <Col span={9}>
          <Card>
            <HighRiskTable />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
