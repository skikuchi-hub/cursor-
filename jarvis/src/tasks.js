// 作業（タスク）の受付・順番待ち・実行・保存。
// 1つの作業 = Claude Code を `claude -p` で1回動かすこと。
// 「続き」の作業は前の作業の Claude セッションを --resume で引き継ぐので、会話のように指示を重ねられる。
import { spawn, execFile } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

const STORE = path.join(config.dataDir, 'tasks.json');
const KEEP = 300;
const FINISHED = new Set(['done', 'needs_confirmation', 'failed', 'cancelled', 'interrupted']);

const tasks = new Map(); // id → task（古い順）
const procs = new Map(); // id → ChildProcess
const waiters = new Map(); // id → [resolve]
const queue = [];

export const isFinished = (t) => FINISHED.has(t.status);

function load() {
  try {
    for (const t of JSON.parse(fs.readFileSync(STORE, 'utf8'))) {
      // 落ちる前に動いていた作業は、続きをやり直せるよう「中断」にしておく
      if (!isFinished(t)) Object.assign(t, { status: 'interrupted', finished_at: now(), say: '作業の途中でジャービスが再起動しました。' });
      tasks.set(t.id, t);
    }
  } catch {}
}

let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 200);
}

export function saveNow() {
  clearTimeout(saveTimer);
  const all = [...tasks.values()].slice(-KEEP);
  fs.mkdirSync(config.dataDir, { recursive: true });
  fs.writeFileSync(STORE + '.tmp', JSON.stringify(all, null, 1));
  fs.renameSync(STORE + '.tmp', STORE);
}

// 止めるときは動いている Claude も止めて、記録を書き切る
export function shutdown() {
  for (const child of procs.values()) child.kill('SIGTERM');
  saveNow();
}

const now = () => new Date().toISOString();

function update(task, patch) {
  Object.assign(task, patch);
  save();
  if (isFinished(task)) {
    for (const resolve of waiters.get(task.id) || []) resolve(task);
    waiters.delete(task.id);
  }
}

export function getTask(id) {
  return tasks.get(id) || null;
}

export function listTasks(limit = 10) {
  return [...tasks.values()].slice(-limit).reverse();
}

/** 新しい作業を受け付ける。continueId があれば、その作業の続き（同じ Claude セッション）として動かす。 */
export function createTask({ instruction, continueId, source }) {
  let sessionId = null;
  if (continueId) {
    const parent = tasks.get(continueId);
    if (!parent) throw new Error(`続きにする作業 ${continueId} が見つかりません`);
    if (!isFinished(parent)) throw new Error(`作業 ${continueId} はまだ動いています。終わってから続きを頼んでください`);
    sessionId = parent.session_id;
  }
  const task = {
    id: `${config.machine}-${randomBytes(3).toString('hex')}`,
    machine: config.machine,
    instruction,
    source: source || 'unknown',
    parent_id: continueId || null,
    status: 'queued',
    created_at: now(),
    started_at: null,
    finished_at: null,
    progress: [],
    result: '',
    say: '',
    session_id: sessionId,
    cost_usd: null,
    error: null,
  };
  tasks.set(task.id, task);
  queue.push(task.id);
  save();
  pump();
  return task;
}

export function cancelTask(id) {
  const task = tasks.get(id);
  if (!task) return null;
  if (task.status === 'queued') {
    queue.splice(queue.indexOf(id), 1);
    update(task, { status: 'cancelled', finished_at: now(), say: '取り消しました。' });
  } else if (task.status === 'running') {
    task.cancelRequested = true;
    procs.get(id)?.kill('SIGTERM');
  }
  return task;
}

/** 作業が終わるか、seconds 秒たつまで待つ。 */
export function waitFor(id, seconds) {
  const task = tasks.get(id);
  if (!task || isFinished(task) || !(seconds > 0)) return Promise.resolve(task);
  return new Promise((resolve) => {
    const list = waiters.get(id) || [];
    list.push(resolve);
    waiters.set(id, list);
    setTimeout(() => resolve(tasks.get(id)), seconds * 1000);
  });
}

function pump() {
  while (procs.size < config.maxParallel && queue.length) run(tasks.get(queue.shift()));
}

function run(task) {
  const args = [
    '-p', task.instruction,
    '--output-format', 'stream-json',
    '--verbose',
    '--permission-mode', config.permissionMode,
    '--append-system-prompt', config.handsPrompt,
  ];
  if (task.session_id) args.push('--resume', task.session_id);

  update(task, { status: 'running', started_at: now() });
  let child;
  try {
    child = spawn(config.claudeBin, args, { cwd: config.workdir, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    return finish(task, { status: 'failed', error: String(e), say: 'Claude Code を起動できませんでした。' });
  }
  procs.set(task.id, child);
  const timer = setTimeout(() => { task.timedOut = true; child.kill('SIGTERM'); }, config.taskTimeoutMs);

  let buf = '';
  let stderr = '';
  let final = null;
  child.stdout.on('data', (chunk) => {
    buf += chunk;
    let nl;
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      let msg;
      try { msg = JSON.parse(line); } catch { continue; }
      // --resume で ID が変わることがあるので、いつも最新を持つ
      if (msg.session_id && msg.session_id !== task.session_id) update(task, { session_id: msg.session_id });
      if (msg.type === 'assistant') noteProgress(task, msg.message);
      if (msg.type === 'result') final = msg;
    }
  });
  child.stderr.on('data', (chunk) => { stderr = (stderr + chunk).slice(-4000); });
  child.on('error', (e) => { stderr += String(e); });
  child.on('close', (code) => {
    clearTimeout(timer);
    procs.delete(task.id);
    if (task.cancelRequested) {
      finish(task, { status: 'cancelled', say: '途中で止めました。' });
    } else if (task.timedOut) {
      finish(task, { status: 'failed', error: 'timeout', say: '時間がかかりすぎたので止めました。' });
    } else if (final && !final.is_error) {
      finish(task, { ...parseResult(final.result || ''), cost_usd: final.total_cost_usd ?? null });
    } else {
      const error = (final && (final.result || final.subtype)) || stderr.trim() || `exit ${code}`;
      finish(task, { status: 'failed', error: String(error).slice(0, 2000), say: 'うまくいきませんでした。Mac の画面で確認してください。' });
    }
    pump();
  });
}

// ツール呼び出しを「いま何をしているか」の短いメモにして残す（get_task で見える）
function noteProgress(task, message) {
  for (const part of message?.content || []) {
    let note = null;
    if (part.type === 'tool_use') {
      const input = part.input || {};
      const detail = input.skill || input.description || input.file_path || input.command || input.pattern || '';
      note = `${part.name}${detail ? ': ' + String(detail).slice(0, 80) : ''}`;
    } else if (part.type === 'text' && part.text.trim()) {
      note = part.text.trim().split('\n')[0].slice(0, 120);
    }
    if (note) task.progress = [...task.progress, { at: now(), note }].slice(-12);
  }
  save();
}

/** 最後の返事から JARVIS_STATUS / JARVIS_SAY を取り出す。 */
export function parseResult(text) {
  const status = text.match(/^\s*JARVIS_STATUS:\s*(done|needs_confirmation|failed)\s*$/m)?.[1] || 'done';
  const say = text.match(/^\s*JARVIS_SAY:\s*(.+)$/m)?.[1].trim() || '';
  const body = text
    .replace(/^\s*JARVIS_(STATUS|SAY):.*$/gm, '')
    .replace(/```[a-z]*\s*```/g, '')
    .trim();
  return { status, say: say || body.split('\n').find((l) => l.trim())?.slice(0, 120) || '終わりました。', result: body };
}

function finish(task, patch) {
  update(task, { ...patch, finished_at: now() });
  announce(task);
}

// 終わったことを知らせる（Mac の通知・読み上げ・iPhone への ntfy）。失敗しても作業には影響させない。
function announce(task) {
  if (task.status === 'cancelled') return;
  const title = task.status === 'needs_confirmation' ? 'ジャービス：確認してください' : task.status === 'failed' ? 'ジャービス：失敗' : 'ジャービス：完了';
  const quote = (s) => JSON.stringify(String(s));
  if (process.platform === 'darwin') {
    if (config.macNotify) execFile('osascript', ['-e', `display notification ${quote(task.say)} with title ${quote(title)} subtitle ${quote(task.id)}`], () => {});
    if (config.macSay) execFile('say', [task.say], () => {});
  }
  if (config.ntfyUrl) {
    fetch(config.ntfyUrl, {
      method: 'POST',
      body: task.say,
      headers: { Title: `=?UTF-8?B?${Buffer.from(title).toString('base64')}?=`, Tags: task.status === 'done' ? 'white_check_mark' : 'warning' },
    }).catch(() => {});
  }
}

load();
