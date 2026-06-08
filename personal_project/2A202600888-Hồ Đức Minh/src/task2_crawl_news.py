"""
Task 2 — Crawl bài báo về nghệ sĩ Việt Nam liên quan tới ma tuý.

Output: data/landing/news/ — mỗi bài 1 file JSON với metadata + nội dung markdown.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler

NEWS_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# ≥5 bài báo về nghệ sĩ Việt Nam liên quan ma tuý
ARTICLES = [
    {
        "url": "https://vnexpress.net/ca-si-long-nhat-son-ngoc-minh-bi-bat-vi-lien-quan-ma-tuy-5060857.html",
        "title": "Ca sĩ Long Nhật, Sơn Ngọc Minh bị bắt vì liên quan ma tuý",
    },
    {
        "url": "https://vnexpress.net/su-nghiep-long-nhat-truoc-khi-bi-bat-vi-lien-quan-ma-tuy-5076081.html",
        "title": "Sự nghiệp Long Nhật trước khi bị bắt vì liên quan ma tuý",
    },
    {
        "url": "https://vnexpress.net/su-nghiep-cua-miu-le-truoc-khi-bi-bat-qua-tang-dung-ma-tuy-5072762.html",
        "title": "Sự nghiệp của Miu Lê trước khi bị bắt quả tang dùng ma tuý",
    },
    {
        "url": "https://vnexpress.net/20-nam-hoat-dong-cua-miu-le-truoc-khi-bi-bat-qua-tang-dung-ma-tuy-5072922.html",
        "title": "20 năm hoạt động của Miu Lê trước khi bị bắt quả tang dùng ma tuý",
    },
    {
        "url": "https://tuoitre.vn/bat-ca-si-long-nhat-va-ca-si-son-ngoc-minh-vi-lien-quan-ma-tuy-20260520082138943.htm",
        "title": "Bắt ca sĩ Long Nhật và ca sĩ Sơn Ngọc Minh vì liên quan ma tuý",
    },
    {
        "url": "https://tuoitre.vn/miu-le-bi-khoi-to-tam-giam-cong-ty-quan-ly-khang-dinh-khong-bao-che-20260516231928239.htm",
        "title": "Miu Lê bị khởi tố tạm giam, công ty quản lý khẳng định không bao che",
    },
    {
        "url": "https://vnexpress.net/nguoi-mau-andrea-aybar-cung-tro-ly-lam-tiec-ma-tuy-trong-can-ho-cao-cap-5059429.html",
        "title": "Người mẫu Andrea Aybar cùng trợ lý làm tiệc ma tuý trong căn hộ cao cấp",
    },
    {
        "url": "https://ngoisao.vnexpress.net/nhung-nghe-si-viet-nga-ngua-vi-ma-tuy-4816068.html",
        "title": "Những nghệ sĩ Việt ngã ngựa vì ma tuý",
    },
]


async def crawl_article(crawler: AsyncWebCrawler, url: str, title: str) -> dict | None:
    """Crawl một bài báo và trả về dict chứa metadata + nội dung."""
    print(f"  [→] Crawling: {title[:60]}")
    try:
        result = await crawler.arun(url=url)
        if not result.success:
            print(f"  [✗] Thất bại: {result.error_message}")
            return None

        return {
            "url": url,
            "title": title,
            "crawled_at": datetime.now().isoformat(),
            "markdown": result.markdown,
        }
    except Exception as e:
        print(f"  [✗] Lỗi: {e}")
        return None


def save_article(data: dict, filename: str) -> Path:
    """Lưu bài báo thành file JSON."""
    output_path = NEWS_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    size_kb = output_path.stat().st_size / 1024
    print(f"  [✓] Lưu: {filename} ({size_kb:.1f} KB)")
    return output_path


async def crawl_all_articles() -> list[Path]:
    """Crawl toàn bộ bài báo và lưu vào data/landing/news/."""
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Thư mục output: {NEWS_DIR}")
    print(f"Số bài cần crawl: {len(ARTICLES)}\n")

    saved_files = []

    async with AsyncWebCrawler() as crawler:
        for i, article in enumerate(ARTICLES, 1):
            filename = f"news_{i:02d}.json"
            output_path = NEWS_DIR / filename

            # Bỏ qua nếu đã crawl rồi
            if output_path.exists() and output_path.stat().st_size > 500:
                print(f"[{i}/{len(ARTICLES)}] Đã có: {filename} — bỏ qua")
                saved_files.append(output_path)
                continue

            print(f"[{i}/{len(ARTICLES)}]")
            data = await crawl_article(crawler, article["url"], article["title"])

            if data:
                path = save_article(data, filename)
                saved_files.append(path)

            # Delay tránh bị rate-limit
            await asyncio.sleep(1)

    print(f"\n{'='*50}")
    print(f"Kết quả: {len(saved_files)}/{len(ARTICLES)} bài báo")
    if len(saved_files) >= 5:
        print("✓ Đạt yêu cầu: ≥5 bài báo")
    else:
        print(f"✗ Chưa đủ: cần thêm {5 - len(saved_files)} bài")

    return saved_files


def main():
    asyncio.run(crawl_all_articles())


if __name__ == "__main__":
    main()
