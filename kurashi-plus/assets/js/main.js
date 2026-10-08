/* くらしプラス 共通スクリプト */
(function () {
  'use strict';
  var cfg = window.KP_CONFIG || {};

  // ヘッダー：スクロールで背景
  var hdr = document.querySelector('.site-header');
  function onScroll(){ if (hdr) hdr.classList.toggle('scrolled', window.scrollY > 12); }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // モバイルメニュー
  var menuBtn = document.querySelector('.menu-btn');
  var nav = document.querySelector('.nav');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      document.body.classList.toggle('menu-open', open);
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('open');
        document.body.classList.remove('menu-open');
      });
    });
  }

  // スクロールで表示
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('.rv').forEach(function (el) { io.observe(el); });
    // グリッド内の要素は順番に少し遅らせる
    document.querySelectorAll('.svc-grid, .feat, .steps').forEach(function (g) {
      Array.prototype.forEach.call(g.children, function (c, i) { if (c.classList.contains('rv')) c.style.transitionDelay = (i * 90) + 'ms'; });
    });
  } else {
    document.querySelectorAll('.rv').forEach(function (el) { el.classList.add('in'); });
  }

  function toast(msg) {
    var t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('show');
    clearTimeout(t._tm); t._tm = setTimeout(function () { t.classList.remove('show'); }, 2600);
  }
  window.kpToast = toast;

  // お問い合わせフォーム
  var form = document.getElementById('contactForm');
  if (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var err = form.querySelector('.err');
      var data = {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        tel: form.tel.value.trim(),
        kind: form.kind.value,
        message: form.message.value.trim(),
        page: location.href,
        ua: navigator.userAgent
      };
      var problems = [];
      if (!data.name) problems.push('お名前');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) problems.push('メールアドレス');
      if (!data.message) problems.push('お問い合わせ内容');
      if (!form.agree.checked) problems.push('プライバシーポリシーへの同意');
      if (problems.length) {
        err.textContent = '入力をご確認ください：' + problems.join('、');
        err.style.display = 'block';
        return;
      }
      err.style.display = 'none';
      var btn = form.querySelector('button[type=submit]');
      btn.disabled = true; btn.textContent = '送信中…';

      var base = location.pathname.replace(/[^/]*$/, '');
      if (cfg.contactApi) {
        fetch(cfg.contactApi, {
          method: 'POST', mode: 'no-cors',
          headers: { 'Content-Type': 'text/plain;charset=utf-8' },
          body: JSON.stringify(data)
        }).then(function () {
          location.href = base + 'thanks.html';
        }).catch(function () {
          btn.disabled = false; btn.textContent = '送信する';
          err.textContent = '送信に失敗しました。時間をおいて再度お試しいただくか、メールでお問い合わせください。';
          err.style.display = 'block';
        });
      } else {
        // 送信先未設定のときはメールソフトを開く
        var body = '【お名前】' + data.name + '\n【メール】' + data.email + '\n【電話】' + data.tel +
          '\n【種別】' + data.kind + '\n\n' + data.message;
        location.href = 'mailto:' + (cfg.contactEmail || 'info@wst-inc.jp') +
          '?subject=' + encodeURIComponent('【くらしプラス】お問い合わせ（' + data.kind + '）') +
          '&body=' + encodeURIComponent(body);
        setTimeout(function () { btn.disabled = false; btn.textContent = '送信する'; }, 1500);
      }
    });
  }

  // ログイン（会員システム接続前のフロント動作）
  var login = document.getElementById('loginForm');
  if (login) {
    login.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var email = login.email.value.trim();
      var pw = login.password.value;
      var err = login.querySelector('.err');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || pw.length < 8) {
        err.textContent = 'メールアドレスと8文字以上のパスワードを入力してください。';
        err.style.display = 'block';
        return;
      }
      if (cfg.authApi) {
        // 会員API接続時：ここで認証APIを呼ぶ
        fetch(cfg.authApi + '/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email, password: pw }), credentials: 'include' })
          .then(function (r) { return r.json(); })
          .then(function (j) {
            if (j && j.ok) { sessionStorage.setItem('kp_user', JSON.stringify(j.user || { email: email })); location.href = 'mypage.html'; }
            else { err.textContent = (j && j.message) || 'ログインに失敗しました。'; err.style.display = 'block'; }
          })
          .catch(function () { err.textContent = '通信に失敗しました。'; err.style.display = 'block'; });
      } else {
        sessionStorage.setItem('kp_user', JSON.stringify({ email: email, name: email.split('@')[0] + ' 様' }));
        location.href = 'mypage.html';
      }
    });
  }

  // マイページ
  var my = document.getElementById('mypage');
  if (my) {
    var raw = sessionStorage.getItem('kp_user');
    if (!raw) { location.replace('login.html'); return; }
    var user = JSON.parse(raw);
    my.querySelector('.name').textContent = user.name || '会員';
    my.querySelector('.mail').textContent = user.email || '';
    var subsKey = 'kp_subs_' + (user.email || '');
    var subs = {};
    try { subs = JSON.parse(localStorage.getItem(subsKey) || '{}'); } catch (e) { subs = {}; }
    var items = my.querySelectorAll('.my-item');
    function paint() {
      var n = 0;
      items.forEach(function (it) {
        var code = it.dataset.code;
        var on = !!subs[code];
        if (on) n++;
        it.classList.toggle('on', on);
        it.querySelector('.st').innerHTML = on ? '<b>ご利用中</b>　次回更新日：毎月1日' : '未加入';
        var b = it.querySelector('button');
        b.textContent = on ? '解約する' : '申し込む';
        b.className = on ? 'btn btn-outline btn-sm' : 'btn btn-teal btn-sm';
      });
      var cnt = my.querySelector('.count');
      if (cnt) cnt.textContent = n;
    }
    items.forEach(function (it) {
      it.querySelector('button').addEventListener('click', function () {
        var code = it.dataset.code;
        var name = it.querySelector('h3').textContent;
        if (subs[code]) {
          if (!confirm(name + ' を解約しますか？\n解約は当月末に反映され、日割り計算はありません。')) return;
          delete subs[code]; toast(name + ' の解約を受け付けました');
        } else {
          if (!confirm(name + ' に申し込みますか？\n月額 ' + (it.dataset.price || '') + '（税抜）')) return;
          subs[code] = { since: new Date().toISOString() }; toast(name + ' のお申し込みを受け付けました');
        }
        localStorage.setItem(subsKey, JSON.stringify(subs));
        paint();
      });
    });
    paint();
    var lo = my.querySelector('.logout');
    if (lo) lo.addEventListener('click', function (ev) { ev.preventDefault(); sessionStorage.removeItem('kp_user'); location.href = 'index.html'; });
  }
})();
