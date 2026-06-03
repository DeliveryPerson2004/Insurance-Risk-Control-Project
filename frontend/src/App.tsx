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
            colorPrimary: '#1677ff',
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
