from pathlib import Path

import yaml

from common.variables import MODELS_MAPPING, GEO_MAPPING


class Mapper:
    def __init__(self, service: str):
        with open(Path(service) / MODELS_MAPPING, 'r') as f:
            self.models = yaml.safe_load(f)
        with open(Path(service) / GEO_MAPPING, 'r') as f:
            self.regions = yaml.safe_load(f)
