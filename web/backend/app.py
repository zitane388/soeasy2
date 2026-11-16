# web/backend/app.py
import sys
import os

# Add parent directory to path to import from main project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import logging

# Import existing project modules
from scrapers.scraper_manager import ScraperManager
from naver_best.orchestrator import NaverBestOrchestrator
from naver_best.models import NaverProductItem

# Import API blueprints
from api.collect import collect_bp
from api.naver_best import naver_best_bp
from api.products import products_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'soeasy2-secret-key-change-in-production'
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173", async_mode='eventlet')

# Global state (in production, use Redis or database)
app_state = {
    'scraper': ScraperManager(),
    'products_pending': [],
    'products_collected': [],
    'naver_best_items': [],
    'naver_best_orchestrator': None,
    'naver_best_urls': [],
}

# Make app_state accessible from blueprints via current_app
app.config['app_state'] = app_state

# Register blueprints
app.register_blueprint(collect_bp, url_prefix='/api/collect')
app.register_blueprint(naver_best_bp, url_prefix='/api/naver-best')
app.register_blueprint(products_bp, url_prefix='/api/products')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'version': 'v2.1.0'})

@app.route('/api/state')
def get_state():
    """Get current application state"""
    return jsonify({
        'products_pending_count': len(app_state['products_pending']),
        'products_collected_count': len(app_state['products_collected']),
        'naver_best_items_count': len(app_state['naver_best_items']),
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to Soeasy2 server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

if __name__ == '__main__':
    logger.info('Starting Soeasy2 Web Server on http://localhost:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
