"""Dataset loaders for Semantic Self-Consistency reproduction.

- load_aqua_rat_test(): 254-sample test split
- load_strategyqa_test(): 687-sample test split
- load_svamp_full(): full 1000-sample set (train + dev + test)
- fetch_data(): downloads datasets from HuggingFace if not already present
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AQUA_PATH = DATA_DIR / "AQuA-RAT.json"
SQA_PATH = DATA_DIR / "StrategyQA.jsonl"
SVAMP_PATH = DATA_DIR / "SVAMP.jsonl"

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


def load_aqua_rat_test() -> list[dict]:
    """AQuA-RAT test split (254 samples)."""
    raw = _load_json(AQUA_PATH)
    return [{"question": r["question"], "correct": r["answer"]} for r in raw]


def load_strategyqa_test() -> list[dict]:
    """StrategyQA test split (687 samples)."""
    raw = _load_jsonl(SQA_PATH)
    return [
        {"question": r["question"], "correct": "yes" if r["answer"] else "no"}
        for r in raw
    ]


def load_svamp_full() -> list[dict]:
    """Full SVAMP (1000 samples)."""
    raw = _load_jsonl(SVAMP_PATH)
    return [{"question": r["question"], "correct": r["answer"]} for r in raw]


def fetch_data() -> None:
    """Download datasets from HuggingFace if not already present."""
    from datasets import load_dataset
    if not AQUA_PATH.exists():
        aqua = load_dataset("lukebarousse/data_aqua_rat", split="test")
        AQUA_PATH.write_text(json.dumps([dict(r) for r in aqua]), encoding="utf-8")
    if not SQA_PATH.exists():
        sq = load_dataset("boolq/StrategyQA", split="test")
        SQA_PATH.write_text("\n".join(json.dumps(dict(r)) for r in sq), encoding="utf-8")
    if not SVAMP_PATH.exists():
        sv = load_dataset("deepmind/svamp", split="train")
        SVAMP_PATH.write_text("\n".join(json.dumps(dict(r)) for r in sv), encoding="utf-8")
