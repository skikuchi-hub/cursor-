# -*- coding: utf-8 -*-
"""EXAmuse 景品仕入れ: 共通モジュール（メール解析・スプレッドシート生成）"""
import os, re, json, glob, email, unicodedata, datetime, tempfile, shutil, subprocess
from email import policy
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

HOME = os.path.expanduser("~")
APP_DIR = os.path.join(HOME, "Library", "Application Support", "examuse-order")
OUT_DIR = os.path.join(HOME, "EXAmuse景品仕入れ")          # 実体（Desktopはエイリアス）
DESKTOP_LINK = os.path.join(HOME, "Desktop", "EXAmuse景品仕入れ")
XLSX_NAME = "仕入れ想定商品.xlsx"
XLSX_PATH = os.path.join(OUT_DIR, XLSX_NAME)
LOCK_PATH = os.path.join(OUT_DIR, "~$" + XLSX_NAME)
IMG_DIR = os.path.join(OUT_DIR, "画像")
ORDER_DIR = os.path.join(OUT_DIR, "発注書")
DB_PATH = os.path.join(APP_DIR, "db.json")
LOG_PATH = os.path.join(HOME, "Library", "Logs", "examuse-sync.log")
MAIL_ROOT = os.path.join(HOME, "Library", "Mail", "V10",
                         "B36077F8-8538-4E49-8C15-C9EFB2095DAF", "INBOX.mbox")
SENDER_FILTER = "8infinity.jp"
MAIL_ACCOUNT = "EXAmuse"
MAIL_BOX = "INBOX"

SHEET_MAIN = "商品一覧"
SHEET_IMG = "画像一覧"
SHEET_HIST = "発注履歴"
SHEET_SET = "設定"

DEFAULT_SETTINGS = [
    ("発注先メール", "inf_main@8infinity.jp", "発注メールの宛先"),
    ("発注先会社名", "株式会社インフィニティ", "発注書の宛名（御中）"),
    ("発注先担当者", "", "空欄なら「ご担当者様」"),
    ("CC", "", "複数はカンマ区切り（空欄可）"),
    ("BCC", "amuse@exploration-holdings.jp", "毎回必ず入れる控え。複数はカンマ区切り"),
    ("差出人メール", "amuse@exploration-holdings.jp", "Apple MailのEXAmuseアカウント"),
    ("差出人表示名", "Exploration Holdings株式会社", ""),
    ("自社名", "Exploration Holdings株式会社", "発注書の発注元"),
    ("自社部署", "", "例：アミューズメント事業部（空欄可）"),
    ("自社郵便番号", "〒810-0041", ""),
    ("自社住所", "福岡県福岡市中央区大名2-2-7 大名センタービル8階", ""),
    ("自社TEL", "092-707-1727", ""),
    ("納品先名", "", "空欄なら発注書に納品先欄を出しません"),
    ("納品先住所", "", ""),
    ("納品先TEL", "", ""),
    ("納品希望日", "", "例：最短 / 10月20日着希望"),
    ("発注金額の上限警告", "300000", "1回の発注合計(税抜)がこの金額を超えると警告"),
    ("Mac発注時の担当者名", "菊地", "Macの「発注書作成＆メール送信.command」から発注したときの担当者名"),
    ("景品マスタ連携", "する", "発注メールを送信したとき「クレーンゲーム日報」の景品マスタへ行を追加する（する／しない）※下書きでは追加しない"),
    ("件名", "【発注書】{自社名} {日付}", "{自社名} {日付} {発注No} が使えます"),
    ("本文冒頭", "いつも大変お世話になっております。\n{自社名}でございます。\n\n下記の通り発注をお願いいたします。\n（発注書を添付しておりますのでご確認ください）", ""),
    ("本文末尾", "ご確認のうえ、納期のご連絡をいただけますと幸いです。\n何卒よろしくお願いいたします。", ""),
    ("署名", "――――――――――――――――――――――――――――――――\nExploration Holdings株式会社\n〒810-0041\n福岡県福岡市中央区大名2-2-7 大名センタービル8階\nMail：amuse@exploration-holdings.jp\nTel：092-707-1727\n――――――――――――Exploration Holdings INC――――――――――――", ""),
]

# 商品一覧の列定義: (ヘッダ, 幅, キー, 編集可)
COLS = [
    ("受信日", 11, "received", False),
    ("商品名", 44, "name", True),
    ("品番", 12, "code", True),
    ("メーカー", 12, "maker", True),
    ("入数\n(1ケース)", 8, "qty_per_case", True),
    ("単価\n(税抜)", 9, "price", True),
    ("ケース金額", 11, None, False),       # 数式
    ("上代\n(税抜)", 9, "retail", True),
    ("種類・アソート", 18, "variety", True),
    ("納期・発売", 18, "delivery", True),
    ("ハーフ", 8, "half", True),
    ("送料・条件", 22, "shipping", True),
    ("販売制限・注意", 24, "restrict", True),
    ("発注\nケース数", 9, "order_cases", True),
    ("発注個数", 9, None, False),          # 数式
    ("発注金額", 11, None, False),         # 数式
    ("機械タイプ", 10, "kind", True),
    ("発注備考", 18, "order_memo", True),
    ("発注状況", 20, "status", True),
    ("チェック結果", 20, "check", True),
    ("画像", 36, None, False),
    ("件名", 40, "subject", False),
    ("メールID", 9, "mail_id", False),
    ("商品キー", 12, "key", False),
    ("メール原文(数量・金額)", 30, "src", False),
]
MACHINE_KINDS = ["カリーノ用", "4人機用"]
COL_IDX = {c[2]: i + 1 for i, c in enumerate(COLS) if c[2]}
COL_CASE_AMT = 7; COL_ORDER_PCS = 15; COL_ORDER_AMT = 16; COL_IMG = 21

def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with open(LOG_PATH, "a") as f: f.write(line + "\n")
    except Exception: pass

def notify(title, text):
    try:
        subprocess.run(["osascript", "-e",
                        'display notification "%s" with title "%s"' % (text.replace('"', "'"), title.replace('"', "'"))],
                       timeout=10)
    except Exception: pass

# ---------------- DB ----------------
def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, encoding="utf-8") as f: return json.load(f)
    return {"mails": {}, "products": {}, "orders": [], "settings": {}, "pending_xlsx": False}

def save_db(db):
    os.makedirs(APP_DIR, exist_ok=True)
    tmp = DB_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DB_PATH)

# ---------------- メール読み込み ----------------
_KEEP = {chr(c): chr(0xE000 + i) for i, c in enumerate(list(range(0x2460, 0x2500)) + list(range(0x3220, 0x3260)))}
_KEEP_R = {v: k for k, v in _KEEP.items()}
def norm(s):
    """NFKC正規化（①②㈰ 等の丸数字は保持）"""
    s = s or ""
    s = "".join(_KEEP.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKC", s).replace("\u00a0", " ")
    return "".join(_KEEP_R.get(ch, ch) for ch in s)

def _jis_to_cp932(b):
    """ISO-2022-JP を cp932 経由でデコード（㈰ 等のNEC特殊文字対応）"""
    out = bytearray(); mode = "ascii"; i = 0
    while i < len(b):
        if b[i] == 0x1B and i + 2 < len(b):
            seq = b[i:i+3]
            if seq in (b"\x1b$B", b"\x1b$@"): mode = "kanji"; i += 3; continue
            if seq in (b"\x1b(B", b"\x1b(J"): mode = "ascii"; i += 3; continue
            if seq == b"\x1b(I": mode = "kana"; i += 3; continue
        if mode == "kanji" and i + 1 < len(b) and b[i] >= 0x21:
            hi, lo = b[i], b[i+1]
            if hi % 2: lo += 0x1F if lo < 0x60 else 0x20; hi = (hi + 1) // 2 + 0x70
            else: lo += 0x7E; hi = hi // 2 + 0x70
            if hi > 0x9F: hi += 0x40
            out += bytes([hi, lo]); i += 2; continue
        if mode == "kana": out.append(b[i] + 0x80); i += 1; continue
        out.append(b[i]); i += 1
    return out.decode("cp932", errors="replace")

def smart_decode(b, charset):
    cs = (charset or "utf-8").lower()
    try: return b.decode(cs)
    except Exception:
        if "2022" in cs or "jis" in cs: return _jis_to_cp932(b)
        return b.decode(cs, errors="replace")

def dec_header(v):
    if v is None: return ""
    try:
        parts = decode_header(str(v)); out = ""
        for val, cs in parts:
            if isinstance(val, bytes):
                out += smart_decode(val, cs) if cs else val.decode("raw-unicode-escape", errors="replace")
            else: out += val
        return re.sub(r"[\r\n\t]+", "", out)
    except Exception: return str(v)

def find_emlx_files():
    files = glob.glob(os.path.join(MAIL_ROOT, "**", "Messages", "*.emlx"), recursive=True)
    return sorted(files)

def html_to_text(html):
    html = re.sub(r"(?is)<(style|script|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(td|th)>", "  ", html)          # 表のセル境界で語がくっつかないように（2026-11-02）
    html = re.sub(r"(?i)</(p|div|tr|li|h\d|table)>", "\n", html)
    html = re.sub(r"<[^>]+>", "", html)
    import html as h
    return h.unescape(html)

def list_mail_ids():
    """Apple Mail(AppleScript)から対象送信者のメッセージ一覧 [(id, 受信日時str)] を取得"""
    scr = '''tell application "Mail"
set out to ""
repeat with m in (messages of mailbox "%s" of account "%s" whose sender contains "%s")
set out to out & (id of m) & "|" & (date received of m) & linefeed
end repeat
return out
end tell''' % (MAIL_BOX, MAIL_ACCOUNT, SENDER_FILTER)
    r = subprocess.run(["osascript", "-e", scr], capture_output=True, text=True, timeout=120)
    if r.returncode != 0: raise RuntimeError("Mail一覧取得失敗: " + r.stderr.strip())
    out = []
    for line in r.stdout.splitlines():
        if "|" in line:
            mid, d = line.split("|", 1); out.append((mid.strip(), d.strip()))
    return out

def fetch_source(mid):
    """Apple Mail からメッセージのソース(RFC822)を取得して bytes で返す"""
    scr = '''tell application "Mail"
set m to first message of mailbox "%s" of account "%s" whose id is %s
return source of m
end tell''' % (MAIL_BOX, MAIL_ACCOUNT, mid)
    r = subprocess.run(["osascript", "-e", scr], capture_output=True, timeout=300)
    if r.returncode != 0: raise RuntimeError("Mailソース取得失敗 id=%s: %s" % (mid, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout

def parse_message_bytes(raw, mid, path=""):
    msg = email.message_from_bytes(raw, policy=policy.compat32)
    partial = False
    subject = dec_header(msg["Subject"])
    sender = dec_header(msg["From"])
    try: dt = parsedate_to_datetime(msg["Date"]).astimezone()
    except Exception: dt = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    text = None; html = None; images = []
    for part in msg.walk():
        if part.is_multipart(): continue
        ct = part.get_content_type()
        if ct in ("text/plain", "text/html"):
            try:
                raw_b = part.get_payload(decode=True) or b""
                val = smart_decode(raw_b, part.get_content_charset())
            except Exception: continue
            if ct == "text/plain" and text is None: text = val
            elif ct == "text/html" and html is None: html = val
            continue
        if ct.startswith("image/"):
            payload = part.get_payload(decode=True)
            if not payload: continue
            fn = dec_header(part.get_filename()) or ((part.get("Content-ID") or "img").strip("<>") + ".jpg")
            images.append((fn, payload))
    body = text if text else html_to_text(html or "")
    return {"id": mid, "subject": subject, "from": sender, "date": dt.strftime("%Y-%m-%d %H:%M"),
            "body": body, "images": images, "partial": partial, "path": path}

def save_images(mail):
    """画像をフォルダへ保存し、保存パスのリストを返す（バナー類は除外）"""
    d = os.path.join(IMG_DIR, mail["id"])
    os.makedirs(d, exist_ok=True)
    paths = []
    for fn, payload in mail["images"]:
        fn = re.sub(r'[/\\:*?"<>|]', "_", fn).strip() or "image.jpg"
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            with open(p, "wb") as f: f.write(payload)
        paths.append(p)
    if not paths and mail.get("path"):  # MIMEに無ければ Mail の Attachments フォルダを探す
        for p in glob.glob(os.path.join(os.path.dirname(os.path.dirname(mail["path"])), "Attachments", mail["id"], "**", "*"), recursive=True):
            if os.path.isfile(p) and p.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                dst = os.path.join(d, os.path.basename(p)); shutil.copy(p, dst); paths.append(dst)
    # 小さい inline バナー（image001.jpg 等）は他に画像があれば除外
    main = [p for p in paths if not re.match(r"image\d{3}\.", os.path.basename(p))]
    return main if main else paths

# ---------------- 商品解析 ----------------
QTY_RE = re.compile(r"^(?P<pre>.*?)(?<![\d/])(?P<n>\d{1,4})\s*(?:入り?|個入り?|個|ヶ|pcs|PCS|ケ)\s*(?:単位|[/／]\s*(?:ケース|C/T|CT|カートン))?(?:(?!別途)[^@＠\n]){0,20}?(?<!別途)[@＠]\s*[¥￥]?\s*(?P<p>\d[\d,]*)\s*(?:円|-|ー|―)?\s*(?P<post>.*)$")
# 「入数 72個 単価 630円」「1ケース72個 卸価格 ¥630」のように @ が無い 1 行形式（2026-11-02）
QTY_PRICE2_RE = re.compile(r"^(?P<pre>.*?)(?:入数|入り数|ケース入数|1\s*(?:ケース|C/T|CT|カートン|c/t))?\s*[:：]?\s*(?<![\d/])(?P<n>\d{1,4})\s*(?:個入り?|入り?|個|ヶ|pcs|PCS|ケ)\s*(?:[/／]\s*(?:ケース|C/T|CT|カートン))?[\s　,、/／]*(?:単価|卸価格|卸値|卸|価格|税抜単価|税抜|特価)\s*[:：]?\s*[¥￥]?\s*(?P<p>\d[\d,]*)\s*(?:円|-|ー|―)?\s*(?P<post>.*)$")
DELIV_RE = re.compile(r"(即納|次回|納期|入荷|発売|締切|出荷予定|\d{1,2}月[上中下]?|\d{1,2}/[上中下]|年内|予定)")
NOISE_RE = re.compile(r"(INFINITY|株式会社インフィニティ|TEL\s*[:：]|FAX|携帯\s*[:：]|Mail\s*[:：]|HP\s*[:：]|〒\s*\d|お世話になって|よろしくお願|宜しくお願|ご検討|何卒|詳しくは|北海道や沖縄|納入日より|商品のご案内|重要|申し訳|監修|お問い合わせ|ご了承|お願い致します|お願いいたします|ご案内です|ご案内！|届きました|企画書|破壊力|実は|確保しながら|コンプリート|注意事項|ご確認ください|メーカーより|厳守|お取引先様|お取り置き|伝票|請求|キャンセルのご連絡|担当者まで|ご理解|ご協力|ございます|です！|です。|でした|ます！|ます。)")
RESTRICT_RULES = [
    (r"ネット販売", "ネット販売NG"),
    (r"ネットキャッチャー|オンラインクレーン", "ネットキャッチャー/オンラインクレーンNG"),
    (r"SNS", "SNS掲載NG"),
    (r"東京・神奈川|神奈川・埼玉|首都圏", "東京・神奈川・埼玉・千葉 案内NG"),
    (r"大手オペレーター", "大手オペレーターNG"),
    (r"直送", "アミューズメント施設へ直送"),
    (r"カタログの転用|転用は", "カタログ転用NG"),
    (r"返品は不可|返品.*不可|キャンセル.*不可", "キャンセル・返品不可"),
    (r"減数の可能性", "減数の可能性あり"),
    (r"国内ライセンス", "国内ライセンス品"),
    (r"物販用商品", "物販用商品"),
    (r"なくなり次第", "なくなり次第終了"),
    (r"別途運賃商品|別途送料", "別途送料あり"),
]
CODE_RE = re.compile(r"\b([A-Z]{2,5}-\d{3,6})\b")
# 入数だけの行（例: 「発送単位：72個」「100個単位 （ハーフ送料1000円）」「72入り」）
QTY_ONLY_RE = re.compile(r"^(?:発送単位|販売単位|出荷単位|単位|入数|入り数|ケース入数|数量|1\s*(?:ケース|C/T|CT|カートン|c/t))?\s*[:：=＝]?\s*(?P<n>\d{1,4})\s*(?:個入り?|入り?|個|ヶ|pcs|PCS|p|P|ケ)\s*(?:単位|入り?|[/／]\s*(?:ケース|C/T|CT|カートン))?\s*(?P<post>.*)$")
# 単価だけの行（例: 「特価 @630」「単価＠900円」「@620-」）
PRICE_ONLY_RE = re.compile(r"^(?:(?:特価プライス|プライス|卸単価|納品価格|納価|特価|単価|卸価格|卸値|卸|価格|税抜単価|税抜|お値段|仕入価格|仕入値|仕切り?値?)\s*[:：]?\s*[@＠]?|[@＠])\s*[¥￥]?\s*(?P<p>\d[\d,]*)\s*(?:円|-|ー|―)?\s*(?:[/／]\s*(?:個|1個|pc))?\s*(?:[（(]?税抜[)）]?)?\s*(?P<post>.*)$")
# 商品名の末尾に入数だけが付いた行（例: 「●NICIセサミストリート キーリング3種72入」＋次の行「@980-」）（2026-11-06）
NAME_QTY_RE = re.compile(r"^(?P<pre>.*\D)(?<![\d/])(?P<n>\d{1,4})\s*(?:入り?|個入り?)\s*$")
# 商品名の候補にしない属性行（2026-11-06）
CAND_SKIP_RE = re.compile(r"^(?:締め?日|締切|品番|JAN|サイズ|商品サイズ|パッケージサイズ|種類|アソート|メーカー|個口|上代|全\s*\d+\s*種|インナー|ディスプレイ)")
# 本文をブロックに分ける区切り線（＊＊＊… / ***…）
BLOCK_SEP_RE = re.compile(r"(?m)^[ 　]*[*＊]{5,}[ 　]*$")
RETAIL_RE = re.compile(r"(?:上代|メーカー希望小売価格|希望小売価格|参考上代|定価)\s*[:：]?\s*[¥￥]?\s*(\d[\d,]*)")
NAME_TAIL_RE = re.compile(r"[\s　]*(残\s*\d+(?:\.\d+)?\s*(?:個|ヶ|ケース|c/t|C/T)?)\s*$")

def _num(s):
    try: return int(s.replace(",", ""))
    except Exception: return None

def _clean_name(s):
    s = s.strip(" 　・:：,、/")
    return s

def _attr_from_line(line, prod):
    """上代・ハーフ・送料・メーカー・種類 を行から抽出して prod にセット。何か取れたら True"""
    hit = False
    m = RETAIL_RE.search(line)
    if m and not prod.get("retail"):
        prod["retail"] = _num(m.group(1)); hit = True
    if "ハーフ" in line:
        if "不可" in line: prod.setdefault("half", "不可")
        elif "可" in line or "ハーフの場合" in line or "ハーフ送料" in line or "ハーフ時" in line or "ハーフ別途" in line or (("送料" in line or "運賃" in line) and re.search(r"\d", line)): prod.setdefault("half", "可")
        if ("送料" in line or "運賃" in line) and re.search(r"\d", line):
            prod["shipping"] = (prod.get("shipping", "") + " " + line.strip("＊*※ ")).strip()
        hit = True
    elif "送料" in line or "運賃" in line:
        if len(line) <= 45 and not NOISE_RE.search(line):
            prod["shipping"] = (prod.get("shipping", "") + " " + line.strip("＊*※ ")).strip(); hit = True
    m = re.search(r"メーカー(?!希望)\s*[:：]?\s*([^/／]+)", line)
    if m and not RETAIL_RE.search(line):
        prod["maker"] = m.group(1).strip(); hit = True
    m = re.search(r"^種類\s*[:：]\s*(.+)$", line) or re.search(r"(アソート.{0,15}|.{0,15}アソート)$", line) or re.search(r"(全\s*\d+\s*種.{0,20})", line)
    if m and len(line) <= 40:
        v = m.group(1).strip()
        if v and v not in prod.get("variety", ""):
            prod["variety"] = (prod.get("variety", "") + " " + v).strip(); hit = True
    return hit

def _delivery_from_subject(subject):
    s = norm(subject)
    hits = re.findall(r"(即納|入荷済み|再入荷|次回[:：]?\s*[\d/上中下～~月]+|\d{1,2}/[上中下][～~]?\s*\d{0,2}/?[上中下]?|\d{1,2}月[上中下]?旬?発売|\d{1,2}月新商品)", s)
    return "、".join(dict.fromkeys(h.strip() for h in hits))

def _restrict_tags(text):
    tags = []
    for pat, tag in RESTRICT_RULES:
        if re.search(pat, text) and tag not in tags: tags.append(tag)
    return "、".join(tags)

def parse_bracket_format(lines, subject):
    idx = [i for i, l in enumerate(lines) if re.search(r"【\s*商\s*品\s*名\s*】", l)]
    prods = []
    for k, i in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        block = lines[i:end]
        p = {}
        p["name"] = _clean_name(re.sub(r".*【\s*商\s*品\s*名\s*】\s*[:：]?", "", block[0]))
        for l in block[1:]:
            m = re.search(r"【\s*品\s*番\s*】\s*[:：]?\s*(\S+)", l)
            if m: p["code"] = m.group(1); continue
            m = re.search(r"【\s*単\s*価\s*】\s*[:：]?\s*[@＠]?\s*(\d[\d,]*)\s*(?:円)?\s*(.*)", l)
            if m:
                p["price"] = _num(m.group(1)); p["src"] = (p.get("src", "") + " / " + l.strip()).strip(" /")
                if m.group(2).strip(): p["shipping"] = m.group(2).strip("＊* ")
                continue
            m = re.search(r"【\s*種\s*類\s*】\s*[:：]?\s*(.+)", l)
            if m: p["variety"] = m.group(1).strip(); continue
            m = re.search(r"【\s*内\s*訳\s*】\s*[:：]?\s*(.+)", l)
            if m: p["variety"] = (p.get("variety", "") + " / " + m.group(1).strip()).strip(" /"); continue
            m = re.search(r"【\s*納\s*期\s*】\s*[:：]?\s*(.+)", l)
            if m: p["delivery"] = m.group(1).strip(); continue
            m = re.search(r"【\s*販売\s*単位\s*】\s*[:：]?\s*(\d+)\s*個?\s*(.*)", l)
            if m:
                p["qty_per_case"] = _num(m.group(1)); p["src"] = (p.get("src", "") + " / " + l.strip()).strip(" /")
                note = re.sub(r"[※＊*].*$", "", m.group(2)).strip()
                if note: p["unit_note"] = note
                continue
            if re.search(r"の場合.*\d+\s*円|の場合.*運賃", l) and len(l) <= 60:
                p["shipping"] = (p.get("shipping", "") + " " + l.strip()).strip(); continue
            if "ハーフ" in l:
                if "不可" in l: p["half"] = "不可"
                else:
                    m2 = re.search(r"「([^」]+)」", l)
                    p["half"] = "可" + ("（%s〜）" % m2.group(1) if m2 else "")
                continue
            m = re.search(r"上代\s*[¥￥]?\s*(\d[\d,]*)", l)
            if m: p["retail"] = _num(m.group(1)); p["src"] = (p.get("src", "") + " / " + l.strip()).strip(" /")
        if not p.get("code"):
            m = CODE_RE.search(p["name"]) or CODE_RE.search(norm(subject))
            if m: p["code"] = m.group(1)
        prods.append(p)
    return prods

def _split_name_tail(name):
    """商品名の末尾の「残20個」などを分離して (商品名, 備考) を返す"""
    m = NAME_TAIL_RE.search(name)
    if m: return name[:m.start()].strip(), m.group(1).replace(" ", "")
    return name, ""

def parse_free_format(lines, subject):
    prods = []
    pend = {}                   # 入数と単価が別行に分かれているときの途中状態 {"qty","price","src","post"}
    pending_deliv = []          # 次の商品に付く納期
    default_deliv = []          # 最初の商品より前の納期（全商品のデフォルト）
    default_attrs = {}          # 最初の商品より前の属性
    tail_attrs = {}             # 最後の商品より後の属性（未設定の全商品へ）
    cand = None; cand_marker = False
    MARK = "★●■◆◎○〇◇□▲△☆※💫⭐🎀【"
    for raw in lines:
        line = raw.strip()
        if not line: continue
        if re.fullmatch(r"[_\-=＝ー―\s]+", line): cand_marker = False; continue   # 区切り線のあとは次の行を商品名の候補にする
        def _emit(name, qty, price, src, posts):
            nonlocal pending_deliv, cand, cand_marker, pend
            name, tail = _split_name_tail(_clean_name(name).lstrip("★●■◆◎○〇◇□▲△☆・*＊ "))
            p = {"name": name, "qty_per_case": qty, "price": price, "src": src}
            if tail: p["note"] = tail
            for post in posts:
                post = post.strip()
                if not post: continue
                _attr_from_line(post, p)
                rest = re.sub(r"(上代|メーカー希望小売価格|希望小売価格)\s*[:：]?\s*[¥￥]?\s*\d[\d,]*\s*(税抜)?|ハーフ(可能|可|不可)|(本州)?送料\s*[¥￥]?\d[\d,]*円?|[（(]ハーフ送料\s*\d[\d,]*円?[)）]", "", post).strip(" 　,、/")
                mm = re.search(r"納期\s*[:：]?\s*(.+)", rest)
                if mm: p["delivery"] = mm.group(1).strip(); rest = ""
                elif rest and DELIV_RE.search(rest): p["delivery"] = rest; rest = ""
                if rest: p["note"] = (p.get("note", "") + " " + rest).strip()
            if pending_deliv and not p.get("delivery"): p["delivery"] = "、".join(pending_deliv)
            pending_deliv = []
            cm = CODE_RE.search(p["name"]) or CODE_RE.search(norm(subject))
            if cm: p["code"] = cm.group(1)
            prods.append(p); cand = None; cand_marker = False; pend = {}
        m = QTY_RE.match(line) or QTY_PRICE2_RE.match(line)
        if m:
            pre = _clean_name(re.sub(r"(?:入数|入り数|ケース入数|発送単位|出荷単位|販売単位|カートン単位|ケース単位|単位|1\s*(?:ケース|C/T|CT|カートン))\s*[:：]?\s*$", "", m.group("pre")))
            name = pre if len(re.sub(r"[\W_]", "", pre)) >= 2 else (cand or "")
            _emit(name, _num(m.group("n")), _num(m.group("p")), line, [m.group("post")])
            continue
        mn = NAME_QTY_RE.match(line)
        if mn and len(re.sub(r"[\W_]", "", mn.group("pre"))) >= 4 and not NOISE_RE.search(line) and not QTY_ONLY_RE.match(line):
            cand = mn.group("pre").strip(); cand_marker = line[0] in MARK
            pend = {"qty": _num(mn.group("n")), "src": [line], "post": []}
            continue
        # 入数と単価が別々の行にある形式（「発送単位：72個」＋「特価 @630」、「100個単位」＋「単価＠900円」）
        mq = QTY_ONLY_RE.match(line); mp = PRICE_ONLY_RE.match(line) if not mq else None
        if mq or mp:
            if mq: pend["qty"] = _num(mq.group("n")); post = mq.group("post")
            else: pend["price"] = _num(mp.group("p")); post = mp.group("post")
            pend.setdefault("src", []).append(line); pend.setdefault("post", [])
            if post.strip(): pend["post"].append(post)
            if pend.get("qty") and pend.get("price"):
                _emit(cand or "", pend["qty"], pend["price"], " / ".join(pend["src"]), pend["post"])
            continue
        mm = re.match(r"^納期\s*[:：]\s*(.+)$", line)
        if mm and len(line) <= 60:
            d = mm.group(1).strip()
            if prods and not prods[-1].get("delivery") and not pend: prods[-1]["delivery"] = d
            else: pending_deliv.append(d)
            continue
        if line.startswith(("※", "＊", "*", "・")) and len(line) > 25 and "ハーフ" not in line and "送料" not in line and "運賃" not in line:
            continue
        probe = {}
        hit = _attr_from_line(line, probe) and len(line) <= 60
        # 「〜アソート 残20個」のように商品名にアソートを含む長い行は、属性ではなく商品名候補として扱う
        if hit and set(probe) <= {"variety"} and len(re.sub(r"[\W_]", "", line)) >= 10 and not re.match(r"^(種類|内訳|全\s*\d|アソート)", line):
            hit = False
        if hit:
            target = prods[-1] if prods else None
            if "retail" in probe:
                if target is None: default_attrs["_retail_src"] = line
                elif line not in target.get("src", ""): target["src"] = (target.get("src", "") + " / " + line).strip(" /")
            if target is None: default_attrs.update({k: v for k, v in probe.items()})
            else:
                for k, v in probe.items():
                    if k == "shipping": target["shipping"] = (target.get("shipping", "") + " " + v).strip() if v not in target.get("shipping", "") else target["shipping"]
                    elif not target.get(k): target[k] = v
                for k, v in probe.items(): tail_attrs.setdefault(k, v)
                if "retail" in probe: tail_attrs.setdefault("_retail_src", line)
            continue
        if len(line) <= 45 and DELIV_RE.search(line) and not NOISE_RE.search(line):
            if not prods: default_deliv.append(line)
            pending_deliv.append(line); continue
        if NOISE_RE.search(line) or len(line) > 70: continue
        if len(re.sub(r"[\W_]", "", line)) < 2: continue
        if line[0] == "※" or CAND_SKIP_RE.match(line): continue
        line = re.sub(r"^(?:商品名|品名)\s*[:：]\s*|^[*＊]+\s*", "", line)   # 「*」は商品名にも注意書きにも使われるので見出し扱いしない
        is_marker = line[0] in MARK and not re.fullmatch(r"【[^】]*】", line)   # 「【サンリオ カフェラテシリーズ】」のようなシリーズ見出しは優先しない
        if is_marker or not cand_marker:
            cand = line; cand_marker = is_marker
    if prods and pending_deliv and not prods[-1].get("delivery"): prods[-1]["delivery"] = "、".join(pending_deliv)
    for p in prods:
        if not p.get("delivery") and default_deliv: p["delivery"] = "、".join(default_deliv)
        for k, v in list(default_attrs.items()) + list(tail_attrs.items()):
            if k == "_retail_src":
                if v not in p.get("src", "") and "上代" not in p.get("src", ""): p["src"] = (p.get("src", "") + " / " + v).strip(" /")
                continue
            if not p.get(k): p[k] = v
    return prods

def parse_products(subject, body):
    text = norm(body)
    lines = [l.strip() for l in text.splitlines()]
    if re.search(r"【\s*商\s*品\s*名\s*】", text):
        prods = parse_bracket_format(lines, subject)
    else:
        prods = []
        blocks = BLOCK_SEP_RE.split(text)
        if len(blocks) >= 2:
            # ＊＊＊ で区切られたブロックごとに 1 商品（上代などの属性もブロック内で完結させる）
            per_block = [parse_free_format([l.strip() for l in b.splitlines()], subject) for b in blocks]
            if sum(1 for ps in per_block if ps) >= 2: prods = [p for ps in per_block for p in ps]
        if not prods: prods = parse_free_format(lines, subject)
    if not prods:  # 入数・単価が取れないメール：商品名の候補（件名の ■・／ 区切り、本文の ★●■◆ 行）ごとに 1 行ずつ作る（2026-11-02 菊地さん：1 メールに複数商品があるときも 1 つずつ）
        prods = [{"name": n, "note": "※入数・単価を自動解析できず。本文を確認してください"} for n in candidate_names(subject, lines)]
    if not prods:  # それでも無ければ件名を商品名にして1行だけ作る
        prods = [{"name": re.sub(r"^(FW|Fwd?|RE)\s*[:：]\s*", "", norm(subject), flags=re.I).strip(), "note": "※自動解析できず。本文を確認してください"}]
    restrict = _restrict_tags(text)
    subj_deliv = _delivery_from_subject(subject)
    for p in prods:
        p.setdefault("restrict", restrict)
        if not p.get("delivery") and subj_deliv: p["delivery"] = subj_deliv
        if p.get("unit_note"): p["shipping"] = (("販売単位" + p.pop("unit_note") + " ") + p.get("shipping", "")).strip()
        if p.get("note"): p["shipping"] = (p.get("shipping", "") + " " + p.pop("note")).strip()
        for k in ("name", "variety", "delivery", "shipping", "maker", "src"):
            if p.get(k): p[k] = re.sub(r"\s+", " ", str(p[k])).strip()
        p.pop("_retail_src", None)
    return prods

SUBJ_DROP_RE = re.compile(r"^(FW|Fwd?|RE)\s*[:：]\s*", re.I)
SUBJ_NOISE_RE = re.compile(r"^(?:\d{1,2}/\d{1,2}\s*締め?切り?|\d{1,2}月(?:[上中下]旬?)?(?:[~～]\d{0,2}月?[上中下]?旬?)?(?:発売|新商品|再入荷|入荷|中下)?|即納|再入荷|入荷しました|新商品|新製品|弊社先行案内|並行ライセンス新商品|ご案内|のご案内|更新|大人気|特価|残り\d+ケース|\d{1,2}月\d{1,2}日締め切り\d{1,2}月発売予定|アミューズメント独占|おすすめ|注目の|さらに再販あり|特価商品のご案内です|即納です|のご案内_\w+|_DB|_ZOE\w*)[!！♪♡★●◆■]*$")
def _subject_parts(subject):
    s = SUBJ_DROP_RE.sub("", norm(subject)).strip()
    s = re.sub(r"[【】\[\]]", " ", s)
    parts = re.split(r"\s*[■●★◆◇□▲△☆◎○〇／/＆&＋+]\s*|\s+[・･]\s+|[:：]\s+|\s{2,}", s)
    out = []
    for p in parts:
        p = p.strip(" 　・,、.!！♪♡✨🍞🦄◤◢")
        # 商品名でない言葉（時期・案内の定型句）を外す
        p = re.sub(r"(弊社先行案内|並行ライセンス新商品|アミューズメント独占|世界中が待望の|日米同時公開|キラキラオーロラ仕様|のご案内です|のご案内|ご案内|特価商品|即納です|入荷しました|新製品|新商品|再入荷|再販あり|さらに|即納|大人気|おすすめ|注目の|全部ほしい|更新|締め?切り?|発売予定|\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2}|\d{1,2}月(?:[上中下]{1,2}旬?)?(?:[~～]\d{0,2}月?[上中下]{0,2}旬?)?(?:発売|中下|末入荷予定|入荷予定)?|残り\d+ケース|_DB|_ZOE\w*|[●★■◆!！♪♡✨]+)", " ", p)
        p = re.sub(r"\s+", " ", p).strip(" 　・,、.:：!！♪♡")
        if len(re.sub(r"[\W_]", "", p)) < 3 or SUBJ_NOISE_RE.match(p) or NOISE_RE.search(p): continue
        if p not in out: out.append(p)
    return out
def candidate_names(subject, lines):
    """入数・単価の行が無いメールから商品名の候補を集める：本文の見出し行（★●■◆【 で始まる短い行）→ 件名の区切り"""
    MARK = "★●■◆◎○〇◇□▲△☆【"
    names = []
    for raw in lines:
        line = raw.strip()
        if not line or line[0] not in MARK: continue
        line = line.lstrip("★●■◆◎○〇◇□▲△☆・ ").strip()
        line = re.sub(r"^【\s*(?:商品名|品名|新商品|即納|再入荷)\s*】\s*[:：]?\s*", "", line).replace("【", "").replace("】", " ").strip()
        if len(re.sub(r"[\W_]", "", line)) < 3 or len(line) > 60 or NOISE_RE.search(line) or DELIV_RE.fullmatch(line) or SUBJ_NOISE_RE.match(line): continue
        if re.search(r"(ご案内|お願い|ください|下さい|ございます|です$|ます$|注意|重要|送料|ハーフ|納期|締切|締め切り)", line): continue
        if line not in names: names.append(line)
    if len(names) >= 2: return names[:12]
    parts = _subject_parts(subject)
    if len(parts) >= 2: return parts[:12]
    return names[:1] or parts[:1]

def assign_images(prods, images):
    """商品と画像の対応付け。数が同じなら順番、ファイル名一致を優先、他は先頭画像"""
    for p in prods: p["image"] = ""
    if not images: return
    used = set()
    for p in prods:
        key = re.sub(r"[\W_]", "", p.get("name", ""))[:6]
        for im in images:
            if im in used: continue
            base = re.sub(r"[\W_]", "", os.path.basename(im))
            if key and len(key) >= 3 and key in base:
                p["image"] = im; used.add(im); break
    rest = [im for im in images if im not in used]
    if len([p for p in prods if not p["image"]]) == len(rest) and rest:
        for p in prods:
            if not p["image"]: p["image"] = rest.pop(0)
    for p in prods:
        if not p["image"]: p["image"] = images[0]

# ---------------- xlsx 読み戻し ----------------
def read_xlsx_overrides(path=XLSX_PATH):
    """既存xlsxからユーザー編集値と設定を読む → (overrides{key:{col:val}}, settings{k:v})"""
    overrides, settings = {}, {}
    if not os.path.exists(path): return overrides, settings
    from openpyxl import load_workbook
    try:
        wb = load_workbook(path, data_only=False)
    except Exception as e:
        log("xlsx読み込み失敗: %s" % e); return overrides, settings
    if SHEET_MAIN in wb.sheetnames:
        ws = wb[SHEET_MAIN]
        hdr = [str(c.value or "").replace("\n", "") for c in ws[1]]
        keycol = None
        for i, h in enumerate(hdr):
            if h == "商品キー": keycol = i
        if keycol is not None:
            editable = [(i + 1, c[2]) for i, c in enumerate(COLS) if c[3]]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if keycol >= len(row) or not row[keycol]: continue
                d = {}
                for ci, k in editable:
                    if ci - 1 >= len(row): continue
                    v = row[ci - 1]
                    if isinstance(v, str): v = v.strip()
                    d[k] = v
                overrides[str(row[keycol])] = d
    if SHEET_SET in wb.sheetnames:
        for row in wb[SHEET_SET].iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                settings[str(row[0]).strip()] = "" if row[1] is None else str(row[1])
    return overrides, settings

def _same(a, b):
    if a in (None, "") and b in (None, ""): return True
    try: return float(a) == float(b)
    except Exception: return str(a).strip() == str(b).strip()

def merge_overrides(db, overrides, settings):
    """xlsxの値が解析値と違う場合だけ『ユーザー編集』として保持する"""
    for key, d in overrides.items():
        prod = db["products"].get(key)
        if not prod: continue
        edit = dict(prod.get("edit", {}))
        for k, v in d.items():
            if k in ("order_cases", "order_memo", "status"):
                if v in (None, ""): edit.pop(k, None)
                else: edit[k] = v
            elif v in (None, ""):
                continue                      # 解析列を空にした場合は解析値を残す
            elif _same(v, prod.get(k)):
                edit.pop(k, None)             # 解析値と同じ → 編集扱いにしない
            else:
                edit[k] = v
        prod["edit"] = edit
    if settings:
        db["settings"].update(settings)

def effective(prod):
    """解析値にユーザー編集値を重ねた辞書"""
    e = dict(prod)
    for k, v in prod.get("edit", {}).items():
        if v is None or v == "":
            if k in ("order_cases", "order_memo", "status"): e[k] = v
            # 空にされた解析列は解析値を残す（誤って消した場合の保険）
        else:
            e[k] = v
    return e

def get_settings(db):
    s = {k: v for k, v, _ in DEFAULT_SETTINGS}
    s.update({k: v for k, v in db.get("settings", {}).items()})
    return s

# ---------------- xlsx 生成 ----------------
def _thumb(src, max_w, max_h, tag):
    from PIL import Image as PILImage
    d = os.path.join(IMG_DIR, "_thumbs"); os.makedirs(d, exist_ok=True)
    name = "%s_%s_%dx%d.jpg" % (os.path.basename(os.path.dirname(src)), re.sub(r"[^\w]", "_", os.path.splitext(os.path.basename(src))[0])[:40], max_w, max_h)
    dst = os.path.join(d, name)
    if not os.path.exists(dst):
        im = PILImage.open(src); im.thumbnail((max_w, max_h)); im = im.convert("RGB"); im.save(dst, "JPEG", quality=82)
    from PIL import Image as PI
    w, h = PI.open(dst).size
    return dst, w, h

def build_xlsx(db, path=XLSX_PATH):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    thin = Side(style="thin", color="BBBBBB"); border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hfill = PatternFill("solid", fgColor="1F4E78"); hfont = Font(bold=True, color="FFFFFF", size=10)
    efill = PatternFill("solid", fgColor="FFF7CC"); newfill = PatternFill("solid", fgColor="E8F5E9")
    wrap = Alignment(wrap_text=True, vertical="top")
    center = Alignment(horizontal="center", vertical="top", wrap_text=True)

    # ---- 商品一覧 ----
    ws = wb.active; ws.title = SHEET_MAIN
    for i, (h, w, k, ed) in enumerate(COLS, 1):
        c = ws.cell(row=1, column=i, value=h); c.fill = hfill; c.font = hfont; c.alignment = center; c.border = border
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "C2"
    prods = sorted(db["products"].values(), key=lambda p: (p.get("received", ""), p.get("key", "")), reverse=True)
    today = datetime.date.today().strftime("%Y-%m-%d")
    r = 2
    for prod in prods:
        p = effective(prod)
        rowh = 60
        for i, (h, w, k, ed) in enumerate(COLS, 1):
            c = ws.cell(row=r, column=i); c.border = border; c.alignment = wrap; c.font = Font(size=10)
            if k:
                v = p.get(k)
                if k in ("qty_per_case", "price", "retail", "order_cases") and v not in (None, ""):
                    try: v = float(v); v = int(v) if v == int(v) else v
                    except Exception: pass
                c.value = v
            if ed and k in ("order_cases", "order_memo"): c.fill = efill
            if k == "received": c.alignment = center
            if k in ("price", "retail"): c.number_format = "#,##0"
        L = get_column_letter
        ws.cell(row=r, column=COL_CASE_AMT, value="=IF(AND(ISNUMBER(%s%d),ISNUMBER(%s%d)),%s%d*%s%d,\"\")" % (L(COL_IDX["qty_per_case"]), r, L(COL_IDX["price"]), r, L(COL_IDX["qty_per_case"]), r, L(COL_IDX["price"]), r)).number_format = "#,##0"
        ws.cell(row=r, column=COL_ORDER_PCS, value="=IF(AND(ISNUMBER(%s%d),ISNUMBER(%s%d)),%s%d*%s%d,\"\")" % (L(COL_IDX["qty_per_case"]), r, L(COL_IDX["order_cases"]), r, L(COL_IDX["qty_per_case"]), r, L(COL_IDX["order_cases"]), r)).number_format = "#,##0"
        ws.cell(row=r, column=COL_ORDER_AMT, value="=IF(AND(ISNUMBER(%s%d),ISNUMBER(%s%d)),%s%d*%s%d,\"\")" % (L(COL_IDX["price"]), r, L(COL_ORDER_PCS), r, L(COL_IDX["price"]), r, L(COL_ORDER_PCS), r)).number_format = "#,##0"
        for ci in (COL_CASE_AMT, COL_ORDER_PCS, COL_ORDER_AMT):
            ws.cell(row=r, column=ci).border = border; ws.cell(row=r, column=ci).alignment = wrap; ws.cell(row=r, column=ci).font = Font(size=10, bold=(ci == COL_ORDER_AMT))
        if prod.get("added", "") == today:
            ws.cell(row=r, column=1).fill = newfill; ws.cell(row=r, column=2).fill = newfill
        img = prod.get("image")
        if img and os.path.exists(img):
            try:
                t, w_, h_ = _thumb(img, 250, 190, "s")
                xi = XLImage(t); ws.add_image(xi, "%s%d" % (L(COL_IMG), r))
                rowh = max(rowh, h_ * 0.75 + 6)
            except Exception as e:
                log("thumb失敗 %s: %s" % (img, e))
        ws.row_dimensions[r].height = rowh
        r += 1
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(COLS)), max(r - 1, 2))
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True,
                        error="0以上の数（ハーフは0.5）を入力してください", errorTitle="発注ケース数")
    ws.add_data_validation(dv); dv.add("%s2:%s%d" % (get_column_letter(COL_IDX["order_cases"]), get_column_letter(COL_IDX["order_cases"]), max(r, 500)))
    for ci in (COL_IDX["mail_id"], COL_IDX["key"]):
        for rr in range(2, r): ws.cell(row=rr, column=ci).font = Font(size=8, color="999999")

    # ---- 画像一覧 ----
    wi = wb.create_sheet(SHEET_IMG)
    for i, (h, w) in enumerate([("受信日", 12), ("件名", 50), ("画像ファイル", 40), ("画像", 90)], 1):
        c = wi.cell(row=1, column=i, value=h); c.fill = hfill; c.font = hfont; c.alignment = center
        wi.column_dimensions[get_column_letter(i)].width = w
    wi.freeze_panes = "A2"
    r = 2
    for mail in sorted(db["mails"].values(), key=lambda m: m.get("date", ""), reverse=True):
        for img in mail.get("images", []):
            if not os.path.exists(img): continue
            wi.cell(row=r, column=1, value=mail.get("date", "")[:10]).alignment = wrap
            wi.cell(row=r, column=2, value=mail.get("subject", "")).alignment = wrap
            wi.cell(row=r, column=3, value=os.path.basename(img)).alignment = wrap
            wi.cell(row=r, column=3).hyperlink = "file://" + img
            try:
                t, w_, h_ = _thumb(img, 640, 480, "l")
                wi.add_image(XLImage(t), "D%d" % r); wi.row_dimensions[r].height = h_ * 0.75 + 6
            except Exception as e: log("thumb失敗 %s: %s" % (img, e))
            r += 1

    # ---- 発注履歴 ----
    wh = wb.create_sheet(SHEET_HIST)
    hcols = [("発注日時", 16), ("発注No", 16), ("送信区分", 10), ("商品名", 44), ("品番", 12), ("ケース数", 9), ("個数", 9), ("単価", 9), ("金額", 11), ("発注書ファイル", 40)]
    for i, (h, w) in enumerate(hcols, 1):
        c = wh.cell(row=1, column=i, value=h); c.fill = hfill; c.font = hfont; c.alignment = center
        wh.column_dimensions[get_column_letter(i)].width = w
    wh.freeze_panes = "A2"
    r = 2
    for o in reversed(db.get("orders", [])):
        for it in o["items"]:
            vals = [o["datetime"], o["no"], o.get("mode", ""), it["name"], it.get("code", ""), it["cases"], it["pcs"], it["price"], it["amount"], os.path.basename(o.get("file", ""))]
            for i, v in enumerate(vals, 1):
                c = wh.cell(row=r, column=i, value=v); c.alignment = wrap; c.border = border
                if i in (8, 9): c.number_format = "#,##0"
            r += 1

    # ---- 設定 ----
    wsx = wb.create_sheet(SHEET_SET)
    for i, (h, w) in enumerate([("項目", 16), ("値", 70), ("説明", 40)], 1):
        c = wsx.cell(row=1, column=i, value=h); c.fill = hfill; c.font = hfont
        wsx.column_dimensions[get_column_letter(i)].width = w
    s = get_settings(db)
    for r, (k, dflt, desc) in enumerate(DEFAULT_SETTINGS, 2):
        wsx.cell(row=r, column=1, value=k).font = Font(bold=True)
        c = wsx.cell(row=r, column=2, value=s.get(k, dflt)); c.alignment = wrap; c.fill = efill
        wsx.cell(row=r, column=3, value=desc).font = Font(color="777777", size=9)
        if "\n" in str(s.get(k, dflt)): wsx.row_dimensions[r].height = 15 * (str(s.get(k, dflt)).count("\n") + 1)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=os.path.dirname(path)); os.close(fd)
    wb.save(tmp); os.replace(tmp, path)
    return path

def xlsx_locked():
    return os.path.exists(LOCK_PATH)
