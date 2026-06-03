import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Input,
  Row,
  Col,
  Typography,
  Space,
  message,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import CaseTable from '../components/cases/CaseTable';
import { fetchCases } from '../api/cases';
import type { CaseListItem } from '../types';
import { TableSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';

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

  const loadData = useCallback(async (
    p?: number,
    s?: number,
    rl?: string,
    mr?: string,
    dr?: [string, string] | undefined,
    kw?: string,
  ) => {
    const pageNum = p ?? 1;
    const sizeNum = s ?? 20;
    setPage(pageNum);
    setPageSize(sizeNum);
    setLoading(true);
    try {
      const res = await fetchCases({
        page: pageNum,
        size: sizeNum,
        risk_level: rl !== undefined ? rl : riskLevel,
        manual_result: mr !== undefined ? mr : manualResult,
        date_from: dr !== undefined ? dr?.[0] : dateRange?.[0],
        date_to: dr !== undefined ? dr?.[1] : dateRange?.[1],
        keyword: kw !== undefined ? kw || undefined : keyword || undefined,
      });
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载案件列表失败');
    } finally {
      setLoading(false);
    }
  }, [riskLevel, manualResult, dateRange, keyword]);

  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true;
      loadData();
    }
  }, [loadData]);

  const handlePageChange = (p: number, ps: number) => {
    loadData(p, ps);
  };

  const handleSearch = () => {
    loadData(1, pageSize, undefined, undefined, undefined, keyword);
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
              onChange={(v) => { setRiskLevel(v); loadData(1, pageSize, v, undefined, undefined, undefined); }}
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
              onChange={(v) => { setManualResult(v); loadData(1, pageSize, undefined, v, undefined, undefined); }}
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
                  const dr: [string, string] = [
                    dates[0].format('YYYY-MM-DD'),
                    dates[1].format('YYYY-MM-DD'),
                  ];
                  setDateRange(dr);
                  loadData(1, pageSize, undefined, undefined, dr, undefined);
                } else {
                  setDateRange(null);
                  loadData(1, pageSize, undefined, undefined, undefined, undefined);
                }
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
        {loading ? (
          <TableSkeleton />
        ) : data.length === 0 ? (
          <EmptyState description="暂无案件" />
        ) : (
          <CaseTable
            data={data}
            loading={false}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: total,
            }}
            onPageChange={handlePageChange}
          />
        )}
      </Card>
    </div>
  );
}
