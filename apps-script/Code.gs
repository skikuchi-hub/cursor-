/**
 * クレーンログ（旧クレーン日報）アプリ（GitHub Pages 版）の保存先 API。
 * スプレッドシート「クレーンゲーム日報」にバインドして使う。
 *
 * デプロイ：デプロイ → 新しいデプロイ → 種類「ウェブアプリ」
 *   次のユーザーとして実行：自分 ／ アクセスできるユーザー：全員
 *   表示されたURLを GitHub Pages 側の config.js の api に入れる。
 *
 * 仕組み：
 *   - 認証はスプレッドシートの「スタッフ」タブの PIN（名前 / PIN / 権限 / 有効）。
 *   - アプリの記録は隠しタブ「_app_db」に JSON で保存（アプリが読み書きする正）。
 *   - 保存と同時に「巡回ログ」「部屋別ログ」「景品マスタ」「経費台帳」の各タブへ行を書き込む（旧「転記」の自動化）。
 *     各タブの最終列「アプリID」で行とアプリの記録を対応づけ、アプリで削除すると行も消える。
 *   - 景品マスタ・過去他社データは毎回タブから読んでアプリに返す（別途の同期は不要）。
 */

var DB_SHEET = "_app_db";
var STAFF_SHEET = "スタッフ";
var ID_HEADER = "アプリID";
var COLS = ["weekly", "prizes", "expenses", "settings"];
var TZ = "Asia/Tokyo";
var MY_STORES = ["博多東平尾1丁目店", "博多竹下2丁目店", "福岡平尾山荘通り店", "福大工学部前店", "福岡下山門通り店"];

/* ===================== 入口 ===================== */
function doGet(e) {
  return out({ ok: true, service: "crane-nippo-api", version: 1, time: nowIso() });
}

function doPost(e) {
  var req = {};
  try { req = JSON.parse((e && e.postData && e.postData.contents) || "{}"); }
  catch (err) { return out({ ok: false, error: "bad_request", message: "JSONが読めません" }); }
  try {
    var me = auth(req.pin);
    if (!me) return out({ ok: false, error: "unauthorized", message: "PINが違います" });
    switch (String(req.action || "")) {
      case "bootstrap": return out(Object.assign({ ok: true }, bootstrap(me)));
      case "add":    return out(withLock(function () { return addDoc(me, req.col, req.rec); }));
      case "patch":  return out(withLock(function () { return patchDoc(me, req.col, req.id, req.obj); }));
      case "remove": return out(withLock(function () { return removeDoc(me, req.col, req.id); }));
      case "put":    return out(withLock(function () { return putDoc(me, req.col, req.id, req.obj); }));
      default: return out({ ok: false, error: "unknown_action", message: "不明な操作: " + req.action });
    }
  } catch (err) {
    return out({ ok: false, error: "server_error", message: String((err && err.message) || err) });
  }
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
function withLock(fn) {
  var lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try { return fn(); } finally { lock.releaseLock(); }
}
function ss() { return SpreadsheetApp.getActive(); }
function nowIso() { return Utilities.formatDate(new Date(), TZ, "yyyy-MM-dd'T'HH:mm:ssXXX"); }
function num(v) { var x = parseFloat(v); return isFinite(x) ? x : 0; }
function clean(s) { return String(s == null ? "" : s).replace(/[\t\r\n]+/g, " ").trim(); }

/* ===================== スタッフ・PIN ===================== */
function ensureStaffSheet() {
  var sh = ss().getSheetByName(STAFF_SHEET);
  if (sh) return sh;
  sh = ss().insertSheet(STAFF_SHEET);
  sh.getRange(1, 1, 1, 5).setValues([["名前", "PIN", "権限", "有効", "メモ"]]).setFontWeight("bold");
  sh.getRange(2, 1, 2, 5).setValues([
    ["菊地翔平", randomPin(), "管理者", true, "初期PIN。好きな番号に変えてOK"],
    ["石原里基", randomPin(), "スタッフ", true, "初期PIN。好きな番号に変えてOK"]
  ]);
  sh.getRange("B:B").setNumberFormat("@");
  sh.getRange(2, 4, 50, 1).insertCheckboxes();
  sh.getRange(1, 7).setValue("アプリに入るためのPIN。PINは他の人と重複しないように。「有効」を外すとその人は入れなくなる。権限が「管理者」の人だけ担当を切り替えて記録できる。");
  sh.setColumnWidth(5, 260);
  return sh;
}
function randomPin() {
  var s = "";
  for (var i = 0; i < 6; i++) s += Math.floor(Math.random() * 10);
  return s;
}
function staffRows() {
  var sh = ensureStaffSheet();
  var last = sh.getLastRow();
  if (last < 2) return [];
  var v = sh.getRange(2, 1, last - 1, 4).getValues();
  var rows = [];
  v.forEach(function (r) {
    var name = clean(r[0]); if (!name) return;
    var pin = clean(r[1]);
    var role = clean(r[2]) === "管理者" ? "admin" : "staff";
    var on = r[3] === true || String(r[3]).toUpperCase() === "TRUE" || r[3] === 1;
    rows.push({ name: name, pin: pin, role: role, active: on });
  });
  return rows;
}
function auth(pin) {
  pin = clean(pin);
  if (!pin) return null;
  var hit = staffRows().filter(function (r) { return r.active && r.pin && r.pin === pin; })[0];
  return hit ? { name: hit.name, role: hit.role } : null;
}
function staffNames() {
  return staffRows().filter(function (r) { return r.active; }).map(function (r) { return r.name; });
}

/* ===================== _app_db（アプリの記録） ===================== */
function dbSheet() {
  var sh = ss().getSheetByName(DB_SHEET);
  if (!sh) {
    sh = ss().insertSheet(DB_SHEET);
    sh.getRange(1, 1, 1, 6).setValues([["col", "id", "createdAt", "updatedAt", "by", "json"]]);
    sh.hideSheet();
  }
  return sh;
}
function readAllDocs() {
  var sh = dbSheet();
  var last = sh.getLastRow();
  var docs = {}; COLS.forEach(function (c) { docs[c] = []; });
  if (last < 2) return docs;
  var v = sh.getRange(2, 1, last - 1, 6).getValues();
  v.forEach(function (r) {
    var col = String(r[0]); if (!docs[col]) return;
    var rec; try { rec = JSON.parse(r[5]); } catch (e) { return; }
    rec.id = String(r[1]);
    docs[col].push(rec);
  });
  return docs;
}
function findDbRow(col, id) {
  var sh = dbSheet();
  var last = sh.getLastRow();
  if (last < 2) return 0;
  var v = sh.getRange(2, 1, last - 1, 2).getValues();
  for (var i = 0; i < v.length; i++) if (String(v[i][0]) === col && String(v[i][1]) === String(id)) return i + 2;
  return 0;
}
function newId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}
function stripId(rec) { var o = {}; for (var k in rec) if (k !== "id") o[k] = rec[k]; return o; }

function addDoc(me, col, rec) {
  if (COLS.indexOf(col) < 0) throw new Error("不明な保存先: " + col);
  rec = rec || {};
  var now = nowIso();
  rec.id = newId();
  rec.createdAt = rec.createdAt || now;
  rec.by = me.name;
  if (col !== "settings") {
    if (me.role !== "admin" || !rec.staff) rec.staff = me.name;   // 担当は PIN の本人（管理者だけ別の担当で記録できる）
    rec.sentAt = now;                                              // スプレッドシートへ即時に書くので「転記済み」
  }
  var docs = readAllDocs();
  materialize(col, rec, docs);
  dbSheet().appendRow([col, rec.id, rec.createdAt, now, me.name, JSON.stringify(stripId(rec))]);
  return { ok: true, rec: rec };
}
function patchDoc(me, col, id, obj) {
  if (COLS.indexOf(col) < 0) throw new Error("不明な保存先: " + col);
  var row = findDbRow(col, id);
  if (!row) throw new Error("記録が見つかりません");
  var sh = dbSheet();
  var rec; try { rec = JSON.parse(sh.getRange(row, 6).getValue()); } catch (e) { rec = {}; }
  Object.keys(obj || {}).forEach(function (k) { if (k !== "id") rec[k] = obj[k]; });
  rec.id = id;
  sh.getRange(row, 4, 1, 3).setValues([[nowIso(), me.name, JSON.stringify(stripId(rec))]]);
  return { ok: true, rec: rec };
}
function removeDoc(me, col, id) {
  if (COLS.indexOf(col) < 0) throw new Error("不明な保存先: " + col);
  var row = findDbRow(col, id);
  if (row) dbSheet().deleteRow(row);
  dematerialize(col, id);
  return { ok: true };
}
function putDoc(me, col, id, obj) {
  if (COLS.indexOf(col) < 0) throw new Error("不明な保存先: " + col);
  var rec = Object.assign({}, obj || {}); rec.id = id;
  var now = nowIso();
  var row = findDbRow(col, id);
  var sh = dbSheet();
  if (row) sh.getRange(row, 4, 1, 3).setValues([[now, me.name, JSON.stringify(stripId(rec))]]);
  else sh.appendRow([col, id, now, now, me.name, JSON.stringify(stripId(rec))]);
  return { ok: true, rec: rec };
}

/* ===================== 起動時にアプリへ渡すもの ===================== */
function bootstrap(me) {
  return {
    me: me,
    staff: staffNames(),
    docs: readAllDocs(),
    sheet_master: readPrizeMaster(),
    stores: readPastStores(),
    time: nowIso()
  };
}

/* 景品マスタタブ → {updatedAt, source, rows:[{name,vendor,kind,cost,rate,qty,stock,memo}]} */
function readPrizeMaster() {
  var sh = ss().getSheetByName("景品マスタ");
  var res = { updatedAt: nowIso(), source: "クレーンゲーム日報／景品マスタ", rows: [] };
  if (!sh) return res;
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return res;
  var hdr = v[0].map(function (h) { return String(h || "").replace(/\s/g, ""); });
  function ci(name) { for (var i = 0; i < hdr.length; i++) if (hdr[i].indexOf(name) === 0) return i; return -1; }
  var C = { name: ci("品名"), vendor: ci("仕入先"), kind: ci("機械タイプ"), cost: ci("仕入単価"), rate: ci("設定獲得率"), qty: ci("買った数量"), stock: ci("残り在庫"), memo: ci("メモ") };
  function g(r, k) { return C[k] >= 0 ? r[C[k]] : ""; }
  function n(x, d) { if (x === "" || x === null || x === undefined) return d; var f = parseFloat(x); return isFinite(f) ? f : d; }
  for (var i = 1; i < v.length; i++) {
    var r = v[i]; var name = clean(g(r, "name")); if (!name) continue;
    res.rows.push({
      name: name, vendor: clean(g(r, "vendor")), kind: clean(g(r, "kind")),
      cost: n(g(r, "cost"), 0), rate: n(g(r, "rate"), null), qty: n(g(r, "qty"), 0), stock: n(g(r, "stock"), null), memo: clean(g(r, "memo"))
    });
  }
  return res;
}

/* 過去他社データタブ（見出しは4行目）→ {months:[...], rows:{店舗名:[月売上...]}} 自社引継ぎ店のみ */
function readPastStores() {
  var sh = ss().getSheetByName("過去他社データ");
  var res = { updatedAt: nowIso(), source: "クレーンゲーム日報／過去他社データ", months: [], rows: {} };
  if (!sh) return res;
  var v = sh.getDataRange().getValues();
  if (v.length < 5) return res;
  var hdr = v[3];
  var mcols = [];
  hdr.forEach(function (h, i) { if (/^\d{4}-\d{2}$/.test(String(h).trim())) mcols.push(i); });
  res.months = mcols.map(function (i) { return String(hdr[i]).trim(); });
  for (var r = 4; r < v.length; r++) {
    var row = v[r]; var name = clean(row[2]); var memo = clean(row[15]);
    if (!name) continue;
    if (MY_STORES.indexOf(name) >= 0 || memo.indexOf("自社引継ぎ店") >= 0) {
      var vals = mcols.map(function (i) { var x = row[i]; return (x === "" || x === null) ? null : (isFinite(parseFloat(x)) ? parseFloat(x) : null); })
        .filter(function (x) { return x !== null; });
      if (vals.length) res.rows[name] = vals;
    }
  }
  return res;
}

/* ===================== 各タブへの書き込み（旧「転記」） ===================== */
function materialize(col, rec, docs) {
  if (col === "weekly") {
    var sh = ss().getSheetByName("巡回ログ");
    if (sh) {
      var r = appendValues(sh, [dateOf(rec.week), rec.store || "", rec.machine || "", rec.prize || "", num(rec.plays), num(rec.pays), num(rec.cost), timeFrac(rec.time), rec.staff || "", sheetMemo(rec)], rec.id);
      sh.getRange(r, 1).setNumberFormat("yyyy/mm/dd");
      sh.getRange(r, 8).setNumberFormat("h:mm");
    }
    var rs = ss().getSheetByName("部屋別ログ");
    if (rs) {
      var lines = roomLines(rec, (docs && docs.weekly) || []);
      lines.forEach(function (line) {
        var rr = appendValues(rs, line, rec.id);
        rs.getRange(rr, 1).setNumberFormat("yyyy/mm/dd");
      });
    }
  } else if (col === "prizes") {
    var ps = ss().getSheetByName("景品マスタ");
    if (ps) {
      var rate = num(rec.rateN) > 0 ? 1 / num(rec.rateN) : "";
      var row = appendValues(ps, [rec.name || "", rec.vendor || "", rec.use || "", num(rec.cost), rate, rec.qty ? num(rec.qty) : ""], rec.id);
      if (rate !== "") ps.getRange(row, 5).setNumberFormat("0.00%");
      if (rec.memo) ps.getRange(row, 11).setValue(clean(rec.memo));            // K列：メモ（G〜J は数式）
    }
  } else if (col === "expenses") {
    var es = ss().getSheetByName("経費台帳");
    if (es) {
      var er = appendValues(es, [dateOf(rec.date), rec.store || "", rec.kind || "", num(rec.net), rec.payee || "", rec.memo || ""], rec.id);
      es.getRange(er, 1).setNumberFormat("yyyy/mm/dd");
    }
  }
}
function dematerialize(col, id) {
  var names = col === "weekly" ? ["巡回ログ", "部屋別ログ"] : col === "prizes" ? ["景品マスタ"] : col === "expenses" ? ["経費台帳"] : [];
  names.forEach(function (n) {
    var sh = ss().getSheetByName(n); if (!sh) return;
    var idc = idColumn(sh, false); if (!idc) return;
    var last = sh.getLastRow(); if (last < 2) return;
    var v = sh.getRange(2, idc, last - 1, 1).getValues();
    for (var i = v.length - 1; i >= 0; i--) if (String(v[i][0]) === String(id)) sh.deleteRow(i + 2);
  });
}
/* A列で見た最終データ行の次に values を書き、アプリID列に id を書く。行番号を返す */
function appendValues(sh, values, id) {
  var colA = sh.getRange(1, 1, sh.getMaxRows(), 1).getValues();
  var last = 1;
  for (var i = colA.length - 1; i >= 1; i--) { if (colA[i][0] !== "" && colA[i][0] !== null) { last = i + 1; break; } }
  var row = last + 1;
  if (row > sh.getMaxRows()) sh.insertRowsAfter(sh.getMaxRows(), 50);
  sh.getRange(row, 1, 1, values.length).setValues([values.map(function (v) { return v === undefined ? "" : v; })]);
  var idc = idColumn(sh, true);
  sh.getRange(row, idc).setValue(id);
  return row;
}
function idColumn(sh, create) {
  var lastCol = Math.max(1, sh.getLastColumn());
  var hdr = sh.getRange(1, 1, 1, lastCol).getValues()[0];
  for (var i = 0; i < hdr.length; i++) if (String(hdr[i]).trim() === ID_HEADER) return i + 1;
  if (!create) return 0;
  var c = lastCol + 1;
  if (c > sh.getMaxColumns()) sh.insertColumnsAfter(sh.getMaxColumns(), 1);
  sh.getRange(1, c).setValue(ID_HEADER).setFontColor("#999999").setFontSize(9);
  sh.setColumnWidth(c, 70);
  return c;
}
/* "YYYY-MM-DD" → スプレッドシートのタイムゾーンでその日の0時の Date。
   new Date(y,m,d) はスクリプトのタイムゾーン基準になり、スプシ側のタイムゾーンと違うと日付が1日ずれるため、
   必ずスプシのタイムゾーンで解釈する */
function sheetTz() { try { return ss().getSpreadsheetTimeZone() || TZ; } catch (e) { return TZ; } }
function dateOf(isoStr) {
  var m = String(isoStr || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return isoStr || "";
  return Utilities.parseDate(m[1] + "-" + m[2] + "-" + m[3], sheetTz(), "yyyy-MM-dd");
}
function timeFrac(t) {
  var m = String(t || "").match(/^(\d{1,2}):(\d{2})/);
  if (!m) return t || "";
  return (+m[1] * 60 + +m[2]) / 1440;
}
function sheetMemo(r) {
  return [r.auto || "", r.memo || ""].filter(Boolean).join(" ｜ ");
}
/* アプリの「部屋別ログ」行（アプリ内の roomLines と同じ並び） */
function roomLines(r, all) {
  var out = [];
  var wk = dateOf(r.week);
  (r.slots || []).forEach(function (x) {
    if (!x.out && (x.filled || "") === (x.prize || "")) return;            // 動きのあった枠だけ
    out.push([wk, r.store, r.machine, "枠" + x.i, "", "", num(r.sBox), x.prize || "", (x.prize && !x.out) ? 1 : 0, x.filled || "", x.filled ? 1 : 0, x.out ? 1 : 0]);
  });
  (r.rooms || []).forEach(function (x) {
    var pair = r.mtype === "4p" ? ((x.k === "A" || x.k === "B") ? r.sAB : r.sCD) : r.sBox;
    // 直前の訪問（同じ週でもよい）。記録の作成時刻で比べる
    var prevR = all.filter(function (o) { return o.id !== r.id && o.store === r.store && o.machine === r.machine && String(o.createdAt || "") < String(r.createdAt || "") && o.rooms; })
      .sort(function (a, b) { return String(b.createdAt || "").localeCompare(String(a.createdAt || "")); })[0];
    var pv = prevR ? (prevR.rooms || []).filter(function (y) { return y.k === x.k; })[0] : null;
    var dif = (pv && pv.counter !== "" && x.counter !== "") ? Math.round((num(x.counter) - num(pv.counter)) * 100) / 100 : "";
    out.push([wk, r.store, r.machine, x.k === "-" ? "本体" : x.k, x.counter === "" ? "" : num(x.counter), dif, num(pair),
      x.prize || "", (x.before === "" || x.before === undefined) ? "" : num(x.before), x.addPrize || "", num(x.add), (x.pays === null || x.pays === undefined) ? "" : x.pays]);
  });
  return out;
}

/* ===================== 旧アプリ（claude.ai アーティファクト版）からのデータ移行 =====================
   Drive 上の移行JSON（{weekly:[...], settings:[...]}）を読み、_app_db に取り込む。
   - 旧アプリで未転記（sentAt なし）の記録は、巡回ログ・部屋別ログにも行を追加する
   - 旧アプリで転記済みの記録は、巡回ログの既存行を探して「アプリID」を付け、部屋別ログの行だけ追加する
   - 同じ id が _app_db にあれば飛ばす（何度実行しても二重にならない）
   実行：エディタで importFromDrive を選んで ▶。ウェブアプリの再デプロイは不要 */
var MIGRATION_FILE_ID = "1VMiTTV6WhZJvxlVaIRccI90-q7NS18dG";   // クレーン日報_旧アプリ移行データ_20261006.json

function importFromDrive() {
  var text = DriveApp.getFileById(MIGRATION_FILE_ID).getBlob().getDataAsString("UTF-8");
  var data = JSON.parse(text);
  var sh = dbSheet();
  var docs = readAllDocs();
  var existing = {};
  COLS.forEach(function (c) { docs[c].forEach(function (r) { existing[c + "/" + r.id] = true; }); });
  var now = nowIso(), added = 0, skipped = 0, toSheet = 0, tagged = 0;

  var weekly = (data.weekly || []).slice().sort(function (a, b) { return String(a.createdAt).localeCompare(String(b.createdAt)); });
  weekly.forEach(function (rec) {
    if (!rec || !rec.id) return;
    if (existing["weekly/" + rec.id]) { skipped++; return; }
    if (!rec.sentAt) {
      materialize("weekly", rec, docs);                 // 巡回ログ＋部屋別ログに行を追加
      rec.sentAt = now; toSheet++;
    } else {
      if (tagExistingLogRow(rec)) tagged++;             // 巡回ログの既存行に アプリID を付ける
      var rs = ss().getSheetByName("部屋別ログ");        // 旧アプリ時代は部屋別ログが空だったので、ここで追加
      if (rs) roomLines(rec, docs.weekly).forEach(function (line) {
        var rr = appendValues(rs, line, rec.id); rs.getRange(rr, 1).setNumberFormat("yyyy/mm/dd");
      });
    }
    rec.by = rec.by || rec.staff || "import";
    sh.appendRow(["weekly", rec.id, rec.createdAt || now, now, "import", JSON.stringify(stripId(rec))]);
    docs.weekly.push(rec); added++;
  });
  (data.settings || []).forEach(function (s0) {
    if (!s0 || !s0.id || existing["settings/" + s0.id]) { skipped++; return; }
    sh.appendRow(["settings", s0.id, now, now, "import", JSON.stringify(stripId(s0))]); added++;
  });
  var msg = "移行完了：取り込み " + added + " 件（うちシートへ新規追加 " + toSheet + " 件、既存行にID付与 " + tagged + " 件）、スキップ " + skipped + " 件";
  Logger.log(msg);
  SpreadsheetApp.getActive().toast(msg);
  return msg;
}
/* 巡回ログで、週・店舗・機械・プレイ数が一致し アプリID が空の行に id を書く */
function tagExistingLogRow(rec) {
  var sh = ss().getSheetByName("巡回ログ"); if (!sh) return false;
  var last = sh.getLastRow(); if (last < 2) return false;
  var idc = idColumn(sh, true);
  var v = sh.getRange(2, 1, last - 1, Math.max(5, idc)).getValues();
  var tz = sheetTz();
  var wk = dateOf(rec.week); var wkKey = wk instanceof Date ? Utilities.formatDate(wk, tz, "yyyy-MM-dd") : String(wk);
  for (var i = 0; i < v.length; i++) {
    var a = v[i][0]; var aKey = a instanceof Date ? Utilities.formatDate(a, tz, "yyyy-MM-dd") : String(a);
    if (aKey === wkKey && String(v[i][1]) === String(rec.store) && String(v[i][2]) === String(rec.machine)
        && num(v[i][4]) === num(rec.plays) && String(v[i][idc - 1] || "") === "") {
      sh.getRange(i + 2, idc).setValue(rec.id); return true;
    }
  }
  return false;
}

/* ===================== 手動メンテ用（エディタから実行） ===================== */
/* 巡回ログ・部屋別ログの A1「週」を「訪問日」に改名（記録は訪問ごと。K列の週キーは数式のまま） */
function renameDateHeaders() {
  ["巡回ログ", "部屋別ログ"].forEach(function (n) {
    var sh = ss().getSheetByName(n); if (!sh) return;
    if (String(sh.getRange(1, 1).getValue()).trim() === "週") sh.getRange(1, 1).setValue("訪問日");
  });
}
/* アプリIDの付いた行の A列（週／日付）を _app_db の記録から書き直す。
   タイムゾーン差で日付が1日ずれて入った行の修復用。何度実行してもよい */
function repairDates() {
  var docs = readAllDocs(); var byId = {};
  docs.weekly.forEach(function (r) { byId[r.id] = r.week; });
  docs.expenses.forEach(function (r) { byId[r.id] = r.date; });
  var n = 0;
  ["巡回ログ", "部屋別ログ", "経費台帳"].forEach(function (name) {
    var sh = ss().getSheetByName(name); if (!sh) return;
    var idc = idColumn(sh, false); if (!idc) return;
    var last = sh.getLastRow(); if (last < 2) return;
    var ids = sh.getRange(2, idc, last - 1, 1).getValues();
    ids.forEach(function (v, i) {
      var d = byId[String(v[0] || "")]; if (!d) return;
      sh.getRange(i + 2, 1).setValue(dateOf(d)).setNumberFormat("yyyy/mm/dd"); n++;
    });
  });
  var msg = "日付を書き直しました：" + n + " 行（スプシのタイムゾーン " + sheetTz() + " 基準）";
  Logger.log(msg); SpreadsheetApp.getActive().toast(msg); return msg;
}
function setup() {            // 初回：スタッフタブと _app_db を作る（再実行しても安全）
  ensureStaffSheet(); dbSheet(); renameDateHeaders();
  SpreadsheetApp.getActive().toast("スタッフタブと _app_db を用意しました。スタッフタブで PIN を確認してください。");
}
