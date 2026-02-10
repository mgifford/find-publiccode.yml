"""Configuration for publiccode.yml discovery and validation framework."""

import os
from typing import List

# Discovery Configuration
PATHS_TO_TEST: List[str] = [
    # PublicCode format
    "/publiccode.yml",
    "/.well-known/publiccode.yml",
    "/publiccode.yaml",
    "/.well-known/publiccode.yaml",
    # CodeMeta format (https://codemeta.github.io/)
    "/codemeta.json",
    "/.well-known/codemeta.json",
    # Code.json format (https://code.gov/)
    "/code.json",
    "/.well-known/code.json",
    # Contribute.json format (Mozilla)
    "/contribute.json",
    "/.well-known/contribute.json",
]

# HTTP Configuration
HTTPS_FIRST = True
FOLLOW_REDIRECTS = True
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 10  # seconds
MAX_FILE_SIZE = 512 * 1024  # 512 KB
USER_AGENT = "PublicCode-Research-Bot/1.0 (+https://github.com/publiccodeyml/publiccode.yml; contact: github.com/mgifford)"

# Domain Variation Testing
TEST_WWW_VARIATIONS = True  # Test both www. and non-www. versions of domains

# Concurrency Configuration
MAX_CONCURRENT_REQUESTS = 10
RATE_LIMIT_DELAY = 0.1  # seconds between requests

# Validation Configuration
VALIDATOR_PATH = os.path.expanduser("~/go/bin/publiccode-parser")
VALIDATOR_TIMEOUT = 30  # seconds

# Usefulness Criteria
USEFULNESS_CHECKS = {
    "has_description": True,
    "description_min_length": 20,
    "has_valid_license": True,
    "has_maintenance_info": True,
    "has_contact": True,
    "urls_reachable": False,  # Set to True for stricter validation (slower)
}

# Output Configuration
OUTPUT_CSV = "results.csv"
OUTPUT_JSON = "results.json"
CHECKPOINT_FILE = "checkpoint.json"
LOG_FILE = "discovery.log"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
