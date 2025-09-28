#!/usr/bin/env python3
"""Fix the quality assurance 'true_positives' error."""

import json
import os
from pathlib import Path

def fix_qa_calibration():
    """Fix the QA calibration file structure."""
    
    qa_dir = Path("data/qa")
    qa_dir.mkdir(exist_ok=True)
    
    # Create proper calibration structure
    calibration_file = qa_dir / "confidence_calibration.json"
    
    proper_structure = {
        "blacklist": {
            "true_positives": 0,
            "false_positives": 0,
            "samples": []
        },
        "whitelist": {
            "true_positives": 0,
            "false_positives": 0,
            "samples": []
        },
        "review": {
            "escalated": 0,
            "resolved": 0,
            "samples": []
        }
    }
    
    # Write the proper structure
    with open(calibration_file, 'w') as f:
        json.dump(proper_structure, f, indent=2)
    
    print(f"✅ Fixed QA calibration file: {calibration_file}")
    
    # Also create QA results file
    qa_results_file = qa_dir / "qa_results.json"
    qa_results = {
        "qa_history": {},
        "accuracy_metrics": {
            "overall_accuracy": 0.0,
            "blacklist_precision": 0.0,
            "whitelist_precision": 0.0,
            "confidence_correlation": 0.0,
            "last_updated": None
        }
    }
    
    with open(qa_results_file, 'w') as f:
        json.dump(qa_results, f, indent=2)
    
    print(f"✅ Created QA results file: {qa_results_file}")

if __name__ == "__main__":
    fix_qa_calibration()