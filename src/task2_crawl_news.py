"""
Task 2 — Crawl bài báo về nghệ sĩ Việt Nam liên quan tới ma tuý.

Crawl ≥5 bài báo từ VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, Tiền Phong.
Lưu mỗi bài thành 1 file JSON với metadata đầy đủ.

Chạy: python -m src.task2_crawl_news
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ≥10 bài báo thực từ các báo uy tín Việt Nam về nghệ sĩ & ma tuý
ARTICLE_URLS = [
    {
        "url": "https://vnexpress.net/ca-si-miu-le-bi-bat-qua-tang-dung-ma-tuy-o-bai-bien-5072657.html",
        "source": "VnExpress",
    },
    {
        "url": "https://vnexpress.net/ca-si-miu-le-bi-bat-voi-cao-buoc-to-chuc-su-dung-ma-tuy-5074769.html",
        "source": "VnExpress",
    },
    {
        "url": "https://tuoitre.vn/bat-ca-si-long-nhat-va-ca-si-son-ngoc-minh-vi-lien-quan-ma-tuy-20260520082138943.htm",
        "source": "Tuổi Trẻ",
    },
    {
        "url": "https://thanhnien.vn/ca-si-long-nhat-bi-bat-showbiz-viet-lien-tiep-chan-dong-vi-ma-tuy-18526052013032001.htm",
        "source": "Thanh Niên",
    },
    {
        "url": "https://dantri.com.vn/van-hoa/nhung-nghe-si-viet-lao-dao-vi-dinh-vao-ma-tuy-20230424033137629.htm",
        "source": "Dân Trí",
    },
    {
        "url": "https://dantri.com.vn/phap-luat/khoi-to-bat-giam-nguoi-mau-andrea-aybar-ca-si-chi-dan-20241114115057035.htm",
        "source": "Dân Trí",
    },
    {
        "url": "https://tienphong.vn/nhieu-nghe-si-viet-bi-bat-vi-dinh-vao-ma-tuy-post1649760.tpo",
        "source": "Tiền Phong",
    },
    {
        "url": "https://tienphong.vn/lien-tiep-nghe-si-dung-chat-cam-post1842599.tpo",
        "source": "Tiền Phong",
    },
    {
        "url": "https://dantri.com.vn/phap-luat/truoc-ca-si-chu-bin-loat-nghe-si-noi-tieng-vuong-lao-ly-vi-ma-tuy-20240608123002810.htm",
        "source": "Dân Trí",
    },
    {
        "url": "https://tienphong.vn/cong-an-tphcm-bat-nguoi-mau-dien-vien-ca-si-su-dung-ma-tuy-post1691448.tpo",
        "source": "Tiền Phong",
    },
]


def _extract_vnexpress(soup: BeautifulSoup, url: str) -> dict:
    title_tag = soup.find("h1", class_="title-detail") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    desc_tag = soup.find("p", class_="description")
    description = desc_tag.get_text(strip=True) if desc_tag else ""

    content_div = soup.find("article", class_="fck_detail") or soup.find("div", class_="fck_detail")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("span", class_="date")
    pub_date = date_tag.get_text(strip=True) if date_tag else ""

    return {"title": title, "description": description, "content": content, "published_date": pub_date}


def _extract_tuoitre(soup: BeautifulSoup, url: str) -> dict:
    title_tag = soup.find("h1", class_="article-title") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    sapo_tag = soup.find("div", class_="sapo")
    description = sapo_tag.get_text(strip=True) if sapo_tag else ""

    content_div = soup.find("div", class_="detail-content") or soup.find("div", id="main-detail-body")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("div", class_="date-time") or soup.find("time")
    pub_date = date_tag.get_text(strip=True) if date_tag else ""

    return {"title": title, "description": description, "content": content, "published_date": pub_date}


def _extract_thanhnien(soup: BeautifulSoup, url: str) -> dict:
    title_tag = soup.find("h1", class_="detail-title") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    sapo_tag = soup.find("div", class_="detail-sapo") or soup.find("p", class_="sapo")
    description = sapo_tag.get_text(strip=True) if sapo_tag else ""

    content_div = soup.find("div", class_="detail-content") or soup.find("div", id="abody")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("time") or soup.find("div", class_="detail-time")
    pub_date = date_tag.get_text(strip=True) if date_tag else ""

    return {"title": title, "description": description, "content": content, "published_date": pub_date}


def _extract_dantri(soup: BeautifulSoup, url: str) -> dict:
    title_tag = soup.find("h1", class_="title-page") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    sapo_tag = soup.find("div", class_="singular-sapo") or soup.find("h2", class_="singular-sapo")
    description = sapo_tag.get_text(strip=True) if sapo_tag else ""

    content_div = soup.find("div", class_="singular-content") or soup.find("div", class_="dt-news__content")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("time") or soup.find("span", class_="dt-news__time")
    pub_date = date_tag.get_text(strip=True) if date_tag else ""

    return {"title": title, "description": description, "content": content, "published_date": pub_date}


def _extract_tienphong(soup: BeautifulSoup, url: str) -> dict:
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    sapo_tag = soup.find("div", class_="article__sapo") or soup.find("p", class_="lead")
    description = sapo_tag.get_text(strip=True) if sapo_tag else ""

    content_div = (
        soup.find("div", class_="article__body")
        or soup.find("div", class_="ArticleBody")
        or soup.find("div", id="article-body")
    )
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("time") or soup.find("span", class_="article__time")
    pub_date = date_tag.get_text(strip=True) if date_tag else ""

    return {"title": title, "description": description, "content": content, "published_date": pub_date}


def _generic_extract(soup: BeautifulSoup, url: str) -> dict:
    """Fallback extractor: lấy tất cả <p> tags."""
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    paragraphs = soup.find_all("p")
    content = "\n\n".join(
        p.get_text(strip=True) for p in paragraphs
        if len(p.get_text(strip=True)) > 50
    )

    return {"title": title, "description": "", "content": content, "published_date": ""}


def crawl_article(url: str, source: str) -> dict | None:
    """Crawl một bài báo, trả về dict với metadata + content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as e:
        print(f"  ✗ Lỗi fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    if "vnexpress.net" in url:
        extracted = _extract_vnexpress(soup, url)
    elif "tuoitre.vn" in url:
        extracted = _extract_tuoitre(soup, url)
    elif "thanhnien.vn" in url:
        extracted = _extract_thanhnien(soup, url)
    elif "dantri.com.vn" in url:
        extracted = _extract_dantri(soup, url)
    elif "tienphong.vn" in url:
        extracted = _extract_tienphong(soup, url)
    else:
        extracted = _generic_extract(soup, url)

    # Nếu content quá ngắn, dùng fallback
    if len(extracted.get("content", "")) < 100:
        extracted = _generic_extract(soup, url)

    return {
        "url": url,
        "source": source,
        "title": extracted["title"],
        "description": extracted.get("description", ""),
        "content": extracted["content"],
        "published_date": extracted.get("published_date", ""),
        "date_crawled": datetime.now().isoformat(),
        "topic": "nghệ sĩ Việt Nam và ma tuý",
    }


def crawl_all():
    """Crawl toàn bộ bài báo trong ARTICLE_URLS."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Task 2: Crawl bài báo về nghệ sĩ & ma tuý")
    print(f"Tổng {len(ARTICLE_URLS)} bài cần crawl")
    print("=" * 60)

    success = 0
    for i, item in enumerate(ARTICLE_URLS, 1):
        url, source = item["url"], item["source"]
        print(f"\n[{i}/{len(ARTICLE_URLS)}] [{source}] {url[:70]}...")

        article = crawl_article(url, source)
        if article is None:
            continue

        filename = f"article_{i:02d}_{source.replace(' ', '_').replace('ổ','o').replace('ề','e')}.json"
        filepath = OUTPUT_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")

        word_count = len(article["content"].split())
        print(f"  ✓ Saved: {filename} | Title: {article['title'][:60]}...")
        print(f"    Content: {word_count} words")
        success += 1

        time.sleep(1.5)  # Lịch sự với server

    print(f"\n{'='*60}")
    print(f"✓ Hoàn thành: {success}/{len(ARTICLE_URLS)} bài crawl thành công")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    crawl_all()
