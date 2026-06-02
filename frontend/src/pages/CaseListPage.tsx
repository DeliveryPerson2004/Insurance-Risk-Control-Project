import { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Input,
  Row,
  Col,
  Typography,
  Space,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import CaseTable from '../components/cases/CaseTable';
import { fetchCases } from '../api/cases';
import type { CaseListItem } from '../types';

const { Title } = Typography;
const { RangePicker } = DatePicker;

export default function CaseListPage() {
  const [data, setData] = useState<CaseListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [riskLevel, setRiskLevel] = useState<string | undefined>(undefined);
  const [manualResult, setManualResult] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [keyword, setKeyword] = useState('');

  const loadData = useCallback(
    async (p?: number, ps?: number) => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = {
          page: p ?? page,
          size: ps ?? pageSize,
        };
        if (riskLevel) params.risk_level = riskLevel;
        if (manualResult) params.manual_result = manualResult;
        if (dateRange) {
          params.date_from = dateRange[0];
          params.date_to = dateRange[1];
        }
        if (keyword) params.keyword = keyword;

        const result = await fetchCases(params as Parameters<typeof fetchCases>[0]);
        setData(result.items);
        setTotal(result.total);
      } catch {
        // error handled by interceptor
      } finally {
        setLoading(false);
      }
    },
    [page, pageSize, riskLevel, manualResult, dateRange, keyword],
  );

  useEffect(() => {
    loadData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePageChange = (p: number, ps: number) => {
    setPage(p);
    setPageSize(ps);
    loadData(p, ps);
  };

  const handleSearch = () => {
    setPage(1);
    loadData(1, pageSize);
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>案件管理</Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              placeholder="风险等级"
              allowClear
              style={{ width: 140 }}
              value={riskLevel}
              onChange={(v) => {
                setRiskLevel(v);
                setPage(1);
                loadData(1, pageSize);
              }}
              options={[
                { label: '高风险', value: 'high' },
                { label: '中风险', value: 'medium' },
                { label: '低风险', value: 'low' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="人工判定"
              allowClear
              style={{ width: 140 }}
              value={manualResult}
              onChange={(v) => {
                setManualResult(v);
                setPage(1);
                loadData(1, pageSize);
              }}
              options={[
                { label: '通过', value: 'pass' },
                { label: '拒绝', value: 'reject' },
                { label: '调查中', value: 'investigate' },
              ]}
            />
          </Col>
          <Col>
            <RangePicker
              placeholder={['开始日期', '结束日期']}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setDateRange([
                    dates[0].format('YYYY-MM-DD'),
                    dates[1].format('YYYY-MM-DD'),
                  ]);
                } else {
                  setDateRange(null);
                }
                setPage(1);
                loadData(1, pageSize);
              }}
            />
          </Col>
          <Col flex="auto">
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="搜索保单号..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onPressEnter={handleSearch}
                allowClear
              />
              <SearchOutlined
                onClick={handleSearch}
                style={{
                  padding: '0 12px',
                  fontSize: 16,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  border: '1px solid #d9d9d9',
                  borderRadius: '0 6px 6px 0',
                  background: '#fafafa',
                }}
              />
            </Space.Compact>
          </Col>
        </Row>
      </Card>

      <Card>
        <CaseTable
          data={data}
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
          }}
          onPageChange={handlePageChange}
        />
      </Card>
    </div>
  );
}
