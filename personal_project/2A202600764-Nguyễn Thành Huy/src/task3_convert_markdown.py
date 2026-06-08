"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Dùng MarkItDown (Microsoft) để convert PDF/DOCX/DOC/HTML/JSON → Markdown.
Output lưu vào data/standardized/, giữ cấu trúc thư mục con.

Chạy: python -m src.task3_convert_markdown
"""

import json
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".html", ".htm"}


def convert_legal_docs():
    """Convert PDF/DOCX/DOC files trong data/landing/legal/ → markdown."""
    legal_in = LANDING_DIR / "legal"
    legal_out = OUTPUT_DIR / "legal"
    legal_out.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()
    converted = 0

    for filepath in sorted(legal_in.iterdir()):
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        print(f"  Converting: {filepath.name} ({filepath.stat().st_size // 1024} KB)")
        try:
            result = md.convert(str(filepath))
            text = result.text_content.strip()

            if len(text) < 100:
                print(f"    ⚠ Nội dung quá ngắn ({len(text)} chars), bỏ qua")
                continue

            output_path = legal_out / f"{filepath.stem}.md"
            output_path.write_text(text, encoding="utf-8")
            print(f"    ✓ Saved: {output_path.name} ({len(text):,} chars)")
            converted += 1

        except Exception as e:
            print(f"    ✗ Lỗi: {e}")

    return converted


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ → markdown."""
    news_in = LANDING_DIR / "news"
    news_out = OUTPUT_DIR / "news"
    news_out.mkdir(parents=True, exist_ok=True)

    converted = 0

    for filepath in sorted(news_in.iterdir()):
        if filepath.suffix.lower() != ".json":
            continue

        print(f"  Converting: {filepath.name}")
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))

            # Build markdown với metadata header
            title = data.get("title", "Bài báo không tiêu đề")
            source = data.get("source", "Không rõ nguồn")
            url = data.get("url", "")
            pub_date = data.get("published_date", "")
            crawled = data.get("date_crawled", "")
            description = data.get("description", "")
            content = data.get("content", "")

            lines = [
                f"# {title}",
                "",
                f"**Nguồn:** {source}",
                f"**URL:** {url}",
                f"**Ngày đăng:** {pub_date}",
                f"**Ngày crawl:** {crawled}",
                "",
                "---",
                "",
            ]
            if description:
                lines += [f"*{description}*", "", "---", ""]
            lines.append(content)

            md_content = "\n".join(lines)

            output_path = news_out / f"{filepath.stem}.md"
            output_path.write_text(md_content, encoding="utf-8")
            print(f"    ✓ Saved: {output_path.name} ({len(md_content):,} chars)")
            converted += 1

        except Exception as e:
            print(f"    ✗ Lỗi: {e}")

    return converted


def convert_all():
    """Convert toàn bộ files trong data/landing/ sang Markdown."""
    print("=" * 60)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 60)

    print("\n--- Legal Documents ---")
    n_legal = convert_legal_docs()

    print("\n--- News Articles ---")
    n_news = convert_news_articles()

    total = n_legal + n_news
    print(f"\n{'='*60}")
    print(f"✓ Hoàn thành: {total} files ({n_legal} legal + {n_news} news)")
    print(f"  Output: {OUTPUT_DIR}")
    return total


if __name__ == "__main__":
    convert_all()
