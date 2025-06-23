#!/usr/bin/env python3
"""
Web Interface for Manual Correction Manager
Provides a web-based UI for managing media classifications and corrections
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import logging
from datetime import datetime
from modules.classifier import learn_from_correction, get_cache_stats, get_unapplied_corrections
from modules.smart_cache import smart_cache
import re

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard."""
    stats = get_cache_stats()
    return render_template('index.html', stats=stats)

@app.route('/corrections')
def corrections():
    """Show all manual corrections."""
    corrections_data = smart_cache.manual_corrections.get("corrections", {})
    corrections_list = []
    
    for folder_name, correction in corrections_data.items():
        corrections_list.append({
            'folder_name': folder_name,
            'original': correction['original'],
            'correct': correction['correct'],
            'reason': correction.get('reason', ''),
            'applied': correction.get('applied', False),
            'timestamp': correction['timestamp']
        })
    
    # Sort by timestamp (newest first)
    corrections_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('corrections.html', corrections=corrections_list)

@app.route('/add_correction', methods=['GET', 'POST'])
def add_correction():
    """Add a new manual correction for category or metadata."""
    if request.method == 'POST':
        folder_name = request.form.get('folder_name', '').strip()
        correct_tmdb_id = request.form.get('correct_tmdb_id', '').strip()
        original_classification = request.form.get('original', 'Unknown').strip()
        correct_classification = request.form.get('correct', '').strip()
        reason = request.form.get('reason', '').strip()

        if not folder_name:
            return jsonify({'success': False, 'message': 'Folder name is required.'})

        try:
            if correct_tmdb_id:
                # This is a metadata correction (e.g., wrong movie)
                from modules.correction_processor import apply_metadata_correction
                
                # Clean up TMDB ID
                tmdb_id_match = re.search(r'(\d+)', correct_tmdb_id)
                if not tmdb_id_match:
                    return jsonify({'success': False, 'message': 'Invalid TMDB ID format.'})
                
                cleaned_tmdb_id = tmdb_id_match.group(1)
                
                # Apply the correction
                result = apply_metadata_correction(folder_name, cleaned_tmdb_id, reason)
                return jsonify(result)

            elif correct_classification:
                # This is a category correction
                learn_from_correction(folder_name, correct_classification, original_classification, reason)
                return jsonify({'success': True, 'message': f'Category correction added for {folder_name}.'})
            
            else:
                return jsonify({'success': False, 'message': 'Either Correct TMDB ID or Correct Classification is required.'})

        except Exception as e:
            logger.error(f"Error processing correction for {folder_name}: {e}")
            return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})

    return render_template('add_correction.html')

@app.route('/api/corrections', methods=['GET'])
def api_corrections():
    """API endpoint to get corrections."""
    corrections_data = smart_cache.manual_corrections.get("corrections", {})
    return jsonify(corrections_data)

@app.route('/api/add_correction', methods=['POST'])
def api_add_correction():
    """API endpoint to add correction."""
    data = request.get_json()
    
    folder_name = data.get('folder_name', '').strip()
    original = data.get('original', '').strip()
    correct = data.get('correct', '').strip()
    reason = data.get('reason', '').strip()
    
    if not all([folder_name, correct]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    try:
        learn_from_correction(folder_name, correct, original or 'Unknown', reason)
        return jsonify({'success': True, 'message': 'Correction added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_correction', methods=['POST'])
def api_delete_correction():
    """API endpoint to delete correction."""
    data = request.get_json()
    folder_name = data.get('folder_name', '').strip()
    
    if not folder_name:
        return jsonify({'success': False, 'message': 'Folder name is required'})
    
    try:
        if folder_name in smart_cache.manual_corrections["corrections"]:
            del smart_cache.manual_corrections["corrections"][folder_name]
            smart_cache._save_manual_corrections()
            return jsonify({'success': True, 'message': 'Correction deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Correction not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/apply_corrections', methods=['POST'])
def api_apply_corrections():
    """API endpoint to apply all unapplied corrections."""
    try:
        unapplied = get_unapplied_corrections()
        applied_count = 0
        
        for correction in unapplied:
            folder_name = correction['folder_name']
            smart_cache.mark_correction_applied(folder_name)
            applied_count += 1
        
        return jsonify({
            'success': True, 
            'message': f'Applied {applied_count} corrections to AI learning'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stats')
def api_stats():
    """API endpoint to get cache statistics."""
    stats = get_cache_stats()
    return jsonify(stats)

@app.route('/api/suggestions')
def api_suggestions():
    """API endpoint to get classification suggestions for unclassified folders."""
    # This would scan the unorganized directory and suggest classifications
    # For now, return empty list
    return jsonify([])

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting web interface on port {port}")
    print(f"Access the interface at: http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 