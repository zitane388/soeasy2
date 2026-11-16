// src/pages/NaverBestPage.jsx
import { useState, useEffect } from 'react'
import { naverBestAPI } from '../services/api'
import { useSocket } from '../hooks/useSocket'
import { Upload, ListChecks, FileText, Globe, Loader, Package } from 'lucide-react'

export default function NaverBestPage() {
  const [loading, setLoading] = useState(false)
  const [currentAction, setCurrentAction] = useState('')
  const [items, setItems] = useState([])
  const { on, off } = useSocket()

  useEffect(() => {
    // Listen for naver_best_item events
    const handleItem = (data) => {
      setItems(prev => [...prev, data])
    }

    on('naver_best_item', handleItem)

    return () => {
      off('naver_best_item', handleItem)
    }
  }, [on, off])

  const handleAction = async (action, apiCall, actionName) => {
    setLoading(true)
    setCurrentAction(actionName)
    try {
      const response = await apiCall()
      console.log(`${actionName} 성공:`, response.data)

      // Show success message based on action
      if (actionName === '스토어 불러오기' && response.data.count !== undefined) {
        alert(`✅ ${response.data.count}개의 스토어 URL을 로드했습니다.`)
      } else if (actionName === '리스트 수집') {
        alert(`✅ ${actionName}이 시작되었습니다. 잠시 기다려주세요.`)
      } else if (actionName === '상세 수집') {
        alert(`✅ ${actionName}이 시작되었습니다. 잠시 기다려주세요.`)
      } else if (actionName === '원산지 수집') {
        alert(`✅ ${actionName}이 시작되었습니다. 잠시 기다려주세요.`)
      }
    } catch (error) {
      console.error(`${actionName} error:`, error)
      alert(`❌ ${actionName} 실패: ` + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
      setCurrentAction('')
    }
  }

  const actions = [
    {
      id: 'load-store',
      label: '스토어 불러오기',
      icon: Upload,
      color: 'blue',
      onClick: () => handleAction('load', () => naverBestAPI.loadStore(), '스토어 불러오기'),
      description: 'CSV에서 네이버 스토어 URL 로드'
    },
    {
      id: 'collect-list',
      label: '리스트 수집',
      icon: ListChecks,
      color: 'green',
      onClick: () => handleAction('list', () => naverBestAPI.collectList(), '리스트 수집'),
      description: '각 스토어의 베스트 상품 리스트 수집'
    },
    {
      id: 'collect-details',
      label: '상세 수집',
      icon: FileText,
      color: 'purple',
      onClick: () => handleAction('details', () => naverBestAPI.collectDetails(), '상세 수집'),
      description: '수집된 상품의 상세 정보 수집'
    },
    {
      id: 'collect-origin',
      label: '원산지 수집',
      icon: Globe,
      color: 'orange',
      onClick: () => handleAction('origin', () => naverBestAPI.collectOrigin(), '원산지 수집'),
      description: '상품의 원산지 정보 수집'
    }
  ]

  const colorClasses = {
    blue: 'bg-blue-600 hover:bg-blue-700 text-white',
    green: 'bg-green-600 hover:bg-green-700 text-white',
    purple: 'bg-purple-600 hover:bg-purple-700 text-white',
    orange: 'bg-orange-600 hover:bg-orange-700 text-white',
  }

  return (
    <div className="max-w-6xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">네이버 베스트 상품 수집</h2>

      {/* Action Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {actions.map((action) => {
          const Icon = action.icon
          const isActive = loading && currentAction === action.label

          return (
            <button
              key={action.id}
              onClick={action.onClick}
              disabled={loading}
              className={`p-6 rounded-lg shadow-lg transition-all ${
                loading
                  ? 'opacity-50 cursor-not-allowed bg-gray-400'
                  : colorClasses[action.color]
              } ${isActive ? 'ring-4 ring-offset-2 ring-gray-400' : ''}`}
            >
              <div className="flex flex-col items-center gap-3">
                {isActive ? (
                  <Loader className="animate-spin" size={32} />
                ) : (
                  <Icon size={32} />
                )}
                <span className="font-semibold text-lg">{action.label}</span>
                <span className="text-xs opacity-90">{action.description}</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <h3 className="font-medium text-blue-900 mb-2">💡 수집 순서</h3>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li><strong>스토어 불러오기</strong>: CSV 파일에서 네이버 스마트스토어 URL 로드</li>
          <li><strong>리스트 수집</strong>: 각 스토어의 베스트 상품 리스트 수집 (Selenium 자동화)</li>
          <li><strong>상세 수집</strong>: 수집된 상품의 상세페이지 정보 수집</li>
          <li><strong>원산지 수집</strong>: 상품의 원산지 정보 추가 수집</li>
        </ol>
      </div>

      {/* Items Display */}
      {items.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-4">
            <Package className="text-primary-600" size={24} />
            <h3 className="text-xl font-bold text-gray-900">
              수집된 상품 ({items.length})
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item, index) => (
              <div key={index} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                {item.image_url && (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="w-full h-48 object-cover rounded mb-3"
                  />
                )}
                <h4 className="font-medium text-gray-900 mb-2 line-clamp-2">
                  {item.name}
                </h4>
                <p className="text-sm text-gray-600 mb-1">
                  가격: {item.price ? `${Number(item.price).toLocaleString()}원` : '가격 정보 없음'}
                </p>
                {item.store_name && (
                  <p className="text-xs text-gray-500">
                    스토어: {item.store_name}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <Package className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-gray-600">
            아직 수집된 상품이 없습니다.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            "스토어 불러오기" 버튼을 눌러 시작하세요.
          </p>
        </div>
      )}
    </div>
  )
}
