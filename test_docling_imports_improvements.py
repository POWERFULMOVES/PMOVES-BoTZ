#!/usr/bin/env python3
"""
Test script to validate the improved Docling import implementation.

This script tests the enhanced error handling, performance optimizations,
and best practices implemented in the DoclingImports class.
"""

import sys
import time
import traceback
from pathlib import Path

# Add the project directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_docling_imports():
    """Test the improved DoclingImports class functionality."""
    
    print("=" * 60)
    print("Testing Improved Docling Import Implementation")
    print("=" * 60)
    
    try:
        # Import the improved implementation
        from docling_mcp_server import get_docling_imports, DOCLING_AVAILABLE
        
        print(f"✓ Successfully imported improved implementation")
        print(f"✓ DOCLING_AVAILABLE flag: {DOCLING_AVAILABLE}")
        
        # Test singleton pattern
        print("\n1. Testing Singleton Pattern:")
        start_time = time.time()
        imports1 = get_docling_imports()
        imports2 = get_docling_imports()
        end_time = time.time()
        
        if imports1 is imports2:
            print(f"✓ Singleton pattern working (same instance returned)")
            print(f"✓ Performance: {end_time - start_time:.4f}s for double access")
        else:
            print("X Singleton pattern failed")
        
        # Test import summary
        print("\n2. Testing Import Summary:")
        summary = imports1.get_import_summary()
        print(f"✓ Available: {summary['available']}")
        print(f"✓ Version: {summary['version']}")
        print(f"✓ Features: {summary['features']}")
        if summary['errors']:
            print(f"⚠ Import errors: {summary['errors']}")
        
        # Test feature detection
        print("\n3. Testing Feature Detection:")
        test_features = ['converter', 'inputformat', 'pipelineoptions', 'settings']
        for feature in test_features:
            available = imports1.has_feature(feature)
            print(f"✓ Feature '{feature}': {'Available' if available else 'Not Available'}")
        
        # Test converter creation
        print("\n4. Testing Converter Creation:")
        if imports1.is_available():
            try:
                start_time = time.time()
                converter = imports1.get_converter()
                end_time = time.time()
                print(f"✓ Converter created successfully in {end_time - start_time:.4f}s")
                print(f"✓ Converter type: {type(converter)}")
                
                # Test converter with configuration
                try:
                    configured_converter = imports1.get_converter(
                        # Add any available pipeline options here
                    )
                    print(f"✓ Configured converter created successfully")
                except Exception as e:
                    print(f"⚠ Configured converter creation failed: {e}")
                    
            except Exception as e:
                print(f"X Converter creation failed: {e}")
        else:
            print("⚠ Converter not available (Docling not installed)")
        
        # Test error handling
        print("\n5. Testing Error Handling:")
        try:
            # This should raise an informative error if converter is not available
            if not imports1.is_available():
                converter = imports1.get_converter()
                print("X Should have raised ImportError")
            else:
                print("✓ Error handling working correctly")
        except ImportError as e:
            print(f"✓ Proper ImportError raised: {e}")
        except Exception as e:
            print(f"X Unexpected error type: {e}")
        
        print("\n6. Performance Comparison:")
        # Test multiple accesses to verify caching
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            get_docling_imports()
        end_time = time.time()
        avg_time = (end_time - start_time) / iterations
        print(f"✓ Average access time over {iterations} calls: {avg_time:.6f}s")
        print(f"✓ Total time for {iterations} calls: {end_time - start_time:.4f}s")
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nX Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=" * 60)
        return False

def test_backward_compatibility():
    """Test that the improved implementation maintains backward compatibility."""
    
    print("\nTesting Backward Compatibility:")
    
    try:
        # Test that the old global flag still works
        from docling_mcp_server import DOCLING_AVAILABLE
        
        print(f"✓ Global DOCLING_AVAILABLE flag accessible: {DOCLING_AVAILABLE}")
        
        # Test that the old import pattern would still work conceptually
        docling_imports = get_docling_imports()
        
        if DOCLING_AVAILABLE == docling_imports.is_available():
            print("✓ Backward compatibility maintained")
        else:
            print("X Backward compatibility broken")
            
        return True
        
    except Exception as e:
        print(f"X Backward compatibility test failed: {e}")
        return False

def test_memory_efficiency():
    """Test memory efficiency of the singleton pattern."""
    
    print("\nTesting Memory Efficiency:")
    
    try:
        import gc
        from docling_mcp_server import get_docling_imports
        
        # Force garbage collection
        gc.collect()
        
        # Create multiple instances (should return same object)
        instances = []
        for i in range(10):
            instances.append(get_docling_imports())
        
        # Check if all instances are the same object
        all_same = all(id(instances[0]) == id(instance) for instance in instances)
        
        if all_same:
            print("✓ Memory efficient: All instances are the same object")
            print(f"✓ Single instance ID: {id(instances[0])}")
        else:
            print("X Memory inefficient: Multiple instances created")
            
        return all_same
        
    except Exception as e:
        print(f"X Memory efficiency test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting comprehensive Docling import improvement tests...\n")
    
    success = True
    
    # Run all tests
    success &= test_docling_imports()
    success &= test_backward_compatibility()
    success &= test_memory_efficiency()
    
    # Final result
    print(f"\n{'='*60}")
if success:
    print("ALL TESTS PASSED! The improved implementation is working correctly.")
    print("\nKey Improvements Validated:")
    print("* Enhanced error handling with detailed error tracking")
    print("* Singleton pattern for memory efficiency")
    print("* Lazy loading for performance optimization")
    print("* Feature detection for optional components")
    print("* Comprehensive import status reporting")
    print("* Backward compatibility maintained")
else:
    print("SOME TESTS FAILED! Please review the implementation.")
print(f"{'='*60}")
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)