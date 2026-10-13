/* =====================================================================================
   クレーンログ ローダー（Apps Script に貼るのはこのファイルだけ。以後の貼り替えは不要）

   本物のコード（apps-script/Code.gs）は GitHub から読み込んで、その場で実行する。
   - 10 分（CODE_TTL_SEC）は CacheService に置いて使い回す。切れたら GitHub を見に行く。
   - GitHub から取れないときは、最後にうまく読めたコードの控え（Drive のファイル）を使う。
   - 取ってきたコードは構文チェック（new Function）に通ったものだけ使う。壊れていれば前のまま。
   - 「selfUpdate」はキャッシュを捨てていますぐ取り直す（15 分ごとのトリガーでも呼ばれる）。
   - Apps Script API・デプロイの作り直しは使わない。ウェブアプリのデプロイはこのローダーの 1 回だけでよい。

   うまく動かないとき：
   - スクリプト プロパティ codeUrl を入れると、そこから読む（別のブランチ・特定コミットに固定できる）。
   - スクリプト プロパティ codeError に、最後に GitHub から読めなかった理由が残る。
   - ウェブアプリの URL を開くと、動いているコードの build・読み込み元・読み込み時刻が JSON で出る。
   ===================================================================================== */
var LOADER_BUILD = "loader-2026-10-13";
var CODE_URL_DEFAULT = "https://raw.githubusercontent.com/skikuchi-hub/cursor-/claude/examuse-prize-handover-8s2xx8/apps-script/Code.gs";
var CODE_TTL_SEC = 600;
var CODE_CACHE_KEY = "crane_code_v1";
var CODE_COPY_NAME = "クレーンログ_Code.gs_控え（自動・消さない）";

/* ---------- 入口（エディタの関数一覧に出す分。ここに無い関数も、下の動的定義で呼べる） ---------- */
function doGet(e)              { return run_("doGet", [e]); }
function doPost(e)             { return run_("doPost", [e]); }
function importPhotoChecks()   { return run_("importPhotoChecks", []); }
function selfUpdate()          { return refreshCode_(); }
function installTriggers()     { return run_("installTriggers", []); }
function setup()               { refreshCode_(); return run_("setup", []); }
function updateMetrics()       { return run_("updateMetrics", []); }
function rebuildPrizeStats()   { return run_("rebuildPrizeStats", []); }
function repairChain()         { return run_("repairChain", []); }
function repairDates()         { return run_("repairDates", []); }
function deleteOrderNo()       { return run_("deleteOrderNo", []); }
function resetBulkCost()       { return run_("resetBulkCost", []); }
function allocateBulkCost()    { return run_("allocateBulkCost", []); }
function authorizeExamuse()    { return run_("authorizeExamuse", []); }
function ensurePrizeColumns()  { return run_("ensurePrizeColumns", []); }
function upgradeStockFormulas(){ return run_("upgradeStockFormulas", []); }
/* 本物のコードの状態を見る（エディタから実行して実行ログで確認） */
function codeStatus() {
  var p = PropertiesService.getScriptProperties().getProperties();
  var msg = "loader " + LOADER_BUILD + " ／ 読み込み元 " + (p.codeSource || "-") + " ／ 取得 " + (p.codeFetchedAt || "-") +
            " ／ build " + (p.codeBuild || "-") + " ／ 最後のエラー " + (p.codeError || "なし") + " ／ URL " + codeUrl_();
  Logger.log(msg); return msg;
}

/* ---------- 本体 ---------- */
function codeUrl_() { return PropertiesService.getScriptProperties().getProperty("codeUrl") || CODE_URL_DEFAULT; }
function nowIso_() { return Utilities.formatDate(new Date(), "Asia/Tokyo", "yyyy-MM-dd'T'HH:mm:ssXXX"); }
function buildOf_(code) { var m = code.match(/var\s+CODE_BUILD\s*=\s*"([^"]+)"/); return m ? m[1] : ""; }
function validCode_(t) {
  if (!t || t.length < 20000 || !/function doPost\(/.test(t)) return false;
  try { new Function(t); return true; } catch (e) { return false; }
}
/* CacheService は 1 値 100KB（バイト）までなので、日本語を含めても収まるよう 3 万文字ずつに分割して置く */
function cachePut_(cache, code) {
  var n = Math.ceil(code.length / 30000), parts = {};
  for (var i = 0; i < n; i++) parts[CODE_CACHE_KEY + "_" + i] = code.slice(i * 30000, (i + 1) * 30000);
  parts[CODE_CACHE_KEY + "_n"] = String(n);
  cache.putAll(parts, CODE_TTL_SEC);
}
function cacheGet_(cache) {
  var n = +(cache.get(CODE_CACHE_KEY + "_n") || 0); if (!n) return null;
  var keys = []; for (var i = 0; i < n; i++) keys.push(CODE_CACHE_KEY + "_" + i);
  var got = cache.getAll(keys), code = "";
  for (var j = 0; j < n; j++) { var part = got[CODE_CACHE_KEY + "_" + j]; if (part == null) return null; code += part; }
  return validCode_(code) ? code : null;
}
function cacheDrop_(cache) {
  var keys = [CODE_CACHE_KEY + "_n"]; for (var i = 0; i < 12; i++) keys.push(CODE_CACHE_KEY + "_" + i);
  try { cache.removeAll(keys); } catch (e) {}
}
/* Drive の控え（GitHub が落ちている・ネットが切れているときの最後の砦） */
function copyFile_(create) {
  var props = PropertiesService.getScriptProperties(), id = props.getProperty("codeCopyId");
  if (id) { try { var f = DriveApp.getFileById(id); if (!f.isTrashed()) return f; } catch (e) {} }
  if (!create) return null;
  var f2 = DriveApp.createFile(CODE_COPY_NAME, "", MimeType.PLAIN_TEXT);
  props.setProperty("codeCopyId", f2.getId()); return f2;
}
function saveCopy_(code) { try { copyFile_(true).setContent(code); } catch (e) {} }
function readCopy_() { try { var f = copyFile_(false); if (!f) return null; var t = f.getBlob().getDataAsString("UTF-8"); return validCode_(t) ? t : null; } catch (e) { return null; } }

/* GitHub から取る。だめなら控え。force＝キャッシュを無視していますぐ取り直す */
function loadCode_(force) {
  var cache = CacheService.getScriptCache(), props = PropertiesService.getScriptProperties();
  if (!force) { var c = cacheGet_(cache); if (c) return c; }
  var code = null, err = "";
  try {
    var res = UrlFetchApp.fetch(codeUrl_() + (codeUrl_().indexOf("?") < 0 ? "?" : "&") + "t=" + Date.now(), { muteHttpExceptions: true, followRedirects: true });
    var sc = res.getResponseCode();
    if (sc === 200) { var t = res.getContentText("UTF-8"); if (validCode_(t)) code = t; else err = "取得した内容がおかしい（長さ " + (t || "").length + "）"; }
    else err = "HTTP " + sc;
  } catch (e) { err = String(e && e.message || e); }
  if (code) {
    cachePut_(cache, code); saveCopy_(code);
    props.setProperties({ codeSource: "github", codeFetchedAt: nowIso_(), codeBuild: buildOf_(code), codeError: "" });
    return code;
  }
  props.setProperty("codeError", nowIso_() + " " + err);
  var copy = readCopy_();
  if (copy) { cachePut_(cache, copy); props.setProperties({ codeSource: "drive（控え）", codeBuild: buildOf_(copy) }); return copy; }
  throw new Error("本物のコードを読み込めません：" + err + "（codeUrl: " + codeUrl_() + "）");
}
function refreshCode_() {
  var before = PropertiesService.getScriptProperties().getProperty("codeBuild") || "";
  cacheDrop_(CacheService.getScriptCache());
  var code = loadCode_(true), b = buildOf_(code);
  var msg = (b === before ? "変更なし" : "更新しました") + "：build " + (b || "?") + "（" + nowIso_() + "）";
  Logger.log(msg); try { SpreadsheetApp.getActive().toast(msg); } catch (e) {}
  return msg;
}
/* 本物のコードの中の関数 name を取り出して呼ぶ */
function run_(name, args) {
  var code = loadCode_(false);
  var getter = new Function(code + "\n;return (typeof " + name + " === 'function') ? " + name + " : null;");
  var fn = getter();
  if (!fn) throw new Error("関数 " + name + " が本物のコードにありません（build " + (buildOf_(code) || "?") + "）");
  return fn.apply(null, Array.prototype.slice.call(args || []));
}
/* 上の一覧に無い関数（トリガーやメニューから名前で呼ばれるもの）も呼べるように、起動時に名前だけ用意する */
(function defineRest_() {
  try {
    var g = (typeof globalThis !== "undefined") ? globalThis : this;
    var code = loadCode_(false);
    var re = /^function\s+([A-Za-z0-9_$]+)\s*\(/gm, m;
    while ((m = re.exec(code))) { (function (n) { if (!(n in g)) g[n] = function () { return run_(n, arguments); }; })(m[1]); }
  } catch (e) { /* 読み込めないときは入口の関数が同じエラーを出す */ }
})();
