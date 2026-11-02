# -*- coding: utf-8 -*-
"""EXAmuse 景品仕入れ: 新着メールを取り込んで『仕入れ想定商品.xlsx』を更新する"""
import os, sys, time, datetime
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
            G.request_done(req["id"], "完了", msg, order_no)
            C.notify("EXAmuse 発注 " + ("送信しました" if result == "sent" else "下書きを作成しました"), msg)
            C.log("発注要求 %s 完了%s: %s" % (req["id"], "（取り残し分を再処理）" if req.get("stale") else "", msg)); n += 1
        except Exception as e:
            C.log("発注要求 %s 失敗: %s" % (req["id"], e))
            try: G.request_done(req["id"], "失敗", "Mac側エラー: %s" % e)
            except Exception: pass
            C.notify("EXAmuse 発注に失敗", str(e)[:120])
    return n

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
