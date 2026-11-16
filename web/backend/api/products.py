# web/backend/api/products.py
from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__)

@products_bp.route('/pending', methods=['GET'])
def get_pending():
    """Get pending products"""
    app_state = current_app.config.get('app_state', {})
    products = app_state.get('products_pending', [])

    return jsonify({
        'count': len(products),
        'products': [
            {
                'name': getattr(p, 'name', ''),
                'brand': getattr(p, 'brand', ''),
                'url': getattr(p, 'url', ''),
                'images': getattr(p, 'images', [])[:5],
            }
            for p in products
        ]
    })

@products_bp.route('/collected', methods=['GET'])
def get_collected():
    """Get collected products"""
    app_state = current_app.config.get('app_state', {})
    products = app_state.get('products_collected', [])

    return jsonify({
        'count': len(products),
        'products': [
            {
                'name': getattr(p, 'name', ''),
                'brand': getattr(p, 'brand', ''),
                'url': getattr(p, 'url', ''),
                'images': getattr(p, 'images', [])[:5],
            }
            for p in products
        ]
    })

@products_bp.route('/pending/<int:index>', methods=['DELETE'])
def delete_pending(index):
    """Delete a pending product"""
    app_state = current_app.config.get('app_state', {})
    products = app_state.get('products_pending', [])

    if 0 <= index < len(products):
        deleted = products.pop(index)
        return jsonify({
            'message': 'Product deleted',
            'name': getattr(deleted, 'name', '')
        })

    return jsonify({'error': 'Invalid index'}), 400

@products_bp.route('/collected/<int:index>', methods=['DELETE'])
def delete_collected(index):
    """Delete a collected product"""
    app_state = current_app.config.get('app_state', {})
    products = app_state.get('products_collected', [])

    if 0 <= index < len(products):
        deleted = products.pop(index)
        return jsonify({
            'message': 'Product deleted',
            'name': getattr(deleted, 'name', '')
        })

    return jsonify({'error': 'Invalid index'}), 400
