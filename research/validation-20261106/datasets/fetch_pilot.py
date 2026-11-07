import argparse
import hashlib
import json
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent
TOTAL_LIMIT = 32 * 1024 * 1024
FILE_LIMIT = 4 * 1024 * 1024
METADATA_LIMIT = 8 * 1024 * 1024
REPOS = {
    "peerread": ("allenai/PeerRead", "9bb37751781a900cee9e74ec3105997732c8e8e5"),
    "ridar": ("THU-KEG/RIDAR", "86aff63bc72dcbb4899aa04102fd9fd9df233dd7"),
    "paperbench": ("openai/frontier-evals", "b78dab1da774a6456b1ed9c48c9ff194ee3ff36d"),
    "sklearn": ("scikit-learn/scikit-learn", "6e37063f7ab7ef7a7e257b9d44bc3ec6ee1b1bcd"),
}
HF_REVISION = "5ca10637e5a74fc20643000b799551b0a27cd92b"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


class Capture:
    def __init__(self, root):
        self.root = root.resolve()
        if not self.root.is_relative_to(ROOT):
            raise ValueError("Output must remain inside the authorized datasets directory")
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.root / "downloads.json"
        self.ledger = (
            json.loads(self.ledger_path.read_text())
            if self.ledger_path.exists()
            else {"schema_version": "qone-dataset-downloads-v1", "files": [], "failures": []}
        )

    def fetch(self, url, local_path, dataset, role, revision="unknown", split="not_applicable",
              git_blob_sha1=None, limit=FILE_LIMIT, expected_sha256=None):
        destination = (self.root / local_path).resolve()
        if not destination.is_relative_to(self.root):
            raise ValueError("Invalid output path")
        for record in self.ledger["files"]:
            if record["path"] == local_path:
                if record["source_url"] != url:
                    raise ValueError("Refusing to replace an existing source")
                payload = destination.read_bytes()
                if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    raise ValueError("Existing raw file hash mismatch")
                return payload
        if destination.exists():
            raise ValueError("Refusing to overwrite an unregistered existing file")
        used_bytes = sum(record["bytes"] for record in self.ledger["files"])
        limit = min(limit, TOTAL_LIMIT - used_bytes)
        if limit <= 0:
            raise ValueError("Total download size limit reached")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".part")
        started = utc_now()
        transport = "urllib"
        result = None
        if "huggingface.co" not in url:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "qone-public-dataset-audit"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = response.read(limit + 1)
                    if len(payload) > limit:
                        raise ValueError("Response exceeds file limit")
                    temporary.write_bytes(payload)
                    result = SimpleNamespace(returncode=0, stdout=str(response.status).encode())
            except Exception as error:
                self.ledger["failures"].append({
                    "source_url": url, "path": local_path, "dataset": dataset,
                    "attempted_at_utc": started, "transport": transport,
                    "error_type": type(error).__name__,
                    "http_status": getattr(error, "code", "unknown"),
                    "raw_response_saved": False,
                })
        if result is None:
            transport = "curl"
            result = subprocess.run(
            ["curl", "--silent", "--show-error", "--fail", "--location",
             "--proto", "=https", "--proto-redir", "=https",
             "--connect-timeout", "12", "--max-time", "40",
             "--max-filesize", str(limit), "--user-agent", "qone-public-dataset-audit",
             "--output", str(temporary), "--write-out", "%{http_code}", url],
            capture_output=True,
            )
        if result.returncode:
            temporary.unlink(missing_ok=True)
            self.ledger["failures"].append({
                "source_url": url, "path": local_path, "dataset": dataset,
                "attempted_at_utc": started, "curl_exit_code": result.returncode,
                "http_status": result.stdout.decode(errors="replace"),
                "raw_response_saved": False,
            })
            write_json(self.ledger_path, self.ledger)
            print(json.dumps({"failed": local_path, "curl_exit_code": result.returncode}), flush=True)
            return None
        payload = temporary.read_bytes()
        if len(payload) > limit:
            temporary.unlink()
            raise ValueError("Downloaded body exceeds bound")
        blob_sha1 = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        if git_blob_sha1 and blob_sha1 != git_blob_sha1:
            temporary.unlink()
            raise ValueError("Downloaded bytes differ from the pinned Git tree")
        if expected_sha256 and hashlib.sha256(payload).hexdigest() != expected_sha256:
            temporary.unlink()
            raise ValueError("Materialized LFS bytes differ from the pointer")
        temporary.replace(destination)
        record = {
            "dataset": dataset, "role": role, "path": local_path, "source_url": url,
            "revision": revision, "split": split, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "download_started_at_utc": started, "downloaded_at_utc": utc_now(),
            "http_status": int(result.stdout),
            "transport": transport,
            "git_blob_sha1": blob_sha1 if git_blob_sha1 else "not_checked",
            "expected_git_blob_sha1": git_blob_sha1 or "unknown",
            "expected_sha256": expected_sha256 or "unknown",
            "per_file_limit_bytes": limit,
        }
        self.ledger["files"].append(record)
        write_json(self.ledger_path, self.ledger)
        print(json.dumps({"captured": local_path, "bytes": len(payload)}), flush=True)
        return payload

    def github_tree(self, dataset):
        repo, revision = REPOS[dataset]
        self.fetch(
            f"https://api.github.com/repos/{repo}/commits/{revision}",
            f"raw/metadata/{dataset}-commit.json", dataset, "revision_metadata", revision,
        )
        payload = self.fetch(
            f"https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1",
            f"raw/metadata/{dataset}-tree.json", dataset, "file_inventory", revision,
            limit=METADATA_LIMIT,
        )
        if payload is None:
            raise ValueError("Pinned source tree could not be fetched")
        tree = json.loads(payload)
        if tree.get("truncated") or tree["sha"] is None:
            raise ValueError("Incomplete source inventory")
        return {row["path"]: row for row in tree["tree"] if row["type"] == "blob"}

    def github_file(self, dataset, tree, path, role, split="not_applicable"):
        repo, revision = REPOS[dataset]
        return self.fetch(
            f"https://raw.githubusercontent.com/{repo}/{revision}/{quote(path)}",
            f"raw/{dataset}/{path}", dataset, role, revision, split,
            git_blob_sha1=tree[path]["sha"],
        )


def acquire(root, only=None):
    capture = Capture(root)
    for dataset in only or REPOS:
        tree = capture.github_tree(dataset)
        if dataset == "peerread":
            paths = ["README.md", "code/models/Review.py", "code/aspect_predict/assign_annot_iclr_2017.py"]
            paths += [
                path for path in tree
                if path.startswith("data/iclr_2017/") and "readme" in path.lower()
            ]
            for path in paths:
                capture.github_file(dataset, tree, path, "documentation")
            for split in ["train", "dev", "test"]:
                prefix = f"data/iclr_2017/{split}/reviews/"
                candidates = sorted(path for path in tree if path.startswith(prefix) and path.endswith(".json"))
                rejected_ids = {
                    "train": {"520", "550", "600", "680"},
                    "dev": {"537", "598", "663", "689"},
                    "test": {"518", "566", "611", "648"},
                }[split]
                quotas = {"true": 6, "false": 4}
                paired = {"true": 0, "false": 0}
                for path in candidates:
                    paper_id = Path(path).stem
                    cached = (root / "raw/peerread" / path).exists()
                    if not cached and paper_id not in rejected_ids and paired["true"] >= quotas["true"]:
                        continue
                    if paper_id in rejected_ids and not cached and paired["false"] >= quotas["false"]:
                        continue
                    parsed_path = path.replace("/reviews/", "/parsed_pdfs/").replace(".json", ".pdf.json")
                    if parsed_path not in tree:
                        continue
                    review_payload = capture.github_file(dataset, tree, path, "human_reviews", split)
                    if not review_payload:
                        continue
                    decision = str(json.loads(review_payload).get("accepted")).lower()
                    if decision not in quotas:
                        continue
                    if paper_id not in rejected_ids and paired[decision] >= quotas[decision]:
                        continue
                    reviews = json.loads(review_payload).get("reviews", [])
                    if not any(
                        type(review.get("RECOMMENDATION")) in (int, float)
                        and re.fullmatch(r"ICLR 2017 conference AnonReviewer[0-9]+", review.get("OTHER_KEYS", ""))
                        and not review.get("IS_META_REVIEW", False)
                        and review.get("comments")
                        for review in reviews
                    ):
                        continue
                    parsed = capture.github_file(dataset, tree, parsed_path, "full_parsed_paper", split)
                    if parsed:
                        paired[decision] += 1
                    if paper_id in rejected_ids and parsed:
                        rejected_ids.remove(paper_id)
                    if all(paired[key] >= quotas[key] for key in quotas) and not rejected_ids:
                        break
            capture.fetch(
                "https://api.openreview.net/invitations?id=ICLR.cc%2F2017%2Fconference%2F-%2Freview",
                "raw/peerread/openreview-2017-review-invitation.json", dataset, "score_scale",
            )
            capture.fetch(
                "https://aclanthology.org/N18-1149.pdf",
                "raw/peerread/peerread-N18-1149.pdf", dataset, "score_scale_paper", "N18-1149",
            )
        elif dataset == "ridar":
            for path in ["README.md", "LICENSE", "core/detector/taxonomy.py"]:
                capture.github_file(dataset, tree, path, "license" if path == "LICENSE" else "documentation")
            capture.fetch(
                "https://arxiv.org/abs/2610.31372v1", "raw/ridar/arxiv-2610.31372v1.html",
                dataset, "paper_identity", "2610.31372v1",
            )
            capture.fetch(
                f"https://huggingface.co/api/datasets/THU-KEG/RIDAR/revision/{HF_REVISION}",
                "raw/metadata/ridar-hf.json", dataset, "dataset_metadata", HF_REVISION,
            )
            for path, role in [("README.md", "dataset_card"), ("riv-gold/annotations.jsonl", "human_annotations")]:
                capture.fetch(
                    f"https://huggingface.co/datasets/THU-KEG/RIDAR/resolve/{HF_REVISION}/{path}",
                    f"raw/ridar-hf/{path}", dataset, role, HF_REVISION, "RIV-Gold",
                )
            gold_tree = capture.fetch(
                f"https://huggingface.co/api/datasets/THU-KEG/RIDAR/tree/{HF_REVISION}/riv-gold/trajectories?recursive=true&limit=1000",
                "raw/metadata/ridar-gold-tree.json", dataset, "trajectory_inventory", HF_REVISION,
                "RIV-Gold", limit=METADATA_LIMIT,
            )
            if gold_tree:
                candidates = [
                    row for row in json.loads(gold_tree)
                    if row["type"] == "file" and row["path"].endswith("/trace.jsonl")
                    and row["size"] <= 2 * 1024 * 1024
                ]
                for row in sorted(candidates, key=lambda item: (item["size"], item["path"]))[:2]:
                    capture.fetch(
                        f"https://huggingface.co/datasets/THU-KEG/RIDAR/resolve/{HF_REVISION}/{quote(row['path'])}",
                        "raw/ridar-hf/" + row["path"], dataset, "complete_trajectory",
                        HF_REVISION, "RIV-Gold", expected_sha256=(row.get("lfs") or {}).get("oid"),
                    )
        elif dataset == "paperbench":
            for path in ["LICENSE", "LICENSE.md", "project/paperbench/LICENSE",
                         "project/paperbench/LICENSE.md", "project/paperbench/README.md",
                         "project/paperbench/data/splits.json", "project/paperbench/data/splits/dev.txt",
                         "project/paperbench/paperbench/paper.py", ".gitattributes",
                         "project/paperbench/experiments/splits/all.txt",
                         "project/paperbench/experiments/splits/dev.txt",
                         "project/paperbench/experiments/splits/testing.txt",
                         "project/paperbench/experiments/splits/debug.txt",
                         "project/paperbench/experiments/splits/lite.txt",
                         "project/paperbench/experiments/splits/human.txt"]:
                if path in tree:
                    capture.github_file(dataset, tree, path, "license" if "LICENSE" in path else "documentation")
            prefix = "project/paperbench/data/papers/semantic-self-consistency/"
            for path in sorted(tree):
                if path.startswith(prefix) and "/" not in path[len(prefix):] and path.endswith((".json", ".yaml", ".md")):
                    payload = capture.github_file(dataset, tree, path, "benchmark_task", "unknown")
                    if payload and payload.startswith(b"version https://git-lfs.github.com/spec/v1"):
                        expected = re.search(rb"oid sha256:([0-9a-f]{64})", payload).group(1).decode()
                        size = int(re.search(rb"size (\d+)", payload).group(1))
                        if size <= FILE_LIMIT:
                            repo, revision = REPOS[dataset]
                            capture.fetch(
                                f"https://media.githubusercontent.com/media/{repo}/{revision}/{path}",
                                "raw/paperbench/materialized/" + Path(path).name, dataset,
                                "benchmark_task_materialized", revision, "unknown", expected_sha256=expected,
                            )
            path = "project/paperbench/data/judge_eval/semantic-self-consistency/0/grading/expected_result.json"
            if path in tree:
                capture.github_file(dataset, tree, path, "judge_validation_labels", "JudgeEval")
            capture.fetch(
                "https://arxiv.org/abs/2504.01848v1", "raw/paperbench/arxiv-2504.01848v1.html",
                dataset, "paper_identity", "2504.01848v1",
            )
        else:
            for path in [
                "COPYING", "sklearn/datasets/_base.py",
                "sklearn/datasets/data/breast_cancer.csv", "sklearn/datasets/data/wine_data.csv",
                "sklearn/datasets/data/diabetes_data_raw.csv.gz", "sklearn/datasets/data/diabetes_target.csv.gz",
                "sklearn/datasets/descr/breast_cancer.rst", "sklearn/datasets/descr/wine_data.rst",
                "sklearn/datasets/descr/diabetes.rst",
            ]:
                capture.github_file(dataset, tree, path, "license" if path == "COPYING" else (
                    "task_data" if "/data/" in path else "documentation"), "unsplit")
            for identifier, slug in [(17, "breast+cancer+wisconsin+diagnostic"), (109, "wine")]:
                capture.fetch(
                    f"https://archive.ics.uci.edu/api/dataset?id={identifier}",
                    f"raw/uci/{identifier}-metadata.json", dataset, "upstream_metadata",
                )
                capture.fetch(
                    f"https://archive.ics.uci.edu/dataset/{identifier}/{slug}",
                    f"raw/uci/{identifier}-page.html", dataset, "upstream_license",
                )
                capture.fetch(
                    f"https://archive.ics.uci.edu/static/public/{identifier}/data.csv",
                    f"raw/uci/{identifier}-data.csv", dataset, "upstream_task_data", split="unsplit",
                )
    return capture


def verify(root):
    ledger = json.loads((root / "downloads.json").read_text())
    checked_bytes = 0
    for record in ledger["files"]:
        payload = (root / record["path"]).read_bytes()
        if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError("Raw hash/size mismatch: " + record["path"])
        if len(payload) > record["per_file_limit_bytes"]:
            raise ValueError("File bound violated")
        checked_bytes += len(payload)
    if checked_bytes > TOTAL_LIMIT:
        raise ValueError("Total bound violated")
    print(json.dumps({"raw_files_verified": len(ledger["files"]), "raw_bytes": checked_bytes,
                      "total_limit_bytes": TOTAL_LIMIT, "status": "pass"}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fetch", "verify"])
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--only", nargs="+", choices=list(REPOS))
    args = parser.parse_args()
    if args.action == "fetch":
        acquire(args.output, args.only)
    verify(args.output)


if __name__ == "__main__":
    main()
