# web/backend/api/naver_best.py
from flask import Blueprint, request, jsonify, current_app
import threading
import logging
from pathlib import Path
import csv

logger = logging.getLogger(__name__)

naver_best_bp = Blueprint('naver_best', __name__)

def get_socketio():
    from app import socketio
    return socketio

@naver_best_bp.route('/load-store', methods=['POST'])
def load_store():
    """Load store URLs from CSV"""
    try:
        # Get absolute path to project root
        project_root = Path(__file__).parent.parent.parent.parent
        path = project_root / "data" / "store.csv"

        if not path.exists():
            return jsonify({'error': f'data/store.csv not found at {path}'}), 404

        with path.open("r", encoding="utf-8") as f:
            urls = [row[0].strip() for row in csv.reader(f) if row and row[0].startswith("http")]

        app_state = current_app.config.get('app_state', {})
        app_state['naver_best_urls'] = urls

        socketio = get_socketio()
        socketio.emit('status', {'message': f'상점 URL {len(urls)}개 로드 완료'})

        return jsonify({
            'count': len(urls),
            'urls': urls
        })

    except Exception as e:
        logger.error(f'Load store error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@naver_best_bp.route('/collect-list', methods=['POST'])
def collect_list():
    """Start collecting BEST product list"""
    app_state = current_app.config.get('app_state', {})
    urls = app_state.get('naver_best_urls', [])

    if not urls:
        return jsonify({'error': 'Store URLs not loaded'}), 400

    def collect_task():
        try:
            from naver_best.orchestrator import NaverBestOrchestrator
            from naver_best.models import NaverProductItem

            socketio = get_socketio()
            items = app_state.setdefault('naver_best_items', [])
            items.clear()

            orchestrator = NaverBestOrchestrator(
                urls_from_store=urls,
                stop_event=threading.Event(),
                items_container=items
            )

            # Setup callbacks
            def on_status(msg):
                socketio.emit('status', {'message': msg})
                logger.info(f'[NAVER_BEST] {msg}')

            def on_render():
                socketio.emit('naver_best_update', {
                    'count': len(items),
                    'items': [
                        {
                            'name': item.name,
                            'url': item.best_detail_url,
                            'images': item.images[:5] if item.images else [],
                            'is_collected': getattr(item, 'is_collected', False),
                        }
                        for item in items[:20]  # Send first 20 items
                    ]
                })

            def on_finished():
                socketio.emit('status', {'message': '✅ 목록 수집 완료'})
                socketio.emit('collect_finished', {'stage': 'list'})

            orchestrator._status = on_status
            orchestrator._render_cards = on_render
            orchestrator._refresh_buttons = on_finished

            app_state['naver_best_orchestrator'] = orchestrator

            # Start collecting
            socketio.emit('status', {'message': '베스트 상품 목록 수집 시작...'})
            orchestrator.collect_list_only()

        except Exception as e:
            logger.error(f'Collect list error: {e}', exc_info=True)
            socketio = get_socketio()
            socketio.emit('error', {'message': f'수집 오류: {str(e)}'})

    thread = threading.Thread(target=collect_task, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': '목록 수집 시작됨'})

@naver_best_bp.route('/collect-details', methods=['POST'])
def collect_details():
    """Start collecting product details"""
    app_state = current_app.config.get('app_state', {})
    orchestrator = app_state.get('naver_best_orchestrator')

    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 400

    items = app_state.get('naver_best_items', [])
    if not items:
        return jsonify({'error': 'No items to collect'}), 400

    def collect_task():
        try:
            socketio = get_socketio()

            def on_status(msg):
                socketio.emit('status', {'message': msg})

            def on_render():
                socketio.emit('naver_best_update', {
                    'count': len(items),
                    'items': [
                        {
                            'name': item.name,
                            'images': item.images[:5] if item.images else [],
                            'is_collected': getattr(item, 'is_collected', False),
                            'description_length': len(item.description) if item.description else 0,
                        }
                        for item in items[:20]
                    ]
                })

            def on_finished():
                socketio.emit('status', {'message': '✅ 상세 수집 완료'})
                socketio.emit('collect_finished', {'stage': 'details'})

            orchestrator._status = on_status
            orchestrator._render_cards = on_render
            orchestrator._refresh_buttons = on_finished

            socketio.emit('status', {'message': '상세 정보 수집 시작...'})
            orchestrator.collect_details_only()

        except Exception as e:
            logger.error(f'Collect details error: {e}', exc_info=True)
            socketio = get_socketio()
            socketio.emit('error', {'message': f'수집 오류: {str(e)}'})

    thread = threading.Thread(target=collect_task, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': '상세 수집 시작됨'})

@naver_best_bp.route('/collect-origin', methods=['POST'])
def collect_origin():
    """Start collecting product origin info"""
    app_state = current_app.config.get('app_state', {})
    orchestrator = app_state.get('naver_best_orchestrator')

    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 400

    items = app_state.get('naver_best_items', [])
    if not items:
        return jsonify({'error': 'No items to collect'}), 400

    def collect_task():
        try:
            socketio = get_socketio()

            def on_status(msg):
                socketio.emit('status', {'message': msg})

            def on_render():
                socketio.emit('naver_best_update', {
                    'count': len(items),
                    'items': [
                        {
                            'name': item.name,
                            'images': item.images[:5] if item.images else [],
                            'is_collected': getattr(item, 'is_collected', False),
                            'origin': getattr(item, 'origin', ''),
                        }
                        for item in items[:20]
                    ]
                })

            def on_finished():
                socketio.emit('status', {'message': '✅ 원산지 수집 완료'})
                socketio.emit('collect_finished', {'stage': 'origin'})

            orchestrator._status = on_status
            orchestrator._render_cards = on_render
            orchestrator._refresh_buttons = on_finished

            socketio.emit('status', {'message': '원산지 정보 수집 시작...'})
            orchestrator.collect_origin_only()

        except Exception as e:
            logger.error(f'Collect origin error: {e}', exc_info=True)
            socketio = get_socketio()
            socketio.emit('error', {'message': f'수집 오류: {str(e)}'})

    thread = threading.Thread(target=collect_task, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': '원산지 수집 시작됨'})

@naver_best_bp.route('/items', methods=['GET'])
def get_items():
    """Get collected BEST items"""
    app_state = current_app.config.get('app_state', {})
    items = app_state.get('naver_best_items', [])

    return jsonify({
        'count': len(items),
        'items': [
            {
                'name': item.name or '상품명 없음',
                'url': item.best_detail_url,
                'images': item.images[:5] if item.images else [],
                'is_collected': getattr(item, 'is_collected', False),
                'description_length': len(item.description) if item.description else 0,
            }
            for item in items
        ]
    })
