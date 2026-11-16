# web/backend/api/collect.py
from flask import Blueprint, request, jsonify, current_app
from flask_socketio import SocketIO
import threading
import logging

logger = logging.getLogger(__name__)

collect_bp = Blueprint('collect', __name__)

def get_socketio():
    """Get SocketIO instance from app context"""
    from app import socketio
    return socketio

@collect_bp.route('/scrape', methods=['POST'])
def scrape_product():
    """
    Scrape product from URL
    Request: {"url": "https://..."}
    """
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    def scrape_task():
        try:
            socketio = get_socketio()
            socketio.emit('status', {'message': f'스크래핑 시작: {url}'})

            scraper = current_app.config.get('app_state', {}).get('scraper')
            if not scraper:
                from scrapers.scraper_manager import ScraperManager
                scraper = ScraperManager()

            # Scrape product
            product = scraper.scrape(url)

            if product:
                # Add to pending list
                app_state = current_app.config.get('app_state', {})
                app_state.setdefault('products_pending', []).append(product)

                socketio.emit('status', {'message': '✅ 스크래핑 완료'})
                socketio.emit('product_scraped', {
                    'product': {
                        'name': getattr(product, 'name', ''),
                        'url': url,
                        'brand': getattr(product, 'brand', ''),
                    }
                })
            else:
                socketio.emit('status', {'message': '❌ 스크래핑 실패'})
                socketio.emit('error', {'message': '상품 정보를 가져올 수 없습니다.'})

        except Exception as e:
            logger.error(f'Scraping error: {e}', exc_info=True)
            socketio = get_socketio()
            socketio.emit('error', {'message': f'오류 발생: {str(e)}'})

    # Run in background thread
    thread = threading.Thread(target=scrape_task, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': '스크래핑 시작됨'})

@collect_bp.route('/pending', methods=['GET'])
def get_pending_products():
    """Get list of pending products"""
    app_state = current_app.config.get('app_state', {})
    products = app_state.get('products_pending', [])

    return jsonify({
        'count': len(products),
        'products': [
            {
                'name': getattr(p, 'name', ''),
                'brand': getattr(p, 'brand', ''),
                'url': getattr(p, 'url', ''),
            }
            for p in products
        ]
    })
