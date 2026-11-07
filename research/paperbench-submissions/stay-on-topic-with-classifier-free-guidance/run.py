import json
import sys
from src.core import run

if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin))))
