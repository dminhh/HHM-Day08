"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft cho PDF/DOCX,
và Word COM automation (win32com) cho file .doc cũ.

Cài đặt:
    pip install markitdown pywin32
"""

import json
from pathlib import Path

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


_WORD_SCRIPT = """
import sys, win32com.client
src, dst = sys.argv[1], sys.argv[2]
word = win32com.client.Dispatch("Word.Application")
word.Visible = False
try:
    doc = word.Documents.Open(src)
    text = doc.Content.Text
    doc.Close(False)
    open(dst, "w", encoding="utf-8").write(text)
finally:
    try: word.Quit()
    except: pass
"""


def _convert_doc_subprocess(filepath: Path, output_path: Path) -> bool:
    """Convert một .doc file trong subprocess riêng để tránh crash lan."""
    import subprocess, sys, tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(_WORD_SCRIPT)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path, str(filepath.resolve()), str(output_path)],
            timeout=60,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return True
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        return False
    finally:
        Path(script_path).unlink(missing_ok=True)


def _convert_docs_with_word(doc_files: list, output_dir: Path) -> int:
    """Convert từng .doc file qua subprocess riêng biệt."""
    success = 0
    for filepath in doc_files:
        print(f"Converting: {filepath.name}")
        output_path = output_dir / f"{filepath.stem}.md"
        try:
            ok = _convert_doc_subprocess(filepath, output_path)
            if ok:
                print(f"  Saved: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
                success += 1
            else:
                print(f"  FAILED: conversion returned empty or error")
        except Exception as e:
            print(f"  FAILED: {e}")
    return success


def convert_legal_docs():
    """Convert PDF/DOCX/DOC files trong data/landing/legal/ sang markdown."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()
    success = 0

    # Tách .doc riêng, xử lý qua một Word session
    doc_files = [f for f in sorted(legal_dir.iterdir()) if f.suffix.lower() == ".doc"]
    other_files = [f for f in sorted(legal_dir.iterdir()) if f.suffix.lower() in (".pdf", ".docx")]

    if doc_files:
        success += _convert_docs_with_word(doc_files, output_dir)

    for filepath in other_files:
        print(f"Converting: {filepath.name}")
        output_path = output_dir / f"{filepath.stem}.md"
        try:
            result = md.convert(str(filepath))
            if not result.text_content.strip():
                print(f"  SKIP: scanned/image PDF, no extractable text")
                continue
            output_path.write_text(result.text_content, encoding="utf-8")
            print(f"  Saved: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"Legal: {success} files converted\n")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0

    for filepath in sorted(news_dir.iterdir()):
        if filepath.suffix.lower() != ".json":
            continue
        print(f"Converting: {filepath.name}")
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            output_path = output_dir / f"{filepath.stem}.md"

            header = f"# {data.get('title', 'Unknown')}\n\n"
            header += f"**Source:** {data.get('url', 'N/A')}\n"
            header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"

            content = header + data.get("content_markdown", "")
            output_path.write_text(content, encoding="utf-8")
            print(f"  Saved: {output_path.name} ({len(content)} chars)")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"News: {success} files converted\n")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("--- News Articles ---")
    convert_news_articles()

    # Summary
    legal_out = list((OUTPUT_DIR / "legal").glob("*.md")) if (OUTPUT_DIR / "legal").exists() else []
    news_out = list((OUTPUT_DIR / "news").glob("*.md")) if (OUTPUT_DIR / "news").exists() else []
    print(f"Total output: {len(legal_out)} legal + {len(news_out)} news markdown files")
    print(f"Output dir: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
