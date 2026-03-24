import argparse
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pipeline.generate import generate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic social media posts into data/posts.jsonl")
    parser.add_argument("--count", type=int, default=10, help="Number of posts to generate (default: 10)")
    parser.add_argument("--theme", type=str, default="general social media", help="Theme for the posts (default: general social media)")
    parser.add_argument("--languages", type=str, default=None, help="Comma-separated languages to mix, e.g. 'English,Mandarin,Spanish'")
    args = parser.parse_args()

    languages = [l.strip() for l in args.languages.split(",")] if args.languages else None

    print("=== Generating Posts ===")
    generate(count=args.count, theme=args.theme, languages=languages)
    print("Done. Run main.py to process the data.")
