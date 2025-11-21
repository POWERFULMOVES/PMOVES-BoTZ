"""
Configuration loader for Docling MCP Server.

This module provides functionality to load configuration from YAML files,
environment variables, and command line arguments.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from .schema import Config, validate_config

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with support for YAML files and environment variables."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to 'config' directory in the same directory as this file.
        """
        if config_dir is None:
            # Default to config directory relative to this file
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)
        
        self.config_files = {
            'default': self.config_dir / 'default.yaml',
            'development': self.config_dir / 'development.yaml',
            'production': self.config_dir / 'production.yaml',
        }
    
    def load_config(
        self,
        environment: str = 'default',
        config_file: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Config:
        """Load configuration from files and environment variables.
        
        Args:
            environment: Environment name (default, development, production)
            config_file: Optional specific config file path
            overrides: Optional configuration overrides
            
        Returns:
            Loaded and validated configuration
            
        Raises:
            FileNotFoundError: If configuration file is not found
            ValueError: If configuration is invalid
        """
        # Start with empty config
        config_data = {}
        
        # Load base configuration
        if config_file:
            # Use specific config file
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            config_data = self._load_yaml_file(config_path)
        else:
            # Load environment-specific configuration
            config_data = self._load_environment_config(environment)
        
        # Apply environment variable overrides
        env_overrides = self._load_environment_variables()
        config_data = self._merge_configs(config_data, env_overrides)
        
        # Apply manual overrides
        if overrides:
            config_data = self._merge_configs(config_data, overrides)
        
        # Create configuration object
        config = Config.from_dict(config_data)
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            raise ValueError(f"Configuration validation errors: {'; '.join(errors)}")
        
        logger.info(f"Configuration loaded successfully for environment: {environment}")
        return config
    
    def _load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load configuration for specific environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Configuration dictionary
        """
        # Start with default configuration
        config_data = {}
        
        if self.config_files['default'].exists():
            config_data = self._load_yaml_file(self.config_files['default'])
        
        # Load environment-specific overrides
        env_file = self.config_files.get(environment)
        if env_file and env_file.exists():
            env_config = self._load_yaml_file(env_file)
            config_data = self._merge_configs(config_data, env_config)
            logger.info(f"Loaded environment-specific configuration: {env_file}")
        
        return config_data
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                logger.info(f"Loaded configuration from: {file_path}")
                return data or {}
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            raise
    
    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Environment variables should be prefixed with DOCLING_MCP_
        and use double underscores for nested configuration.
        
        Examples:
            DOCLING_MCP_SERVER__HOST=0.0.0.0
            DOCLING_MCP_SERVER__PORT=3020
            DOCLING_MCP_LOGGING__LEVEL=DEBUG
            DOCLING_MCP_SSE__KEEPALIVE_INTERVAL=0.5
            
        Returns:
            Configuration dictionary
        """
        overrides = {}
        prefix = "DOCLING_MCP_"
        
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = env_var[len(prefix):].lower()
                
                # Convert double underscores to nested dictionary structure
                keys = config_key.split('__')
                
                # Try to convert value to appropriate type
                converted_value = self._convert_env_value(value)
                
                # Build nested dictionary
                current = overrides
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                current[keys[-1]] = converted_value
                logger.debug(f"Loaded environment variable: {env_var} = {converted_value}")
        
        return overrides
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable value to appropriate type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Converted value
        """
        # Strip whitespace first
        value = value.strip()
        
        # Try to convert to boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try to convert to integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try to convert to list (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # Return as string
        return value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result
    
    def create_default_config(self) -> None:
        """Create default configuration file if it doesn't exist."""
        default_config = {
            'server': {
                'host': '0.0.0.0',
                'port': 3020,
                'transport': 'stdio',
                'name': 'docling-mcp'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'name': 'docling-mcp',
                'output': 'stdout'
            },
            'sse': {
                'endpoint': '/mcp',
                'keepalive_interval': 0.1,
                'connection_timeout': 30.0,
                'max_queue_size': 1000,
                'cors_origins': ['*'],
                'cors_methods': ['GET', 'OPTIONS'],
                'cors_headers': ['Content-Type', 'Accept', 'Cache-Control'],
                'cors_max_age': 86400
            },
            'performance': {
                'tool_timeout': 30.0,
                'max_connections': 100,
                'rate_limit_requests': 1000,
                'rate_limit_window': 3600
            },
            'security': {
                'enable_cors': True,
                'allowed_origins': ['*'],
                'enable_rate_limiting': False,
                'max_request_size': 10485760  # 10MB
            },
            'docling': {
                'cache_dir': '/data/cache',
                'enable_cache': True,
                'max_file_size': 104857600,  # 100MB
                'supported_formats': ['pdf', 'docx', 'pptx', 'xlsx', 'html', 'txt', 'md'],
                'pipeline_options': {}
            },
            'health_check': {
                'endpoint': '/health',
                'interval': 30,
                'timeout': 10,
                'retries': 3,
                'start_period': 30
            }
        }
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Write default configuration
        default_file = self.config_dir / 'default.yaml'
        if not default_file.exists():
            with open(default_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Created default configuration file: {default_file}")
        else:
            logger.info(f"Default configuration file already exists: {default_file}")
    
    def create_environment_templates(self) -> None:
        """Create environment-specific configuration templates."""
        # Development configuration
        dev_config = {
            'logging': {
                'level': 'DEBUG'
            },
            'performance': {
                'tool_timeout': 60.0,  # Longer timeout for development
                'max_connections': 50
            },
            'security': {
                'enable_cors': True,
                'allowed_origins': ['http://localhost:*', 'https://localhost:*']
            }
        }
        
        # Production configuration
        prod_config = {
            'logging': {
                'level': 'WARNING',
                'output': '/var/log/docling-mcp.log'
            },
            'performance': {
                'tool_timeout': 30.0,
                'max_connections': 200,
                'rate_limit_requests': 500,
                'rate_limit_window': 3600
            },
            'security': {
                'enable_cors': True,
                'allowed_origins': [],  # Specify actual origins in production
                'enable_rate_limiting': True,
                'max_request_size': 52428800  # 50MB
            },
            'health_check': {
                'interval': 60,
                'timeout': 15,
                'retries': 5
            }
        }
        
        # Write development configuration
        dev_file = self.config_dir / 'development.yaml'
        if not dev_file.exists():
            with open(dev_file, 'w', encoding='utf-8') as f:
                yaml.dump(dev_config, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Created development configuration template: {dev_file}")
        
        # Write production configuration
        prod_file = self.config_dir / 'production.yaml'
        if not prod_file.exists():
            with open(prod_file, 'w', encoding='utf-8') as f:
                yaml.dump(prod_config, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Created production configuration template: {prod_file}")


# Global configuration loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """Get global configuration loader instance.
    
    Args:
        config_dir: Optional configuration directory
        
    Returns:
        Configuration loader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader


def load_config(
    environment: str = 'default',
    config_file: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> Config:
    """Load configuration using global loader.
    
    Args:
        environment: Environment name
        config_file: Optional specific config file path
        overrides: Optional configuration overrides
        
    Returns:
        Loaded configuration
    """
    loader = get_config_loader()
    return loader.load_config(environment, config_file, overrides)