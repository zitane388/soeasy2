// src/pages/CollectedPage.jsx
import { useState, useEffect } from 'react'
import { productsAPI } from '../services/api'
import { useSocket } from '../hooks/useSocket'
import { Package, Trash2, ExternalLink, RefreshCw } from 'lucide-react'

export default function CollectedPage() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const { on, off } = useSocket()

  useEffect(() => {
    loadProducts()

    // Listen for new collected products
    const handleNewProduct = (data) => {
      setProducts(prev => [...prev, data])
    }

    on('product_collected', handleNewProduct)

    return () => {
      off('product_collected', handleNewProduct)
    }
  }, [on, off])

  const loadProducts = async () => {
    setLoading(true)
    try {
      const data = await productsAPI.getCollected()
      setProducts(data)
    } catch (error) {
      console.error('Failed to load products:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (productId) => {
    if (!window.confirm('이 상품을 삭제하시겠습니까?')) {
      return
    }

    try {
      await productsAPI.deleteCollected(productId)
      setProducts(prev => prev.filter(p => p.id !== productId))
    } catch (error) {
      console.error('Failed to delete product:', error)
      alert('삭제 실패: ' + error.message)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-primary-600" size={48} />
      </div>
    )
  }

  if (products.length === 0) {
    return (
      <div className="max-w-6xl">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">수집 완료 상품</h2>
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <Package className="mx-auto mb-4 text-gray-400" size={64} />
          <p className="text-xl text-gray-600 mb-2">수집 완료된 상품이 없습니다</p>
          <p className="text-sm text-gray-500">
            상품 수집 페이지에서 상품을 수집해보세요.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          수집 완료 상품 ({products.length})
        </h2>
        <button
          onClick={loadProducts}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          새로고침
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product) => (
          <div
            key={product.id || product.url}
            className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
          >
            {/* Product Image */}
            {product.thumbnail_url && (
              <div className="aspect-square bg-gray-100">
                <img
                  src={product.thumbnail_url}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.style.display = 'none'
                  }}
                />
              </div>
            )}

            {/* Product Info */}
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                {product.name || '상품명 없음'}
              </h3>

              {product.price && (
                <p className="text-lg font-bold text-primary-600 mb-2">
                  {Number(product.price).toLocaleString()}원
                </p>
              )}

              {product.brand && (
                <p className="text-sm text-gray-600 mb-1">
                  브랜드: {product.brand}
                </p>
              )}

              {product.category && (
                <p className="text-sm text-gray-600 mb-3">
                  카테고리: {product.category}
                </p>
              )}

              {/* Options */}
              {product.options && product.options.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-gray-500 mb-1">옵션:</p>
                  <div className="flex flex-wrap gap-1">
                    {product.options.slice(0, 5).map((option, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                      >
                        {option}
                      </span>
                    ))}
                    {product.options.length > 5 && (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                        +{product.options.length - 5}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-3 border-t">
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-primary-50 text-primary-700 rounded hover:bg-primary-100 transition-colors"
                >
                  <ExternalLink size={16} />
                  원본 보기
                </a>
                <button
                  onClick={() => handleDelete(product.id || product.url)}
                  className="flex items-center justify-center px-3 py-2 text-sm bg-red-50 text-red-700 rounded hover:bg-red-100 transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
