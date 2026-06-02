import { Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

const { Dragger } = Upload;

interface Props {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

export default function BatchUpload({ onUpload, disabled }: Props) {
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
    <Dragger {...props}>
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">点击或拖拽 CSV/Excel 文件到此处上传</p>
      <p className="ant-upload-hint">支持 .csv / .xlsx / .xls 格式，最大 10,000 条</p>
    </Dragger>
  );
}
