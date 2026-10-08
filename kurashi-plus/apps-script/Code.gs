/**
 * くらしプラス お問い合わせフォーム受信用 Apps Script
 *
 * セットアップ：
 * 1. 新しい Google スプレッドシート（例「くらしプラス お問い合わせ」）を作り、拡張機能 → Apps Script を開く
 * 2. この内容を貼り付けて保存
 * 3. デプロイ → 新しいデプロイ → 種類：ウェブアプリ
 *    - 次のユーザーとして実行：自分
 *    - アクセスできるユーザー：全員
 * 4. 表示されたウェブアプリの URL を サイトの config.js の contactApi に入れる
 *
 * 受信すると「お問い合わせ」タブに1行追加し、TO_ADDRESS にメールで通知します。
 */
var TO_ADDRESS = 'info@wst-inc.jp';
var SITE_NAME = 'くらしプラス';

function doPost(e) {
  var out = { ok: false };
  try {
    var data = JSON.parse(e.postData.contents || '{}');
    var sheet = getSheet_();
    var now = new Date();
    sheet.appendRow([
      now, data.name || '', data.email || '', data.tel || '', data.kind || '',
      data.message || '', data.page || '', data.ua || ''
    ]);
    var body =
      '【' + SITE_NAME + '】サイトからお問い合わせがありました。\n\n' +
      '受信日時：' + Utilities.formatDate(now, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm') + '\n' +
      'お名前　：' + (data.name || '') + '\n' +
      'メール　：' + (data.email || '') + '\n' +
      '電話番号：' + (data.tel || '') + '\n' +
      '種別　　：' + (data.kind || '') + '\n\n' +
      '--- お問い合わせ内容 ---\n' + (data.message || '') + '\n\n' +
      '送信元ページ：' + (data.page || '');
    MailApp.sendEmail({
      to: TO_ADDRESS,
      replyTo: data.email || TO_ADDRESS,
      subject: '【' + SITE_NAME + '】お問い合わせ（' + (data.kind || '') + '）' + (data.name || ''),
      body: body
    });
    // 自動返信（送信者へ）
    if (data.email) {
      MailApp.sendEmail({
        to: data.email,
        subject: '【' + SITE_NAME + '】お問い合わせを受け付けました',
        body:
          (data.name || '') + ' 様\n\n' +
          'このたびは ' + SITE_NAME + ' へお問い合わせいただきありがとうございます。\n' +
          '以下の内容で受け付けました。担当者より平日12:00〜18:00の間にご返信いたします。\n\n' +
          '--- お問い合わせ内容 ---\n' + (data.message || '') + '\n\n' +
          '※このメールは自動送信です。心当たりのない場合は破棄してください。\n\n' +
          '株式会社WST\n' + TO_ADDRESS
      });
    }
    out.ok = true;
  } catch (err) {
    out.error = String(err);
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return ContentService.createTextOutput('ok');
}

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('お問い合わせ');
  if (!sh) {
    sh = ss.insertSheet('お問い合わせ');
    sh.appendRow(['受信日時', 'お名前', 'メール', '電話番号', '種別', '内容', '送信元ページ', 'UA']);
    sh.setFrozenRows(1);
  }
  return sh;
}
