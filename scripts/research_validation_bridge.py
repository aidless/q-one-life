"""Relay public pilot prompts between cloud files and the local model gateway."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--mailbox", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--model", default="kiro/deepseek-3.2")
    parser.add_argument("--max-calls", type=int, default=216)
    parser.add_argument("--max-seconds", type=int, default=1800)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    base = ["ssh", "-p", str(args.port), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", args.host]
    args.log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    calls = 0
    seen = set()
    poll = """
import json,pathlib,sys
root=pathlib.Path(sys.argv[1])
pending=[]
for path in sorted(root.glob('*.request.json')):
 identifier=path.name.split('.')[0]
 if not (root/(identifier+'.response.json')).exists():
  pending.append({'id':identifier,'request':json.loads(path.read_text())})
print(json.dumps({'pending':pending,'done':(pathlib.Path(sys.argv[2])/'summary.json').is_file()}))
"""
    deliver = """
import json,pathlib,sys
root=pathlib.Path(sys.argv[1])
for entry in json.load(sys.stdin):
 target=root/(entry['id']+'.response.json')
 temporary=target.with_suffix('.tmp')
 temporary.write_text(json.dumps(entry['response']))
 temporary.replace(target)
"""

    def ask(entry):
        request = entry["request"]
        if (
            not re.fullmatch(r"[0-9a-f]{32}", entry["id"])
            or request.get("model") != args.model
            or request.get("max_tokens", 0) > 1100
            or set(request) - {"model", "messages", "temperature", "max_tokens"}
        ):
            raise ValueError("invalid bridge request")
        start = time.monotonic()
        try:
            raw = json.dumps(request).encode()
            connection = urllib.request.Request(
                "http://127.0.0.1:3425/v1/chat/completions", data=raw,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(connection, timeout=55) as response:
                payload = json.load(response)
        except Exception as exc:
            payload = {"error_type": type(exc).__name__}
        with args.log.open("a") as handle:
            handle.write(json.dumps({
                "id": entry["id"], "elapsed_sec": time.monotonic() - start,
                "error_type": payload.get("error_type"), "usage": payload.get("usage"),
            }) + "\n")
        return {"id": entry["id"], "response": payload}

    while time.monotonic() - started < args.max_seconds:
        command = "python3 -c " + shlex.quote(poll) + " " + shlex.quote(args.mailbox) + " " + shlex.quote(args.output_root)
        completed = subprocess.run(base + [command], capture_output=True, text=True, timeout=20, check=True)
        payload = json.loads(completed.stdout)
        if payload["done"]:
            print(json.dumps({"state": "completed", "calls": calls}))
            return 0
        pending = [entry for entry in payload["pending"] if entry["id"] not in seen]
        if pending:
            if calls + len(pending) > args.max_calls:
                raise RuntimeError("bridge model-call budget reached")
            with ThreadPoolExecutor(max_workers=3) as pool:
                answers = list(pool.map(ask, pending))
            command = "python3 -c " + shlex.quote(deliver) + " " + shlex.quote(args.mailbox)
            subprocess.run(base + [command], input=json.dumps(answers), text=True, capture_output=True, check=True, timeout=20)
            seen.update(entry["id"] for entry in pending)
            calls += len(pending)
            print(json.dumps({"state": "running", "calls": calls}), flush=True)
        else:
            time.sleep(2)
    raise RuntimeError("bridge wall-time limit reached")


if __name__ == "__main__":
    raise SystemExit(main())
