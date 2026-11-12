# -*- coding: utf-8 -*-
"""EXAmuse 景品仕入れ: 新着メールを取り込んで『仕入れ想定商品.xlsx』を更新する"""
import os, re, sys, time, email, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examuse_common as C
import examuse_gsheet as G

def process_requests(db):
    """スプレッドシートの「🧸 景品発注」メニューから登録された発注要求を処理する"""
    try:
        reqs, ver = G.requests_pending()
        if ver >= 2 and int(db.get("gs_schema", 1)) < 2:
            # Apps Script が v2 になった直後: メール原文列(W)を全商品に埋めるため一度だけ全件送る
            r = G.push(db, list(db["products"].keys()), [], force=False)
            if not r["error"]: db["gs_schema"] = 2; C.log("Apps Script v2 を検出: メール原文列を全商品に反映しました")
            C.save_db(db)
    except Exception as e:
        import time as _t
        if "unknown action" in str(e):
            if _t.time() - db.get("gs_oldver_warn", 0) > 3600:
                C.log("Apps Script が旧バージョンです。最新コードを貼り直して「デプロイを管理→新バージョン」で更新してください（発注要求の自動処理は未稼働）")
                db["gs_oldver_warn"] = _t.time(); C.save_db(db)
        else: C.log("発注要求の取得エラー: %s" % e)
        return 0
    n = 0
    for req in reqs:
        try:
            if not G.request_claim(req["id"]): continue
        except Exception as e:
            C.log("発注要求の確保エラー: %s" % e); continue
        try:
            import examuse_order as O
            order_no, result, path, tot = O.run_request(req, db)
            msg = "%s（%s）%d商品 %s 発注書:%s%s" % (order_no, "送信済" if result == "sent" else "Mailに下書きを作成", len(req["items"]), O.yen(tot[2]), os.path.basename(path), ("　担当:" + req["person"]) if req.get("person") else "")
            # 手動送信を検知したときに発注要求の行を更新できるよう、要求IDと結果文を控える
            for o in reversed(db.get("orders", [])):
                if o.get("no") == order_no: o["req_id"] = req["id"]; o["req_result"] = msg; break
            C.save_db(db)
            G.request_done(req["id"], "完了", msg, order_no)
            C.notify("EXAmuse 発注 " + ("送信しました" if result == "sent" else "下書きを作成しました"), msg)
            C.log("発注要求 %s 完了%s: %s" % (req["id"], "（取り残し分を再処理）" if req.get("stale") else "", msg)); n += 1
        except Exception as e:
            C.log("発注要求 %s 失敗: %s" % (req["id"], e))
            try: G.request_done(req["id"], "失敗", "Mac側エラー: %s" % e)
            except Exception: pass
            C.notify("EXAmuse 発注に失敗", str(e)[:120])
    return n

# ---------------- 手で送った下書きの検知（送信済み → 発注済み＋景品マスタ＋発注履歴） ----------------
ORDER_NO_RE = re.compile(r"EH-\d{8}-\d+")
SENT_TAG = "[送信済み検知]"

def _flat(s):
    return re.sub(r"\s+", "", C.norm(s or ""))

def _req_from_log(order_no):
    """古い発注（要求IDを控える前のもの）は sync ログの「発注要求 Rxxx 完了: 発注No…」行から要求IDと結果文を拾う"""
    found = None
    try:
        with open(C.LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r"発注要求 (R\d+) 完了(?:（[^）]*）)?: (%s（.*)$" % re.escape(order_no), line)
                if m: found = (m.group(1), m.group(2).strip())
    except Exception: pass
    return found or (None, None)

def _check_one(db, order_no, body, mail_id, sent_at, dry):
    """1 通の手動送信メールを照合して ④ と同じ登録をする。戻り値: 結果の短い説明（sent_done に記録）"""
    orders = [o for o in db.get("orders", []) if o.get("no") == order_no]
    if len(orders) != 1: return None, "Mac の発注記録に %s が %d 件（あいまいなので何もしません）" % (order_no, len(orders))
    order = orders[0]
    if order.get("mode") != "下書き": return "skip", "発注記録の区分が「%s」（下書き以外は登録済み）→記録のみ" % order.get("mode")
    items = order.get("items") or []
    if not items: return None, "発注記録に商品がありません"
    # メール本文と発注要求の商品が一致するか（下書きを手で書き換えて送った場合は自動登録しない）
    fb = _flat(body)
    missing = [i["name"] for i in items if _flat(i["name"]) not in fb]
    n_lines = len(re.findall(r"[@＠][\d,]+[=＝][¥￥]", fb))
    if missing or n_lines != len(items):
        return None, "メール本文の商品が発注要求と一致しません（要求%d商品／本文%d行%s）" % (len(items), n_lines, ("／本文に無い: " + "、".join(missing)[:80]) if missing else "")
    data = G.read_all()
    info = {str(p.get("key")): p for p in data.get("products", [])}
    lack = [i["key"] for i in items if i["key"] not in info]
    if lack: return None, "スプレッドシートの商品一覧に該当行がありません: %s" % ", ".join(lack)
    sts = [str(info[i["key"]].get("status") or "") for i in items]
    if all(s.startswith("発注済") for s in sts): return "skip", "スプレッドシートで既に発注済み→記録のみ"
    if not all(order_no in s and s.startswith("下書き作成") for s in sts):
        return None, "スプレッドシートの発注状況が %s の下書きと一致しません: %s" % (order_no, " / ".join(sorted(set(sts)))[:120])
    if dry: return "dry", "（試し実行）登録できる状態です: %d商品" % len(items)
    import examuse_order as O
    settings = O.settings_from_gs(data)
    stamp = datetime.date.today().strftime("%Y-%m-%d"); label = "発注済 %s (%s)" % (stamp, order_no)
    errs = []
    try: G.mark([{"key": i["key"], "status": label} for i in items])
    except Exception as e: errs.append("発注済み化: %s" % e)
    for i in items:
        if i["key"] in db["products"]: db["products"][i["key"]].setdefault("edit", {})["status"] = label
    now = datetime.datetime.fromtimestamp(sent_at).strftime("%Y-%m-%d %H:%M")
    try: G.history([[now, order_no, "送信（下書きから手動）", i["name"], i.get("code", ""), i["cases"], i["pcs"], i["price"], i["amount"], os.path.basename(order.get("file", "")), order.get("person", "")] for i in items])
    except Exception as e: errs.append("発注履歴: %s" % e)
    added = 0
    if str(settings.get("景品マスタ連携", "する")).strip() != "しない":
        try:
            rows = O.master_rows([dict(i, kind=str(info[i["key"]].get("kind") or ""), memo=str(info[i["key"]].get("order_memo") or "")) for i in items], settings, order_no, "sent", info)
            for r in rows: r["mode"] = "送信済（下書きから手動送信・自動検知）"
            added = int(G.master_append(rows).get("added") or 0)
        except Exception as e: errs.append("景品マスタ: %s" % e)
    req_id, req_msg = order.get("req_id"), order.get("req_result")
    if not req_id: req_id, req_msg = _req_from_log(order_no)
    if req_id:
        # 状態を「完了」以外にして、スプシのメニュー「手動で送った→発注済み」の候補から外す（二重登録防止）
        try: G.request_done(req_id, "完了（送信済）", "%s ／ %s 手動送信を自動検知して登録（景品マスタ %d 行追加）" % (req_msg or order_no, stamp, added), order_no)
        except Exception as e: errs.append("発注要求: %s" % e)
    else: errs.append("発注要求の行が特定できず未更新（スプシのメニューで③を押さないこと）")
    order["mode"] = "下書き→送信済"
    res = "登録: %d商品を発注済み／景品マスタ %d 行追加／発注履歴 %d 行" % (len(items), added, len(items))
    if errs:
        res += "　※一部失敗: " + " / ".join(errs)
        C.notify("EXAmuse 送信済み検知：一部失敗", ("%s %s" % (order_no, " / ".join(errs)))[:120])
    else: C.notify("EXAmuse 手動送信を検知", "%s を発注済みにし景品マスタへ %d 行登録しました" % (order_no, added))
    return "done", res

def check_sent(db, dry=False):
    """送信済みメールボックスを見て、Mac が作った下書き（発注No入り）を手で送ったものを ④ と同じく登録する。
    メールは送らない。発注No ごとに一度だけ（db["sent_done"]）。初回起動より前に送ったメールは記録だけ。"""
    done = db.setdefault("sent_done", {}); seen = db.setdefault("sent_seen", {})
    if not db.get("sent_init_at") and not dry:
        db["sent_init_at"] = time.time(); C.save_db(db)
        C.log("%s 開始：%s より前に送信したメールは記録だけして登録しません" % (SENT_TAG, datetime.datetime.fromtimestamp(db["sent_init_at"]).strftime("%Y-%m-%d %H:%M:%S")))
    init = db.get("sent_init_at") or 0
    mails = C.list_sent_mails(days=14)
    to_addr = C.ORDER_TO.lower()
    for mid, sent_at, to, subject in mails:
        if mid in seen and not dry: continue
        if to_addr not in to:
            seen[mid] = "宛先対象外"; continue
        try:
            raw = C.fetch_source(mid, C.SENT_BOX); mail = C.parse_message_bytes(raw, mid)
            nos = sorted(set(ORDER_NO_RE.findall(subject + "\n" + mail["body"])))
            when = datetime.datetime.fromtimestamp(sent_at).strftime("%Y-%m-%d %H:%M")
            if len(nos) != 1:
                C.log("%s id=%s %s 送信「%s」: 発注No が %s のため何もしません" % (SENT_TAG, mid, when, subject, ("%d 個（%s）" % (len(nos), ",".join(nos))) if nos else "見つからない"))
                seen[mid] = "発注No %d 個" % len(nos); continue
            no = nos[0]
            if no in done and not dry:
                seen[mid] = "処理済み %s" % no; continue
            rec = {"mail_id": mid, "message_id": str(email.message_from_bytes(raw).get("Message-ID") or "").strip("<> "), "sent": when, "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            if sent_at < init and not dry:
                rec["result"] = "検知開始より前の送信→記録のみ"; done[no] = rec; seen[mid] = rec["result"]
                C.log("%s %s（id=%s %s 送信）: %s" % (SENT_TAG, no, mid, when, rec["result"])); continue
            kind, res = _check_one(db, no, mail["body"], mid, sent_at, dry)
            C.log("%s %s（id=%s %s 送信）: %s" % (SENT_TAG, no, mid, when, res))
            if dry: continue
            seen[mid] = res[:60]
            if kind: rec["result"] = res; done[no] = rec   # あいまい（kind=None）は sent_done に入れない（メニュー③で手動対応）
        except Exception as e:
            C.log("%s id=%s 失敗: %s" % (SENT_TAG, mid, e))
        if not dry: C.save_db(db)
    ids = {m[0] for m in mails}
    for k in [k for k in seen if k not in ids]: del seen[k]   # 14 日より古いものは忘れる（sent_done は残す）
    if not dry: C.save_db(db)

def protected_rows():
    """スプレッドシート上で手修正済み／発注が進んでいる行（再解析で上書きしない）: {商品キー: 行データ}"""
    out = {}
    if not G.configured(): return out
    for r in G.read_all().get("products", []):
        src = str(r.get("src") or ""); cases = str(r.get("order_cases") if r.get("order_cases") is not None else "").strip(); st = str(r.get("status") or "").strip()
        if "アプリで修正" in src or cases not in ("", "None") or st: out[str(r.get("key"))] = r
    return out

def main(argv):
    force = "--force" in argv
    quiet = "--quiet" in argv
    reparse = set()
    if "--reparse" in argv:   # 指定メールIDだけ再解析する（例: --reparse 87930,87926）
        reparse = {x.strip() for x in argv[argv.index("--reparse") + 1].split(",") if x.strip()}
    if "--dump" in argv:      # メール本文（解析に使う形）と解析結果をファイルに書く：python3 examuse_sync.py --dump 88349,88341 → ~/EXAmuse景品仕入れ/メール本文_88349.txt
        os.makedirs(C.OUT_DIR, exist_ok=True); paths = []
        for mid in [x.strip() for x in argv[argv.index("--dump") + 1].split(",") if x.strip()]:
            try:
                mail = C.parse_message_bytes(C.fetch_source(mid), mid)
                prods = C.parse_products(mail["subject"], mail["body"])
                path = os.path.join(C.OUT_DIR, "メール本文_%s.txt" % mid)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("件名: %s\n受信: %s\n差出人: %s\n\n===== 解析結果（%d商品）=====\n" % (mail["subject"], mail["date"], mail["from"], len(prods)))
                    for i, p in enumerate(prods, 1): f.write("%d. %s | 入数=%s 単価=%s | %s\n" % (i, p.get("name"), p.get("qty_per_case"), p.get("price"), p.get("src") or p.get("note") or ""))
                    f.write("\n===== 本文（正規化後）=====\n" + C.norm(mail["body"]) + "\n")
                paths.append(path); C.log("本文を書き出し: %s（%d商品）" % (path, len(prods)))
            except Exception as e:
                C.log("--dump 失敗 id=%s: %s" % (mid, e))
        print("\n".join(paths)); return 0
    db = C.load_db()
    if G.configured() and "--no-requests" not in argv:
        if process_requests(db): db = C.load_db()
    if G.configured() and "--no-sent" not in argv:
        # 手で送った下書きの検知（失敗しても取り込みループは止めない）。--sent-dry-run は何も書かずに判定だけログに出す
        try: check_sent(db, dry="--sent-dry-run" in argv)
        except Exception as e: C.log("%s 失敗: %s" % (SENT_TAG, e))
        if "--sent-dry-run" in argv: return 0
    if "--wait" in argv: time.sleep(20)   # Mailがダウンロードを終えるのを待つ
    # （xlsxモードのみ）先にxlsx上のユーザー編集を取り込んでから新着を処理する
    if not G.configured():
        ov, st = C.read_xlsx_overrides(); C.merge_overrides(db, ov, st)
    os.makedirs(C.OUT_DIR, exist_ok=True); os.makedirs(C.IMG_DIR, exist_ok=True); os.makedirs(C.ORDER_DIR, exist_ok=True)
    new_prods = []; reparsed_keys = []; protected = {}
    if force or reparse:
        try: protected = protected_rows()
        except Exception as e: C.log("保護行の取得に失敗したため再解析を中止します: %s" % e); return 1
    try:
        ids = C.list_mail_ids()
    except Exception as e:
        C.log("Mail一覧取得エラー: %s" % e); ids = []
    for mid, _d in ids:
        if mid in db["mails"] and not force and mid not in reparse: continue
        try:
            mail = C.parse_message_bytes(C.fetch_source(mid), mid)
            if C.SENDER_FILTER not in mail["from"].lower(): continue
            images = C.save_images(mail)
            prods = C.parse_products(mail["subject"], mail["body"])
            C.assign_images(prods, images)
            today = datetime.date.today().strftime("%Y-%m-%d")
            for i, p in enumerate(prods, 1):
                key = "%s-%d" % (mid, i)
                old = db["products"].get(key, {})
                if old and key in protected:
                    # シート側で手修正済み／発注済みの行は解析値で上書きしない（シートの値を編集値として控える）
                    r = protected[key]; ed = old.setdefault("edit", {})
                    for k in ("name", "qty_per_case", "price"):
                        if r.get(k) not in (None, ""): ed[k] = r[k]
                    db["products"][key] = old
                    C.log("再解析スキップ（シートで保護）: %s %s" % (key, r.get("name")))
                    continue
                p.update({"key": key, "mail_id": mid, "subject": mail["subject"], "received": mail["date"][:10],
                          "added": old.get("added", today), "status": "", "order_cases": None, "order_memo": "", "edit": old.get("edit", {})})
                db["products"][key] = p
                if not old: new_prods.append(p)
                elif mid in reparse or force: reparsed_keys.append(key)
            db["mails"][mid] = {"id": mid, "subject": mail["subject"], "date": mail["date"], "from": mail["from"],
                                "images": images, "n_products": len(prods)}
        except Exception as e:
            C.log("解析エラー id=%s: %s" % (mid, e))
    new_mail_ids = sorted({p["mail_id"] for p in new_prods})
    if G.configured():
        # ---- Googleスプレッドシート ----
        keys = sorted(set(db.get("gs_pending", [])) | {p["key"] for p in new_prods} | (set(db["products"].keys()) if force else set()))
        keys = [k for k in keys if k not in protected]
        mids = sorted(set(db.get("gs_pending_mails", [])) | set(new_mail_ids) | (set(db["mails"].keys()) if force else set()))
        if keys or mids or reparsed_keys:
            r = G.push(db, keys, mids, force=force)
            t = r["total"]
            if reparsed_keys and not force:
                # 再解析した既存行（保護行は除外済み）は解析列を書き直す（発注ケース数・機械タイプ・備考・状況・画像は Apps Script 側で保持）
                r2 = G.push(db, sorted(set(reparsed_keys) - set(keys)), [], force=True)
                for k2 in t: t[k2] += r2["total"][k2]
                if r2["error"]: r["error"] = (r["error"] or "") + " " + r2["error"]
                r["done_keys"] |= r2["done_keys"]
            db["gs_pending"] = [k for k in keys if k not in r["done_keys"]]
            db["gs_pending_mails"] = [m for m in mids if m not in r["done_mails"]]
            C.log("スプレッドシート更新: 追加%d / 更新%d / 画像%d / メール画像%d（商品合計%d）%s" % (t["added"], t["updated"], t["imaged"], t["mail_images"], len(db["products"]), "" if not r["error"] else " ※未送信あり→次回再送"))
            if new_prods and not quiet:
                names = "、".join(p["name"][:18] for p in new_prods[:3])
                C.notify("EXAmuse 新着商品 %d件（スプレッドシート更新）" % len(new_prods), names)
        else:
            C.log("新着なし")
        C.save_db(db)
        return 0
    # ---- Googleスプレッドシート未設定の間は xlsx を更新 ----
    if new_prods or force or db.get("pending_xlsx") or not os.path.exists(C.XLSX_PATH):
        if C.xlsx_locked():
            db["pending_xlsx"] = True
            C.log("xlsxがExcelで開かれているため更新を保留（新着%d件）" % len(new_prods))
            if new_prods and not quiet:
                C.notify("EXAmuse 新着商品", "%d件の新商品。Excelを閉じると反映されます" % len(new_prods))
        else:
            C.build_xlsx(db); db["pending_xlsx"] = False
            C.log("xlsx更新: 新着%d件 / 商品合計%d件" % (len(new_prods), len(db["products"])))
            if new_prods and not quiet:
                names = "、".join(p["name"][:18] for p in new_prods[:3])
                C.notify("EXAmuse 新着商品 %d件" % len(new_prods), names)
    else:
        C.log("新着なし")
    C.save_db(db)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
