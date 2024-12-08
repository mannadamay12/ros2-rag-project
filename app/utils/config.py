import os
from pathlib import Path
from typing import Dict, Any
import yaml

class Config:
    def __init__(self, config_path: str = "./app/configs/sources.yaml"):
        self.config_path = Path(config_path)
        self._load_config()
        
    def _load_config(self) -> None:
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    @property
    def documentation_sources(self) -> Dict[str, Any]:
        return self.config.get('sources', {}).get('documentation', {})