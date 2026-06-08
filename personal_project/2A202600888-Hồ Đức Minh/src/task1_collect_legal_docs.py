"""
Task 1 — Thu thập văn bản pháp luật về ma tuý và các chất cấm.

Các file được tải thủ công từ vbpl.vn vào data/landing/legal/:
    - 73_2021_QH14_445185.doc  : Luật Phòng, chống ma tuý 2021 (73/2021/QH15)
    - 105_2021_ND-CP_496664.doc: Nghị định 105/2021/NĐ-CP
    - 109_2021_ND-CP_497098.doc: Nghị định 109/2021/NĐ-CP
    - 116_2021_ND-CP_482328.doc: Nghị định 116/2021/NĐ-CP
    - 144_2021_ND-CP_425471.doc: Nghị định 144/2021/NĐ-CP
"""

from pathlib import Path

LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
VALID_EXTENSIONS = {".pdf", ".docx", ".doc"}


def setup_directory() -> None:
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    LEGAL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục: {LEGAL_DIR}")


def list_legal_docs() -> list[Path]:
    """Trả về danh sách file PDF/DOCX hợp lệ trong data/landing/legal/."""
    if not LEGAL_DIR.exists():
        return []
    return [
        f for f in LEGAL_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]


def collect_legal_docs() -> list[Path]:
    """
    Thiết lập thư mục và kiểm tra các văn bản pháp luật đã thu thập.
    """
    setup_directory()
    files = list_legal_docs()

    print(f"\nVăn bản pháp luật trong data/landing/legal/ ({len(files)} file):")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")

    if len(files) >= 3:
        print(f"\n✓ Đạt yêu cầu: {len(files)}/3 văn bản")
    else:
        print(f"\n✗ Chưa đủ: {len(files)}/3 văn bản — cần thêm {3 - len(files)} file")

    return files


if __name__ == "__main__":
    collect_legal_docs()
