import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const envFile = path.join(ROOT, '.env');
if (fs.existsSync(envFile)) process.loadEnvFile(envFile);

const env = process.env;
const expandHome = (p) => (p && p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p);
const int = (v, d) => (Number.isFinite(parseInt(v, 10)) ? parseInt(v, 10) : d);

// "macbook=https://a.example.com,imac=https://b.example.com" → { macbook: 'https://a…', … }
function parsePeers(s) {
  const peers = {};
  for (const part of (s || '').split(',').map((x) => x.trim()).filter(Boolean)) {
    const i = part.indexOf('=');
    if (i > 0) peers[part.slice(0, i).trim()] = part.slice(i + 1).trim().replace(/\/+$/, '');
  }
  return peers;
}

export const config = {
  token: env.JARVIS_TOKEN || '',
  machine: (env.JARVIS_MACHINE || os.hostname().split('.')[0]).toLowerCase(),
  port: int(env.JARVIS_PORT, 8787),
  workdir: expandHome(env.JARVIS_WORKDIR || '~'),
  claudeBin: expandHome(env.JARVIS_CLAUDE_BIN || 'claude'),
  permissionMode: env.JARVIS_PERMISSION_MODE || 'auto',
  peers: parsePeers(env.JARVIS_PEERS),
  maxParallel: int(env.JARVIS_MAX_PARALLEL, 2),
  taskTimeoutMs: int(env.JARVIS_TASK_TIMEOUT_MIN, 60) * 60_000,
  macNotify: env.JARVIS_MAC_NOTIFY === '1',
  macSay: env.JARVIS_MAC_SAY === '1',
  ntfyUrl: env.JARVIS_NTFY_URL || '',
  dataDir: expandHome(env.JARVIS_DATA_DIR || path.join(ROOT, 'data')),
  handsPrompt: fs.readFileSync(path.join(ROOT, 'prompts', 'hands.md'), 'utf8'),
};

export function checkConfig() {
  const problems = [];
  if (config.token.length < 24) problems.push('JARVIS_TOKEN が未設定か短すぎます（24文字以上）');
  if (!/^[a-z0-9-]+$/.test(config.machine)) problems.push('JARVIS_MACHINE は小文字英数字とハイフンだけにしてください');
  if (!fs.existsSync(config.workdir)) problems.push(`JARVIS_WORKDIR が見つかりません: ${config.workdir}`);
  return problems;
}
