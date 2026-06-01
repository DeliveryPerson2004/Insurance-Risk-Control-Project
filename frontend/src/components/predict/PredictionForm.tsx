import { useState, useEffect, useCallback } from 'react';
import {
  Form, Select, InputNumber, Input, Button, Collapse, Steps, Space, message, Spin,
} from 'antd';
import type { FieldOption } from '../../types';
import { getFieldOptions } from '../../api/predict';

interface Props {
  onResult: (result: any) => void;
  loading: boolean;
}

type ViewMode = 'collapse' | 'steps';

export default function PredictionForm({ onResult, loading }: Props) {
  const [form] = Form.useForm();
  const [fields, setFields] = useState<FieldOption[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('collapse');
  const [fetching, setFetching] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);

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
    if (field.type === 'select') {
      return (
        <Form.Item
          key={field.name}
          name={field.name}
          label={field.label}
          rules={[{ required: field.required, message: `请选择${field.label}` }]}
        >
          <Select
            showSearch
            placeholder={field.placeholder || `请选择${field.label}`}
            options={(field.options || []).map((o) => ({ value: o, label: o }))}
          />
        </Form.Item>
      );
    }
    return (
      <Form.Item
        key={field.name}
        name={field.name}
        label={field.label}
        rules={[{ required: field.required, message: `请输入${field.label}` }]}
      >
        <InputNumber
          style={{ width: '100%' }}
          min={field.min}
          step={field.step}
          placeholder={field.placeholder}
        />
      </Form.Item>
    );
  };

  if (fetching) {
    return <Spin tip="加载字段配置..." style={{ display: 'block', textAlign: 'center', padding: 48 }} />;
  }

  // 向导步骤
  const stepItems = [
    { title: '诊断+金额', groups: ['诊断信息', '金额信息'] },
    { title: '保单+时间', groups: ['保单信息', '时间特征'] },
    { title: '画像+医院', groups: ['被保险人画像', '医院信息'] },
    { title: '确认提交', groups: [] as string[] },
  ];

  return (
    <div>
      {/* 模式切换 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16, gap: 8 }}>
        <Button
          size="small"
          type={viewMode === 'collapse' ? 'primary' : 'default'}
          onClick={() => setViewMode('collapse')}
        >
          折叠面板
        </Button>
        <Button
          size="small"
          type={viewMode === 'steps' ? 'primary' : 'default'}
          onClick={() => setViewMode('steps')}
        >
          向导
        </Button>
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => onResult(values)}
      >
        {/* insuree_id */}
        <Form.Item
          name="insuree_id"
          label="被保险人 ID"
          rules={[{ required: true, message: '请输入被保险人 ID' }]}
        >
          <Input placeholder="请输入被保险人 ID" />
        </Form.Item>

        {viewMode === 'collapse' ? (
          <Collapse
            defaultActiveKey={[groups[0]]}
            items={groups.map((group) => ({
              key: group,
              label: `${group} (${getFieldsByGroup(group).length} 字段)`,
              children: (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {getFieldsByGroup(group).map(renderField)}
                </div>
              ),
            }))}
          />
        ) : (
          <div>
            <Steps
              current={currentStep}
              size="small"
              style={{ marginBottom: 24 }}
              onChange={setCurrentStep}
              items={stepItems.map((s) => ({ title: s.title }))}
            />
            {currentStep < 3 ? (
              <>
                {stepItems[currentStep].groups.map((group) => (
                  <div key={group} style={{ marginBottom: 16 }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{group}</div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {getFieldsByGroup(group).map(renderField)}
                    </div>
                  </div>
                ))}
                <div style={{ textAlign: 'right', marginTop: 16 }}>
                  <Button type="primary" onClick={async () => {
                    try {
                      const currentFields = stepItems[currentStep].groups
                        .flatMap((g) => getFieldsByGroup(g).map((f) => f.name));
                      await form.validateFields(currentFields);
                      setCurrentStep((s) => Math.min(s + 1, 3));
                    } catch {
                      // validation failed, Ant Design will show field errors
                    }
                  }}>
                    下一步
                  </Button>
                </div>
              </>
            ) : (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>
                  确认提交 — 请检查所有已填写字段
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                  <Button onClick={() => setCurrentStep(2)}>上一步</Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    提交预测
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {viewMode === 'collapse' && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <Button onClick={() => form.resetFields()}>重置</Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              提交预测
            </Button>
          </div>
        )}
      </Form>
    </div>
  );
}
