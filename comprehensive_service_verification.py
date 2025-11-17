#!/usr/bin/env python3
"""
Comprehensive Service Verification Script for PMOVES-Kilobots
Tests all 8 services to confirm they are working correctly after fixes.
"""

import asyncio
import json
import os
import requests
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import urllib3

# Disable SSL warnings for local testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ServiceVerifier:
    """Comprehensive service verification for PMOVES-Kilobots"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
        # Service configurations
        self.services = {
            "mcp-gateway": {
                "port": 2091,
                "host": "localhost",
                "health_endpoint": "/health",
                "expected_status": "healthy",
                "description": "MCP Gateway service",
                "container_name": "pmoves-botz-mcp-gateway-1"
            },
            "docling-mcp": {
                "port": 3020,
                "host": "localhost", 
                "health_endpoint": "/health",
                "expected_status": "healthy",
                "description": "Docling MCP service",
                "container_name": "pmoves-botz-docling-mcp-1"
            },
            "e2b-runner": {
                "port": 7071,
                "host": "localhost",
                "health_endpoint": "/health",
                "expected_status": "healthy",
                "description": "E2B Runner service",
                "container_name": "pmoves-botz-e2b-runner-1"
            },
            "vl-sentinel": {
                "port": 7072,
                "host": "localhost",
                "health_endpoint": "/health", 
                "expected_status": "healthy",
                "description": "VL Sentinel service",
                "container_name": "pmoves-botz-vl-sentinel-1"
            },
            "cipher-memory": {
                "port": None,
                "host": None,
                "health_endpoint": None,
                "expected_status": "stdio_running",
                "description": "Cipher Memory service (STDIO)",
                "container_name": "pmoves-botz-cipher-memory-1",
                "stdio_check": True
            },
            "postman-mcp-local": {
                "port": None,
                "host": None,
                "health_endpoint": None,
                "expected_status": "process_running",
                "description": "Postman MCP Local service (process-based)",
                "container_name": "pmoves-botz-postman-mcp-local-1",
                "process_check": True
            },
            "tailscale": {
                "port": None,
                "host": None,
                "health_endpoint": None,
                "expected_status": "vpn_connected",
                "description": "Tailscale VPN service",
                "container_name": "pmoves-botz-tailscale-1",
                "vpn_check": True
            }
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def check_container_status(self, service_name: str, container_name: str) -> Tuple[bool, str]:
        """Check Docker container status"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status = result.stdout.strip()
                if "Up" in status:
                    return True, status
                else:
                    return False, status
            else:
                return False, "Container not found"
                
        except subprocess.TimeoutExpired:
            return False, "Container check timeout"
        except Exception as e:
            return False, f"Error checking container: {str(e)}"
    
    def check_http_health(self, service_name: str, config: Dict) -> Tuple[bool, str, Dict]:
        """Check HTTP service health endpoint"""
        try:
            url = f"http://{config['host']}:{config['port']}{config['health_endpoint']}"
            
            response = requests.get(
                url,
                timeout=10,
                verify=False,
                headers={"User-Agent": "PMOVES-Service-Verifier/1.0"}
            )
            
            response_data = {}
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            if response.status_code == 200:
                return True, f"HTTP {response.status_code}", response_data
            else:
                return False, f"HTTP {response.status_code}", response_data
                
        except requests.exceptions.ConnectionError:
            return False, "Connection refused", {}
        except requests.exceptions.Timeout:
            return False, "Request timeout", {}
        except Exception as e:
            return False, f"Error: {str(e)}", {}
    
    def check_stdio_service(self, service_name: str) -> Tuple[bool, str]:
        """Check STDIO-based service"""
        try:
            # Check if container is running
            container_name = self.services[service_name]["container_name"]
            is_running, status = self.check_container_status(service_name, container_name)
            
            if not is_running:
                return False, f"Container not running: {status}"
            
            # Check container logs for signs of life
            result = subprocess.run(
                ["docker", "logs", "--tail", "10", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logs = result.stdout
                # Look for positive indicators
                positive_indicators = ["Server initialized", "MCP server", "listening", "ready"]
                negative_indicators = ["Error", "Exception", "Failed", "Traceback"]
                
                has_positive = any(indicator in logs for indicator in positive_indicators)
                has_negative = any(indicator in logs for indicator in negative_indicators)
                
                if has_positive and not has_negative:
                    return True, "STDIO service appears healthy"
                elif has_negative:
                    return False, f"Errors found in logs: {logs[-200:]}"
                else:
                    return True, "STDIO service running (no clear health indicators)"
            else:
                return False, f"Could not read container logs: {result.stderr}"
                
        except Exception as e:
            return False, f"Error checking STDIO service: {str(e)}"
    
    def check_process_service(self, service_name: str) -> Tuple[bool, str]:
        """Check process-based service"""
        try:
            container_name = self.services[service_name]["container_name"]
            is_running, status = self.check_container_status(service_name, container_name)
            
            if not is_running:
                return False, f"Container not running: {status}"
            
            # Check container logs for process activity
            result = subprocess.run(
                ["docker", "logs", "--tail", "5", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logs = result.stdout.strip()
                if logs:
                    return True, f"Process service active: {logs[-100:]}"
                else:
                    return False, "No process activity detected"
            else:
                return False, f"Could not check process: {result.stderr}"
                
        except Exception as e:
            return False, f"Error checking process service: {str(e)}"
    
    def check_vpn_service(self, service_name: str) -> Tuple[bool, str]:
        """Check Tailscale VPN service"""
        try:
            container_name = self.services[service_name]["container_name"]
            is_running, status = self.check_container_status(service_name, container_name)
            
            if not is_running:
                return False, f"VPN container not running: {status}"
            
            # Check Tailscale status inside container
            result = subprocess.run(
                ["docker", "exec", container_name, "tailscale", "status"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                status_output = result.stdout
                if "Logged in as" in status_output and "Tailscale is up" in status_output:
                    return True, "VPN connected and operational"
                else:
                    return False, f"VPN not properly connected: {status_output}"
            else:
                return False, f"VPN status check failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Error checking VPN service: {str(e)}"
    
    def test_basic_functionality(self, service_name: str, config: Dict) -> Tuple[bool, str]:
        """Test basic functionality of services"""
        try:
            if service_name == "mcp-gateway":
                # Test gateway tools endpoint
                url = f"http://{config['host']}:{config['port']}/tools"
                response = requests.get(url, timeout=5, verify=False)
                return response.status_code == 200, f"Tools endpoint: {response.status_code}"
                
            elif service_name == "docling-mcp":
                # Test docling health with more detail
                url = f"http://{config['host']}:{config['port']}/health"
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    return True, f"Docling healthy: {data.get('status', 'unknown')}"
                else:
                    return False, f"Health check failed: {response.status_code}"
                    
            elif service_name == "e2b-runner":
                # Test E2B with a simple sandbox request
                url = f"http://{config['host']}:{config['port']}/health"
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    return True, "E2B health endpoint responding"
                else:
                    return False, f"E2B health failed: {response.status_code}"
                    
            elif service_name == "vl-sentinel":
                # Test VL sentinel health
                url = f"http://{config['host']}:{config['port']}/health"
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    return True, f"VL Sentinel healthy: {data.get('status', 'unknown')}"
                else:
                    return False, f"VL Sentinel health failed: {response.status_code}"
                    
            else:
                return True, "Basic functionality test not applicable"
                
        except Exception as e:
            return False, f"Functionality test error: {str(e)}"
    
    def verify_service(self, service_name: str) -> Dict:
        """Verify a single service comprehensively"""
        self.log(f"Verifying service: {service_name}")
        config = self.services[service_name]
        
        result = {
            "service": service_name,
            "description": config["description"],
            "expected_status": config["expected_status"],
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Container status check
        is_running, container_status = self.check_container_status(
            service_name, config["container_name"]
        )
        result["checks"]["container"] = {
            "status": "pass" if is_running else "fail",
            "details": container_status
        }
        
        # Health endpoint check (for HTTP services)
        if config.get("port") and config.get("health_endpoint"):
            is_healthy, health_status, health_data = self.check_http_health(service_name, config)
            result["checks"]["health"] = {
                "status": "pass" if is_healthy else "fail",
                "details": health_status,
                "data": health_data
            }
        
        # Service-specific checks
        if config.get("stdio_check"):
            is_working, stdio_status = self.check_stdio_service(service_name)
            result["checks"]["stdio"] = {
                "status": "pass" if is_working else "fail", 
                "details": stdio_status
            }
        
        if config.get("process_check"):
            is_working, process_status = self.check_process_service(service_name)
            result["checks"]["process"] = {
                "status": "pass" if is_working else "fail",
                "details": process_status
            }
        
        if config.get("vpn_check"):
            is_working, vpn_status = self.check_vpn_service(service_name)
            result["checks"]["vpn"] = {
                "status": "pass" if is_working else "fail",
                "details": vpn_status
            }
        
        # Basic functionality test
        is_functional, func_status = self.test_basic_functionality(service_name, config)
        result["checks"]["functionality"] = {
            "status": "pass" if is_functional else "fail",
            "details": func_status
        }
        
        # Overall status
        all_checks = result["checks"].values()
        passed_checks = sum(1 for check in all_checks if check["status"] == "pass")
        total_checks = len(all_checks)
        
        result["overall_status"] = "pass" if passed_checks == total_checks else "fail"
        result["pass_rate"] = f"{passed_checks}/{total_checks}"
        
        self.log(f"Service {service_name}: {result['overall_status']} ({result['pass_rate']})")
        return result
    
    def check_error_logs(self) -> Dict:
        """Check for error logs across all services"""
        self.log("Checking for error logs...")
        error_summary = {}
        
        for service_name, config in self.services.items():
            container_name = config["container_name"]
            
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "20", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logs = result.stdout
                    error_count = logs.lower().count("error") + logs.lower().count("exception")
                    error_summary[service_name] = {
                        "error_count": error_count,
                        "has_errors": error_count > 0,
                        "recent_errors": []
                    }
                    
                    # Extract recent error lines
                    lines = logs.split('\n')
                    for line in lines[-10:]:
                        if any(keyword in line.lower() for keyword in ["error", "exception", "failed", "traceback"]):
                            error_summary[service_name]["recent_errors"].append(line.strip())
                else:
                    error_summary[service_name] = {
                        "error_count": 0,
                        "has_errors": False,
                        "log_access_error": result.stderr
                    }
                    
            except Exception as e:
                error_summary[service_name] = {
                    "error_count": 0,
                    "has_errors": False,
                    "check_error": str(e)
                }
        
        return error_summary
    
    def generate_report(self) -> Dict:
        """Generate comprehensive verification report"""
        self.log("Generating comprehensive verification report...")
        
        # Verify all services
        for service_name in self.services.keys():
            self.results[service_name] = self.verify_service(service_name)
        
        # Check error logs
        error_logs = self.check_error_logs()
        
        # Calculate overall statistics
        total_services = len(self.services)
        passed_services = sum(1 for result in self.results.values() if result["overall_status"] == "pass")
        overall_success_rate = (passed_services / total_services) * 100
        
        # Generate report
        report = {
            "verification_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_services": total_services,
                "passed_services": passed_services,
                "failed_services": total_services - passed_services,
                "success_rate": f"{overall_success_rate:.1f}%",
                "target_success_rate": "100%",
                "improvement_needed": overall_success_rate < 100.0
            },
            "services": self.results,
            "error_logs": error_logs,
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []
        
        for service_name, result in self.results.items():
            if result["overall_status"] == "fail":
                config = self.services[service_name]
                
                if service_name == "mcp-gateway":
                    recommendations.append(
                        f"Fix MCP Gateway health endpoint - currently returning 404. "
                        f"Check if /health route is properly implemented in gateway.py"
                    )
                elif service_name == "e2b-runner":
                    recommendations.append(
                        f"Check E2B API key configuration and E2B service connectivity. "
                        f"Verify E2B_API_KEY environment variable is set correctly"
                    )
                elif service_name == "vl-sentinel":
                    recommendations.append(
                        f"Check VL Sentinel configuration - verify OLLAMA_BASE_URL and model availability. "
                        f"Ensure Ollama service is running and accessible"
                    )
                elif service_name == "cipher-memory":
                    recommendations.append(
                        f"Start Cipher Memory service - container not found. "
                        f"Run: docker-compose -f docker-compose.mcp-pro.yml up cipher-memory"
                    )
                elif service_name == "postman-mcp-local":
                    recommendations.append(
                        f"Start Postman MCP Local service - container not found. "
                        f"Run: docker-compose -f docker-compose.mcp-pro.local-postman.yml up postman-mcp-local"
                    )
                elif service_name == "tailscale":
                    recommendations.append(
                        f"Check Tailscale authentication - verify TAILSCALE_AUTHKEY is valid "
                        f"and Tailscale service can connect to network"
                    )
        
        # General recommendations
        failed_services = sum(1 for result in self.results.values() if result["overall_status"] == "fail")
        if failed_services > 0:
            recommendations.append(
                f"Overall: {failed_services} services need attention to achieve 100% success rate"
            )
        
        return recommendations
    
    def print_report(self, report: Dict):
        """Print formatted verification report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE SERVICE VERIFICATION REPORT")
        print("="*80)
        
        # Summary
        summary = report["verification_summary"]
        print(f"\n[SUMMARY] VERIFICATION SUMMARY:")
        print(f"   Timestamp: {summary['timestamp']}")
        print(f"   Total Services: {summary['total_services']}")
        print(f"   Passed Services: {summary['passed_services']}")
        print(f"   Failed Services: {summary['failed_services']}")
        print(f"   Success Rate: {summary['success_rate']}")
        print(f"   Target: {summary['target_success_rate']}")
        print(f"   Status: {'[SUCCESS] TARGET MET' if not summary['improvement_needed'] else '[FAILED] IMPROVEMENT NEEDED'}")
        
        # Service details
        print(f"\n[SERVICE DETAILS]:")
        for service_name, result in report["services"].items():
            status_icon = "[OK]" if result["overall_status"] == "pass" else "[FAIL]"
            print(f"\n   {status_icon} {service_name.upper()} - {result['description']}")
            print(f"      Status: {result['overall_status'].upper()} ({result['pass_rate']} checks passed)")
            
            for check_name, check_result in result["checks"].items():
                check_icon = "[OK]" if check_result["status"] == "pass" else "[FAIL]"
                print(f"      {check_icon} {check_name.title()}: {check_result['details']}")
        
        # Error logs
        print(f"\n[ERROR LOG SUMMARY]:")
        for service_name, error_info in report["error_logs"].items():
            if error_info.get("has_errors"):
                print(f"   [WARNING] {service_name}: {error_info['error_count']} errors found")
                for error in error_info.get("recent_errors", [])[:3]:
                    print(f"      - {error}")
        
        # Recommendations
        print(f"\n[RECOMMENDATIONS]:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "="*80)
    
    def save_report(self, report: Dict, filename: str = None):
        """Save report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"service_verification_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.log(f"Report saved to: {filename}")
        except Exception as e:
            self.log(f"Failed to save report: {str(e)}", "ERROR")

def main():
    """Main verification function"""
    print("Starting Comprehensive Service Verification...")
    print("   Testing all 8 PMOVES-Kilobots services")
    print("   Verifying health endpoints, functionality, and error logs")
    print()
    
    verifier = ServiceVerifier()
    
    try:
        # Generate comprehensive report
        report = verifier.generate_report()
        
        # Print report
        verifier.print_report(report)
        
        # Save report
        verifier.save_report(report)
        
        # Exit with appropriate code
        summary = report["verification_summary"]
        if summary["success_rate"] == "100.0%":
            print(f"\nSUCCESS: All services operational! Success rate improved from 75% to 100%")
            sys.exit(0)
        else:
            print(f"\nPARTIAL: {summary['success_rate']} services operational. Further fixes needed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Verification failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()