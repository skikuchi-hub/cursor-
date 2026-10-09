// くらしプラス 接続設定
// contactApi: お問い合わせフォームの送信先（Apps Script ウェブアプリの URL）。
//             空のままだとメールソフトが開く方式（mailto）になります。
// contactEmail: mailto 方式のときの宛先。
// signupUrl: 会員システムのお申し込みページ URL。設定すると「お申し込み手続きへ進む」ボタンがそこへ飛びます。
// authApi: 会員ログイン API のベース URL（未接続なら空のまま。空のときはフロントのみで動くデモ表示）。
window.KP_CONFIG = {
  contactApi: "",
  contactEmail: "info@wst-inc.jp",
  signupUrl: "",
  authApi: ""
};
