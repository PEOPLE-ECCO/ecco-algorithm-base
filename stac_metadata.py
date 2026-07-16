import json
import os
from datetime import datetime, timezone
from typing import Dict


def build_stac_properties(parameters: Dict) -> Dict:
    """
    Builds the STAC 'properties' block shared by both the prefect_wrapper and
    cwl_wrapper execution patterns. solution/solutionVersion/cdseVersion are
    baked into the algorithm image as env vars (see ALGORITHM_BASE for the
    same build-arg -> ENV -> os.getenv() pattern), so every wrapper reads the
    same contract instead of guessing its own image identity at runtime.
    """
    return {
        "solution": os.getenv("SOLUTION"),
        "solutionVersion": os.getenv("SOLUTION_VERSION"),
        "cdseVersion": os.getenv("CDSE_VERSION"),
        "inputParameters": json.dumps(parameters),
        "executionDateTime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
