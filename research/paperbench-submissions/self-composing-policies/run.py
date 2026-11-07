import json
import sys
from src.agent import CompoNetAgent

if __name__ == "__main__":
    data = json.load(sys.stdin)
    agent = CompoNetAgent(n_actions=6)
    agent.add_module()
    print(json.dumps({"paper_id": "self-composing-policies", "modules": agent.parameter_accounting()["n_modules"], "status": "smoke_entry"}))
