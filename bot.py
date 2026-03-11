"""
🏅 Bot Telegram Giá Vàng - Quốc Bảo Lâm
Phiên bản GitHub Actions (chạy mỗi 5 phút tự động)
"""

import requests
import re
import json
import os
from datetime import datetime

# =============================================
# TOKEN lấy từ GitHub Secrets (không cần điền tay)
# =============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID   = os.environ.get("CHAT_ID", "")

STATE_FILE = "price_state.json"

LOAI_VANG = [
    {"id": 2, "ten": "Vàng 9999 - 24K"},
    {"id": 3, "ten": "Vàng 23K"},
    {"id": 4, "ten": "Vàng 16K"},
]

API_URL = "https://quocbaolam.com/api/bieudo.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quocbaolam.com/gia-vang",
    "Origin": "https://quocbaolam.com",
    "Content-Type": "application/x-www-form-urlencoded",
}


def lay_gia_vang(loai_id, thang, nam):
    try:
        res = requests.post(
            API_URL,
            data={"id": loai_id, "month": thang, "year": nam},
            headers=HEADERS,
            timeout=10,
        )
        res.raise_for_status()
        match = re.search(r"var CHARTS\s*=\s*(\{.*?\});", res.text, re.DOTALL)
        if not match:
            return None
        charts = json.loads(match.group(1))
        ngay_idx = datetime.now().day - 1
        gia_mua = charts["price1"][ngay_idx]
        gia_ban = charts["price"][ngay_idx]
        while ngay_idx > 0 and (gia_mua == 0 or gia_ban == 0):
            ngay_idx -= 1
            gia_mua = charts["price1"][ngay_idx]
            gia_ban = charts["price"][ngay_idx]
        return {"gia_mua": gia_mua, "gia_ban": gia_ban}
    except Exception as e:
        print(f"  Loi khi lay id={loai_id}: {e}")
        return None


def fmt(so):
    return f"{so:,}".replace(",", ".") + " d"


def xu_huong(moi, cu):
    if moi > cu:
        return f"Tang +{fmt(moi - cu)}"
    elif moi < cu:
        return f"Giam -{fmt(cu - moi)}"
    return "Khong doi"


def gui_telegram(tin_nhan, label=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": tin_nhan,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        data = res.json()
        if data.get("ok"):
            print(f"  Da gui Telegram [{label}]")
            return True
        else:
            print(f"  Telegram loi: {data.get('description')}")
            return False
    except Exception as e:
        print(f"  Loi gui Telegram: {e}")
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
    now = datetime.now()
    thang, nam = now.month, now.year
    gio = now.hour

    print(f"[{now.strftime('%H:%M:%S')}] Dang kiem tra gia vang...")

    gia_cu = doc_gia_cu()
    gia_moi = {}
    thay_doi = []
    lan_dau = len(gia_cu) == 0

    for loai in LOAI_VANG:
        data = lay_gia_vang(loai["id"], thang, nam)
        if not data or data["gia_mua"] == 0:
            continue
        gia_moi[str(loai["id"])] = data
        cu = gia_cu.get(str(loai["id"]))
        if cu and (data["gia_mua"] != cu["gia_mua"] or data["gia_ban"] != cu["gia_ban"]):
            thay_doi.append({"ten": loai["ten"], "moi": data, "cu": cu})
            print(f"  [{loai['ten']}] THAY DOI!")
        else:
            print(f"  [{loai['ten']}] Mua: {fmt(data['gia_mua'])} | Ban: {fmt(data['gia_ban'])}")

    luu_gia_moi(gia_moi)

    if thay_doi:
        lines = [
            "🚨 <b>CẢNH BÁO: GIÁ VÀNG VỪA THAY ĐỔI!</b>",
            f"⏰ {now.strftime('%H:%M - %d/%m/%Y')}",
            "━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for item in thay_doi:
            moi, cu, ten = item["moi"], item["cu"], item["ten"]
            lines += [
                f"💎 <b>{ten}</b>",
                f"  Mua: {fmt(cu['gia_mua'])} → <b>{fmt(moi['gia_mua'])}</b>  📈📉 {xu_huong(moi['gia_mua'], cu['gia_mua'])}",
                f"  Bán: {fmt(cu['gia_ban'])} → <b>{fmt(moi['gia_ban'])}</b>  📈📉 {xu_huong(moi['gia_ban'], cu['gia_ban'])}",
                "",
            ]
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━",
            '🔗 <a href="https://quocbaolam.com/gia-vang">Xem chi tiet</a>',
            "📞 Hotline: 077 939 7939",
        ]
        gui_telegram("\n".join(lines), "canh bao thay doi")

    elif gio in [8, 12, 17] or lan_dau:
        label = "khoi dong lan dau" if lan_dau else f"ban tin {gio}h"
        tieu_de = "🤖 <b>QUỐC BẢO LÂM BOT XIN KÍNH CHÀO</b>" if lan_dau else "🏅 <b>GIÁ VÀNG QUỐC BẢO LÂM</b>"
        lines = [
            tieu_de,
            f"📅 {now.strftime('%H:%M - %d/%m/%Y')}",
            "━━━━━━━━━━━━━━━━━━━━━",
            "",
            "📌 <b>Giá hiện tại:</b>",
            "",
        ]
        for loai in LOAI_VANG:
            data = gia_moi.get(str(loai["id"]))
            if data and data["gia_mua"] > 0:
                lines += [
                    f"💰 <b>{loai['ten']}</b>",
                    f"  🟢 Mua: <code>{fmt(data['gia_mua'])}</code>",
                    f"  🔴 Bán: <code>{fmt(data['gia_ban'])}</code>",
                    "",
                ]
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━",
            "🔍 Tu dong kiem tra moi <b>5 phut</b>",
            "🔔 Bot se thong bao ngay khi gia thay doi!",
        ]
        gui_telegram("\n".join(lines), label)
    else:
        print("  Gia khong doi, khong gui Telegram.")


if __name__ == "__main__":
    main()
