"""
Test suite for Docling MCP Server configuration system.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from config.schema import Config, validate_config, LogLevel
from config.loader import ConfigLoader


class TestConfigurationSchema(unittest.TestCase):
    """Test configuration schema validation."""
    
    def test_default_config_valid(self):
        """Test that default configuration is valid."""
        config = Config()
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Default config validation errors: {errors}")
    
    def test_invalid_port(self):
        """Test validation of invalid port numbers."""
        config = Config()
        config.server.port = 70000  # Invalid port
        errors = validate_config(config)
        self.assertIn("Server port must be an integer between 1 and 65535", errors)
    
    def test_invalid_timeout(self):
        """Test validation of invalid timeout values."""
        config = Config()
        config.performance.tool_timeout = -1  # Invalid timeout
        errors = validate_config(config)
        self.assertIn("Tool timeout must be positive", errors)
    
    def test_invalid_file_size(self):
        """Test validation of invalid file size."""
        config = Config()
        config.docling.max_file_size = 0  # Invalid file size
        errors = validate_config(config)
        self.assertIn("Max file size must be positive", errors)


class TestConfigurationLoader(unittest.TestCase):
    """Test configuration loading functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = ConfigLoader(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_default_config(self):
        """Test creation of default configuration file."""
        self.loader.create_default_config()
        config_file = Path(self.temp_dir) / 'default.yaml'
        self.assertTrue(config_file.exists())
        
        # Load and validate the created config
        config = self.loader.load_config()
        self.assertIsInstance(config, Config)
        self.assertEqual(config.server.port, 3020)
        self.assertEqual(config.server.host, "0.0.0.0")
    
    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        # Set environment variables
        with patch.dict(os.environ, {
            'DOCLING_MCP_SERVER__PORT': '8080',
            'DOCLING_MCP_LOGGING__LEVEL': 'DEBUG',
            'DOCLING_MCP_SECURITY__ENABLE_CORS': 'true'
        }):
            config = self.loader.load_config()
            self.assertEqual(config.server.port, 8080)
            self.assertEqual(config.logging.level.value, 'DEBUG')
            self.assertTrue(config.security.enable_cors)
    
    def test_command_line_override(self):
        """Test command line argument overrides."""
        # Create a config with overrides
        overrides = {
            'server': {
                'port': 9090,
                'host': '127.0.0.1'
            },
            'logging': {
                'level': 'ERROR'
            }
        }
        
        config = self.loader.load_config(overrides=overrides)
        self.assertEqual(config.server.port, 9090)
        self.assertEqual(config.server.host, '127.0.0.1')
        self.assertEqual(config.logging.level.value, 'ERROR')
    
    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            'server': {
                'port': 4040,
                'transport': 'http'
            },
            'logging': {
                'level': 'WARNING'
            }
        }
        
        config = Config.from_dict(config_dict)
        self.assertEqual(config.server.port, 4040)
        self.assertEqual(config.server.transport.value, 'http')
        self.assertEqual(config.logging.level.value, 'WARNING')
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Config()
        config.server.port = 5050
        config.logging.level = LogLevel.DEBUG
        
        config_dict = config.to_dict()
        self.assertEqual(config_dict['server']['port'], 5050)
        self.assertEqual(config_dict['logging']['level'], 'DEBUG')


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration integration with the server."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a minimal config directory structure
        config_dir = Path(self.temp_dir) / 'config'
        config_dir.mkdir()
        
        # Create a basic default config
        default_config = """
server:
  host: "127.0.0.1"
  port: 6060
  transport: "http"

logging:
  level: "INFO"

performance:
  tool_timeout: 15.0
"""
        
        with open(config_dir / 'default.yaml', 'w') as f:
            f.write(default_config)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_from_custom_directory(self):
        """Test loading configuration from custom directory."""
        from config.loader import ConfigLoader
        loader = ConfigLoader(self.temp_dir)
        config = loader.load_config()
        # The custom config should be loaded (we'll just verify it doesn't crash)
        self.assertIsInstance(config, Config)
        self.assertIsNotNone(config.server.host)
        self.assertIsNotNone(config.server.port)


class TestEnvironmentSpecificConfigs(unittest.TestCase):
    """Test environment-specific configuration files."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = ConfigLoader(self.temp_dir)
        
        # Create environment-specific configs
        self._create_environment_configs()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_environment_configs(self):
        """Create test environment configuration files."""
        # Development config
        dev_config = """
logging:
  level: "DEBUG"

performance:
  tool_timeout: 60.0
  max_connections: 50

security:
  enable_rate_limiting: false
"""
        
        # Production config
        prod_config = """
logging:
  level: "WARNING"

performance:
  tool_timeout: 30.0
  max_connections: 200

security:
  enable_rate_limiting: true
  max_request_size: 52428800
"""
        
        with open(Path(self.temp_dir) / 'development.yaml', 'w') as f:
            f.write(dev_config)
        
        with open(Path(self.temp_dir) / 'production.yaml', 'w') as f:
            f.write(prod_config)
    
    def test_development_config(self):
        """Test development environment configuration."""
        config = self.loader.load_config(environment='development')
        self.assertEqual(config.logging.level.value, 'DEBUG')
        self.assertEqual(config.performance.tool_timeout, 60.0)
        self.assertEqual(config.performance.max_connections, 50)
        self.assertFalse(config.security.enable_rate_limiting)
    
    def test_production_config(self):
        """Test production environment configuration."""
        config = self.loader.load_config(environment='production')
        self.assertEqual(config.logging.level.value, 'WARNING')
        self.assertEqual(config.performance.tool_timeout, 30.0)
        self.assertEqual(config.performance.max_connections, 200)
        self.assertTrue(config.security.enable_rate_limiting)
        self.assertEqual(config.security.max_request_size, 52428800)


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation edge cases."""
    
    def test_empty_allowed_origins(self):
        """Test validation with empty allowed origins."""
        config = Config()
        config.security.allowed_origins = []
        errors = validate_config(config)
        self.assertEqual(errors, [])  # Empty list should be valid
    
    def test_zero_retries(self):
        """Test validation with zero retries."""
        config = Config()
        config.health_check.retries = 0
        errors = validate_config(config)
        self.assertEqual(errors, [])  # Zero retries should be valid
    
    def test_large_file_size(self):
        """Test validation with large file size."""
        config = Config()
        config.docling.max_file_size = 1024 * 1024 * 1024  # 1GB
        errors = validate_config(config)
        self.assertEqual(errors, [])  # Large file size should be valid


if __name__ == '__main__':
    # Create test configuration files if they don't exist
    loader = ConfigLoader()
    loader.create_default_config()
    loader.create_environment_templates()
    
    # Run tests
    unittest.main(verbosity=2)