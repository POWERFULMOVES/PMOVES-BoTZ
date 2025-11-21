#!/usr/bin/env python3
"""
Simple test script to validate improved Docling import implementation.
"""

import sys
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("Testing improved Docling import implementation...")
    
    try:
        # Test the improved import
        from docling_mcp_server import get_docling_imports, DOCLING_AVAILABLE
        
        print(f"SUCCESS: Import completed")
        print(f"DOCLING_AVAILABLE: {DOCLING_AVAILABLE}")
        
        # Test singleton pattern
        imports1 = get_docling_imports()
        imports2 = get_docling_imports()
        
        if imports1 is imports2:
            print("SUCCESS: Singleton pattern working")
        else:
            print("FAIL: Singleton pattern failed")
        
        # Test import summary
        summary = imports1.get_import_summary()
        print(f"Available: {summary['available']}")
        print(f"Version: {summary['version']}")
        print(f"Features: {summary['features']}")
        
        # Test converter creation if available
        if imports1.is_available():
            try:
                converter = imports1.get_converter()
                print(f"SUCCESS: Converter created - {type(converter)}")
            except Exception as e:
                print(f"FAIL: Converter creation failed - {e}")
        else:
            print("INFO: Converter not available (Docling not installed)")
        
        print("SUCCESS: All tests completed!")
        return True
        
    except Exception as e:
        print(f"FAIL: Test failed - {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)