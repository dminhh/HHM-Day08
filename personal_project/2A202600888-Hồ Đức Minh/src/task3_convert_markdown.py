"""
Task 3 — Convert toàn bộ file trong data/landing/ sang Markdown.

- PDF/DOCX/DOC trong data/landing/legal/  → data/standardized/legal/
- JSON (crawled news) trong data/landing/news/ → data/standardized/news/

Dùng MarkItDown (Microsoft) cho legal docs.
News JSON đã có field 'markdown' từ Crawl4AI nên extract trực tiếp.
"""

import json
import subprocess
from pathlib import Path

from markitdown import MarkItDown

BASE_DIR = Path(__file__).parent.parent
LANDING_DIR = BASE_DIR / "data" / "landing"
STANDARDIZED_DIR = BASE_DIR / "data" / "standardized"

LEGAL_IN = LANDING_DIR / "legal"
LEGAL_OUT = STANDARDIZED_DIR / "legal"
NEWS_IN = LANDING_DIR / "news"
NEWS_OUT = STANDARDIZED_DIR / "news"

LEGAL_EXTENSIONS = {".pdf", ".docx", ".doc"}


def convert_doc_with_antiword(f: Path) -> str | None:
    """Dùng antiword để convert .doc sang text (hỗ trợ tiếng Việt UTF-8)."""
    result = subprocess.run(
        ["antiword", "-m", "UTF-8.txt", str(f)],
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout.decode("utf-8", errors="replace")
    return None


def convert_legal_docs() -> list[Path]:
    """Convert PDF/DOCX/DOC legal docs sang Markdown."""
    LEGAL_OUT.mkdir(parents=True, exist_ok=True)
    md = MarkItDown()
    converted = []

    legal_files = [
        f for f in LEGAL_IN.iterdir()
        if f.is_file() and f.suffix.lower() in LEGAL_EXTENSIONS
    ]
    print(f"Legal docs cần convert: {len(legal_files)}")

    for f in legal_files:
        out_path = LEGAL_OUT / (f.stem + ".md")
        if out_path.exists() and out_path.stat().st_size > 100:
            print(f"  [skip] {f.name}")
            converted.append(out_path)
            continue

        print(f"  [→] {f.name}", end=" ... ", flush=True)
        text = None

        # Thử MarkItDown trước (PDF, DOCX)
        try:
            result = md.convert(str(f))
            text = result.text_content
        except Exception:
            pass

        # Fallback: antiword cho .doc binary
        if not text and f.suffix.lower() == ".doc":
            text = convert_doc_with_antiword(f)

        if text and len(text.strip()) > 100:
            out_path.write_text(text, encoding="utf-8")
            size_kb = out_path.stat().st_size / 1024
            print(f"✓ ({size_kb:.1f} KB)")
            converted.append(out_path)
        else:
            print(f"✗ không extract được nội dung")

    return converted


def convert_news_docs() -> list[Path]:
    """Extract markdown từ news JSON (đã có sẵn từ Crawl4AI)."""
    NEWS_OUT.mkdir(parents=True, exist_ok=True)
    converted = []

    news_files = sorted(NEWS_IN.glob("*.json"))
    print(f"\nNews files cần convert: {len(news_files)}")

    for f in news_files:
        out_path = NEWS_OUT / (f.stem + ".md")
        if out_path.exists() and out_path.stat().st_size > 100:
            print(f"  [skip] {f.name}")
            converted.append(out_path)
            continue

        print(f"  [→] {f.name}", end=" ... ", flush=True)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Thêm metadata vào đầu file markdown
            content = f"# {data.get('title', f.stem)}\n\n"
            content += f"**URL:** {data.get('url', '')}\n\n"
            content += f"**Crawled at:** {data.get('crawled_at', '')}\n\n"
            content += "---\n\n"
            content += data.get("markdown", "")

            out_path.write_text(content, encoding="utf-8")
            size_kb = out_path.stat().st_size / 1024
            print(f"✓ ({size_kb:.1f} KB)")
            converted.append(out_path)
        except Exception as e:
            print(f"✗ {e}")

    return converted


def convert_all() -> list[Path]:
    """Convert toàn bộ landing files sang standardized markdown."""
    print("=" * 50)
    print("TASK 3 — Convert sang Markdown")
    print("=" * 50)

    legal_files = convert_legal_docs()
    news_files = convert_news_docs()
    all_files = legal_files + news_files

    print(f"\nKết quả: {len(all_files)} file đã convert")
    print(f"  - Legal: {len(legal_files)} file → {LEGAL_OUT}")
    print(f"  - News:  {len(news_files)} file → {NEWS_OUT}")

    return all_files


if __name__ == "__main__":
    convert_all()
