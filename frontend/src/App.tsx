import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom'
import { Suspense } from 'react'
import {
  HomePage,
  ApiDataPage,
  ApiDataDebugPage,
  SimpleDebugPage,
  TestPage,
  SymbolDetailPage,
  AccountManagementPage,
  TradingDeskPage,
  OrderQueryPage,
  StrategiesPage,
  StrategyEditorPage,
  ExecutionPage,
  ReviewPage,
  ReplayPage,
} from '@/common/router/routes'

function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-background text-on-surface-variant text-sm">
      加载中...
    </div>
  )
}

// 使用 DataRouter（createBrowserRouter + RouterProvider）。
// 必需：strategy-engine 的 useUnsavedChanges hook 调用 useBlocker，
// 而 useBlocker 要求上下文必须是 DataRouter（BrowserRouter + <Routes> 不支持）。
// 所有懒加载页面通过共享 Suspense layout route 获得统一的 fallback。
const router = createBrowserRouter([
  {
    element: (
      <Suspense fallback={<Loading />}>
        <Outlet />
      </Suspense>
    ),
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/api-data', element: <ApiDataPage /> },
      { path: '/api-data-debug', element: <ApiDataDebugPage /> },
      { path: '/simple-debug', element: <SimpleDebugPage /> },
      { path: '/test-page', element: <TestPage /> },
      { path: '/symbol-detail', element: <SymbolDetailPage /> },
      { path: '/account', element: <AccountManagementPage /> },
      { path: '/account/manage', element: <AccountManagementPage /> },
      { path: '/account/trading', element: <TradingDeskPage /> },
      { path: '/account/orders', element: <OrderQueryPage /> },
      { path: '/strategies', element: <StrategiesPage /> },
      { path: '/strategy-editor', element: <StrategyEditorPage /> },
      { path: '/execution', element: <ExecutionPage /> },
      { path: '/review', element: <ReviewPage /> },
      { path: '/replay', element: <ReplayPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
