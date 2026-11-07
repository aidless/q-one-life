"""Dataset loaders for Semantic Self-Consistency reproduction.

The three target splits are the public sources verified on 2026-11-07:
- AQuA-RAT test: 254 rows
- SVAMP: 1000 rows
- StrategyQA test: 687 rows
"""

from __future__ import annotations

import json
import hashlib
import urllib.request
from pathlib import Path

DATA_SOURCES = {
    "aqua_test.jsonl": {
        "url": "https://raw.githubusercontent.com/google-deepmind/AQuA/master/test.json",
        "rows": 254,
        "bytes": 130192,
        "sha256": "de41581881ef95c5588c44ddc701c77fd480839241dd422a0d181262af24520c",
        "license": "AQuA public repository distribution",
    },
    "svamp.json": {
        "url": "https://raw.githubusercontent.com/arkilpatel/SVAMP/main/SVAMP.json",
        "rows": 1000,
        "bytes": 339970,
        "sha256": "5be77703a6d891ae476d7c082787ad361392aa02453b132516cdd5f4e7934e3e",
        "license": "SVAMP public repository distribution",
    },
    "strategyqa_test.json": {
        "url": "https://huggingface.co/datasets/ChilleD/StrategyQA/resolve/main/test.json",
        "rows": 687,
        "bytes": 176993,
        "sha256": "6da41445f044a7abde29f987d3311757cd0c33e759ea6f37fa100917bf0a82b0",
        "license": "MIT (ChilleD/StrategyQA mirror)",
    },
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AQUA_PATH = DATA_DIR / "aqua_test.jsonl"
SQA_PATH = DATA_DIR / "strategyqa_test.json"
SVAMP_PATH = DATA_DIR / "svamp.json"

# --- k-shot prompts (verbatim-ish from Wei et al. 2022 tables 20/21/25) ---

AQUA_SHOT_PROMPT = """Question: Adam can make 5 dollars an hour. How much money will he make in 4 hours?
A: Adam makes $5/hour; over 4 hours = 20 dollars.
The answer is 20.

Question: A team has 5 field goals (2 pts each) and 3 three-pointers. What is their total?
A: 5 * 2 = 10; 3 * 3 = 9; total = 19.
The answer is 19.

Question: Each person eats 3 pizza slices; 7 people; pizzas have 8 slices each. How many pizzas to order?
A: 7 * 3 = 21 slices; 21 / 8 = 2.625, so 3 pizzas.
The answer is 3.

Question: Each car holds 27 people. A 4-car train holds how many?
A: 4 * 27 = 108.
The answer is 108."""

STRATEGYQA_SHOT_PROMPT = """Question: A person is in the middle of the ocean. They are wearing a life jacket. There is no land in sight. They are drowning. True or False?
A: With a life jacket, a person in the ocean is not necessarily drowning. False.
The answer is False.

Question: Monday comes after Tuesday. True or False?
A: Monday comes before Tuesday. False.
The answer is False.

Question: Two people are walking down the street. One is waving his hands. The other person is blind. True or False?
A: The blind person cannot see, so the statement is not necessarily true. False.
The answer is False.

Question: A man is sitting in a room with a dog. The dog barks at the door. The dog will not let the man leave. The man leaves the room. True or False?
A: We don't know whether the dog actually prevented him. False.
The answer is False.

Question: A person is swimming in the middle of the ocean and is not wearing a life jacket. They are drowning. True or False?
A: Without a life jacket, drowning in the middle of the ocean is true.
The answer is True.

Question: The sun rises in the west and sets in the east. True or False?
A: The sun rises in the east. False.
The answer is False."""

SVAMP_SHOT_PROMPT = """Question: Jessica has 72 apples. She puts them into 9 bags. How many apples are in each bag?
A: 72 / 9 = 8.
The answer is 8.

Question: At the arcade Joel won 3 tickets and then won 2 more. How many tickets did he have in total?
A: 3 + 2 = 5.
The answer is 5.

Question: A bakery sells 4 cookies per box. How many cookies are in 5 boxes?
A: 4 * 5 = 20.
The answer is 20.

Question: Each balloon costs $2. Five friends each buy one balloon. How much money did they spend?
A: 1 balloon = $2; 5 * $2 = $10.
The answer is 10.

Question: Mia has 6 stickers. She gives 2 to her sister. How many stickers does Mia have now?
A: 6 - 2 = 4.
The answer is 4.

Question: If 3 pencils cost $6, how much do 4 pencils cost?
A: 1 pencil = $2; 4 * $2 = $8.
The answer is 8.

Question: A farmer has 12 chickens and sells 5. How many chickens remain?
A: 12 - 5 = 7.
The answer is 7.

Question: There are 9 rows of chairs. Each row has 6 chairs. How many chairs are there?
A: 9 * 6 = 54.
The answer is 54."""

MAX_TOKENS = {
    "svamp": 250,
    "aqua_rat": 400,
    "strategyqa": 450,
}

TEMPERATURE = 0.8
TOP_P = 1.0
N_SAMPLES = 10


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line]


def _verify(path: Path) -> None:
    meta = DATA_SOURCES[path.name]
    data = path.read_bytes()
    if len(data) != meta["bytes"]:
        raise ValueError(f"{path.name}: expected {meta['bytes']} bytes, got {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != meta["sha256"]:
        raise ValueError(f"{path.name}: SHA-256 mismatch")


def load_aqua_rat_test() -> list[dict]:
    """AQuA-RAT test split (254 samples)."""
    if not AQUA_PATH.is_file():
        raise FileNotFoundError(AQUA_PATH)
    _verify(AQUA_PATH)
    raw = _load_jsonl(AQUA_PATH)
    if len(raw) != DATA_SOURCES[AQUA_PATH.name]["rows"]:
        raise ValueError("AQuA-RAT row count mismatch")
    return [{"question": r["question"], "correct": r["correct"]} for r in raw]


def load_strategyqa_test() -> list[dict]:
    """StrategyQA test split (687 samples)."""
    if not SQA_PATH.is_file():
        raise FileNotFoundError(SQA_PATH)
    _verify(SQA_PATH)
    raw = _load_json(SQA_PATH)
    if not isinstance(raw, list):
        raise ValueError("StrategyQA is not a JSON array")
    if len(raw) != DATA_SOURCES[SQA_PATH.name]["rows"]:
        raise ValueError("StrategyQA row count mismatch")
    return [
        {"question": r["question"], "correct": "true" if r["answer"] else "false"}
        for r in raw
    ]


def load_svamp_full() -> list[dict]:
    """Full SVAMP (1000 samples)."""
    if not SVAMP_PATH.is_file():
        raise FileNotFoundError(SVAMP_PATH)
    _verify(SVAMP_PATH)
    raw = _load_json(SVAMP_PATH)
    if not isinstance(raw, list):
        raise ValueError("SVAMP is not a JSON array")
    if len(raw) != DATA_SOURCES[SVAMP_PATH.name]["rows"]:
        raise ValueError("SVAMP row count mismatch")
    return [{"question": r["Question"], "correct": str(r["Answer"])} for r in raw]


def fetch_data() -> None:
    """Download and verify the three target public files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, meta in DATA_SOURCES.items():
        path = DATA_DIR / name
        if path.is_file():
            _verify(path)
            continue
        data = urllib.request.urlopen(meta["url"], timeout=60).read()
        path.write_bytes(data)
        _verify(path)


def dataset_manifest() -> list[dict]:
    return [
        {
            "file": name,
            "url": meta["url"],
            "rows": meta["rows"],
            "bytes": meta["bytes"],
            "sha256": meta["sha256"],
            "license": meta["license"],
        }
        for name, meta in DATA_SOURCES.items()
    ]
