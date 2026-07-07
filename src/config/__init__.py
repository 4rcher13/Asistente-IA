from .settings import ConfigView, config, validate_config, config_to_dict

# Alias retrocompatible
Config = ConfigView

__all__ = ["Config", "ConfigView", "config", "validate_config", "config_to_dict"]
