import argparse
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pipeline.generate import generate
from pipeline.extract import extract
from pipeline.transform import transform
from pipeline.load import load


def run(count: int, theme: str, languages: list[str] | None = None):
    lang_display = f" in {', '.join(languages)}" if languages else ""

    print("=== ETL Pipeline (Full Run) ===")

    print(f"[1/4] Generating {count} posts about '{theme}'{lang_display}...")
    generate(count=count, theme=theme, languages=languages)

    print("[2/4] Extracting data...")
    posts = extract()

    print("[3/4] Transforming data...")
    report_data = transform(posts)
    report_data["theme"] = theme

    print("[4/4] Loading report...")
    load(report_data)

    print("Done. Check output/report.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate posts and run the full ETL pipeline in one step")
    parser.add_argument("--count", type=int, default=10, help="Number of posts to generate (default: 10)")
    parser.add_argument("--theme", type=str, default="general social media", help="Theme for the posts (default: general social media)")
    parser.add_argument("--languages", type=str, default=None, help="Comma-separated languages to mix, e.g. 'English,Mandarin,Spanish'")
    args = parser.parse_args()

    languages = [l.strip() for l in args.languages.split(",")] if args.languages else None
    run(count=args.count, theme=args.theme, languages=languages)
