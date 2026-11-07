import json
import sys
from src.data import class_split

if __name__ == "__main__":
    data = json.load(sys.stdin)
    print(json.dumps({"paper_id": "self-expansion", "tasks": len(class_split()), "status": "smoke_entry"}))
