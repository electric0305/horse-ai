from pathlib import Path

def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    sample_dir = data_dir / "sample"

    print(f"Project root   : {project_root}")
    print(f"data           : {data_dir}")
    print(f"data/raw       : {raw_dir}")
    print(f"data/processed : {processed_dir}")
    print(f"data/sample    : {sample_dir}")

    # 動作確認用に、小さなダミーファイルを書いてみる
    sample_file = sample_dir / "dummy_sample.txt"
    sample_file.write_text("This is a dummy sample file.\n", encoding="utf-8")
    print(f"Created sample file: {sample_file}")

if __name__ == "__main__":
    main()