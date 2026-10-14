// jarvis-bridge：ChatGPT（Dots）からは MCP、Siri ショートカットからは REST で、この Mac の Claude Code に仕事を渡す。
//   POST /mcp                     MCP（Streamable HTTP）  … ChatGPT のカスタムアプリに登録する
//   /api/...                      REST                   … Siri ショートカット・ほかの Mac から使う
//   /t/<合言葉>/mcp, /t/<合言葉>/api/...  ヘッダーを付けられない相手向け（URL に合言葉を入れる）
import { timingSafeEqual } from 'node:crypto';
import express from 'express';
import { z } from 'zod';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { config, checkConfig } from './config.js';
import * as tasks from './tasks.js';

const problems = checkConfig();
if (problems.length) {
  console.error('設定を直してください（jarvis/.env）:\n- ' + problems.join('\n- '));
  process.exit(1);
}

// ───────────── 仕事の受け渡し（この Mac か、ほかの Mac か） ─────────────

const machineOf = (taskId) => String(taskId).split('-')[0];
const isLocal = (machine) => !machine || machine === config.machine;

async function remote(machine, method, path, body) {
  const base = config.peers[machine];
  if (!base) throw new Error(`${machine} という Mac は登録されていません（いま使えるのは ${allMachines().join(', ')}）`);
  const res = await fetch(`${base}/api${path}`, {
    method,
    headers: { Authorization: `Bearer ${config.token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(70_000),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `${machine} からの応答が ${res.status} でした`);
  return data;
}

const allMachines = () => [config.machine, ...Object.keys(config.peers)];
const clampWait = (s, max) => Math.max(0, Math.min(Number(s) || 0, max));

// 声で返すのに要る分だけに絞った形
function view(t) {
  if (!t) return null;
  return {
    task_id: t.id,
    machine: t.machine,
    status: t.status,
    say: t.say || (t.status === 'queued' ? '順番待ちです。' : t.status === 'running' ? '作業中です。' : ''),
    instruction: t.instruction,
    result: t.result ? t.result.slice(0, 6000) : '',
    progress: t.progress.slice(-5).map((p) => p.note),
    continues: t.parent_id,
    created_at: t.created_at,
    finished_at: t.finished_at,
    error: t.error,
  };
}

const ops = {
  async start({ instruction, continue_task_id, machine, wait_seconds = 0, source }) {
    const target = machine || (continue_task_id ? machineOf(continue_task_id) : config.machine);
    if (!isLocal(target)) {
      return remote(target, 'POST', '/tasks', { instruction, continue_task_id, machine: target, wait_seconds, source });
    }
    const task = tasks.createTask({ instruction, continueId: continue_task_id, source });
    return view(await tasks.waitFor(task.id, wait_seconds));
  },
  async get(id, wait_seconds = 0) {
    if (!isLocal(machineOf(id))) return remote(machineOf(id), 'GET', `/tasks/${encodeURIComponent(id)}?wait=${wait_seconds}`);
    const t = tasks.getTask(id);
    if (!t) throw new Error(`作業 ${id} が見つかりません`);
    return view(await tasks.waitFor(id, wait_seconds));
  },
  async cancel(id) {
    if (!isLocal(machineOf(id))) return remote(machineOf(id), 'POST', `/tasks/${encodeURIComponent(id)}/cancel`);
    const t = tasks.cancelTask(id);
    if (!t) throw new Error(`作業 ${id} が見つかりません`);
    return view(t);
  },
  async list(limit = 10, everywhere = true) {
    const mine = tasks.listTasks(limit).map(view);
    if (!everywhere) return { machines: [{ machine: config.machine, online: true }], tasks: mine };
    const machines = [{ machine: config.machine, online: true }];
    let all = mine;
    await Promise.all(Object.keys(config.peers).map(async (m) => {
      try {
        const r = await remote(m, 'GET', `/tasks?limit=${limit}&scope=local`);
        all = all.concat(r.tasks);
        machines.push({ machine: m, online: true });
      } catch {
        machines.push({ machine: m, online: false });
      }
    }));
    all.sort((a, b) => b.created_at.localeCompare(a.created_at));
    return { machines, tasks: all.slice(0, limit) };
  },
};

// ───────────── MCP（ChatGPT / Dots 用） ─────────────

const asText = (obj) => ({ content: [{ type: 'text', text: JSON.stringify(obj, null, 1) }] });
const asError = (e) => ({ content: [{ type: 'text', text: `エラー: ${e.message}` }], isError: true });
const safe = (fn) => async (args) => { try { return asText(await fn(args)); } catch (e) { return asError(e); } };

function buildMcpServer() {
  const server = new McpServer(
    { name: 'jarvis-bridge', version: '0.1.0' },
    {
      instructions:
        '菊地さんの Mac（' + allMachines().join(' / ') + '）で Claude Code を動かす道具です。' +
        '業務の依頼は run_task に話し言葉のまま渡し、終わっていなければ get_task で様子を見ます。' +
        '結果の status が needs_confirmation なら、say を読み上げて菊地さんの返事を聞き、' +
        'OK なら continue_task_id にその作業の task_id を入れて run_task で続けます。',
    },
  );

  const machineArg = z.string().optional().describe(`どの Mac で動かすか（${allMachines().join(' / ')}）。省略すると ${config.machine}`);

  server.registerTool('run_task', {
    title: 'Mac の Claude Code に仕事を頼む',
    description:
      '菊地さんの指示を Mac の Claude Code に渡して実行させる。経理・監査・明細・メール下書き・ファイル作業など、' +
      'Mac 上のスキルとファイルが要る仕事はすべてこれ。指示は聞き取った話し言葉をほぼそのまま渡してよい。' +
      'wait_seconds の間に終われば結果が返る。終わらなければ task_id が返るので、あとで get_task で確認する。' +
      '前の作業の続き（「OK 送って」「さっきのを Wetopia 分だけ」など）は continue_task_id を付ける。',
    inputSchema: {
      instruction: z.string().min(1).describe('やってほしいこと（話し言葉のままでよい）'),
      continue_task_id: z.string().optional().describe('続きにする前の作業の task_id'),
      machine: machineArg,
      wait_seconds: z.number().min(0).max(45).optional().describe('結果を待つ秒数（既定 20、最大 45）'),
    },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
  }, safe((a) => ops.start({ ...a, wait_seconds: clampWait(a.wait_seconds ?? 20, 45), source: 'mcp' })));

  server.registerTool('get_task', {
    title: '作業の様子・結果を見る',
    description: 'run_task で頼んだ作業の状態（queued / running / done / needs_confirmation / failed / cancelled / interrupted）と結果を返す。wait_seconds を付けると終わるまで少し待つ。',
    inputSchema: {
      task_id: z.string().describe('run_task が返した task_id'),
      wait_seconds: z.number().min(0).max(45).optional().describe('終わるまで待つ秒数（既定 0、最大 45）'),
    },
    annotations: { readOnlyHint: true },
  }, safe((a) => ops.get(a.task_id, clampWait(a.wait_seconds, 45))));

  server.registerTool('list_tasks', {
    title: '最近の作業の一覧',
    description: 'すべての Mac の最近の作業と、どの Mac がつながっているかを返す。「いま何やってる？」「さっきのどうなった？」に使う。',
    inputSchema: { limit: z.number().min(1).max(50).optional().describe('件数（既定 10）') },
    annotations: { readOnlyHint: true },
  }, safe((a) => ops.list(a.limit ?? 10)));

  server.registerTool('cancel_task', {
    title: '作業を止める',
    description: '順番待ちか実行中の作業を止める。',
    inputSchema: { task_id: z.string() },
    annotations: { destructiveHint: true },
  }, safe((a) => ops.cancel(a.task_id)));

  return server;
}

// ───────────── HTTP ─────────────

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));

const tokenBuf = Buffer.from(config.token);
function tokenOk(given) {
  const b = Buffer.from(String(given || ''));
  return b.length === tokenBuf.length && timingSafeEqual(b, tokenBuf);
}
function auth(req, res, next) {
  const bearer = (req.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (tokenOk(req.params.token) || tokenOk(bearer)) return next();
  res.status(401).json({ error: '合言葉が違います' });
}

app.get('/healthz', (_req, res) => res.json({ ok: true, machine: config.machine }));

const api = express.Router({ mergeParams: true });
api.use(auth);
const handle = (fn) => async (req, res) => {
  try { res.json(await fn(req)); } catch (e) { res.status(400).json({ error: e.message }); }
};

// MCP（ステートレス：リクエストごとにサーバーを作る）
api.post('/mcp', async (req, res) => {
  const server = buildMcpServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
  res.on('close', () => { transport.close(); server.close(); });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (e) {
    console.error('MCP error', e);
    if (!res.headersSent) res.status(500).json({ jsonrpc: '2.0', error: { code: -32603, message: 'internal error' }, id: null });
  }
});
api.all('/mcp', (_req, res) => res.status(405).set('Allow', 'POST').end());

api.get('/api/status', handle(() => ops.list(5)));
api.get('/api/tasks', handle((req) => ops.list(Number(req.query.limit) || 10, req.query.scope !== 'local')));
api.post('/api/tasks', handle((req) => {
  const { instruction, continue_task_id, machine, wait_seconds, source } = req.body || {};
  if (!instruction || typeof instruction !== 'string') throw new Error('instruction（指示）がありません');
  return ops.start({ instruction, continue_task_id, machine, wait_seconds: clampWait(wait_seconds, 55), source: source || 'api' });
}));
api.get('/api/tasks/:id', handle((req) => ops.get(req.params.id, clampWait(req.query.wait, 55))));
api.post('/api/tasks/:id/cancel', handle((req) => ops.cancel(req.params.id)));

// Siri ショートカット向け：話した内容を渡す → 待つ → 読み上げる一文を返す。
// 「続けて」「OK」は直前の作業（needs_confirmation）の続きとして扱う。
api.post('/api/ask', handle(async (req) => {
  const { text, machine } = req.body || {};
  if (!text || typeof text !== 'string') throw new Error('text（話した内容）がありません');
  const recent = tasks.listTasks(1)[0];
  const followUp = recent && recent.status === 'needs_confirmation' && /^(ok|オーケー|おけ|はい|うん|いいよ|進めて|続けて|送って|お願い)/i.test(text.trim());
  const t = await ops.start({
    instruction: text,
    continue_task_id: followUp ? recent.id : undefined,
    machine,
    wait_seconds: 50,
    source: 'siri',
  });
  const say = t.status === 'queued' || t.status === 'running'
    ? 'わかりました。少し時間がかかるので、終わったら通知します。'
    : t.say;
  return { say, task_id: t.task_id, status: t.status };
}));

// 合言葉入りの URL を先に見る（'/' に先にマッチすると、ヘッダーが無いので 401 になってしまう）
app.use('/t/:token', api);
app.use('/', api);

for (const sig of ['SIGTERM', 'SIGINT']) process.on(sig, () => { tasks.shutdown(); process.exit(0); });

app.listen(config.port, '127.0.0.1', () => {
  console.log(`jarvis-bridge [${config.machine}] http://127.0.0.1:${config.port}  peers: ${Object.keys(config.peers).join(', ') || 'なし'}`);
});
