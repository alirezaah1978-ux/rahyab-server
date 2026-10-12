# -*- coding: utf-8 -*-
"""📡 سرور فرمان رهیاب — روی Hugging Face Space (رایگان، بدون کارت بانکی)
وب‌هوک تلگرام → پاسخ لحظه‌ای (بدون تأخیر ۱۰ دقیقه‌ای)
+ داشبورد وضعیت + نگه‌داشتن Space بیدار با /ping

متغیرهای محیطی (Space → Settings → Variables and secrets):
  TELEGRAM_BOT_TOKEN   توکن ربات
  TELEGRAM_CHAT_ID     چت‌آیدی مالک (فقط او فرمان می‌دهد)
  WEBHOOK_SECRET       رمز مسیر وب‌هوک (خودت بساز، مثلاً 20 حرف تصادفی)
  GH_PAT               (اختیاری) توکن گیت‌هاب برای فرمان‌های سنگین (قیمت/فرصت/اسکن)
  GH_REPO              alirezaah1978-ux/lead-hunter
"""
import json, os, re, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT   = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
SECRET = os.environ.get("WEBHOOK_SECRET", "rahyaab")
PAT    = os.environ.get("GH_PAT", "")
REPO   = os.environ.get("GH_REPO", "alirezaah1978-ux/lead-hunter")
PORT   = int(os.environ.get("PORT", "7860"))

_cache = {"t": 0, "html": ""}

HELP = """🎛️ <b>مرکز فرمان رهیاب</b>
• <b>رادار</b> — دلار/طلا/سکه/کریپتو (لحظه‌ای)
• <b>وضعیت</b> — خلاصه‌ی داده‌های موتور
• <b>قیمت</b> · <b>فرصت</b> · <b>پست</b> — انتشار فوری در کانال‌ها
• <b>اسکن</b> — عمده‌فروشی‌های تلگرام (۳ ساعت اخیر)
• <b>راهنما</b> — همین متن"""

KEYS = [("price_dollar_rl","دلار",1),("geram18","گرم طلا ۱۸",1),("sekeb","سکه امامی",1),
        ("crypto-bitcoin","بیت‌کوین",10),("crypto-ethereum","اتریوم",10)]

def tg(method, **p):
    if not TOKEN: return {"ok": False, "err": "no token"}
    url = f"https://api.telegram.org/bot{TOKEN}/{method}?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(url, timeout=25) as r: return json.load(r)
    except Exception as e:
        return {"ok": False, "err": type(e).__name__}

def send(text):
    return tg("sendMessage", chat_id=CHAT, text=text[:3900], parse_mode="HTML",
              disable_web_page_preview="true")

def get_json(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def clean_num(s):
    s = re.sub(r"<[^>]+>", "", str(s)).replace(",", "").replace("%", "").replace("٪", "").strip()
    try: return float(s)
    except Exception: return 0.0

def radar_lines():
    out = []
    for k, fa, _ in KEYS:
        try:
            d = get_json(f"https://api.tgju.org/v1/market/indicator/summary-table-data/{k}")
            row = d["data"][0]
            price, pct = clean_num(row[0]), clean_num(row[5])
            unit = "$" if k.startswith("crypto") else "ت"
            if not k.startswith("crypto"): price /= 10
            arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "=")
            out.append(f"{fa}: {price:,.0f} {unit}  {arrow}{pct:+.2f}٪")
        except Exception:
            out.append(f"{fa}: (خطای دریافت)")
    return out

def status_text():
    try:
        d = get_json(f"https://raw.githubusercontent.com/{REPO}/main/engine/output/real_report.json")
        s = d.get("stats", {})
        return (f"📋 <b>وضعیت موتور</b>\n"
                f"آگهی بررسی‌شده: {s.get('unique','?')}\nفرصت شناسایی‌شده: {s.get('pairs','?')}\n"
                f"تأمین‌کننده یدکی: ۴۰\nکانال عمده فعال: ۷\nگزارش: {d.get('generated_at','?')}")
    except Exception as e:
        return f"⚠ وضعیت خوانده نشد ({type(e).__name__})"

def dispatch(kind):
    if not PAT: return "⚠ برای این فرمان، GH_PAT را در Settings اسپیس ست کن."
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/actions/workflows/channel-posts.yml/dispatches",
            data=json.dumps({"ref": "main", "inputs": {"type": kind}}).encode(),
            headers={"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json",
                     "User-Agent": "rahyaab"}, method="POST")
        urllib.request.urlopen(req, timeout=25)
        return f"⏳ فرمان «{kind}» ثبت شد — نتیجه تا ۱–۲ دقیقه در کانال/پیوی می‌آید."
    except Exception as e:
        return f"⚠ ارسال فرمان نشد ({type(e).__name__})"

def handle(text):
    t = text.strip()
    if any(x in t for x in ("راهنما", "/help", "/start", "help")): return HELP
    if "رادار" in t: return "📡 <b>رادار</b>\n" + "\n".join(radar_lines())
    if "وضعیت" in t: return status_text()
    if "اسکن" in t and PAT:
        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/actions/workflows/omde-scan.yml/dispatches",
                data=json.dumps({"ref": "main"}).encode(),
                headers={"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json",
                         "User-Agent": "rahyaab"}, method="POST")
            urllib.request.urlopen(req, timeout=25)
            return "⏳ اسکن عمده شروع شد — نتیجه در پیوی می‌آید."
        except Exception:
            pass
    if "قیمت" in t: return dispatch("price")
    if "فرصت" in t: return dispatch("opps")
    if "پست" in t or "درس" in t: return dispatch("insight")
    return "🤔 نشناختم.\n\n" + HELP

DASH = """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>رهیاب — پنل</title>
<style>body{{background:#0d1117;color:#e6edf3;font-family:system-ui,Segoe UI,Tahoma;margin:0;padding:24px}}
h1{{font-size:22px}} .c{{background:#161b22;border:1px solid #21262d;border-radius:14px;padding:16px;margin:10px 0;max-width:760px}}
.m{{color:#7ee2a8;font-family:monospace;direction:ltr;text-align:left;white-space:pre-wrap}}
.s{{color:#8b9bb5;font-size:13px}}</style>
<h1>📡 پنل رهیاب</h1>
<div class="c"><b>رادار زنده</b><div class="m">{radar}</div></div>
<div class="c"><b>وضعیت موتور</b><div class="m">{status}</div></div>
<div class="c"><b>فرمان‌های ربات</b><div class="s">راهنما · وضعیت · رادار · قیمت · فرصت · اسکن · پست</div>
<div class="s">وضعیت: وب‌هوک ❯ {hook} | گیت‌هاب ❯ {pat}</div></div>
<p class="s">سرور روی Hugging Face Space رایگان اجرا می‌شود — /ping برای بیدار نگه‌داشتن.</p>
"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/ping":
            return self._send(200, "ok", "text/plain")
        if p == "/":
            if time.time() - _cache["t"] > 60:
                _cache["html"] = DASH.format(radar="\n".join(radar_lines()),
                                             status=re.sub(r"<[^>]+>", "", status_text()),
                                             hook="✅" if SECRET else "❌", pat="✅" if PAT else "—")
                _cache["t"] = time.time()
            return self._send(200, _cache["html"])
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        if not p.startswith(f"/webhook/{SECRET}"):
            return self._send(403, "forbidden", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", 0))
            u = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(200, "ok", "text/plain")
        msg = u.get("message") or u.get("edited_message") or {}
        if str((msg.get("chat") or {}).get("id")) == CHAT and (msg.get("text") or "").strip():
            threading.Thread(target=lambda: send(handle(msg["text"])), daemon=True).start()
        self._send(200, "ok", "text/plain")

    def log_message(self, *a): pass

if __name__ == "__main__":
    print(f"📡 سرور رهیاب روی پورت {PORT} | ربات: {'✅' if TOKEN else '—'} | وب‌هوک: {'✅' if SECRET else '—'}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
