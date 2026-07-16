import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional


def build_stac_properties(parameters: Dict, cdse_version: Optional[str] = None) -> Dict:
    """
    Builds the STAC 'properties' block shared by both the prefect_wrapper and
    cwl_wrapper execution patterns. SOLUTION/SOLUTION_VERSION are baked into the
    algorithm image as env vars, so every wrapper reads the same contract
    instead of guessing its own image identity at runtime. cdse_version is
    fetched live from the openEO backend (openeo_util.get_backend_version).
    """
    return {
        "solution": os.getenv("SOLUTION"),
        "solutionVersion": os.getenv("SOLUTION_VERSION"),
        "cdseVersion": cdse_version,
        "inputParameters": json.dumps(parameters),
        "executionDateTime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
