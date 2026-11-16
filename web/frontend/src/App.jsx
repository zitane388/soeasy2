// src/App.jsx
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { useSocket } from './hooks/useSocket'
import CollectPage from './pages/CollectPage'
import NaverBestPage from './pages/NaverBestPage'
import CollectedPage from './pages/CollectedPage'
import { Package, ShoppingBag, CheckCircle, Settings, Activity } from 'lucide-react'

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <MainContent />
      </div>
    </BrowserRouter>
  )
}

function Sidebar() {
  const location = useLocation()

  const menuItems = [
    { path: '/', label: '상품 수집', icon: Package },
    { path: '/naver-best', label: '네이버 상품 수집', icon: ShoppingBag },
    { path: '/collected', label: '수집 완료', icon: CheckCircle },
  ]

  return (
    <div className="w-64 bg-white shadow-lg flex flex-col">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold text-primary-600">Soeasy2</h1>
        <p className="text-sm text-gray-500">v2.1.0</p>
      </div>

      <nav className="flex-1 p-4">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

function MainContent() {
  const { isConnected, statusMessage } = useSocket()

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header isConnected={isConnected} statusMessage={statusMessage} />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<CollectPage />} />
          <Route path="/naver-best" element={<NaverBestPage />} />
          <Route path="/collected" element={<CollectedPage />} />
        </Routes>
      </main>
    </div>
  )
}

function Header({ isConnected, statusMessage }) {
  return (
    <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h2 className="text-xl font-semibold text-gray-800">상품 수집기</h2>
        <div className="flex items-center gap-2">
          <Activity size={16} className={isConnected ? 'text-green-500' : 'text-gray-400'} />
          <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-gray-500'}`}>
            {isConnected ? '연결됨' : '연결 안 됨'}
          </span>
        </div>
      </div>

      {statusMessage && (
        <div className="text-sm text-gray-600 bg-gray-100 px-4 py-2 rounded-lg max-w-md truncate">
          {statusMessage}
        </div>
      )}
    </header>
  )
}

export default App
