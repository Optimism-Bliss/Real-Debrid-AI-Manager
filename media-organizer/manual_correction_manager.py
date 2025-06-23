#!/usr/bin/env python3
"""
Manual Correction Manager for Media Organizer
Allows users to correct misclassifications and teach the AI system
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional
from modules.classifier import learn_from_correction, get_cache_stats, get_unapplied_corrections
from modules.smart_cache import smart_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManualCorrectionManager:
    def __init__(self):
        self.corrections_file = "/app/data/manual_corrections.json"
        
    def show_cache_stats(self):
        """Display cache statistics."""
        stats = get_cache_stats()
        print("\n=== Cache Statistics ===")
        print(f"Processed files: {stats['processed_files']}")
        print(f"AI classifications: {stats['ai_classifications']}")
        print(f"File hashes: {stats['file_hashes']}")
        print(f"Manual corrections: {stats['manual_corrections']}")
        print(f"Learning patterns: {stats['learning_patterns']}")
    
    def add_correction(self, folder_name: str, original_classification: str, 
                      correct_classification: str, reason: str = ""):
        """Add a manual correction."""
        try:
            learn_from_correction(folder_name, correct_classification, original_classification, reason)
            print(f"✓ Added correction: {folder_name}")
            print(f"  {original_classification} → {correct_classification}")
            if reason:
                print(f"  Reason: {reason}")
        except Exception as e:
            print(f"✗ Error adding correction: {e}")
    
    def list_corrections(self):
        """List all manual corrections."""
        corrections = smart_cache.manual_corrections.get("corrections", {})
        if not corrections:
            print("No manual corrections found.")
            return
        
        print("\n=== Manual Corrections ===")
        for folder_name, correction in corrections.items():
            print(f"\nFolder: {folder_name}")
            print(f"  Original: {correction['original']}")
            print(f"  Correct: {correction['correct']}")
            print(f"  Applied: {correction.get('applied', False)}")
            if correction.get('reason'):
                print(f"  Reason: {correction['reason']}")
            print(f"  Date: {correction['timestamp']}")
    
    def list_unapplied_corrections(self):
        """List corrections that haven't been applied to AI learning."""
        unapplied = get_unapplied_corrections()
        if not unapplied:
            print("No unapplied corrections found.")
            return
        
        print("\n=== Unapplied Corrections ===")
        for correction in unapplied:
            print(f"\nFolder: {correction['folder_name']}")
            print(f"  Original: {correction['original']}")
            print(f"  Correct: {correction['correct']}")
            if correction.get('reason'):
                print(f"  Reason: {correction['reason']}")
    
    def apply_corrections_to_ai(self):
        """Apply all unapplied corrections to AI learning."""
        unapplied = get_unapplied_corrections()
        if not unapplied:
            print("No unapplied corrections to process.")
            return
        
        print(f"Applying {len(unapplied)} corrections to AI learning...")
        for correction in unapplied:
            folder_name = correction['folder_name']
            smart_cache.mark_correction_applied(folder_name)
            print(f"✓ Applied: {folder_name}")
        
        print("All corrections applied successfully!")
    
    def interactive_correction(self):
        """Interactive mode for adding corrections."""
        print("\n=== Interactive Correction Mode ===")
        print("Enter folder names and their correct classifications.")
        print("Type 'quit' to exit.")
        
        while True:
            print("\n" + "="*50)
            folder_name = input("Folder name (or 'quit'): ").strip()
            if folder_name.lower() == 'quit':
                break
            
            if not folder_name:
                print("Please enter a folder name.")
                continue
            
            print("\nClassification options:")
            print("1. JAV")
            print("2. Movie") 
            print("3. Shows")
            print("4. SKIP")
            
            choice = input("Select correct classification (1-4): ").strip()
            classifications = {1: "JAV", 2: "Movie", 3: "Shows", 4: "SKIP"}
            
            if choice not in ['1', '2', '3', '4']:
                print("Invalid choice. Please select 1-4.")
                continue
            
            correct_classification = classifications[int(choice)]
            
            # Get original classification from cache
            original_classification = smart_cache.get_cached_classification(folder_name)
            if not original_classification:
                original_classification = input("Original classification (if unknown, press Enter): ").strip() or "Unknown"
            
            reason = input("Reason for correction (optional): ").strip()
            
            self.add_correction(folder_name, original_classification, correct_classification, reason)
    
    def batch_correction_from_file(self, file_path: str):
        """Load corrections from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                corrections = json.load(f)
            
            print(f"Loading {len(corrections)} corrections from {file_path}...")
            
            for correction in corrections:
                folder_name = correction.get('folder_name')
                original = correction.get('original', 'Unknown')
                correct = correction.get('correct')
                reason = correction.get('reason', '')
                
                if not all([folder_name, correct]):
                    print(f"✗ Skipping invalid correction: {correction}")
                    continue
                
                self.add_correction(folder_name, original, correct, reason)
            
            print("Batch correction completed!")
            
        except Exception as e:
            print(f"✗ Error loading corrections from file: {e}")
    
    def export_corrections(self, file_path: str):
        """Export all corrections to a JSON file."""
        try:
            corrections = smart_cache.manual_corrections.get("corrections", {})
            export_data = []
            
            for folder_name, correction in corrections.items():
                export_data.append({
                    "folder_name": folder_name,
                    "original": correction["original"],
                    "correct": correction["correct"],
                    "reason": correction.get("reason", ""),
                    "timestamp": correction["timestamp"]
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Exported {len(export_data)} corrections to {file_path}")
            
        except Exception as e:
            print(f"✗ Error exporting corrections: {e}")
    
    def cleanup_cache(self, days: int = 30):
        """Clean up old cache entries."""
        try:
            smart_cache.cleanup_old_cache(days)
            print(f"✓ Cleaned up cache entries older than {days} days")
        except Exception as e:
            print(f"✗ Error cleaning cache: {e}")

def main():
    """Main function for command line interface."""
    manager = ManualCorrectionManager()
    
    if len(sys.argv) < 2:
        print("Manual Correction Manager")
        print("Usage:")
        print("  python manual_correction_manager.py stats                    # Show cache statistics")
        print("  python manual_correction_manager.py list                     # List all corrections")
        print("  python manual_correction_manager.py unapplied               # List unapplied corrections")
        print("  python manual_correction_manager.py apply                   # Apply corrections to AI")
        print("  python manual_correction_manager.py interactive             # Interactive correction mode")
        print("  python manual_correction_manager.py add <folder> <orig> <correct> [reason]  # Add correction")
        print("  python manual_correction_manager.py batch <file.json>       # Load corrections from file")
        print("  python manual_correction_manager.py export <file.json>      # Export corrections to file")
        print("  python manual_correction_manager.py cleanup [days]          # Clean up old cache")
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        manager.show_cache_stats()
    
    elif command == "list":
        manager.list_corrections()
    
    elif command == "unapplied":
        manager.list_unapplied_corrections()
    
    elif command == "apply":
        manager.apply_corrections_to_ai()
    
    elif command == "interactive":
        manager.interactive_correction()
    
    elif command == "add":
        if len(sys.argv) < 5:
            print("Usage: python manual_correction_manager.py add <folder> <orig> <correct> [reason]")
            return
        
        folder_name = sys.argv[2]
        original = sys.argv[3]
        correct = sys.argv[4]
        reason = sys.argv[5] if len(sys.argv) > 5 else ""
        
        manager.add_correction(folder_name, original, correct, reason)
    
    elif command == "batch":
        if len(sys.argv) < 3:
            print("Usage: python manual_correction_manager.py batch <file.json>")
            return
        
        file_path = sys.argv[2]
        manager.batch_correction_from_file(file_path)
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: python manual_correction_manager.py export <file.json>")
            return
        
        file_path = sys.argv[2]
        manager.export_corrections(file_path)
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        manager.cleanup_cache(days)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main() 