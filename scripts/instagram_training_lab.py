from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


METRIC_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*(?P<suffix>[kmb])?", re.I)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class TrainingExample:
    post_url: str
    likes: int = 0
    views: int = 0
    hook_text: str = ""
    caption: str = ""
    frame_path: str = ""
    media_path: str = ""
    buckets: list[str] = field(default_factory=list)
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_url": self.post_url,
            "likes": self.likes,
            "views": self.views,
            "hook_text": self.hook_text,
            "caption": self.caption,
            "frame_path": self.frame_path,
            "media_path": self.media_path,
            "buckets": self.buckets,
            "score": self.score,
        }


def parse_metric(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return 0
    match = METRIC_RE.search(cleaned)
    if not match:
        return 0
    number = float(match.group("number"))
    suffix = (match.group("suffix") or "").lower()
    multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1)
    return int(number * multiplier)


def clean_hook_text(value: str) -> str:
    text = str(value or "").strip()
    quote_match = re.search(r'text that says\s+[\"“](.*?)[\"”]', text, re.I)
    if quote_match:
        text = quote_match.group(1)
    text = re.sub(r"\b(?:wealth|nealth|ealth|mealth|wealtl)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .,:;-")
    return text


def short_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def hook_buckets(text: str) -> list[str]:
    lowered = text.lower()
    buckets: list[str] = []
    checks = [
        ("first_ever", r"\b(first ever|first-ever|for the first time|first time)\b"),
        ("after_years", r"\b(after|in|over)\s+\d+\s+years\b"),
        ("big_number", r"(\$?\d+(?:\.\d+)?\s*(million|billion|trillion|k|m|b)|\d+%)"),
        ("ranking", r"\b(most|biggest|richest|highest|longest|best|top\s+\d+|#\d+)\b"),
        ("future_date", r"\b(20\d{2}|this year|next year|before the end of the year)\b"),
        ("surprise", r"\b(insane|wild|secret|hidden|suddenly|nobody|you probably didn't know|hardest hitting)\b"),
        ("world_power", r"\b(china|iran|trump|xi|president|countries|world|debt|developing country)\b"),
        ("celebrity", r"\b(drake|michael jackson|shakira|ronaldo|messi|keanu|zendaya|batman|james bond)\b"),
        ("tech_future", r"\b(ai|iphone|playstation|gta|tesla|electric|robot|app|technology|future)\b"),
        ("place_visual", r"\b(city|earth|homes|buildings|airport|road|mansion|places|sights)\b"),
    ]
    for name, pattern in checks:
        if re.search(pattern, lowered):
            buckets.append(name)
    return buckets or ["plain_fact"]


def read_examples(csv_path: Path) -> list[TrainingExample]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    examples: list[TrainingExample] = []
    for row in rows:
        post_url = (row.get("post_url") or row.get("url") or "").strip()
        if not post_url:
            continue
        hook_text = clean_hook_text(row.get("hook_text") or row.get("hook") or row.get("title") or "")
        example = TrainingExample(
            post_url=post_url,
            likes=parse_metric(row.get("likes")),
            views=parse_metric(row.get("views")),
            hook_text=hook_text,
            caption=(row.get("caption") or "").strip(),
            frame_path=(row.get("frame_path") or "").strip(),
            media_path=(row.get("media_path") or "").strip(),
        )
        example.buckets = hook_buckets(" ".join([example.hook_text, example.caption]))
        example.score = max(example.views, example.likes)
        examples.append(example)
    return examples


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def download_post(example: TrainingExample, media_dir: Path, cookies_browser: str | None = None) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "yt-dlp",
        "--no-playlist",
        "--print",
        "after_move:filepath",
        "-P",
        str(media_dir),
        "-o",
        "%(id)s.%(ext)s",
    ]
    if cookies_browser:
        command.extend(["--cookies-from-browser", cookies_browser])
    command.append(example.post_url)
    completed = run_command(command)
    paths = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not paths:
        raise RuntimeError(f"yt-dlp did not return a filepath for {example.post_url}")
    example.media_path = paths[-1]
    return example.media_path


def extract_first_frame(example: TrainingExample, frames_dir: Path) -> str:
    source = Path(example.media_path or example.frame_path)
    if not source.exists():
        return example.frame_path
    frames_dir.mkdir(parents=True, exist_ok=True)
    target = frames_dir / f"{short_id(example.post_url)}.jpg"
    if source.suffix.lower() in IMAGE_EXTENSIONS:
        shutil.copy2(source, target)
    else:
        run_command([
            "ffmpeg",
            "-y",
            "-ss",
            "0",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(target),
        ])
    example.frame_path = str(target)
    return example.frame_path


def ranked_examples(examples: list[TrainingExample], sort_by: str) -> list[TrainingExample]:
    key = "likes" if sort_by == "likes" else "views"
    return sorted(examples, key=lambda example: getattr(example, key), reverse=True)


def relative_path(path: str, base_dir: Path) -> str:
    if not path:
        return ""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def write_contact_sheet(examples: list[TrainingExample], output_path: Path, sort_by: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for rank, example in enumerate(ranked_examples(examples, sort_by), start=1):
        frame = relative_path(example.frame_path, output_path.parent)
        metric = example.likes if sort_by == "likes" else example.views
        img = f'<img src="{html.escape(frame)}" alt="frame">' if frame else '<div class="missing">No frame</div>'
        cards.append(
            f"""
            <article class="card">
              <div class="rank">#{rank}</div>
              {img}
              <h2>{html.escape(example.hook_text or "No hook text")}</h2>
              <p><b>{sort_by.title()}:</b> {metric:,} &nbsp; <b>Likes:</b> {example.likes:,} &nbsp; <b>Views:</b> {example.views:,}</p>
              <p><b>Buckets:</b> {html.escape(", ".join(example.buckets))}</p>
              <a href="{html.escape(example.post_url)}">Open post</a>
            </article>
            """
        )
    output_path.write_text(
        f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>BuzzWire IG Training Contact Sheet</title>
  <style>
    body {{ margin: 0; background: #050505; color: #f7f7f7; font-family: Arial, sans-serif; }}
    header {{ padding: 24px; border-bottom: 1px solid #242424; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; padding: 18px; }}
    .card {{ background: #111; border: 1px solid #2d2d2d; border-radius: 8px; padding: 12px; }}
    .rank {{ color: #ffd23f; font-weight: 800; margin-bottom: 8px; }}
    img, .missing {{ width: 100%; aspect-ratio: 9 / 16; object-fit: cover; background: #222; border-radius: 6px; }}
    h2 {{ font-size: 18px; line-height: 1.15; }}
    p {{ color: #cfcfcf; font-size: 13px; }}
    a {{ color: #ffd23f; }}
  </style>
</head>
<body>
  <header>
    <h1>BuzzWire IG Training Contact Sheet</h1>
    <p>Sorted by {html.escape(sort_by)}. Use this to compare top hooks vs weak hooks.</p>
  </header>
  <main>
    {''.join(cards)}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


def analyze_patterns(examples: list[TrainingExample]) -> dict[str, Any]:
    bucket_scores: dict[str, list[int]] = defaultdict(list)
    for example in examples:
        for bucket in example.buckets:
            bucket_scores[bucket].append(example.score)
    patterns = []
    for bucket, scores in bucket_scores.items():
        patterns.append({
            "bucket": bucket,
            "count": len(scores),
            "average_score": round(sum(scores) / len(scores)),
            "max_score": max(scores),
        })
    patterns.sort(key=lambda item: (item["average_score"], item["count"]), reverse=True)
    top_examples = [example.to_dict() for example in ranked_examples(examples, "views")[:10]]
    weak_examples = [example.to_dict() for example in ranked_examples(examples, "views")[-10:]]
    return {
        "total_examples": len(examples),
        "patterns": patterns,
        "top_examples": top_examples,
        "weak_examples": weak_examples,
    }


def write_summary(analysis: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# BuzzWire IG Training Summary",
        "",
        f"Examples analyzed: {analysis['total_examples']}",
        "",
        "## Winning Buckets",
        "",
    ]
    for pattern in analysis["patterns"][:12]:
        lines.append(
            f"- `{pattern['bucket']}`: avg {pattern['average_score']:,}, max {pattern['max_score']:,}, n={pattern['count']}"
        )
    lines.extend(["", "## Top Hooks", ""])
    for example in analysis["top_examples"][:10]:
        lines.append(f"- {example['views']:,} views / {example['likes']:,} likes: {example['hook_text']}")
    lines.extend(["", "## Weaker Hooks", ""])
    for example in analysis["weak_examples"][:10]:
        lines.append(f"- {example['views']:,} views / {example['likes']:,} likes: {example['hook_text']}")
    lines.extend([
        "",
        "## BuzzWire Takeaways",
        "",
        "- Put the biggest name, number, date, ranking, or first-ever claim in the first line.",
        "- Prefer visual facts over abstract summaries.",
        "- Use a collage frame when the story needs context: hero image, circular inset, yellow arrow, huge headline.",
        "- Separate true news claims from entertainment/listicle claims, and keep risky politics source-led.",
    ])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(examples: list[TrainingExample], out_dir: Path, sort_by: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    examples_path = out_dir / "training_examples.json"
    examples_path.write_text(
        json.dumps([example.to_dict() for example in examples], indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    analysis = analyze_patterns(examples)
    (out_dir / "pattern_analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    write_summary(analysis, out_dir / "training_summary.md")
    write_contact_sheet(examples, out_dir / f"contact_sheet_by_{sort_by}.html", sort_by)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BuzzWire IG training contact sheets and hook analysis.")
    parser.add_argument("csv_path", type=Path, help="CSV with post_url, likes, views, hook_text, caption columns.")
    parser.add_argument("--out", type=Path, default=Path("data/training/instagram"), help="Output directory.")
    parser.add_argument("--sort-by", choices=["views", "likes"], default="views")
    parser.add_argument("--download", action="store_true", help="Download posts with yt-dlp before extracting frames.")
    parser.add_argument("--cookies-browser", help="Optional yt-dlp browser cookies source, e.g. chrome.")
    parser.add_argument("--limit", type=int, default=0, help="Limit examples processed.")
    args = parser.parse_args()

    examples = read_examples(args.csv_path)
    if args.limit:
        examples = examples[: args.limit]

    media_dir = args.out / "media"
    frames_dir = args.out / "frames"
    for example in examples:
        if args.download:
            download_post(example, media_dir, args.cookies_browser)
        if example.media_path or example.frame_path:
            extract_first_frame(example, frames_dir)

    write_outputs(examples, args.out, args.sort_by)
    print(f"Analyzed {len(examples)} examples into {args.out}")
    print(f"Open {args.out / f'contact_sheet_by_{args.sort_by}.html'}")


if __name__ == "__main__":
    main()
