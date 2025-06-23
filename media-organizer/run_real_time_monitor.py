#!/usr/bin/env python3
"""
Script to run the real-time media monitor
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """Check and install required dependencies."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "watchdog>=3.0.0",
        "requests>=2.31.0"
    ]
    
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name)
            print(f"✓ {package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is not installed. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✓ {package_name} installed successfully")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package_name}")
                return False
    
    return True

def setup_environment():
    """Setup environment variables."""
    print("🔧 Setting up environment...")
    
    # Check for required environment variables
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for AI classification',
        'REAL_DEBRID_API_KEY': 'Real-Debrid API key for .strm generation',
        'TMDB_API_KEY': 'TMDB API key for movie/show metadata'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var}: {description}")
    
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nYou can set them using:")
        print("   export OPENAI_API_KEY='your-key'")
        print("   export REAL_DEBRID_API_KEY='your-key'")
        print("   export TMDB_API_KEY='your-key'")
        print("\nOr create a .env file in the media-organizer directory.")
    
    return len(missing_vars) == 0

def create_env_file():
    """Create .env file template."""
    env_template = """# Media Organizer Environment Variables

# OpenAI API Key for AI classification
OPENAI_API_KEY=your_openai_api_key_here

# Real-Debrid API Key for .strm file generation
REAL_DEBRID_API_KEY=your_real_debrid_api_key_here

# TMDB API Key for movie/show metadata
TMDB_API_KEY=your_tmdb_api_key_here

# AI Confidence Threshold (0.0-1.0)
AI_CONFIDENCE_THRESHOLD=0.7

# Web Interface Port
PORT=5000

# Debug Mode
DEBUG=True
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_template)
        print("📄 Created .env file template. Please edit it with your API keys.")
        return False
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Real-time Media Monitor')
    parser.add_argument('--path', default='/app/media/unorganized',
                       help='Path to monitor for new torrents')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon process')
    parser.add_argument('--setup', action='store_true',
                       help='Setup environment and dependencies only')
    parser.add_argument('--web', action='store_true',
                       help='Also start web interface')
    
    args = parser.parse_args()
    
    print("🎬 Real-time Media Monitor")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies. Exiting.")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        if not create_env_file():
            print("❌ Environment not properly configured. Please set up API keys.")
            sys.exit(1)
    
    if args.setup:
        print("✅ Setup completed. Run without --setup to start monitoring.")
        return
    
    # Start real-time monitor
    print(f"\n🚀 Starting real-time monitor...")
    print(f"📁 Monitoring path: {args.path}")
    print(f"🤖 AI Classification: {'Enabled' if os.getenv('OPENAI_API_KEY') else 'Disabled'}")
    print(f"🔗 Real-Debrid Integration: {'Enabled' if os.getenv('REAL_DEBRID_API_KEY') else 'Disabled'}")
    print(f"🌐 Web Interface: {'Enabled' if args.web else 'Disabled'}")
    
    if args.web:
        print("\n🌐 Starting web interface in background...")
        # Start web interface in background
        import subprocess
        web_process = subprocess.Popen([
            sys.executable, "run_web_interface.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"📱 Web interface started on port {os.getenv('PORT', '5000')}")
        print(f"🌐 Access at: http://localhost:{os.getenv('PORT', '5000')}")
    
    print("\n👀 Real-time monitor is running...")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Import and run real-time monitor
        from real_time_monitor import RealTimeMonitor
        
        monitor = RealTimeMonitor(args.path)
        monitor.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping real-time monitor...")
        if args.web and 'web_process' in locals():
            web_process.terminate()
            print("🌐 Web interface stopped")
        print("✅ Real-time monitor stopped")
    except Exception as e:
        print(f"❌ Error starting real-time monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 