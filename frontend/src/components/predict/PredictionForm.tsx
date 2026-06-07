import { useState, useEffect, useCallback } from 'react';
import { Form, Select, InputNumber, Input, Button, App, Spin } from 'antd';
import type { FieldOption } from '../../types';
import { getFieldOptions } from '../../api/predict';

interface Props {
  onResult: (result: any) => void;
  loading: boolean;
}

export default function PredictionForm({ onResult, loading }: Props) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [fields, setFields] = useState<FieldOption[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    getFieldOptions()
      .then((data) => {
        setFields(data.fields);
        setGroups(data.groups);
      })
      .catch(() => message.error('获取字段配置失败'))
      .finally(() => setFetching(false));
  }, []);

  const getFieldsByGroup = useCallback(
    (group: string) => fields.filter((f) => f.group === group),
    [fields],
  );

  const renderField = (field: FieldOption) => {
    const normOptions = (field.options || []).map((o) =>
      typeof o === 'string' ? { value: o, label: o } : o,
    );

    if (field.type === 'select') {
      return (
        <Form.Item
          key={field.name}
          name={field.name}
          label={<span style={{ fontSize: 12, color: '#6B625D' }}>{field.label}</span>}
          rules={[{ required: field.required, message: `请选择${field.label}` }]}
        >
          <Select
            showSearch
            placeholder={field.placeholder || `请选择${field.label}`}
            options={normOptions}
          />
        </Form.Item>
      );
    }

    // field.type === 'number' — InputNumber
    return (
      <Form.Item
        key={field.name}
        name={field.name}
        label={<span style={{ fontSize: 12, color: '#6B625D' }}>{field.label}</span>}
        rules={[{ required: field.required, message: `请输入${field.label}` }]}
      >
        <InputNumber
          style={{ width: '100%' }}
          min={field.min}
          max={field.max}
          step={field.step}
          placeholder={field.placeholder}
        />
      </Form.Item>
    );
  };

  if (fetching) {
    return <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} />;
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={(values) => onResult(values)}
    >
      {/* 被保险人 ID — 全宽 */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E7E5E2',
        borderRadius: 6,
        padding: '16px 24px',
        marginBottom: 16,
      }}>
        <Form.Item
          name="insuree_id"
          label={<span style={{ fontSize: 12, color: '#6B625D' }}>被保险人 ID</span>}
          rules={[{ required: true, message: '请输入被保险人 ID' }]}
          style={{ marginBottom: 0 }}
        >
          <Input placeholder="请输入被保险人 ID" />
        </Form.Item>
      </div>

      {/* 字段分组 — 2 列瀑布流，无行边界 */}
      <div style={{
        columnCount: 2,
        columnGap: 16,
      }}>
        {groups.map((group) => (
          <div key={group} style={{
            breakInside: 'avoid',
            background: '#FFFFFF',
            border: '1px solid #E7E5E2',
            borderRadius: 6,
            padding: '16px 24px',
            marginBottom: 16,
          }}>
            <h4 style={{ marginBottom: 12 }}>
              {group}
              <span style={{ fontWeight: 400, fontSize: 11, color: '#A8A29E', marginLeft: 8 }}>
                {getFieldsByGroup(group).length} 字段
              </span>
            </h4>
            {getFieldsByGroup(group).map(renderField)}
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
        <Button onClick={() => form.resetFields()}>重置</Button>
        <Button type="primary" htmlType="submit" loading={loading}>
          提交预测
        </Button>
      </div>
    </Form>
  );
}
