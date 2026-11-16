// src/pages/CollectPage.jsx
import { useState } from 'react'
import { collectAPI } from '../services/api'
import { Search, Loader } from 'lucide-react'

export default function CollectPage() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const handleScrape = async (e) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    try {
      await collectAPI.scrape(url)
      setUrl('')
    } catch (error) {
      console.error('Scrape error:', error)
      alert('스크래핑 실패: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">상품 수집</h2>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <form onSubmit={handleScrape} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              상품 URL
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.uniqlo.com/jp/..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin" size={20} />
                    수집 중...
                  </>
                ) : (
                  <>
                    <Search size={20} />
                    정보수집하기
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="text-sm text-gray-600">
            <p className="font-medium mb-2">지원 사이트:</p>
            <ul className="list-disc list-inside space-y-1 text-gray-500">
              <li>Uniqlo Japan (uniqlo.com/jp)</li>
              <li>Uniqlo Vietnam (uniqlo.com/vn)</li>
              <li>GU Japan (gu-global.com/jp)</li>
              <li>Muji Japan (muji.com/jp)</li>
            </ul>
          </div>
        </form>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-blue-900 mb-2">💡 사용 방법</h3>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li>Chrome Extension이 설치되어 있어야 합니다</li>
          <li>지원 사이트의 상품 URL을 입력하세요</li>
          <li>"정보수집하기" 버튼을 클릭하세요</li>
          <li>Chrome 브라우저가 자동으로 열리고 데이터를 수집합니다</li>
        </ol>
      </div>
    </div>
  )
}
