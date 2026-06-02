import { Modal, Form, Radio, Input } from 'antd';
import { useEffect } from 'react';

interface AdjudicateValues {
  manual_result: 'pass' | 'reject' | 'investigate';
  remark?: string;
}

interface Props {
  open: boolean;
  onOk: (values: AdjudicateValues) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function AdjudicateModal({ open, onOk, onCancel, loading }: Props) {
  const [form] = Form.useForm<AdjudicateValues>();

  useEffect(() => {
    if (open) {
      form.resetFields();
    }
  }, [open, form]);

  return (
    <Modal
      title="人工判定"
      open={open}
      onOk={() => form.submit()}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onOk}
        initialValues={{ manual_result: undefined, remark: '' }}
      >
        <Form.Item
          name="manual_result"
          label="判定结果"
          rules={[{ required: true, message: '请选择判定结果' }]}
        >
          <Radio.Group>
            <Radio value="pass">通过</Radio>
            <Radio value="reject">拒绝</Radio>
            <Radio value="investigate">调查中</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item
          name="remark"
          label="备注"
          rules={[{ max: 512, message: '备注不超过512字' }]}
        >
          <Input.TextArea rows={4} maxLength={512} showCount placeholder="可选备注" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
