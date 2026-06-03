import { Empty } from 'antd';
import type { ReactNode } from 'react';

interface Props {
  description?: string;
  image?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ description = '暂无数据', image, action }: Props) {
  return (
    <Empty
      image={image || Empty.PRESENTED_IMAGE_SIMPLE}
      description={description}
      style={{ padding: '60px 0' }}
    >
      {action}
    </Empty>
  );
}
