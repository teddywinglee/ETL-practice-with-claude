import argparse
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pipeline.extract import extract
from pipeline.transform import transform
from pipeline.load import load


def run(theme: str):
    print("=== ETL Pipeline ===")

    print("[1/3] Extracting data...")
    posts = extract()

    print("[2/3] Transforming data...")
    report_data = transform(posts)
    report_data["theme"] = theme

    print("[3/3] Loading report...")
    load(report_data)

    print("Done. Check output/report.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the ETL pipeline on data/posts.jsonl and produce an HTML report."
    )
    parser.add_argument("--theme", type=str, default="Social Media", help="Report title theme (default: Social Media)")
    args = parser.parse_args()

    run(theme=args.theme)
