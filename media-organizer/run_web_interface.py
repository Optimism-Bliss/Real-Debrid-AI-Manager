#!/usr/bin/env python3
"""
Script to run the web interface for manual corrections
"""

import os
import sys
import subprocess

def main():
    print("🎬 Media Organizer - Web Interface")
    print("=" * 50)
    
    # Check if required packages are installed
    try:
        import flask
        print("✓ Flask is installed")
    except ImportError:
        print("✗ Flask is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask>=2.3.0"])
        print("✓ Flask installed successfully")
    
    try:
        import openai
        print("✓ OpenAI is installed")
    except ImportError:
        print("✗ OpenAI is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai>=1.0.0"])
        print("✓ OpenAI installed successfully")
    
    # Set environment variables
    port = os.getenv('PORT', '5000')
    debug = os.getenv('DEBUG', 'True')
    
    print(f"\n🚀 Starting web interface...")
    print(f"📱 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"🌐 URL: http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    # Run the web interface
    try:
        from web_interface import app
        app.run(host='0.0.0.0', port=int(port), debug=(debug.lower() == 'true'))
    except KeyboardInterrupt:
        print("\n👋 Web interface stopped")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 