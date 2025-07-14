#!/usr/bin/env python3
"""
Master test runner for DeepResearch2 production validation
"""
import sys
import subprocess
import os
from pathlib import Path

def run_test_suite():
    """Run complete test suite for production validation"""
    print("🧪 DeepResearch2 Production Test Suite")
    print("=" * 50)
    
    os.chdir(Path(__file__).parent)
    
    test_scripts = [
        ("Quick Validation", "test_quick_validation.py"),
        ("Database Compatibility", "test_database_compatibility.py"),
        ("Production Readiness", "production_test.py"),
        ("End-to-End Testing", "test_end_to_end.py"),
    ]
    
    results = {}
    
    for test_name, script in test_scripts:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = subprocess.run([
                sys.executable, script
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ {test_name} PASSED")
                results[test_name] = "PASSED"
            else:
                print(f"❌ {test_name} FAILED")
                print(f"Error output: {result.stderr}")
                results[test_name] = "FAILED"
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} TIMEOUT")
            results[test_name] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            results[test_name] = "ERROR"
    
    print("\n" + "=" * 50)
    print("📊 TEST SUITE SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for status in results.values() if status == "PASSED")
    total = len(results)
    
    for test_name, status in results.items():
        emoji = "✅" if status == "PASSED" else "❌"
        print(f"{emoji} {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🚀 DeepResearch2 is PRODUCTION READY!")
        return 0
    else:
        print("⚠️  Some tests failed. Review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_test_suite())
