"""
Bot Telegram Giá Vàng - Quốc Bảo Lâm
Chỉ gửi khi giá thay đổi hoặc chạy manual
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import json
import os
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID   = os.environ.get("CHAT_ID", "")

STATE_FILE = "price_state.json"

VN_TZ = timezone(timedelta(hours=7))

LOAI_VANG = [
    {"ten": "Vàng 9999 Quốc Bảo Lâm"},
    {"ten": "Vàng 98 Quốc Bảo Lâm"},
    {"ten": "Vàng QBL 98%"},
    {"ten": "Vàng QBL 75% 18k"},
    {"ten": "Vàng QBL 610"},
]

URL = "https://giavangmaothiet.com/gia-vang-quoc-bao-lam-hom-nay/"

def get_session():
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return session

def lay_gia_vang():
    try:
        session = get_session()
        res = session.get(URL, timeout=15)
        res.raise_for_status()
        text = res.text

        m_time = re.search(r'Cập nhật lúc:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
        update_time = m_time.group(1) if m_time else None

        gia = {}
        for loai in LOAI_VANG:
            ten = loai["ten"]
            pat = re.escape(ten) + r'[\s\S]*?(\d{1,3}(?:\.\d{3})+)\s*[\s\S]*?(\d{1,3}(?:\.\d{3})+)'
            match = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            if match:
                mua = int(match.group(1).replace('.', ''))
                ban = int(match.group(2).replace('.', ''))
                gia[ten] = {"gia_mua": mua, "gia_ban": ban}
        return gia, update_time
    except Exception as e:
        print(f"  Lỗi scrape: {e}")
        return {}, None

def fmt(so):
    return f"{so:,}".replace(",", ".") + "₫"

def xu_huong(moi, cu):
    if moi > cu: return f"📈 +{fmt(moi - cu)}"
    if moi < cu: return f"📉 -{fmt(cu - moi)}"
    return "➡️ Không đổi"

def gui_telegram(tin_nhan):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": CHAT_ID, "text": tin_nhan, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=10)
        return res.json().get("ok", False)
    except:
        return False

def doc_gia_cu():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def luu_gia_moi(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def main():
    now = datetime.now(VN_TZ)
    print(f"[{now.strftime('%H:%M:%S')} ICT] Đang kiểm tra...")

    gia_moi, update_time = lay_gia_vang()
    if not gia_moi:
        print("  Không lấy được dữ liệu")
        return

    gia_cu = doc_gia_cu()
    thay_doi = []
    co_gia_cu = len(gia_cu) > 0

    for loai in LOAI_VANG:
        ten = loai["ten"]
        data = gia_moi.get(ten)
        if not data: continue
        cu = gia_cu.get(ten)
        if co_gia_cu and cu and (data["gia_mua"] != cu["gia_mua"] or data["gia_ban"] != cu["gia_ban"]):
            thay_doi.append({"ten": ten, "moi": data, "cu": cu})

    luu_gia_moi(gia_moi)

    # Chỉ gửi tin nhắn khi có thay đổi giá
    if thay_doi:
        lines = [
            "🚨 <b>CẢNH BÁO: GIÁ VÀNG VỪA THAY ĐỔI!</b>",
            f"⏰ {now.strftime('%H:%M - %d/%m/%Y')} (Giờ VN)",
            f"📌 Cập nhật lúc: {update_time or 'N/A'}",
            "━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        for item in thay_doi:
            moi, cu, ten = item["moi"], item["cu"], item["ten"]
            lines += [
                f"💎 <b>{ten}</b>",
                f"  Mua: {fmt(cu['gia_mua'])} → <b>{fmt(moi['gia_mua'])}</b>  {xu_huong(moi['gia_mua'], cu['gia_mua'])}",
                f"  Bán: {fmt(cu['gia_ban'])} → <b>{fmt(moi['gia_ban'])}</b>  {xu_huong(moi['gia_ban'], cu['gia_ban'])}",
                ""
            ]
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━",
            '🔗 <a href="https://giavangmaothiet.com/gia-vang-quoc-bao-lam-hom-nay/">Xem chi tiết</a>',
            "📞 Hotline: 077 939 7939"
        ]
        gui_telegram("\n".join(lines))
        print("  Đã gửi cảnh báo thay đổi giá")
    else:
        print("  Giá không thay đổi, không gửi tin nhắn")

if __name__ == "__main__":
    main()
