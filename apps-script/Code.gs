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
   - 巡回報告に添付した写真は Drive「クレーンログ写真」に保存し、「写真」タブに 1 行追加（毎日の自動チェックが H 列以降を埋める）。
 */

var DB_SHEET = "_app_db";
var STAFF_SHEET = "スタッフ";
var ID_HEADER = "アプリID";
var COLS = ["weekly", "prizes", "expenses", "settings", "sourcing"];   // sourcing＝仕入れ候補の判断（見送り／保留／発注）
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
      case "photo":  return out(withLock(function () { return addPhoto(me, req.id, req.data, req.mime, req.kind); }));
      case "update": return out(withLock(function () { return updateDoc(me, req.col, req.id, req.obj); }));
      case "sourcing":       requireSourcing(me); return out(Object.assign({ ok: true }, readSourcing(!!req.force)));
      case "sourcingSet":    requireSourcing(me); return out(withLock(function () { return sourcingSet(me, req.key, req.decision, req.cases, req.machine, req.note); }));
      case "sourcingFix":    requireSourcing(me); return out(withLock(function () { return sourcingFix(me, req.key, req.fields); }));
      case "sourcingSubmit": requireSourcing(me); return out(withLock(function () { return sourcingSubmit(me, req.keys); }));
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
  var ncol = Math.max(5, sh.getLastColumn());
  var hdr = sh.getRange(1, 1, 1, ncol).getValues()[0].map(function (h) { return clean(h); });
  var sc = hdr.indexOf("仕入れ");                                    // 「仕入れ」列（チェック）。管理者は常に可
  var v = sh.getRange(2, 1, last - 1, ncol).getValues();
  var rows = [];
  var yes = function (x) { return x === true || String(x).toUpperCase() === "TRUE" || x === 1; };
  v.forEach(function (r) {
    var name = clean(r[0]); if (!name) return;
    var pin = clean(r[1]);
    var role = clean(r[2]) === "管理者" ? "admin" : "staff";
    rows.push({ name: name, pin: pin, role: role, active: yes(r[3]), sourcing: role === "admin" || (sc >= 0 && yes(r[sc])) });
  });
  return rows;
}
/* スタッフタブに「仕入れ」列（F）を足す。管理者と石原さんに初期チェック。再実行しても安全 */
function ensureSourcingColumn() {
  var sh = ensureStaffSheet();
  var ncol = Math.max(5, sh.getLastColumn());
  var hdr = sh.getRange(1, 1, 1, ncol).getValues()[0].map(function (h) { return clean(h); });
  if (hdr.indexOf("仕入れ") >= 0) return "already";
  var c = 6;
  if (clean(sh.getRange(1, c).getValue())) sh.insertColumnBefore(c);
  sh.getRange(1, c).setValue("仕入れ").setFontWeight("bold");
  sh.getRange(2, c, 50, 1).insertCheckboxes();
  var last = sh.getLastRow();
  if (last >= 2) {
    var v = sh.getRange(2, 1, last - 1, 3).getValues();
    v.forEach(function (r, i) { if (clean(r[2]) === "管理者" || clean(r[0]) === "石原里基") sh.getRange(i + 2, c).setValue(true); });
  }
  var note = clean(sh.getRange(1, 8).getValue());
  sh.getRange(1, 8).setValue((note ? note + " " : "") + "「仕入れ」にチェックのある人だけ、アプリの仕入れタブ（EXAmuse の発注）を使える。管理者は常に可。");
  return "added";
}
function auth(pin) {
  pin = clean(pin);
  if (!pin) return null;
  var hit = staffRows().filter(function (r) { return r.active && r.pin && r.pin === pin; })[0];
  return hit ? { name: hit.name, role: hit.role, sourcing: !!hit.sourcing } : null;
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
  if (col === "weekly") applySalesDelta(rec, docs.weekly);   // 売上は月の累計入力 → 前回との差分を記録
  materialize(col, rec, docs);
  dbSheet().appendRow([col, rec.id, rec.createdAt, now, me.name, JSON.stringify(stripId(rec))]);
  if (col === "prizes") dropCache("sheet_master");
  return { ok: true, rec: rec };
}

/* ===================== 売上：累計入力 → 今回分（差分） =====================
   アプリは機械に出ている「今月の累計売上」を入力する運用。記録では
   sAB/sCD/sBox/sales/plays に「前回訪問との差分（今回分）」を、cum に入力した累計を持つ。
   前回＝同じ店・同じ機械・同じ月（訪問日の月）で、作成時刻がこの記録より前の直近の記録。
   古い記録（cum なし）は入力値を累計とみなす。累計が前回より小さいときはリセット扱いで入力値をそのまま今回分にする */
var PLAY_PRICE = 100;
function cumOf(r) { var c = r && r.cum; return c ? { sAB: num(c.sAB), sCD: num(c.sCD), sBox: num(c.sBox) } : { sAB: num(r && r.sAB), sCD: num(r && r.sCD), sBox: num(r && r.sBox) }; }
function applySalesDelta(rec, allWeekly) {
  var cum = cumOf(rec);
  var mon = String(rec.week || "").slice(0, 7);
  var prev = (allWeekly || []).filter(function (o) {
    return o.id !== rec.id && o.store === rec.store && o.machine === rec.machine &&
      String(o.week || "").slice(0, 7) === mon && String(o.createdAt || "") < String(rec.createdAt || "");
  }).sort(function (a, b) { return String(b.createdAt || "").localeCompare(String(a.createdAt || "")); })[0];
  var pc = prev ? cumOf(prev) : { sAB: 0, sCD: 0, sBox: 0 };
  function d(f) { var c = cum[f], p = pc[f]; return prev ? (c > 0 && c < p ? c : c - p) : c; }
  rec.sAB = d("sAB"); rec.sCD = d("sCD"); rec.sBox = d("sBox");
  rec.sales = rec.mtype === "box" ? rec.sBox : rec.sAB + rec.sCD;
  rec.plays = Math.round(rec.sales / PLAY_PRICE);
  rec.cum = cum; rec.prevId = prev ? prev.id : "";
  return rec;
}
/* メモ（auto）の先頭の金額部分を「今回分（累計）」の表記に書き換える */
function yen(n) { return Math.round(num(n)).toLocaleString("ja-JP"); }
function rewriteAutoMoney(rec) {
  var auto = String(rec.auto || "");
  var prev = rec.prevId ? "" : null;                                  // 月の初回は累計表記なし
  var money = rec.mtype === "box"
    ? "売上" + yen(rec.sBox) + "円" + (rec.prevId ? "（累計" + yen(cumOf(rec).sBox) + "円）" : "")
    : "AB" + yen(rec.sAB) + "/CD" + yen(rec.sCD) + "円" + (rec.prevId ? "（累計 AB" + yen(cumOf(rec).sAB) + "/CD" + yen(cumOf(rec).sCD) + "）" : "");
  var parts = auto.split(" ｜ ");
  if (parts.length && /^(売上[\d,]+円|AB[\d,]+\/CD[\d,]+円)/.test(parts[0])) parts[0] = money; else parts.unshift(money);
  rec.auto = parts.join(" ｜ ");
  return rec;
}
/* 既存の記録を全部、累計入力→差分のルールで計算し直し、_app_db と巡回ログ（プレイ数）・部屋別ログ（ペア売上）を更新する。
   何度実行しても結果は同じ。エディタから実行 */
function recomputeSalesDeltas() {
  var sh = dbSheet(); var last = sh.getLastRow(); if (last < 2) return "記録なし";
  var v = sh.getRange(2, 1, last - 1, 6).getValues();
  var rows = [];
  v.forEach(function (r, i) { if (String(r[0]) !== "weekly") return; var rec; try { rec = JSON.parse(r[5]); } catch (e) { return; } rec.id = String(r[1]); rows.push({ row: i + 2, rec: rec }); });
  rows.sort(function (a, b) { return String(a.rec.createdAt || "").localeCompare(String(b.rec.createdAt || "")); });
  var done = [], changed = 0;
  var log = ss().getSheetByName("巡回ログ"), room = ss().getSheetByName("部屋別ログ");
  var logId = log ? idColumn(log, false) : 0, roomId = room ? idColumn(room, false) : 0;
  var logIds = (log && logId && log.getLastRow() > 1) ? log.getRange(2, logId, log.getLastRow() - 1, 1).getValues().map(function (x) { return String(x[0]); }) : [];
  var roomVals = (room && roomId && room.getLastRow() > 1) ? room.getRange(2, 1, room.getLastRow() - 1, roomId).getValues() : [];
  rows.forEach(function (x) {
    var rec = x.rec, before = JSON.stringify([rec.sAB, rec.sCD, rec.sBox, rec.sales, rec.plays]);
    applySalesDelta(rec, done); rewriteAutoMoney(rec);
    done.push(rec);
    if (JSON.stringify([rec.sAB, rec.sCD, rec.sBox, rec.sales, rec.plays]) !== before || !x.rec.cum) changed++;
    sh.getRange(x.row, 4, 1, 2).setValues([[nowIso(), "recompute"]]);
    sh.getRange(x.row, 6).setValue(JSON.stringify(stripId(rec)));
    // 巡回ログ：E列 プレイ数、J列 メモ（金額表記を今回分に）
    logIds.forEach(function (id, i) { if (id === rec.id) { log.getRange(i + 2, 5).setValue(num(rec.plays)); log.getRange(i + 2, 10).setValue(sheetMemo(rec)); } });
    // 部屋別ログ：G列 ペア売上（A/B→sAB、C/D→sCD、枠・本体→sBox）、F列 カウンター差（直前の訪問と比較）
    var prevR = done.filter(function (o) { return o.id !== rec.id && o.store === rec.store && o.machine === rec.machine && String(o.createdAt || "") < String(rec.createdAt || "") && o.rooms; })
      .sort(function (a, b) { return String(b.createdAt || "").localeCompare(String(a.createdAt || "")); })[0];
    roomVals.forEach(function (rv, i) {
      if (String(rv[roomId - 1]) !== rec.id) return;
      var k = String(rv[3]); var pair = (k === "A" || k === "B") ? rec.sAB : (k === "C" || k === "D") ? rec.sCD : rec.sBox;
      room.getRange(i + 2, 7).setValue(num(pair));
      var x = (rec.rooms || []).filter(function (y) { return (y.k === "-" ? "本体" : y.k) === k; })[0];
      var pv = (prevR && x) ? (prevR.rooms || []).filter(function (y) { return y.k === x.k; })[0] : null;
      if (x) room.getRange(i + 2, 6).setValue((pv && pv.counter !== "" && x.counter !== "") ? Math.round((num(x.counter) - num(pv.counter)) * 100) / 100 : "");
    });
  });
  var msg = "売上の差分を計算し直しました：" + rows.length + " 件（値が変わった/累計を補った " + changed + " 件）";
  Logger.log(msg); SpreadsheetApp.getActive().toast(msg); return msg;
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
  if (row && me.role !== "admin") {                     // 削除は登録した本人か管理者だけ
    var rec; try { rec = JSON.parse(dbSheet().getRange(row, 6).getValue()); } catch (e) { rec = {}; }
    var owner = rec.by || rec.staff || "";
    if (owner && owner !== me.name) throw new Error("この記録は " + owner + " さんが登録したものなので削除できません");
  }
  if (row) {
    var old; try { old = JSON.parse(dbSheet().getRange(row, 6).getValue()); } catch (e) { old = {}; }
    (old.photos || []).forEach(function (p) { try { DriveApp.getFileById(p.fid).setTrashed(true); } catch (e) {} });
    dbSheet().deleteRow(row);
  }
  dematerialize(col, id);
  if (col === "prizes") dropCache("sheet_master");
  return { ok: true };
}
/* 記録の修正（登録した本人か管理者）。巡回の記録のみ。
   createdAt・by・sentAt・photos は元の値を保ち、売上の差分を計算し直して、巡回ログ・部屋別ログ・景品実績の行を作り直す。
   同じ店舗・機械のあとの訪問は「前回」が変わるので、差分と行を同じように作り直す（写真タブの行はそのまま） */
var REFRESH_TABS = ["巡回ログ", "部屋別ログ", "景品実績"];
function updateDoc(me, col, id, obj) {
  if (col !== "weekly") throw new Error("この記録は修正できません");
  var row = findDbRow(col, id);
  if (!row) throw new Error("記録が見つかりません");
  var sh = dbSheet();
  var old; try { old = JSON.parse(sh.getRange(row, 6).getValue()); } catch (e) { old = {}; }
  var owner = old.by || old.staff || "";
  if (me.role !== "admin" && owner && owner !== me.name) throw new Error("この記録は " + owner + " さんが登録したものなので修正できません");
  var rec = Object.assign({}, obj || {});
  rec.id = id; rec.createdAt = old.createdAt || rec.createdAt || nowIso(); rec.by = old.by || me.name; rec.sentAt = old.sentAt || nowIso();
  if (old.photos) rec.photos = old.photos;
  if (me.role !== "admin" || !rec.staff) rec.staff = old.staff || me.name;
  rec.editedAt = nowIso(); rec.editedBy = me.name;
  var docs = readAllDocs();
  docs.weekly = docs.weekly.map(function (r) { return r.id === id ? rec : r; });
  applySalesDelta(rec, docs.weekly);
  sh.getRange(row, 4, 1, 3).setValues([[nowIso(), me.name, JSON.stringify(stripId(rec))]]);
  rematerialize(rec, docs);
  // あとの訪問（同じ店舗・機械）を作り直す
  var later = docs.weekly.filter(function (r) { return r.id !== id && r.store === rec.store && r.machine === rec.machine && String(r.createdAt || "") > String(rec.createdAt || ""); })
    .sort(function (a, b) { return String(a.createdAt || "").localeCompare(String(b.createdAt || "")); });
  var recs = [];
  later.forEach(function (r) {
    applySalesDelta(r, docs.weekly); rewriteAutoMoney(r);
    var rr = findDbRow("weekly", r.id); if (!rr) return;
    sh.getRange(rr, 4, 1, 3).setValues([[nowIso(), "recompute", JSON.stringify(stripId(r))]]);
    rematerialize(r, docs); recs.push(r);
  });
  return { ok: true, rec: rec, recs: recs };
}
function rematerialize(rec, docs) {
  REFRESH_TABS.forEach(function (n) {
    var sh = ss().getSheetByName(n); if (!sh) return;
    var idc = idColumn(sh, false); if (!idc) return;
    var last = sh.getLastRow(); if (last < 2) return;
    var v = sh.getRange(2, idc, last - 1, 1).getValues();
    for (var i = v.length - 1; i >= 0; i--) if (String(v[i][0]) === String(rec.id)) sh.deleteRow(i + 2);
  });
  var earlier = { weekly: docs.weekly.filter(function (o) { return String(o.createdAt || "") < String(rec.createdAt || ""); }) };
  materialize("weekly", rec, earlier);
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
  if (!PropertiesService.getScriptProperties().getProperty("photoTrigger")) {   // 10分ごとのトリガーが無いときだけ、起動時に取り込む（遅くなるので setup でトリガーを入れる）
    try { importPhotoChecksIfDue(); } catch (e) { Logger.log("importPhotoChecks: " + e); }
  }
  return {
    me: me,
    staff: staffNames(),
    docs: readAllDocs(),
    sheet_master: cachedJson("sheet_master", 120, readPrizeMaster),
    stores: cachedJson("stores", 300, readPastStores),
    time: nowIso()
  };
}
/* 読むだけで変わりにくいものは CacheService に数分置く（アプリの起動を速くする） */
function cachedJson(key, sec, fn) {
  var c = CacheService.getScriptCache();
  try { var hit = c.get("bs_" + key); if (hit) return JSON.parse(hit); } catch (e) {}
  var val = fn();
  try { c.put("bs_" + key, JSON.stringify(val), sec); } catch (e) {}
  return val;
}
function dropCache(key) { try { CacheService.getScriptCache().remove("bs_" + key); } catch (e) {} }

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
    appendPrizeStats(rec, (docs && docs.weekly) || []);
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
  var names = col === "weekly" ? ["巡回ログ", "部屋別ログ", PRIZE_STATS_SHEET, PHOTO_SHEET] : col === "prizes" ? ["景品マスタ"] : col === "expenses" ? ["経費台帳"] : [];
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
      x.prize || "", (x.before === "" || x.before === undefined) ? "" : num(x.before), x.addPrize || "", num(x.add), (x.pays === null || x.pays === undefined) ? "" : x.pays,
      num(x.take) > 0 ? num(x.take) : ""]);                                       // M列 回収数（機械から抜いて在庫へ戻した数）
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

/* ===================== 景品実績（景品ごとの区間データ。再現性のための元データ） =====================
   訪問ごとに「前回訪問から今回まで」の区間を景品単位で1行にする。
   4人機：部屋のカウンター差＝その景品のプレイ数、在庫差＝払出。区間の景品＝前回訪問時にその部屋へ入れていた景品。
   BOX：売上は景品に分けられないので払出だけ（プレイ数・売上は空欄）。
   列：訪問日 / 店舗 / 機械 / 部屋 / 景品 / 日数 / プレイ数 / 払出数 / 仕入単価 / 景品原価 / 売上 / 原価率 / 獲得率(1/N) / 担当 / アプリID */
var PRIZE_STATS_SHEET = "景品実績";
function prizeStatsSheet() {
  var sh = ss().getSheetByName(PRIZE_STATS_SHEET);
  if (!sh) {
    sh = ss().insertSheet(PRIZE_STATS_SHEET);
    sh.getRange(1, 1, 1, 15).setValues([["訪問日", "店舗", "機械", "部屋", "景品", "日数", "プレイ数", "払出数", "仕入単価", "景品原価", "売上", "原価率", "獲得率(1/N)", "担当", ID_HEADER]]).setFontWeight("bold");
    sh.getRange(1, 17).setValue("アプリが自動で書く。1行＝前回訪問から今回までの区間 × 景品。4人機はカウンター差がプレイ数、BOX機は払出数のみ。");
    sh.setFrozenRows(1);
  }
  return sh;
}
function unitCostMap() {
  var m = {}; readPrizeMaster().rows.forEach(function (r) { if (r.name && !(r.name in m)) m[r.name] = num(r.cost); });
  return m;
}
function daysBetween(a, b) {               // "YYYY-MM-DD" 同士
  var da = dateOf(a), db = dateOf(b);
  if (!(da instanceof Date) || !(db instanceof Date)) return 1;
  return Math.max(1, Math.round((db.getTime() - da.getTime()) / 864e5));
}
function prizeStatRows(rec, allWeekly, units) {
  var prev = allWeekly.filter(function (o) { return o.id !== rec.id && o.store === rec.store && o.machine === rec.machine && String(o.createdAt || "") < String(rec.createdAt || "") && ((o.rooms && o.rooms.length) || (o.slots && o.slots.length)); })
    .sort(function (a, b) { return String(b.createdAt || "").localeCompare(String(a.createdAt || "")); })[0];
  if (!prev) return [];
  var days = daysBetween(prev.week, rec.week), wk = dateOf(rec.week), out = [];
  if (rec.mtype !== "box" && rec.rooms && rec.rooms.length) {
    (rec.rooms || []).forEach(function (x) {
      var pv = (prev.rooms || []).filter(function (y) { return y.k === x.k; })[0]; if (!pv) return;
      var prize = (pv.addPrize && num(pv.add) > 0) ? pv.addPrize : (pv.prize || ""); if (!prize) return;
      var hasC = pv.counter !== "" && x.counter !== "" && pv.counter !== undefined && x.counter !== undefined;
      var plays = hasC ? Math.max(0, num(x.counter) - num(pv.counter)) : "";
      var pays = (x.pays === null || x.pays === undefined) ? "" : num(x.pays);
      var unit = units[prize]; var cost = (pays !== "" && unit) ? pays * unit : "";
      var sales = plays !== "" ? plays * PLAY_PRICE : "";
      var ratio = (sales !== "" && sales > 0 && cost !== "") ? cost / sales : "";
      var nOf = (plays !== "" && pays !== "" && pays > 0) ? plays / pays : "";
      out.push([wk, rec.store, rec.machine, x.k === "-" ? "本体" : x.k, prize, days, plays, pays, unit || "", cost, sales, ratio, nOf, rec.staff || ""]);
    });
  } else if (rec.mtype === "box" || (rec.slots && rec.slots.length)) {
    var outs = {}; (rec.slots || []).forEach(function (x) { if (x.out && x.prize) outs[x.prize] = (outs[x.prize] || 0) + 1; });
    var inPlace = {}; (prev.slots || []).forEach(function (x) { var n = x.filled || x.prize; if (n) inPlace[n] = true; });
    Object.keys(inPlace).forEach(function (prize) {
      var pays = outs[prize] || 0, unit = units[prize];
      out.push([wk, rec.store, rec.machine, "BOX", prize, days, "", pays, unit || "", unit ? pays * unit : "", "", "", "", rec.staff || ""]);
    });
  }
  return out;
}
function appendPrizeStats(rec, allWeekly) {
  var rows = prizeStatRows(rec, allWeekly, unitCostMap()); if (!rows.length) return 0;
  var sh = prizeStatsSheet();
  rows.forEach(function (row) {
    var r = appendValues(sh, row, rec.id);
    sh.getRange(r, 1).setNumberFormat("yyyy/mm/dd"); sh.getRange(r, 12).setNumberFormat("0.0%"); sh.getRange(r, 13).setNumberFormat("0.0");
  });
  return rows.length;
}
/* 景品実績タブを全記録から作り直す（エディタから実行。再実行しても同じ結果） */
function rebuildPrizeStats() {
  var sh = prizeStatsSheet();
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, sh.getMaxColumns()).clearContent();
  var docs = readAllDocs(), units = unitCostMap(), n = 0;
  var all = docs.weekly.slice().sort(function (a, b) { return String(a.createdAt || "").localeCompare(String(b.createdAt || "")); });
  all.forEach(function (rec, i) { n += appendPrizeStatsWith(rec, all.slice(0, i), units, sh); });
  var msg = "景品実績を作り直しました：" + n + " 行";
  Logger.log(msg); SpreadsheetApp.getActive().toast(msg); return msg;
}
function appendPrizeStatsWith(rec, prevAll, units, sh) {
  var rows = prizeStatRows(rec, prevAll, units); if (!rows.length) return 0;
  rows.forEach(function (row) {
    var r = appendValues(sh, row, rec.id);
    sh.getRange(r, 1).setNumberFormat("yyyy/mm/dd"); sh.getRange(r, 12).setNumberFormat("0.0%"); sh.getRange(r, 13).setNumberFormat("0.0");
  });
  return rows.length;
}

/* ===================== 写真（巡回報告に添付した機械の写真） =====================
   アプリから action:"photo" で base64 の JPEG が届く。Drive の「クレーンログ写真／店舗／yyyy-MM」に保存し、
   記録（_app_db の photos[]）と「写真」タブに 1 行追加する。リンクを知っている人は見られる設定にする
   （アプリでサムネイルを出すため。写真は機械の正面だけなので個人情報は写らない運用）。
   種別は 補充前（着いてすぐ）／補充後（補充・入れ替え後）。「写真」タブの I 列以降は、毎日の自動チェック（Claude のルーティン）が Drive の
   「クレーンログ写真／_チェック結果」に置く JSON を importPhotoChecks() が取り込んで埋める。 */
var PHOTO_SHEET = "写真";
var PHOTO_ROOT = "クレーンログ写真";
var PHOTO_CHECK_DIR = "_チェック結果";
var PHOTO_HEADERS = ["訪問日", "店舗", "機械", "担当", "種別", "写真URL", "ファイルID", "登録日時",
  "チェック日時", "空き部屋", "空き数", "報告の払出", "照合", "POP数", "陳列スコア", "所見", "競合メモ"];
var PHOTO_KINDS = { before: "補充前", after: "補充後" };
var PHOTO_MAX_BYTES = 6 * 1024 * 1024;

function photoSheet() {
  var sh = ss().getSheetByName(PHOTO_SHEET);
  if (!sh) {
    sh = ss().insertSheet(PHOTO_SHEET);
    sh.getRange(1, 1, 1, PHOTO_HEADERS.length).setValues([PHOTO_HEADERS]).setFontWeight("bold");
    sh.getRange(1, PHOTO_HEADERS.length + 1).setValue("A〜H はアプリが書く（種別＝補充前／補充後）。I〜Q は毎日の自動チェック（Drive の _チェック結果 から取り込み）。");
    sh.setFrozenRows(1); sh.setColumnWidth(6, 220); sh.setColumnWidth(16, 320);
  }
  return sh;
}
function folderUnder(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}
function photoRoot() { return folderUnder(DriveApp.getRootFolder(), PHOTO_ROOT); }
function photoCheckDir() { return folderUnder(photoRoot(), PHOTO_CHECK_DIR); }

function addPhoto(me, id, data, mime, kind) {
  kind = kind === "after" ? "after" : "before";
  var row = findDbRow("weekly", id);
  if (!row) throw new Error("記録が見つかりません");
  var sh = dbSheet();
  var rec; try { rec = JSON.parse(sh.getRange(row, 6).getValue()); } catch (e) { rec = {}; }
  var owner = rec.by || rec.staff || "";
  if (me.role !== "admin" && owner && owner !== me.name) throw new Error("この記録は " + owner + " さんのものなので写真を付けられません");
  var b64 = String(data || "").replace(/^data:[^;]+;base64,/, "");
  if (!b64) throw new Error("写真のデータがありません");
  var bytes = Utilities.base64Decode(b64);
  if (bytes.length > PHOTO_MAX_BYTES) throw new Error("写真が大きすぎます（" + Math.round(bytes.length / 1024 / 1024) + "MB）");
  var ext = /png/i.test(mime || "") ? "png" : "jpg";
  var n = (rec.photos || []).filter(function (p) { return (p.kind || "before") === kind; }).length + 1;
  var day = String(rec.week || "").slice(0, 10) || Utilities.formatDate(new Date(), TZ, "yyyy-MM-dd");
  var name = day + "_" + clean(rec.store) + "_" + clean(rec.machine).replace(/[\/\\:*?"<>|]/g, "") + "_" + PHOTO_KINDS[kind] + n + "_" + id + "." + ext;
  var folder = folderUnder(folderUnder(photoRoot(), clean(rec.store) || "店舗不明"), day.slice(0, 7));
  var file = folder.createFile(Utilities.newBlob(bytes, ext === "png" ? "image/png" : "image/jpeg", name));
  try { file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch (e) {}
  var p = { fid: file.getId(), url: "https://drive.google.com/file/d/" + file.getId() + "/view", at: nowIso(), by: me.name, kind: kind };
  rec.photos = (rec.photos || []).concat([p]);
  rec.id = id;
  sh.getRange(row, 4, 1, 3).setValues([[nowIso(), me.name, JSON.stringify(stripId(rec))]]);
  var ps = photoSheet();
  var r = appendValues(ps, [dateOf(rec.week), rec.store || "", rec.machine || "", rec.staff || "", PHOTO_KINDS[kind], p.url, p.fid, p.at], id);
  ps.getRange(r, 1).setNumberFormat("yyyy/mm/dd");
  return { ok: true, rec: rec, photo: p };
}

/* 自動チェックの結果を取り込む。_チェック結果 フォルダの JSON（1 回分）：
   { "checkedAt": "2026-10-08T22:10:00+09:00",
     "items": [ { "fid": "<DriveファイルID>", "emptyRooms": [5,6], "emptyCount": 2, "reportedPays": 2, "match": "一致|不一致|不明",
                  "popCount": 9, "score": 4, "note": "…", "competitor": "…" } ] }
   取り込んだファイルは名前の先頭に done_ を付ける（何度実行しても二重にならない） */
function importPhotoChecks() {
  var dir = photoCheckDir();
  var files = dir.getFiles(), n = 0, m = 0;
  var ps = photoSheet();
  var last = ps.getLastRow();
  var fids = last >= 2 ? ps.getRange(2, 7, last - 1, 1).getValues().map(function (r) { return String(r[0]); }) : [];
  while (files.hasNext()) {
    var f = files.next();
    var name = f.getName();
    if (/^done_/.test(name) || !/\.json$/i.test(name)) continue;
    var data; try { data = JSON.parse(f.getBlob().getDataAsString("UTF-8")); } catch (e) { Logger.log("JSON不正: " + name); continue; }
    var at = data.checkedAt || nowIso();
    (data.items || []).forEach(function (it) {
      var i = fids.indexOf(String(it.fid || "")); if (i < 0) return;
      var rooms = Array.isArray(it.emptyRooms) ? it.emptyRooms.join(",") : String(it.emptyRooms || "");
      ps.getRange(i + 2, 9, 1, 9).setValues([[at, rooms, it.emptyCount == null ? "" : num(it.emptyCount), it.reportedPays == null ? "" : num(it.reportedPays),
        it.match || "", it.popCount == null ? "" : num(it.popCount), it.score == null ? "" : num(it.score), clean(it.note || ""), clean(it.competitor || "")]]);
      m++;
    });
    f.setName("done_" + name); n++;
  }
  PropertiesService.getScriptProperties().setProperty("photoChecksAt", String(Date.now()));
  var msg = "チェック結果を取り込みました：" + n + " ファイル / " + m + " 枚";
  Logger.log(msg); return msg;
}
/* アプリ起動（bootstrap）のたびに呼ばれる。10 分に 1 回だけ Drive を見に行く */
function importPhotoChecksIfDue() {
  var pr = PropertiesService.getScriptProperties();
  var at = num(pr.getProperty("photoChecksAt"));
  if (Date.now() - at < 10 * 60 * 1000) return;
  pr.setProperty("photoChecksAt", String(Date.now()));
  importPhotoChecks();
}
/* 自動チェック用：未チェックの写真を JSON で返す（エディタから実行して確認する用） */
function pendingPhotos() {
  var ps = photoSheet(); var last = ps.getLastRow(); if (last < 2) return [];
  var v = ps.getRange(2, 1, last - 1, PHOTO_HEADERS.length).getValues();
  var out = [];
  v.forEach(function (r) { if (r[6] && !r[8]) out.push({ date: r[0], store: r[1], machine: r[2], staff: r[3], kind: r[4], url: r[5], fid: r[6] }); });
  Logger.log(JSON.stringify(out)); return out;
}

/* ===================== 仕入れ（EXAmuse 仕入れ想定商品スプシとの連携） =====================
   アプリの「仕入れ」タブ用。インフィニティからのメールを Mac が解析して書く「商品一覧」を読み、
   見送り／保留／発注の判断は _app_db（col=sourcing、id=商品キー）に持つ。
   「発注」にした商品は 商品一覧 の N 発注ケース数・Q 機械タイプ・R 発注備考 にも書く（スプシ側のメニューと同じ状態になる）。
   「発注要求を出す」は、EXAmuse 側 Apps Script の submitRequest と同じ形で「発注要求」タブの 2 行目に行を挿入する
   （状態=待機中、モード=下書き、内容(JSON)）。あとは Mac の examuse_sync が 2 分以内に拾い、発注書と Mail 下書きを作る。 */
var EXAMUSE_SHEET_ID = "1c2dDei3-fMUtsAFXl4cnqvTMTuhjKrLEVSi0NSwEtAw";
var EXA = { date: 1, name: 2, code: 3, maker: 4, qty: 5, price: 6, caseAmt: 7, retail: 8, variety: 9, lead: 10, half: 11, ship: 12, caution: 13,
  cases: 14, pcs: 15, amount: 16, machine: 17, memo: 18, status: 19, check: 20, image: 21, subject: 22, mailId: 23, key: 24, raw: 25 };
var SOURCING_DAYS = 60;      // 何日前までの商品を返すか
function exaSs() { return SpreadsheetApp.openById(EXAMUSE_SHEET_ID); }
function requireSourcing(me) { if (!me || !(me.role === "admin" || me.sourcing)) throw new Error("仕入れの操作は許可された人だけです（スタッフタブの「仕入れ」にチェック）"); }
function exaItems() {
  var sh = exaSs().getSheetByName("商品一覧"); if (!sh) return [];
  var last = sh.getLastRow(); if (last < 2) return [];
  var ncol = Math.max(sh.getLastColumn(), EXA.raw);
  var v = sh.getRange(2, 1, last - 1, ncol).getValues();
  var f = sh.getRange(2, EXA.image, last - 1, 1).getFormulas();
  var tz = sheetTz(), out = [];
  var since = new Date(Date.now() - SOURCING_DAYS * 864e5);
  for (var i = 0; i < v.length; i++) {
    var r = v[i]; var key = clean(r[EXA.key - 1]); if (!key) continue;
    var d = r[EXA.date - 1]; var date = d instanceof Date ? Utilities.formatDate(d, tz, "yyyy-MM-dd") : String(d || "").slice(0, 10);
    if (d instanceof Date && d < since) continue;
    var m = String(f[i][0] || "").match(/IMAGE\("([^"]+)"/);
    out.push({
      row: i + 2, key: key, date: date, name: clean(r[EXA.name - 1]), code: clean(r[EXA.code - 1]), maker: clean(r[EXA.maker - 1]),
      qty: numOrNull(r[EXA.qty - 1]), price: numOrNull(r[EXA.price - 1]), retail: numOrNull(r[EXA.retail - 1]),
      variety: clean(r[EXA.variety - 1]), lead: clean(r[EXA.lead - 1]), half: clean(r[EXA.half - 1]), ship: clean(r[EXA.ship - 1]), caution: clean(r[EXA.caution - 1]),
      cases: numOrNull(r[EXA.cases - 1]), machine: clean(r[EXA.machine - 1]), memo: clean(r[EXA.memo - 1]), status: clean(r[EXA.status - 1]), check: clean(r[EXA.check - 1]),
      img: m ? m[1] : "", subject: clean(r[EXA.subject - 1]), mailId: String(r[EXA.mailId - 1] || "").replace(/\.0$/, ""), raw: clean(r[EXA.raw - 1])
    });
  }
  return out;
}
function numOrNull(x) { if (x === "" || x === null || x === undefined) return null; var n = parseFloat(x); return isFinite(n) ? n : null; }
function exaRequests(n) {
  var sh = exaSs().getSheetByName("発注要求"); if (!sh) return [];
  var last = sh.getLastRow(); if (last < 2) return [];
  var v = sh.getRange(2, 1, Math.min(last - 1, n || 10), 10).getValues(), out = [];
  v.forEach(function (r) { if (!r[0]) return; out.push({ id: String(r[0]), at: String(r[1]), state: String(r[2]), mode: String(r[3]), n: num(r[4]), amount: num(r[5]), result: String(r[6] || ""), orderNo: String(r[7] || ""), staff: String(r[9] || "") }); });
  return out;
}
function exaSetting(name) {
  var sh = exaSs().getSheetByName("設定"); if (!sh) return "";
  var v = sh.getDataRange().getValues();
  for (var i = 1; i < v.length; i++) if (clean(v[i][0]) === name) return v[i][1];
  return "";
}
function readSourcing(force) {
  var cache = CacheService.getScriptCache(), hit = force ? null : cache.get("sourcing");
  if (hit) { try { return JSON.parse(hit); } catch (e) {} }
  var res = { items: exaItems(), requests: exaRequests(10), limit: num(exaSetting("発注金額の上限警告")) || 300000, time: nowIso() };
  try { cache.put("sourcing", JSON.stringify(res), 90); } catch (e) {}
  return res;
}
function exaRowByKey(sh, key) {
  var last = sh.getLastRow(); if (last < 2) return 0;
  var v = sh.getRange(2, EXA.key, last - 1, 1).getValues();
  for (var i = 0; i < v.length; i++) if (clean(v[i][0]) === key) return i + 2;
  return 0;
}
/* 判断を保存。decision: skip（見送り）／hold（保留）／order（発注）／空（未判断に戻す） */
function sourcingSet(me, key, decision, cases, machine, note) {
  key = clean(key); if (!key) throw new Error("商品キーがありません");
  decision = clean(decision); if (["skip", "hold", "order", ""].indexOf(decision) < 0) throw new Error("判断の値が不正です");
  var sh = exaSs().getSheetByName("商品一覧"); var row = exaRowByKey(sh, key);
  if (!row) throw new Error("商品一覧にこの商品が見つかりません");
  var status = clean(sh.getRange(row, EXA.status).getValue());
  if (/発注済/.test(status)) throw new Error("この商品は発注済みです");
  if (decision === "order") {
    cases = num(cases); if (!(cases > 0)) throw new Error("数量を選んでください");
    if (!(cases === 0.5 || cases === Math.floor(cases))) throw new Error("数量は ハーフ（0.5）か 1 ケース単位です");
    machine = clean(machine); if (["4人機用", "カリーノ用", ""].indexOf(machine) < 0) throw new Error("機械タイプの値が不正です");
    sh.getRange(row, EXA.cases).setValue(cases);
    if (machine) sh.getRange(row, EXA.machine).setValue(machine);
    sh.getRange(row, EXA.memo).setValue(clean(note || ""));
  } else {
    sh.getRange(row, EXA.cases).setValue("");          // 発注をやめたら N を空に（スプシ側の ① チェックに拾われないように）
  }
  var rec = { key: key, decision: decision, cases: decision === "order" ? num(cases) : null, machine: clean(machine || ""), note: clean(note || ""), by: me.name, at: nowIso() };
  var dbs = dbSheet(), r = findDbRow("sourcing", key), now = nowIso();
  if (decision === "") { if (r) dbs.deleteRow(r); return { ok: true, rec: null }; }
  if (r) dbs.getRange(r, 4, 1, 3).setValues([[now, me.name, JSON.stringify(rec)]]);
  else dbs.appendRow(["sourcing", key, now, now, me.name, JSON.stringify(rec)]);
  rec.id = key;
  try { CacheService.getScriptCache().remove("sourcing"); } catch (e) {}
  return { ok: true, rec: rec };
}
/* 解析漏れの手直し：商品名・品番・入数・単価 を 商品一覧 に書く */
function sourcingFix(me, key, fields) {
  key = clean(key); fields = fields || {};
  var sh = exaSs().getSheetByName("商品一覧"); var row = exaRowByKey(sh, key);
  if (!row) throw new Error("商品一覧にこの商品が見つかりません");
  if (fields.name !== undefined) sh.getRange(row, EXA.name).setValue(clean(fields.name));
  if (fields.code !== undefined) sh.getRange(row, EXA.code).setValue(clean(fields.code));
  // 入数・単価は金額に直結するので管理者だけ（スタッフからの指定は無視する）
  if (me.role === "admin") {
    if (fields.qty !== undefined) sh.getRange(row, EXA.qty).setValue(fields.qty === "" ? "" : num(fields.qty));
    if (fields.price !== undefined) sh.getRange(row, EXA.price).setValue(fields.price === "" ? "" : num(fields.price));
  }
  var raw = clean(sh.getRange(row, EXA.raw).getValue());
  sh.getRange(row, EXA.raw).setValue((raw ? raw + " ／ " : "") + "アプリで修正(" + me.name + " " + nowIso().slice(0, 10) + ")");
  try { CacheService.getScriptCache().remove("sourcing"); } catch (e) {}
  return { ok: true };
}
/* 「発注」にした商品をまとめて発注要求タブへ（EXAmuse 側 submitRequest と同じ行形式） */
function sourcingSubmit(me, keys) {
  keys = (keys || []).map(clean).filter(Boolean);
  if (!keys.length) throw new Error("発注する商品がありません");
  var ss2 = exaSs(), sh = ss2.getSheetByName("商品一覧"), rq = ss2.getSheetByName("発注要求");
  if (!sh || !rq) throw new Error("仕入れ想定商品スプシのタブが見つかりません");
  var items = [], errors = [], total = 0;
  keys.forEach(function (key) {
    var row = exaRowByKey(sh, key); if (!row) { errors.push(key + "：商品一覧にない"); return; }
    var r = sh.getRange(row, 1, 1, EXA.raw).getValues()[0];
    var name = clean(r[EXA.name - 1]), qty = num(r[EXA.qty - 1]), price = num(r[EXA.price - 1]), cases = num(r[EXA.cases - 1]);
    var status = clean(r[EXA.status - 1]);
    if (/発注済|下書き作成/.test(status)) { errors.push(name + "：すでに " + status); return; }
    if (!name) { errors.push(key + "：商品名が空（「直す」で入れてください）"); return; }
    if (!(qty > 0)) { errors.push(name + "：入数が空"); return; }
    if (!(price > 0)) { errors.push(name + "：単価が空"); return; }
    if (!(cases > 0)) { errors.push(name + "：ケース数が空"); return; }
    var pcs = Math.round(qty * cases), amount = Math.round(price * pcs); total += amount;
    items.push({ key: key, name: name, code: clean(r[EXA.code - 1]), qty: qty, price: price, cases: cases, pcs: pcs, amount: amount, memo: clean(r[EXA.memo - 1]), kind: clean(r[EXA.machine - 1]) });
  });
  if (errors.length) throw new Error("発注できない商品があります：\n" + errors.join("\n"));
  var tz = "Asia/Tokyo", now = new Date();
  var reqId = "R" + Utilities.formatDate(now, tz, "yyyyMMddHHmmss");
  rq.insertRowBefore(2);
  rq.getRange(2, 1, 1, 10).setValues([[reqId, Utilities.formatDate(now, tz, "yyyy-MM-dd HH:mm:ss"), "待機中", "下書き", items.length, total, "", "", JSON.stringify(items), me.name]]);
  rq.getRange(2, 6).setNumberFormat("#,##0");
  // 判断レコードを「要求済み」に
  var dbs = dbSheet();
  items.forEach(function (it) {
    var r = findDbRow("sourcing", it.key); var rec;
    try { rec = r ? JSON.parse(dbs.getRange(r, 6).getValue()) : {}; } catch (e) { rec = {}; }
    rec.key = it.key; rec.decision = "order"; rec.requestId = reqId; rec.requestedAt = nowIso(); rec.by = rec.by || me.name;
    if (r) dbs.getRange(r, 4, 1, 3).setValues([[nowIso(), me.name, JSON.stringify(rec)]]);
    else dbs.appendRow(["sourcing", it.key, nowIso(), nowIso(), me.name, JSON.stringify(rec)]);
  });
  try { CacheService.getScriptCache().remove("sourcing"); } catch (e) {}
  return { ok: true, requestId: reqId, n: items.length, total: total, warn: total > (num(exaSetting("発注金額の上限警告")) || 300000) ? "合計が上限警告額を超えています" : "" };
}

/* 仕入れ連携の初回認可用：エディタで一度 ▶ 実行し、仕入れ想定商品スプシへのアクセスを承認する（以後は不要） */
function authorizeExamuse() {
  var name = exaSs().getName(); var n = exaItems().length;
  var msg = "仕入れ想定商品スプシ「" + name + "」を読めました：商品 " + n + " 件（直近 " + SOURCING_DAYS + " 日）";
  Logger.log(msg); SpreadsheetApp.getActive().toast(msg); return msg;
}

/* ===================== 手動メンテ用（エディタから実行） ===================== */
/* 巡回ログ・部屋別ログの A1「週」を「訪問日」に改名（記録は訪問ごと。K列の週キーは数式のまま） */
function renameDateHeaders() {
  ["巡回ログ", "部屋別ログ"].forEach(function (n) {
    var sh = ss().getSheetByName(n); if (!sh) return;
    if (String(sh.getRange(1, 1).getValue()).trim() === "週") sh.getRange(1, 1).setValue("訪問日");
  });
  upgradeStockFormulas();
}
/* 部屋別ログ M列「回収数」と、景品マスタ J列（残り在庫）に回収分を足し戻す数式。再実行しても安全 */
function upgradeStockFormulas() {
  var rs = ss().getSheetByName("部屋別ログ");
  if (rs && String(rs.getRange(1, 13).getValue()).trim() === "") rs.getRange(1, 13).setValue("回収数");
  var pm = ss().getSheetByName("景品マスタ");
  if (pm) {
    var f = String(pm.getRange(2, 10).getFormula() || "");
    if (f && f.indexOf("$M$") < 0) {
      pm.getRange(2, 10).setFormula("=ARRAYFORMULA(IF((A2:A500=\"\")+(F2:F500=\"\"),\"\",F2:F500-I2:I500+IF(A2:A500=\"\",0,SUMIF('部屋別ログ'!$H$2:$H$8000,A2:A500,'部屋別ログ'!$M$2:$M$8000))))");
    }
  }
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
/* 旧アプリから移行した記録のうち、10/6 に入力されたのに訪問日が 10/5（当時の週キー）になっていた4件を 10/6 に直す。
   _app_db の week を書き換え、巡回ログ・部屋別ログの A列も repairDates() で書き直す。何度実行しても同じ結果 */
function fixVisitDates() {
  var FIX = { m7v9mtwhkj2lf1ga4ovx: "2026-10-06", "6sxqysgo5hojclaycvdn": "2026-10-06", zgjurui20aaixqesdaz6: "2026-10-06", y6k1s9p3ptibnslmheeu: "2026-10-06" };
  var sh = dbSheet(); var last = sh.getLastRow(); var n = 0;
  if (last >= 2) {
    var v = sh.getRange(2, 1, last - 1, 6).getValues();
    v.forEach(function (r, i) {
      if (String(r[0]) !== "weekly" || !FIX[String(r[1])]) return;
      var rec; try { rec = JSON.parse(r[5]); } catch (e) { return; }
      if (rec.week === FIX[String(r[1])]) return;
      rec.week = FIX[String(r[1])];
      sh.getRange(i + 2, 4, 1, 3).setValues([[nowIso(), "fixdate", JSON.stringify(rec)]]); n++;
    });
  }
  var msg = "訪問日を直しました：" + n + " 件 → " + repairDates();
  Logger.log(msg); SpreadsheetApp.getActive().toast(msg); return msg;
}
/* 写真チェック結果の取り込みを 10 分ごとのトリガーにする（アプリ起動時の取り込みをやめて起動を速くする）。再実行しても 1 本だけ */
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === "importPhotoChecks") ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger("importPhotoChecks").timeBased().everyMinutes(10).create();
  PropertiesService.getScriptProperties().setProperty("photoTrigger", "1");
  return "importPhotoChecks を 10 分ごとに実行するトリガーを入れました";
}
function setup() {            // 初回：スタッフタブと _app_db を作る（再実行しても安全）
  ensureStaffSheet(); dbSheet(); renameDateHeaders(); photoSheet(); photoCheckDir();
  var sc = ensureSourcingColumn(); var tr = installTriggers();
  SpreadsheetApp.getActive().toast("スタッフタブ（仕入れ列 " + sc + "）・_app_db・写真タブ・Drive の写真フォルダ・" + tr);
}
