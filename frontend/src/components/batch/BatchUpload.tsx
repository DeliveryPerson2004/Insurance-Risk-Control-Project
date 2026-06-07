import { Upload, App } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

const { Dragger } = Upload;

interface Props {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

export default function BatchUpload({ onUpload, disabled }: Props) {
  const { message } = App.useApp();
  const props: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv,.xlsx,.xls',
    disabled,
    beforeUpload: (file) => {
      const isAllowed =
        file.name.endsWith('.csv') ||
        file.name.endsWith('.xlsx') ||
        file.name.endsWith('.xls');
      if (!isAllowed) {
        message.error('仅支持 CSV 和 Excel 文件');
        return Upload.LIST_IGNORE;
      }
      onUpload(file);
      return false;
    },
    showUploadList: false,
  };

  return (
    <Dragger
      {...props}
      style={{
        border: '2px dashed #D6D3D0',
        borderRadius: 6,
        background: '#FAFAF9',
        padding: '32px 24px',
      }}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined style={{ color: '#A8A29E', fontSize: 32 }} />
      </p>
      <p style={{ color: '#44403C', fontSize: 14, marginBottom: 4, fontWeight: 500 }}>
        点击或拖拽 CSV/Excel 文件到此处上传
      </p>
      <p style={{ color: '#A8A29E', fontSize: 12, margin: 0 }}>
        支持 .csv / .xlsx / .xls 格式，最大 100MB
      </p>
    </Dragger>
  );
}
