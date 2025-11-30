# -*- coding: utf-8 -*-
"""
race_result.csv から horse_id / jockey_id / trainer_id の
ユニーク値を抽出して 1列CSV を3つ出力します。
出力先は入力CSVと同じフォルダになります。
"""

import csv
import os
import argparse

# --- ここを追加：スクリプト場所から既定入力パスを作る ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_INPUT = os.path.join(PROJ_ROOT, "horse_ai_scrapy", "data", "race_result.csv")

def detect_idx(header: list[str]) -> tuple[int, int, int]:
    """ヘッダ行から列位置を推定（0始まり）。"""
    name_to_idx = {name: i for i, name in enumerate(header)}

    def find(candidates: list[str], fallback_idx: int) -> int:
        for n in candidates:
            if n in name_to_idx:
                return name_to_idx[n]
        return fallback_idx

    horse_idx   = find(["horse_id"], 3)                 # 4項目目
    jockey_idx  = find(["jockey_id"], 5)    # 6項目目（綴りゆれ対応）
    trainer_idx = find(["trainer_id"], 6)               # 7項目目
    return horse_idx, jockey_idx, trainer_idx

def sort_keys(values: set[str]) -> list[str]:
    if not values:
        return []
    all_digit = all(v.isdigit() for v in values)
    return sorted(values, key=(lambda x: int(x)) if all_digit else None)

def export_unique_ids(in_path: str, write_header: bool = True) -> None:
    out_base = os.path.dirname(os.path.abspath(in_path)) or "."
    horses, jockeys, trainers = set(), set(), set()

    with open(in_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise RuntimeError("空のCSVです: " + in_path)

        h_idx, j_idx, t_idx = detect_idx(header)
        max_idx = max(h_idx, j_idx, t_idx)

        for row in reader:
            if not row or len(row) <= max_idx:
                continue
            horse_id   = row[h_idx].strip()
            jockey_id  = row[j_idx].strip()
            trainer_id = row[t_idx].strip()
            if horse_id:   horses.add(horse_id)
            if jockey_id:  jockeys.add(jockey_id)
            if trainer_id: trainers.add(trainer_id)

    files = [
        ("horse_id.csv",   "horse_id",   sort_keys(horses)),
        ("jockey_id.csv",  "jockey_id",  sort_keys(jockeys)),
        ("trainer_id.csv", "trainer_id", sort_keys(trainers)),
    ]
    for fname, header_name, values in files:
        out_path = os.path.join(out_base, fname)
        with open(out_path, "w", newline="", encoding="utf-8") as wf:
            if write_header:
                wf.write(header_name + "\n")
            for v in values:
                wf.write(v + "\n")
        print(f"Wrote {out_path} ({len(values)}件)")

def main():
    ap = argparse.ArgumentParser(description="race_result.csv からユニークID一覧を出力します。")
    ap.add_argument(
        "input_csv",
        nargs="?",
        default=DEFAULT_INPUT,  # ← ここが scripts/ 配下でも安全
        help=f"入力CSVのパス（既定: {DEFAULT_INPUT}）",
    )
    ap.add_argument("--no-header", action="store_true", help="出力CSVにヘッダ行を付けない")
    args = ap.parse_args()

    print(f"[INFO] input = {os.path.abspath(args.input_csv)}")
    export_unique_ids(args.input_csv, write_header=not args.no_header)

if __name__ == "__main__":
    main()