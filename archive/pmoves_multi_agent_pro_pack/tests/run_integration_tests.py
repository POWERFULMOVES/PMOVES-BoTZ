#!/usr/bin/env python3
"""
Integration Test Runner for Docling MCP Server

This script orchestrates the execution of all integration tests for the docling-mcp service,
including setup, execution, and reporting of test results.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Orchestrates integration test execution for Docling MCP Server."""

    def __init__(self, test_dir: str = "tests", verbose: bool = False):
        """Initialize the test runner."""
        self.test_dir = Path(test_dir)
        self.verbose = verbose
        self.results = {}
        self.start_time = None
        self.end_time = None

    def setup_test_environment(self) -> bool:
        """Set up the test environment."""
        logger.info("Setting up test environment...")
        
        try:
            # Check if test requirements are installed
            requirements_file = self.test_dir / "test_requirements.txt"
            if requirements_file.exists():
                logger.info("Installing test requirements...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to install test requirements: {result.stderr}")
                    return False
            
            # Create test data directory
            test_data_dir = self.test_dir / "data"
            test_data_dir.mkdir(exist_ok=True)
            
            # Create sample test documents
            self._create_test_documents(test_data_dir)
            
            logger.info("✓ Test environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up test environment: {e}")
            return False

    def _create_test_documents(self, test_data_dir: Path):
        """Create sample test documents."""
        logger.info("Creating test documents...")
        
        # Create a simple text document
        text_doc = test_data_dir / "test_document.txt"
        text_doc.write_text("This is a test document for Docling MCP integration testing.\nIt contains multiple lines of text.")
        
        # Create a markdown document
        md_doc = test_data_dir / "test_document.md"
        md_doc.write_text("""# Test Document

This is a test markdown document.

## Section 1
Some content here.

## Section 2
More content here.
""")
        
        # Create a JSON document
        json_doc = test_data_dir / "test_document.json"
        json_data = {
            "title": "Test Document",
            "content": "This is a test JSON document",
            "metadata": {
                "author": "Test Suite",
                "created": "2024-01-01"
            }
        }
        json_doc.write_text(json.dumps(json_data, indent=2))
        
        logger.info(f"✓ Created test documents in {test_data_dir}")

    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        logger.info("Running unit tests...")
        
        try:
            # Run pytest with unit test marker
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_dir),
                "-m", "unit",
                "--tb=short",
                "--cov=docling_mcp_server",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml"
            ]
            
            if self.verbose:
                cmd.append("-v")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.results["unit_tests"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("✓ Unit tests passed")
                return True
            else:
                logger.error("✗ Unit tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run unit tests: {e}")
            self.results["unit_tests"] = {"success": False, "error": str(e)}
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        logger.info("Running integration tests...")
        
        try:
            # Run pytest with integration test marker
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_dir),
                "-m", "integration",
                "--tb=short",
                "--timeout=60"
            ]
            
            if self.verbose:
                cmd.append("-v")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.results["integration_tests"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("✓ Integration tests passed")
                return True
            else:
                logger.error("✗ Integration tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run integration tests: {e}")
            self.results["integration_tests"] = {"success": False, "error": str(e)}
            return False

    def run_docker_tests(self) -> bool:
        """Run Docker integration tests."""
        logger.info("Running Docker integration tests...")
        
        try:
            # Check if Docker is available
            docker_check = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if docker_check.returncode != 0:
                logger.warning("Docker not available, skipping Docker tests")
                self.results["docker_tests"] = {"success": True, "skipped": True}
                return True
            
            # Run Docker tests
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_dir),
                "-m", "docker",
                "--tb=short"
            ]
            
            if self.verbose:
                cmd.append("-v")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.results["docker_tests"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("✓ Docker tests passed")
                return True
            else:
                logger.error("✗ Docker tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run Docker tests: {e}")
            self.results["docker_tests"] = {"success": False, "error": str(e)}
            return False

    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        logger.info("Running performance tests...")
        
        try:
            # Run pytest with performance test marker
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_dir),
                "-m", "performance",
                "--tb=short",
                "--benchmark-only"
            ]
            
            if self.verbose:
                cmd.append("-v")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.results["performance_tests"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("✓ Performance tests passed")
                return True
            else:
                logger.error("✗ Performance tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run performance tests: {e}")
            self.results["performance_tests"] = {"success": False, "error": str(e)}
            return False

    def run_security_tests(self) -> bool:
        """Run security tests."""
        logger.info("Running security tests...")
        
        try:
            # Run pytest with security test marker
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_dir),
                "-m", "security",
                "--tb=short"
            ]
            
            if self.verbose:
                cmd.append("-v")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.results["security_tests"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("✓ Security tests passed")
                return True
            else:
                logger.error("✗ Security tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run security tests: {e}")
            self.results["security_tests"] = {"success": False, "error": str(e)}
            return False

    def generate_test_report(self) -> Dict:
        """Generate comprehensive test report."""
        logger.info("Generating test report...")
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_suite": "Docling MCP Server Integration Tests",
            "results": self.results,
            "summary": {
                "total_tests": len(self.results),
                "passed_tests": sum(1 for r in self.results.values() if r.get("success", False)),
                "failed_tests": sum(1 for r in self.results.values() if not r.get("success", False)),
                "skipped_tests": sum(1 for r in self.results.values() if r.get("skipped", False))
            },
            "duration": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "total_duration": self.end_time - self.start_time if self.start_time and self.end_time else None
            }
        }
        
        # Save report to file
        report_file = self.test_dir / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Test report saved to {report_file}")
        return report

    def print_summary(self, report: Dict):
        """Print test summary."""
        print("\n" + "="*60)
        print("DOCLING MCP SERVER INTEGRATION TEST SUMMARY")
        print("="*60)
        
        summary = report["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Skipped: {summary['skipped_tests']}")
        
        if report["duration"]["total_duration"]:
            print(f"Duration: {report['duration']['total_duration']:.2f} seconds")
        
        print("\nDetailed Results:")
        for test_type, result in self.results.items():
            status = "✓ PASSED" if result.get("success", False) else "✗ FAILED"
            if result.get("skipped", False):
                status = "- SKIPPED"
            print(f"  {test_type}: {status}")
        
        print("\n" + "="*60)

    def run_all_tests(self) -> bool:
        """Run all test suites."""
        logger.info("Starting comprehensive integration test suite...")
        self.start_time = time.time()
        
        # Setup environment
        if not self.setup_test_environment():
            return False
        
        # Run test suites
        test_suites = [
            ("unit_tests", self.run_unit_tests),
            ("integration_tests", self.run_integration_tests),
            ("docker_tests", self.run_docker_tests),
            ("performance_tests", self.run_performance_tests),
            ("security_tests", self.run_security_tests)
        ]
        
        all_passed = True
        for suite_name, suite_func in test_suites:
            try:
                if not suite_func():
                    all_passed = False
            except Exception as e:
                logger.error(f"Test suite {suite_name} failed with exception: {e}")
                self.results[suite_name] = {"success": False, "error": str(e)}
                all_passed = False
        
        self.end_time = time.time()
        
        # Generate report
        report = self.generate_test_report()
        self.print_summary(report)
        
        return all_passed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Docling MCP Server integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test-dir", default="tests", help="Test directory")
    parser.add_argument("--suite", choices=["unit", "integration", "docker", "performance", "security", "all"],
                       default="all", help="Test suite to run")
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(test_dir=args.test_dir, verbose=args.verbose)
    
    if args.suite == "all":
        success = runner.run_all_tests()
    elif args.suite == "unit":
        success = runner.setup_test_environment() and runner.run_unit_tests()
    elif args.suite == "integration":
        success = runner.setup_test_environment() and runner.run_integration_tests()
    elif args.suite == "docker":
        success = runner.setup_test_environment() and runner.run_docker_tests()
    elif args.suite == "performance":
        success = runner.setup_test_environment() and runner.run_performance_tests()
    elif args.suite == "security":
        success = runner.setup_test_environment() and runner.run_security_tests()
    else:
        logger.error(f"Unknown test suite: {args.suite}")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())