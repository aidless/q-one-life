import json
import sys
from src.utils import modal_answer, parse_answer

if __name__ == "__main__":
    data = json.load(sys.stdin)
    answers = data.get("datasets", {}).get("answers", [])
    responses = data.get("datasets", {}).get("responses", [])
    print(json.dumps({"paper_id": "semantic-self-consistency", "chosen": modal_answer(answers), "parsed": [parse_answer(r) for r in responses], "status": "smoke_entry"}))
