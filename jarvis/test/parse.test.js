import { test } from 'node:test';
import assert from 'node:assert/strict';

process.env.JARVIS_DATA_DIR = (await import('node:os')).tmpdir() + '/jarvis-test-' + process.pid;
const { parseResult } = await import('../src/tasks.js');

test('JARVIS_STATUS と JARVIS_SAY を取り出し、本文から消す', () => {
  const r = parseResult('3件作りました。\n\n```\nJARVIS_STATUS: needs_confirmation\nJARVIS_SAY: 送信してよいですか？\n```');
  assert.equal(r.status, 'needs_confirmation');
  assert.equal(r.say, '送信してよいですか？');
  assert.equal(r.result, '3件作りました。');
});

test('書式が無いときは done と本文の1行目', () => {
  const r = parseResult('\n終わりました。\n詳細');
  assert.equal(r.status, 'done');
  assert.equal(r.say, '終わりました。');
});
