"""Run evaluation on all questions 1-10.

Usage:
    python pipeline.py openai
    python pipeline.py anthropic
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "scripts" / "run_evaluation.py"
    sys.exit(subprocess.run([sys.executable, str(script)] + sys.argv[1:], check=False).returncode)
