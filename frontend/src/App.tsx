import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PredictionPage from './pages/PredictionPage';
import BatchPredictPage from './pages/BatchPredictPage';
import CaseListPage from './pages/CaseListPage';
import CaseDetailPage from './pages/CaseDetailPage';
import AdminPage from './pages/AdminPage';
import AppLayout from './components/layout/AppLayout';
import ErrorBoundary from './components/common/ErrorBoundary';

/** ErrorBoundary 测试页：访问 /error-test 验证错误捕获 */
function ErrorTestPage() {
  throw new Error('ErrorBoundary 手动测试 — 如果你看到这个页面，说明 ErrorBoundary 正常捕获了错误。');
  return null;
}

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.user_role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            // 品牌色
            colorPrimary: '#4A5630',
            colorPrimaryHover: '#3B4526',
            colorPrimaryActive: '#3B4526',
            colorPrimaryBg: '#EDF0E7',
            colorPrimaryBgHover: '#E3E7DA',
            // 中性色
            colorText: '#292524',
            colorTextSecondary: '#44403C',
            colorTextTertiary: '#6B625D',
            colorTextQuaternary: '#A8A29E',
            colorBorder: '#E7E5E2',
            colorBorderSecondary: '#D6D3D0',
            colorFill: '#E7E5E2',
            colorFillSecondary: '#EDF0E7',
            colorFillTertiary: '#F5F3F0',
            colorFillQuaternary: '#FAFAF9',
            // 背景
            colorBgContainer: '#FFFFFF',
            colorBgElevated: '#FFFFFF',
            colorBgLayout: '#FAFAF9',
            colorBgSpotlight: '#292524',
            // 语义色
            colorSuccess: '#4A5630',
            colorWarning: '#947008',
            colorError: '#DC2626',
            colorInfo: '#6B625D',
            colorSuccessBg: '#F2F7ED',
            colorWarningBg: '#FFF8EB',
            colorErrorBg: '#FEF2F2',
            colorInfoBg: '#EDF0E7',
            colorSuccessBorder: '#4A5630',
            colorWarningBorder: '#947008',
            colorErrorBorder: '#DC2626',
            // 字体
            fontFamily: "'Inter', system-ui, -apple-system, 'Microsoft YaHei', sans-serif",
            fontSize: 14,
            fontSizeHeading1: 32,
            fontSizeHeading2: 24,
            fontSizeHeading3: 18,
            fontSizeHeading4: 16,
            fontSizeHeading5: 14,
            lineHeight: 1.6,
            // 圆角
            borderRadius: 6,
            borderRadiusLG: 8,
            borderRadiusSM: 4,
            // 阴影
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            boxShadowSecondary: '0 4px 12px rgba(0,0,0,0.08)',
            // 间距
            padding: 16,
            paddingLG: 24,
            paddingXS: 8,
            margin: 16,
            marginLG: 24,
            // 其他
            controlHeight: 36,
            controlHeightLG: 44,
            wireframe: false,
          },
          components: {
            Layout: {
              bodyBg: '#FAFAF9',
              headerBg: '#FAFAF9',
              siderBg: '#EBE8E4',
              triggerBg: '#EBE8E4',
              triggerColor: '#44403C',
            },
            Menu: {
              itemBg: 'transparent',
              itemColor: '#44403C',
              itemHoverBg: '#D6D3D0',
              itemSelectedBg: '#EDF0E7',
              itemSelectedColor: '#4A5630',
              subMenuItemBg: 'transparent',
            },
            Card: {
              paddingLG: 24,
            },
            Table: {
              headerBg: '#FAFAF9',
              headerColor: '#6B625D',
              rowHoverBg: '#EDF0E7',
              borderColor: '#E7E5E2',
            },
            Tag: {
              defaultBg: '#F5F3F0',
              defaultColor: '#44403C',
            },
            Tabs: {
              inkBarColor: '#4A5630',
              itemActiveColor: '#4A5630',
              itemHoverColor: '#3B4526',
              itemSelectedColor: '#4A5630',
            },
            Modal: {
              boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
            },
          },
        }}
      >
        <AntApp>
          <ErrorBoundary>
            <BrowserRouter>
            <Routes>
              <Route
                path="/login"
                element={
                  <GuestRoute>
                    <LoginPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="predict/single" element={<PredictionPage />} />
                <Route path="predict/batch" element={<BatchPredictPage />} />
                <Route path="cases" element={<CaseListPage />} />
                <Route path="cases/:id" element={<CaseDetailPage />} />
                <Route path="admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
              </Route>
              {/* ErrorBoundary 测试路由：访问 /error-test 触发错误页 */}
              <Route path="/error-test" element={<ErrorTestPage />} />
              <Route path="*" element={<div style={{ padding: 48, textAlign: 'center' }}>404</div>} />
            </Routes>
          </BrowserRouter>
          </ErrorBoundary>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
