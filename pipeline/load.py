from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

OUTPUT_FILE = Path("output/report.html")


def load(report_data: dict):
    # Compute overall dominant sentiment
    totals = {"positive": 0, "neutral": 0, "negative": 0}
    for cluster in report_data["clusters"]:
        for key, val in cluster["sentiment_breakdown"].items():
            totals[key] += val
    overall_sentiment = max(totals, key=totals.get).capitalize()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report.html")

    html = template.render(
        theme=report_data["theme"],
        generated_at=datetime.now().strftime("%B %d, %Y at %H:%M"),
        total_posts=report_data["total_posts"],
        total_topics=report_data["total_topics"],
        overall_sentiment=overall_sentiment,
        language_counts=report_data.get("language_counts", {}),
        clusters=report_data["clusters"],
    )

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"    Report saved to {OUTPUT_FILE}")
