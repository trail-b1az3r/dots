#!/usr/bin/env python3
"""Train Summit's notification importance model: train.py [--out FILE] [--check].

Reads data.jsonl (make_data.py writes it) and fits a logistic regression with L2 over the hashed features that
dots/.config/quickshell/Summit/services/importance.js computes: node runs that very file for the features, so what is
trained is exactly what Summit scores. Prints its accuracy on a fifth of the data it did not train on and on the
hand-written holdout.jsonl, then writes the weights (assets/model/importance.json in Summit, about 40 KB).

    --check   train in memory and compare with the file in Summit; fail if they differ (the tests run this)

Needs python3 with numpy, and node.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUMMIT = ROOT / "dots/.config/quickshell/Summit"
JS = SUMMIT / "services/importance.js"
OUT = SUMMIT / "assets/model/importance.json"

# Loads importance.js (a QML JavaScript library: its ".pragma library" line is not JavaScript) and prints the hashed
# features of each notification given on stdin, one JSON array a line.
NODE = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8").replace(/^\.pragma library\s*$/m, "");
const m = { exports: {} };
vm.runInNewContext(src, { module: m, Math, JSON, Object, String, Infinity });
const lines = fs.readFileSync(0, "utf8").split("\n").filter(Boolean);
const out = [];
for (const line of lines) out.push(JSON.stringify(m.exports.hashed(m.exports.features(JSON.parse(line)))));
process.stdout.write(out.join("\n") + "\n");
"""


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def featurize(rows: list[dict]) -> list[list[list[int]]]:
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    done = subprocess.run(["node", "-e", NODE, str(JS)], input=text, capture_output=True, text=True, check=True)
    return [json.loads(line) for line in done.stdout.splitlines()]


def matrix(feats: list[list[list[int]]], buckets: int) -> np.ndarray:
    x = np.zeros((len(feats), buckets), dtype=np.float64)
    for i, row in enumerate(feats):
        for bucket, sign in row:
            x[i, bucket] += sign
    return x


def fit(x: np.ndarray, y: np.ndarray, l2: float = 1e-3, steps: int = 1500, lr: float = 0.05) -> tuple[np.ndarray, float]:
    """Full-batch Adam on the logistic loss; deterministic (no randomness at all)."""
    w = np.zeros(x.shape[1])
    b = 0.0
    m_w = np.zeros_like(w); v_w = np.zeros_like(w); m_b = v_b = 0.0
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    for t in range(1, steps + 1):
        p = 1 / (1 + np.exp(-(x @ w + b)))
        g_w = x.T @ (p - y) / len(y) + l2 * w
        g_b = float(np.mean(p - y))
        m_w = beta1 * m_w + (1 - beta1) * g_w; v_w = beta2 * v_w + (1 - beta2) * g_w ** 2
        m_b = beta1 * m_b + (1 - beta1) * g_b; v_b = beta2 * v_b + (1 - beta2) * g_b ** 2
        w -= lr * (m_w / (1 - beta1 ** t)) / (np.sqrt(v_w / (1 - beta2 ** t)) + eps)
        b -= lr * (m_b / (1 - beta1 ** t)) / (np.sqrt(v_b / (1 - beta2 ** t)) + eps)
    return w, b


def accuracy(x, y, w, b, threshold=0.5) -> float:
    p = 1 / (1 + np.exp(-(x @ w + b)))
    return float(np.mean((p >= threshold) == (y == 1)))


def train() -> tuple[dict, dict]:
    buckets = int(subprocess.run(["node", "-e", NODE.replace("const lines", "process.stdout.write(String(m.exports.BUCKETS)); process.exit(0);\nconst lines"), str(JS)],
                                 input="", capture_output=True, text=True, check=True).stdout)
    data = load(HERE / "data.jsonl")
    holdout = load(HERE / "holdout.jsonl")
    x = matrix(featurize(data), buckets)
    y = np.array([r["label"] for r in data], dtype=np.float64)
    xh = matrix(featurize(holdout), buckets)
    yh = np.array([r["label"] for r in holdout], dtype=np.float64)
    cut = len(y) * 4 // 5   # the data is shuffled already (make_data.py)
    w, b = fit(x[:cut], y[:cut])
    report = {"validation": accuracy(x[cut:], y[cut:], w, b), "holdout": accuracy(xh, yh, w, b),
              "examples": len(y), "holdout_examples": len(yh)}
    w, b = fit(x, y)   # the model that ships learns from all of it
    report["holdout_final"] = accuracy(xh, yh, w, b)
    model = {"version": 1, "buckets": buckets, "threshold": 0.5, "bias": round(float(b), 4),
             "w": [round(float(v), 4) for v in w]}
    return model, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    model, report = train()
    print(json.dumps(report))
    text = json.dumps(model, separators=(",", ":")) + "\n"
    if args.check:
        same = args.out.is_file() and args.out.read_text() == text
        print("the model in Summit matches the training" if same else "the model in Summit is out of date: run train.py")
        return 0 if same else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out} ({len(text) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
