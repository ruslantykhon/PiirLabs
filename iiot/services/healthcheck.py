import os
import sys
import time
from pathlib import Path

def main():
    path = Path(
        os.getenv("HEALTH_FILE") or "/tmp/healthy"
    )

    if not path.is_file():
        return 1
    age = time.time() - path.stat().st_mtime
    return 0 if age < 15 else 1

if __name__ == "__main__":
    sys.exit(main())