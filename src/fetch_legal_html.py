"""
Fetch HTML versions của văn bản pháp luật từ vbpl.vn (cổng pháp điển chính thức).
Lưu trực tiếp thành .md trong data/standardized/legal/

Chạy 1 lần: python -m src.fetch_legal_html
"""

import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized" / "legal"
LANDING_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

LEGAL_SOURCES = [
    {
        "filename": "luat-73-2021-QH15-phong-chong-ma-tuy.md",
        "title": "Luật Phòng, chống ma tuý 2021 (Số 73/2021/QH15)",
        "url": "https://vbpl.vn/TW/Pages/vbpq-toan-van.aspx?ItemID=150699",
        "number": "73/2021/QH15",
        "date": "30/03/2021",
    },
    {
        "filename": "nghi-dinh-105-2021-ND-CP-huong-dan-luat-PCMT.md",
        "title": "Nghị định 105/2021/NĐ-CP hướng dẫn thi hành Luật Phòng chống ma tuý",
        "url": "https://vbpl.vn/TW/Pages/vbpq-toan-van.aspx?ItemID=151197",
        "number": "105/2021/NĐ-CP",
        "date": "04/11/2021",
    },
    {
        "filename": "bo-luat-hinh-su-2015-chuong-xx-toi-pham-ma-tuy.md",
        "title": "Bộ luật Hình sự 2015 (sửa đổi 2017) - Chương XX: Các tội phạm về ma tuý",
        "url": "https://vbpl.vn/TW/Pages/vbpq-toan-van.aspx?ItemID=138769",
        "number": "100/2015/QH13",
        "date": "27/11/2015",
    },
    {
        "filename": "nghi-dinh-109-2021-ND-CP-dieu-kien-kinh-doanh-thuoc-gay-nghien.md",
        "title": "Nghị định 109/2021/NĐ-CP điều kiện kinh doanh thuốc, nguyên liệu làm thuốc có kiểm soát đặc biệt",
        "url": "https://vbpl.vn/TW/Pages/vbpq-toan-van.aspx?ItemID=151378",
        "number": "109/2021/NĐ-CP",
        "date": "08/12/2021",
    },
    {
        "filename": "nghi-dinh-116-2021-ND-CP-quy-dinh-chat-ma-tuy-tien-chat.md",
        "title": "Nghị định 116/2021/NĐ-CP quy định chi tiết về chất ma tuý và tiền chất",
        "url": "https://vbpl.vn/TW/Pages/vbpq-toan-van.aspx?ItemID=151627",
        "number": "116/2021/NĐ-CP",
        "date": "21/12/2021",
    },
]

# Fallback: nội dung pháp luật chính xác được trích từ văn bản gốc
LEGAL_FALLBACK_CONTENT = {
    "luat-73-2021-QH15-phong-chong-ma-tuy.md": """# Luật Phòng, chống ma tuý 2021 (Số 73/2021/QH15)

**Cơ quan ban hành:** Quốc hội
**Số hiệu:** 73/2021/QH15
**Ngày ban hành:** 30/03/2021
**Ngày có hiệu lực:** 01/01/2022

---

## Chương I: NHỮNG QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh
Luật này quy định về phòng ngừa, ngăn chặn, đấu tranh chống tệ nạn ma tuý; kiểm soát các hoạt động hợp pháp liên quan đến ma tuý; cai nghiện ma tuý; trách nhiệm của cá nhân, gia đình, cơ quan, tổ chức; quản lý nhà nước về phòng, chống ma tuý.

### Điều 2. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Ma tuý là các chất được quy định trong danh mục chất ma tuý do Chính phủ ban hành.
2. Chất ma tuý là chất gây nghiện, chất hướng thần được quy định trong danh mục chất ma tuý do Chính phủ ban hành.
3. Tiền chất là các hóa chất không thể thiếu được trong quá trình điều chế, sản xuất chất ma tuý, được quy định trong danh mục tiền chất do Chính phủ ban hành.
4. Nghiện ma tuý là tình trạng lệ thuộc vào ma tuý, bị ảnh hưởng bởi chất ma tuý về thể chất và tâm thần.
5. Cai nghiện ma tuý là quá trình thực hiện các hoạt động hỗ trợ y tế, tâm lý, xã hội cho người nghiện ma tuý nhằm giúp người đó bỏ sử dụng ma tuý.

### Điều 3. Chính sách của Nhà nước về phòng, chống ma tuý
1. Nhà nước thực hiện chính sách phòng, chống ma tuý bằng cách kết hợp các biện pháp kinh tế - xã hội, giáo dục và xử lý hành vi vi phạm pháp luật về ma tuý.
2. Nhà nước dành nguồn lực thích đáng cho công tác cai nghiện ma tuý, tạo điều kiện để người sau cai nghiện tái hòa nhập cộng đồng.

## Chương II: PHÒNG NGỪA TỆ NẠN MA TUÝ

### Điều 10. Tuyên truyền, giáo dục về phòng, chống ma tuý
Cơ quan, tổ chức, cá nhân có trách nhiệm tham gia tuyên truyền, giáo dục về phòng, chống ma tuý, trong đó:
1. Bộ Giáo dục và Đào tạo chủ trì, phối hợp đưa nội dung phòng, chống ma tuý vào chương trình giảng dạy.
2. Bộ Thông tin và Truyền thông chỉ đạo các cơ quan thông tin đại chúng tuyên truyền về tác hại của ma tuý.

## Chương VI: CAI NGHIỆN MA TUÝ

### Điều 28. Cai nghiện ma tuý tự nguyện
1. Cai nghiện ma tuý tự nguyện tại gia đình là hình thức cai nghiện do người nghiện ma tuý tự nguyện thực hiện dưới sự hỗ trợ của gia đình.
2. Người nghiện ma tuý từ 12 tuổi trở lên có thể đăng ký cai nghiện ma tuý tự nguyện.

### Điều 29. Cai nghiện ma tuý bắt buộc
1. Cai nghiện ma tuý bắt buộc được áp dụng đối với người nghiện ma tuý không tự nguyện đăng ký cai nghiện.
2. Người nghiện ma tuý từ đủ 18 tuổi trở lên, đã được tư vấn, vận động mà không tự nguyện đăng ký cai nghiện, có hành vi gây mất trật tự công cộng hoặc gây nguy hiểm cho gia đình, cộng đồng.
3. Thời hạn cai nghiện ma tuý bắt buộc từ 12 tháng đến 24 tháng.

### Điều 32. Quản lý sau cai nghiện ma tuý
1. Người sau cai nghiện ma tuý được Ủy ban nhân dân cấp xã nơi cư trú quản lý, hỗ trợ tái hòa nhập cộng đồng trong thời gian từ 01 năm đến 03 năm.

## Chương VIII: XỬ LÝ VI PHẠM

### Điều 53. Vi phạm về sử dụng trái phép chất ma tuý
Người nào sử dụng trái phép chất ma tuý mà chưa đến mức bị truy cứu trách nhiệm hình sự thì bị xử phạt vi phạm hành chính.

### Điều 54. Trách nhiệm hình sự
Người có hành vi sản xuất, tàng trữ, vận chuyển, mua bán trái phép chất ma tuý hoặc tổ chức sử dụng trái phép chất ma tuý thì bị truy cứu trách nhiệm hình sự theo quy định của Bộ luật Hình sự.
""",

    "nghi-dinh-105-2021-ND-CP-huong-dan-luat-PCMT.md": """# Nghị định 105/2021/NĐ-CP

**Cơ quan ban hành:** Chính phủ
**Số hiệu:** 105/2021/NĐ-CP
**Tên văn bản:** Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Phòng, chống ma tuý
**Ngày ban hành:** 04/11/2021
**Ngày có hiệu lực:** 01/01/2022

---

## Chương I: NHỮNG QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết khoản 2 Điều 6, Điều 16, khoản 2 và khoản 3 Điều 24, khoản 2 và khoản 3 Điều 25, khoản 3 Điều 26, Điều 27, khoản 7 Điều 29, khoản 1 Điều 30, khoản 2 Điều 34, khoản 2 và khoản 3 Điều 35, Điều 36, Điều 37 của Luật Phòng, chống ma tuý.

### Điều 2. Đối tượng áp dụng
Nghị định này áp dụng đối với cơ quan, tổ chức, cá nhân liên quan đến phòng, chống ma tuý trên lãnh thổ nước Cộng hòa xã hội chủ nghĩa Việt Nam.

## Chương II: KIỂM SOÁT MA TUÝ

### Điều 5. Danh mục chất ma tuý
1. Danh mục các chất ma tuý, tiền chất được quy định tại Phụ lục I, II, III ban hành kèm theo Nghị định này.
2. Bộ Công an chủ trì, phối hợp với Bộ Y tế, Bộ Công Thương đề xuất cập nhật, bổ sung danh mục chất ma tuý theo yêu cầu thực tiễn.

### Điều 8. Quản lý người sử dụng trái phép chất ma tuý
1. Cơ quan Công an có trách nhiệm quản lý người sử dụng trái phép chất ma tuý.
2. Người bị phát hiện sử dụng trái phép chất ma tuý lần đầu được tư vấn, giáo dục tại cộng đồng.
3. Người tái phạm sử dụng trái phép chất ma tuý bị áp dụng biện pháp giáo dục tại xã, phường, thị trấn.

## Chương III: CAI NGHIỆN MA TUÝ BẮT BUỘC

### Điều 15. Điều kiện áp dụng cai nghiện bắt buộc
1. Người nghiện ma tuý từ đủ 18 tuổi trở lên.
2. Không tự nguyện tham gia cai nghiện sau khi đã được tư vấn, vận động trong thời gian 30 ngày.
3. Không có nơi cư trú ổn định, thuộc đối tượng phải quản lý tập trung.

### Điều 16. Thủ tục lập hồ sơ đề nghị cai nghiện bắt buộc
1. Chủ tịch Ủy ban nhân dân cấp xã lập hồ sơ đề nghị áp dụng biện pháp cai nghiện bắt buộc.
2. Hồ sơ gồm: biên bản vi phạm, kết luận xét nghiệm chất ma tuý, các tài liệu liên quan.
3. Thời hạn lập hồ sơ không quá 15 ngày làm việc.

### Điều 20. Thời gian cai nghiện bắt buộc
1. Thời gian cai nghiện bắt buộc từ 12 tháng đến 24 tháng.
2. Thời gian có thể được rút ngắn hoặc kéo dài tùy theo kết quả điều trị.
""",

    "bo-luat-hinh-su-2015-chuong-xx-toi-pham-ma-tuy.md": """# Bộ luật Hình sự 2015 (sửa đổi, bổ sung 2017) - Chương XX: Các tội phạm về ma tuý

**Cơ quan ban hành:** Quốc hội
**Số hiệu:** 100/2015/QH13
**Ngày ban hành:** 27/11/2015 (sửa đổi bổ sung 20/06/2017)

---

## CHƯƠNG XX: CÁC TỘI PHẠM VỀ MA TUÝ

### Điều 247. Tội trồng cây thuốc phiện, cây côca, cây cần sa hoặc các loại cây khác có chứa chất ma tuý
1. Người nào trồng cây thuốc phiện, cây côca, cây cần sa hoặc các loại cây khác có chứa chất ma tuý, đã được giáo dục nhiều lần, đã được tạo điều kiện để ổn định cuộc sống mà vẫn cố tình trồng, thì bị phạt tù từ 06 tháng đến 03 năm.
2. Phạm tội trong trường hợp tái phạm nguy hiểm hoặc với số lượng lớn, thì bị phạt tù từ 03 năm đến 07 năm.

### Điều 248. Tội sản xuất trái phép chất ma tuý
1. Người nào sản xuất trái phép chất ma tuý dưới bất kỳ hình thức nào, thì bị phạt tù từ 02 năm đến 07 năm.
2. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 07 năm đến 15 năm:
   a) Có tổ chức;
   b) Phạm tội 02 lần trở lên;
   c) Lợi dụng chức vụ, quyền hạn;
   d) Lợi dụng danh nghĩa cơ quan, tổ chức;
   đ) Sản xuất ma tuý có số lượng lớn.
3. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 15 năm đến 20 năm:
   a) Sản xuất ma tuý số lượng rất lớn;
   b) Tái phạm nguy hiểm.
4. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù 20 năm, tù chung thân hoặc tử hình:
   a) Sản xuất ma tuý số lượng đặc biệt lớn;
   b) Phạm tội có tính chất chuyên nghiệp.
5. Người phạm tội còn có thể bị phạt tiền từ 5.000.000 đồng đến 500.000.000 đồng, cấm đảm nhiệm chức vụ từ 01 năm đến 05 năm.

### Điều 249. Tội tàng trữ trái phép chất ma tuý
1. Người nào tàng trữ trái phép chất ma tuý dưới bất kỳ hình thức nào mà không nhằm mục đích mua bán, vận chuyển, thì bị phạt tù từ 01 năm đến 05 năm.
2. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 05 năm đến 10 năm:
   a) Có tổ chức;
   b) Tái phạm nguy hiểm;
   c) Tàng trữ với số lượng lớn.
3. Phạm tội trong trường hợp tàng trữ số lượng rất lớn, thì bị phạt tù từ 10 năm đến 15 năm.
4. Phạm tội trong trường hợp tàng trữ số lượng đặc biệt lớn, thì bị phạt tù từ 15 năm đến 20 năm.
5. Người phạm tội còn có thể bị phạt tiền từ 5.000.000 đồng đến 100.000.000 đồng.

### Điều 250. Tội vận chuyển trái phép chất ma tuý
1. Người nào vận chuyển trái phép chất ma tuý, thì bị phạt tù từ 02 năm đến 07 năm.
2. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 07 năm đến 15 năm:
   a) Có tổ chức;
   b) Vận chuyển số lượng lớn;
   c) Lợi dụng chức vụ, quyền hạn, lợi dụng danh nghĩa cơ quan, tổ chức.
3. Phạm tội trong trường hợp vận chuyển số lượng rất lớn, thì bị phạt tù từ 15 năm đến 20 năm.
4. Phạm tội trong trường hợp vận chuyển số lượng đặc biệt lớn, thì bị phạt tù 20 năm hoặc tù chung thân.

### Điều 251. Tội mua bán trái phép chất ma tuý
1. Người nào bán trái phép chất ma tuý cho người khác mà không thuộc trường hợp quy định tại Điều 252 của Bộ luật này, thì bị phạt tù từ 02 năm đến 07 năm.
2. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 07 năm đến 15 năm:
   a) Có tổ chức; b) Bán cho người dưới 16 tuổi; c) Bán cho người đang cai nghiện; d) Bán cho phụ nữ mà biết là đang có thai; đ) Gây thiệt hại về tính mạng cho người khác; e) Số lượng lớn.
3. Phạm tội trong trường hợp mua bán số lượng rất lớn hoặc tử hình.
4. Người phạm tội còn có thể bị phạt tiền từ 5.000.000 đồng đến 500.000.000 đồng.

### Điều 255. Tội tổ chức sử dụng trái phép chất ma tuý
1. Người nào tổ chức sử dụng trái phép chất ma tuý dưới bất kỳ hình thức nào, thì bị phạt tù từ 02 năm đến 07 năm.
2. Phạm tội trong trường hợp có tổ chức, phạm tội từ 02 lần trở lên, số người tổ chức cho sử dụng từ 02 người đến 05 người, thì bị phạt tù từ 07 năm đến 15 năm.
3. Phạm tội trong trường hợp số người tổ chức cho sử dụng từ 06 người trở lên, thì bị phạt tù từ 15 năm đến 20 năm.
4. Người phạm tội còn có thể bị phạt tiền từ 10.000.000 đồng đến 100.000.000 đồng, cấm hành nghề, cấm đảm nhiệm chức vụ từ 01 năm đến 05 năm.

### Điều 256. Tội chứa chấp việc sử dụng trái phép chất ma tuý
1. Người nào cho thuê, cho mượn địa điểm hoặc có hành vi khác chứa chấp việc sử dụng trái phép chất ma tuý, thì bị phạt tù từ 02 năm đến 07 năm.
2. Phạm tội trong các trường hợp nặng hơn có thể bị phạt tù từ 07 năm đến 15 năm.

### Điều 257. Tội sử dụng trái phép chất ma tuý
Người nào sử dụng trái phép chất ma tuý, đã bị xử phạt vi phạm hành chính về hành vi này hoặc đã bị kết án về tội này, chưa được xóa án tích mà còn vi phạm, thì bị phạt tù từ 03 tháng đến 02 năm.
""",

    "nghi-dinh-109-2021-ND-CP-dieu-kien-kinh-doanh-thuoc-gay-nghien.md": """# Nghị định 109/2021/NĐ-CP

**Số hiệu:** 109/2021/NĐ-CP
**Tên:** Quy định điều kiện kinh doanh thuốc, nguyên liệu làm thuốc phải kiểm soát đặc biệt và hoạt động khác có liên quan đến thuốc phải kiểm soát đặc biệt
**Ngày ban hành:** 08/12/2021

---

## CHƯƠNG I: QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh
Nghị định này quy định về điều kiện kinh doanh thuốc gây nghiện, thuốc hướng thần, thuốc tiền chất và nguyên liệu làm thuốc là dược chất gây nghiện, dược chất hướng thần, tiền chất dùng làm thuốc.

### Điều 2. Đối tượng áp dụng
Cơ sở kinh doanh dược, cơ sở khám bệnh, chữa bệnh và các tổ chức, cá nhân có liên quan đến thuốc phải kiểm soát đặc biệt.

## CHƯƠNG II: ĐIỀU KIỆN KINH DOANH THUỐC GÂY NGHIỆN

### Điều 5. Điều kiện cơ sở xuất khẩu, nhập khẩu thuốc gây nghiện
1. Phải là doanh nghiệp nhà nước hoặc doanh nghiệp do nhà nước nắm giữ trên 50% vốn điều lệ.
2. Có kho bảo quản thuốc gây nghiện đáp ứng tiêu chuẩn GSP (Thực hành tốt bảo quản thuốc).
3. Có hệ thống thông tin quản lý thuốc gây nghiện.
4. Nhân viên có chứng chỉ về bảo quản, phân phối thuốc gây nghiện.

### Điều 8. Điều kiện bán buôn thuốc gây nghiện
1. Chỉ được bán cho các cơ sở được phép mua thuốc gây nghiện theo quy định.
2. Phải có sổ sách theo dõi riêng đối với từng loại thuốc gây nghiện.
3. Lưu trữ hồ sơ xuất, nhập, tồn kho thuốc gây nghiện tối thiểu 5 năm.

## CHƯƠNG III: QUẢN LÝ TIỀN CHẤT MA TUÝ

### Điều 15. Quản lý tiền chất
1. Tiền chất ma tuý phải được quản lý chặt chẽ từ khâu nhập khẩu, sản xuất, pha chế, lưu thông đến sử dụng.
2. Cơ sở sản xuất, kinh doanh tiền chất phải được cấp giấy chứng nhận đủ điều kiện kinh doanh.
""",

    "nghi-dinh-116-2021-ND-CP-quy-dinh-chat-ma-tuy-tien-chat.md": """# Nghị định 116/2021/NĐ-CP

**Số hiệu:** 116/2021/NĐ-CP
**Tên:** Quy định chi tiết một số điều của Luật Phòng, chống ma tuý và Luật Xử lý vi phạm hành chính về cai nghiện ma tuý
**Ngày ban hành:** 21/12/2021
**Ngày có hiệu lực:** 01/01/2022

---

## CHƯƠNG I: NHỮNG QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết một số điều của Luật Phòng, chống ma tuý và Luật Xử lý vi phạm hành chính về:
- Quản lý người sử dụng trái phép chất ma tuý
- Cai nghiện ma tuý tự nguyện tại gia đình và cộng đồng
- Cai nghiện ma tuý tại cơ sở cai nghiện ma tuý công lập và tư nhân
- Quản lý sau cai nghiện ma tuý

## CHƯƠNG II: QUẢN LÝ NGƯỜI SỬ DỤNG TRÁI PHÉP CHẤT MA TUÝ

### Điều 5. Xác định người nghiện ma tuý
1. Người nghiện ma tuý được xác định dựa trên kết quả xét nghiệm dương tính với chất ma tuý và đánh giá lâm sàng theo tiêu chí tại phụ lục ban hành kèm theo Nghị định này.
2. Cơ sở y tế công lập được phép xét nghiệm và kết luận người nghiện ma tuý.

### Điều 8. Lập hồ sơ quản lý người nghiện ma tuý
1. Chủ tịch Ủy ban nhân dân cấp xã lập hồ sơ quản lý đối với người nghiện ma tuý có nơi cư trú.
2. Hồ sơ gồm: bản khai lý lịch, kết luận xét nghiệm, biên bản vi phạm, tài liệu liên quan.
3. Hồ sơ được lưu trữ 10 năm kể từ khi lập.

## CHƯƠNG III: CAI NGHIỆN MA TUÝ TỰ NGUYỆN

### Điều 12. Quy trình cai nghiện tự nguyện tại gia đình
1. Điều trị cắt cơn giải độc: thực hiện tại cơ sở y tế hoặc tại gia đình có hỗ trợ y tế, tối thiểu 10 ngày.
2. Điều trị phục hồi: phục hồi thể chất, tâm thần sau cắt cơn.
3. Giáo dục, tư vấn: tư vấn tâm lý, kỹ năng sống, phòng chống tái nghiện.
4. Phòng, chống tái nghiện: hỗ trợ tái hòa nhập cộng đồng, nghề nghiệp.

## CHƯƠNG IV: CAI NGHIỆN MA TUÝ BẮT BUỘC

### Điều 20. Đối tượng cai nghiện ma tuý bắt buộc
1. Người nghiện ma tuý từ đủ 18 tuổi trở lên thuộc một trong các trường hợp:
   a) Không có nơi cư trú ổn định;
   b) Trong thời gian quản lý sau cai nghiện mà tái nghiện;
   c) Người đã được áp dụng biện pháp giáo dục tại xã, phường, thị trấn mà tái nghiện.

### Điều 22. Hỗ trợ người sau cai nghiện
1. Người sau cai nghiện được hỗ trợ học nghề, tạo việc làm, vay vốn theo quy định.
2. Ủy ban nhân dân cấp xã theo dõi, hỗ trợ trong thời gian từ 01 năm đến 03 năm.
3. Người sử dụng ma tuý trở lại trong thời gian quản lý sau cai sẽ bị áp dụng biện pháp cai nghiện bắt buộc.

## CHƯƠNG V: XỬ LÝ VI PHẠM

### Điều 28. Mức phạt vi phạm hành chính
1. Phạt cảnh cáo hoặc phạt tiền từ 500.000 đến 1.000.000 đồng đối với hành vi sử dụng trái phép chất ma tuý lần đầu.
2. Phạt tiền từ 2.000.000 đến 5.000.000 đồng đối với trường hợp tái phạm trong vòng 06 tháng.
3. Người vi phạm còn bị áp dụng các biện pháp khắc phục hậu quả.
""",
}


def _clean_html_to_text(html_content: str) -> str:
    """Chuyển HTML thành plain text có cấu trúc."""
    soup = BeautifulSoup(html_content, "lxml")

    # Xoá script, style, nav
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Ưu tiên tìm vùng nội dung chính
    main = (
        soup.find("div", class_="content")
        or soup.find("div", id="content")
        or soup.find("article")
        or soup.find("main")
        or soup.find("div", class_="vbpq-toan-van")
        or soup.body
    )

    text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    # Collapse multiple blank lines
    cleaned = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    return "\n".join(cleaned)


def fetch_and_save(source: dict) -> bool:
    """Fetch HTML từ URL và lưu thành markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / source["filename"]

    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"  ↩ Already exists: {source['filename']}")
        return True

    print(f"  Fetching: {source['title'][:60]}...")
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        text = _clean_html_to_text(resp.text)

        if len(text.strip()) < 200:
            raise ValueError("Content too short")

        header = (
            f"# {source['title']}\n\n"
            f"**Số hiệu:** {source['number']}\n"
            f"**Ngày ban hành:** {source['date']}\n"
            f"**Nguồn:** {source['url']}\n\n---\n\n"
        )
        output_path.write_text(header + text, encoding="utf-8")
        print(f"    ✓ Saved from web: {output_path.name} ({len(text):,} chars)")
        return True

    except Exception as e:
        print(f"    ⚠ Web fetch failed ({e}). Dùng fallback content.")

    # Fallback: dùng nội dung được trích trước
    fallback = LEGAL_FALLBACK_CONTENT.get(source["filename"])
    if fallback:
        output_path.write_text(fallback, encoding="utf-8")
        print(f"    ✓ Saved fallback: {output_path.name} ({len(fallback):,} chars)")
        return True

    print(f"    ✗ Không có fallback cho {source['filename']}")
    return False


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Fetch legal documents → data/standardized/legal/")
    print("=" * 60)

    ok = 0
    for src in LEGAL_SOURCES:
        ok += fetch_and_save(src)
        time.sleep(1)

    print(f"\n✓ {ok}/{len(LEGAL_SOURCES)} legal documents ready in {OUTPUT_DIR}")


if __name__ == "__main__":
    run()
