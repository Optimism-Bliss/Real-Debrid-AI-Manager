#!/usr/bin/env python3
"""
Local test script to verify the modular organize_media.py works
This simulates what would happen in the Docker container
"""

import os
import sys

# Add current directory to Python path (like Docker would do)
sys.path.insert(0, '/app')  # Simulate Docker's /app directory
sys.path.insert(0, '.')     # Also add current directory

# Mock environment variables for testing
os.environ.setdefault('OPENAI_API_KEY', 'test-key')
os.environ.setdefault('TMDB_API_KEY', 'test-key') 
os.environ.setdefault('PERPLEXITY_API_KEY', 'test-key')

def test_imports():
    """Test all module imports like Docker would"""
    print("🧪 Testing module imports (Docker simulation)...")
    
    try:
        # Test importing main script
        print("Testing main organize_media.py import...")
        
        # Test config module
        from modules.config import UNORGANIZED_DIR, DEST_DIRS, JAV_PREFIXES
        print("✅ modules.config imported successfully")
        
        # Test utils module
        from modules.utils import load_tracking, save_tracking, copy_file_if_changed
        print("✅ modules.utils imported successfully")
        
        # Test JAV detector
        from modules.jav_detector import is_jav_prefix, extract_jav_code
        print("✅ modules.jav_detector imported successfully")
        
        # Test classifier
        from modules.classifier import classify_folder, is_tv_show
        print("✅ modules.classifier imported successfully")
        
        # Test API extractors
        from modules.api_extractors import extract_show_name, extract_movie_name
        print("✅ modules.api_extractors imported successfully")
        
        # Test TMDB API
        from modules.tmdb_api import search_tmdb_movie, search_tmdb_tv
        print("✅ modules.tmdb_api imported successfully")
        
        # Test processors
        from modules.processors import process_jav_files, process_tv_shows, process_movies
        print("✅ modules.processors imported successfully")
        
        print("\n🎉 All modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_functionality():
    """Test basic functionality"""
    print("\n🔧 Testing basic functionality...")
    
    try:
        from modules.jav_detector import is_jav_prefix, extract_jav_code
        from modules.classifier import classify_folder, is_tv_show
        
        # Test cases from the logs that were problematic
        test_cases = [
            # JAV that were misclassified as Movies
            ("169bbs.com@SONE-564_[4K]", "JAV"),
            ("DASS-616ch", "JAV"), 
            ("fc2-ppv-4652840-HD", "JAV"),
            ("hhd800.com@START-296", "JAV"),
            
                # Shows that were misclassified as Movies
    ("[TorrentCouch.com].Black.Mirror.S04.Complete.1080p.HD.x264.[4.6GB]", "Shows"),
    ("Friends.S01.UHD.BluRay.2160p.DTS-HD.MA.5.1.DV.HEVC.REMUX-FraMeSToR", "Shows"),
    ("Better.Call.Saul.S01.2160p.NF.WEBRip.DTS.x264-SNEAkY", "Shows"),
            
            # Movies that should stay as movies
            ("Interstellar.2014.2160p.PROPER.IMAX.REMUX.DV.HDR10+.TrueHD.7.1.Atmos-jennaortegaUHD", "Movie"),
            ("Logan.2017.2160p.UHD.BDRemux.TrueHD.Atmos.7.1.DoVi.HYBRID.P8", "Movie"),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for test_name, expected_category in test_cases:
            actual_category = classify_folder(test_name)
            is_correct = actual_category == expected_category
            
            status = "✅" if is_correct else "❌"
            print(f"{status} {test_name}")
            print(f"    Expected: {expected_category}, Got: {actual_category}")
            
            if is_correct:
                correct += 1
        
        print(f"\n📊 Results: {correct}/{total} ({correct/total*100:.1f}%) tests passed")
        return correct == total
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Local Test (Docker Simulation)")
    print("=" * 50)
    
    # Test imports
    import_success = test_imports()
    
    if import_success:
        # Test functionality
        func_success = test_functionality()
        
        if func_success:
            print("\n🎉 ALL TESTS PASSED! Ready for Docker deployment.")
        else:
            print("\n⚠️  Imports work but functionality has issues.")
    else:
        print("\n❌ Import tests failed. Fix imports before proceeding.")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 