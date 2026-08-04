#!/usr/bin/env python3
"""Generate Ototext !-command bot + worker n8n workflows."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = "/workspace/data/ototext-state.json"

COMMAND_JS = r'''
const STATE_PATH = '__STATE_PATH__';
const fs = require('fs');
const path = require('path');

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function saveState(state) {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
}

function defaultState() {
  const main = (($env.BOT_PREFIX || '!').toString()) || '!';
  return {
    admins: [],
    botWid: '',
    mainPrefix: main,
    prefixes: [main],
    numbers: [],
    activeNumberId: '',
    broadcast: { running: false, text: '', texts: [], textIndex: 0, intervalMin: 3, index: 0, sent: 0, lastSendAt: 0, startedAt: 0, cycle: 0, windowStart: '', windowEnd: '' },
    dm: { running: false, text: '', groupId: '', intervalMin: 3, queue: [], index: 0, sent: 0, failed: 0, lastSendAt: 0, startedAt: 0, windowStart: '', windowEnd: '' },
    mining: { running: false, targetGroupId: '', targetName: '', members: 0, addedToday: 0, pending: 0, totalTarget: 0, durationMin: 0, startedAt: 0, lastAddAt: 0, dayKey: '' },
    filters: { minUye: 0 },
    blacklist: [],
    invites: [],
    logGroupId: '',
    pending: null,
    guard: {
      enabled: false,
      groups: {},
      stickerLimit: 4,
      stickerWindowMs: 15000,
      kickOnCall: true,
      kickOnStickerSpam: true,
      lockOnIncident: true,
      protectAdmins: true,
      stickerHits: {},
      lockedGroups: {},
    },
    daily: { dayKey: '', broadcastSent: 0, dmSent: 0, errors: 0, starts: 0, stops: 0, events: [] },
    stats: { commands: 0, broadcastSent: 0, dmSent: 0, joins: 0, startedAt: Date.now() },
  };
}

function ensureState() {
  let s = loadState();
  if (!s) s = defaultState();
  const d = defaultState();
  s.admins = Array.isArray(s.admins) ? s.admins : [];
  s.blacklist = Array.isArray(s.blacklist) ? s.blacklist : [];
  s.invites = Array.isArray(s.invites) ? s.invites : [];
  s.filters = s.filters || { minUye: 0 };
  s.broadcast = Object.assign(d.broadcast, s.broadcast || {});
  s.dm = Object.assign(d.dm, s.dm || {});
  s.mining = Object.assign(d.mining, s.mining || {});
  s.stats = Object.assign(d.stats, s.stats || {});
  s.mainPrefix = (s.mainPrefix || d.mainPrefix || '!').toString();
  s.prefixes = Array.isArray(s.prefixes) ? s.prefixes.map(String).filter(Boolean) : [];
  if (!s.prefixes.length) s.prefixes = [s.mainPrefix];
  if (!s.prefixes.includes(s.mainPrefix)) s.prefixes.unshift(s.mainPrefix);
  s.prefixes = [...new Set(s.prefixes)];
  s.logGroupId = s.logGroupId || '';
  s.pending = s.pending || null;
  s.daily = Object.assign({ dayKey: '', broadcastSent: 0, dmSent: 0, errors: 0, starts: 0, stops: 0, events: [] }, s.daily || {});
  s.broadcast.windowStart = s.broadcast.windowStart || '';
  s.broadcast.windowEnd = s.broadcast.windowEnd || '';
  s.broadcast.texts = Array.isArray(s.broadcast.texts) ? s.broadcast.texts.filter((t) => String(t || '').trim()) : [];
  s.broadcast.textIndex = Number(s.broadcast.textIndex) || 0;
  if (!s.broadcast.texts.length && s.broadcast.text) s.broadcast.texts = [s.broadcast.text];
  s.dm.windowStart = s.dm.windowStart || '';
  s.dm.windowEnd = s.dm.windowEnd || '';
  s.numbers = Array.isArray(s.numbers) ? s.numbers : [];
  s.activeNumberId = s.activeNumberId || '';
  s.guard = Object.assign({
    enabled: false,
    groups: {},
    stickerLimit: 4,
    stickerWindowMs: 15000,
    kickOnCall: true,
    kickOnStickerSpam: true,
    lockOnIncident: true,
    protectAdmins: true,
    stickerHits: {},
    lockedGroups: {},
  }, s.guard || {});
  if (!s.guard.groups || typeof s.guard.groups !== 'object') s.guard.groups = {};
  if (!s.guard.stickerHits || typeof s.guard.stickerHits !== 'object') s.guard.stickerHits = {};
  if (!s.guard.lockedGroups || typeof s.guard.lockedGroups !== 'object') s.guard.lockedGroups = {};
  if (typeof s.guard.lockOnIncident !== 'boolean') s.guard.lockOnIncident = true;
  ensureNumbers(s);
  return s;
}

function ensureNumbers(state) {
  if (!Array.isArray(state.numbers)) state.numbers = [];
  const envId = String($env.ID_INSTANCE || '').trim();
  const envTok = String($env.API_TOKEN || '').trim();
  if (envId && envTok && envId !== 'YOUR_INSTANCE_ID' && envTok !== 'YOUR_API_TOKEN_INSTANCE') {
    let primary = state.numbers.find((n) => String(n.instanceId) === envId);
    if (!primary) {
      primary = {
        id: 'n-primary',
        name: 'Ana',
        instanceId: envId,
        apiToken: envTok,
        wid: state.botWid || '',
        addedAt: Date.now(),
      };
      state.numbers.unshift(primary);
    } else {
      primary.apiToken = envTok;
      if (!primary.name) primary.name = 'Ana';
    }
  }
  if (!state.activeNumberId && state.numbers.length) state.activeNumberId = state.numbers[0].id;
  if (state.activeNumberId && !state.numbers.some((n) => n.id === state.activeNumberId) && state.numbers.length) {
    state.activeNumberId = state.numbers[0].id;
  }
  return state;
}

function getNumberByRef(state, ref) {
  const raw = String(ref || '').trim();
  if (!raw) return null;
  if (/^\d+$/.test(raw)) {
    const idx = parseInt(raw, 10) - 1;
    if (idx >= 0 && idx < state.numbers.length) return state.numbers[idx];
  }
  const low = raw.toLowerCase();
  return state.numbers.find((n) => String(n.id) === raw || String(n.name || '').toLowerCase() === low || String(n.instanceId) === raw) || null;
}

function getActiveNumber(state) {
  return state.numbers.find((n) => n.id === state.activeNumberId) || state.numbers[0] || null;
}

function formatNumberLine(n, i, activeId) {
  const mark = n.id === activeId ? ' ✅' : '';
  const phone = n.wid ? String(n.wid).replace('@c.us', '') : '-';
  return `${i + 1}. ${n.name || 'Numara'}${mark}\n   tel: ${phone}\n   instance: ${n.instanceId}`;
}

function guardApplies(state, groupId) {
  if (!state.guard?.enabled) return false;
  if (!groupId || !String(groupId).endsWith('@g.us')) return false;
  const keys = Object.keys(state.guard.groups || {});
  if (!keys.length) return true; // tüm gruplar (bot admin olmalı)
  return !!state.guard.groups[groupId];
}

function guardProtected(state, participantId) {
  if (!state.guard?.protectAdmins) return false;
  const p = normId(participantId);
  if (!p) return true;
  if (state.admins.includes(p)) return true;
  if (normId(state.botWid) === p) return true;
  return false;
}

async function guardKick(state, groupId, participantId, reason) {
  const pid = normId(participantId);
  if (!groupId || !pid) return { ok: false, error: 'eksik id' };
  if (guardProtected(state, pid)) return { ok: false, error: 'korumalı (admin/bot)' };
  try {
    const res = await api.call(this, 'POST', 'removeGroupParticipant', {
      groupId,
      participantChatId: pid,
    });
    const ok = res && res.removeParticipant !== false;
    await pushLog.call(this, state, 'guard', `Kick ${pid} @ ${groupId} | ${reason} | ok=${ok}`);
    return { ok, res };
  } catch (e) {
    await pushLog.call(this, state, 'error', `Guard kick fail: ${e.message || e}`);
    return { ok: false, error: e.message || String(e) };
  }
}

async function guardSetMembersCanWrite(state, groupId, allow) {
  if (!groupId || !String(groupId).endsWith('@g.us')) return { ok: false, error: 'grup yok' };
  try {
    const res = await api.call(this, 'POST', 'updateGroupSettings', {
      groupId,
      allowParticipantsSendMessages: !!allow,
    });
    const ok = !!(res && res.updateGroupSettings);
    if (!state.guard.lockedGroups || typeof state.guard.lockedGroups !== 'object') state.guard.lockedGroups = {};
    if (allow) delete state.guard.lockedGroups[groupId];
    else state.guard.lockedGroups[groupId] = { at: Date.now(), by: 'guard' };
    await pushLog.call(
      this,
      state,
      'guard',
      `Group ${allow ? 'UNLOCK' : 'LOCK'} ${groupId} | ok=${ok} | ${res?.reason || ''}`,
    );
    return { ok, res };
  } catch (e) {
    await pushLog.call(this, state, 'error', `Guard lock fail: ${e.message || e}`);
    return { ok: false, error: e.message || String(e) };
  }
}

async function guardLockAfterIncident(state, groupId, reason) {
  if (!state.guard?.lockOnIncident) return { ok: false, skipped: true };
  const lock = await guardSetMembersCanWrite.call(this, state, groupId, false);
  return { ...lock, reason };
}

async function handleGuardSticker(state, body) {
  const g = state.guard;
  if (!g.kickOnStickerSpam) return null;
  const chatId = body.senderData?.chatId || '';
  const sender = body.senderData?.sender || '';
  if (!guardApplies(state, chatId)) return null;
  const key = `${chatId}|${normId(sender)}`;
  const now = Date.now();
  const windowMs = Math.max(3000, Number(g.stickerWindowMs) || 15000);
  const limit = Math.max(2, Number(g.stickerLimit) || 4);
  let hits = Array.isArray(g.stickerHits[key]) ? g.stickerHits[key] : [];
  hits = hits.filter((t) => now - t <= windowMs);
  hits.push(now);
  g.stickerHits[key] = hits;
  // bellek temizliği
  const keys = Object.keys(g.stickerHits);
  if (keys.length > 500) {
    for (const k of keys.slice(0, keys.length - 400)) delete g.stickerHits[k];
  }
  if (hits.length < limit) return null;
  g.stickerHits[key] = [];
  const kicked = await guardKick.call(this, state, chatId, sender, `sticker-spam x${hits.length}/${windowMs}ms`);
  const locked = await guardLockAfterIncident.call(this, state, chatId, 'sticker-spam');
  const lines = [`🛡️ Guard: sticker spam`];
  if (kicked.ok) lines.push(`Çıkarıldı: ${normId(sender)}`);
  else lines.push(`Kick: ${kicked.error || 'olmadı'}`);
  if (locked.ok) lines.push('Sohbet kilitlendi — sadece adminler yazabilir.');
  else if (!locked.skipped) lines.push(`Kilit: ${locked.error || locked.res?.reason || 'olmadı'}`);
  lines.push(`Açmak için: ${(state.mainPrefix || '!')}guard yaz`);
  return { chatId, reply: lines.join('\n') };
}

async function handleGuardCall(state, body) {
  const g = state.guard;
  if (!g.kickOnCall) return null;
  const status = String(body.status || '').toLowerCase();
  if (status && status !== 'offer') return null;
  const from = normId(body.from || body.senderData?.sender || '');
  const chatId = body.chatId || body.senderData?.chatId || body.idGroup || '';
  // Grup araması: chatId grup ise o gruptan at + kilitle
  if (chatId && String(chatId).endsWith('@g.us') && guardApplies(state, chatId)) {
    const kicked = await guardKick.call(this, state, chatId, from, 'group-call');
    const locked = await guardLockAfterIncident.call(this, state, chatId, 'group-call');
    const lines = ['🛡️ Guard: grup araması'];
    if (kicked.ok) lines.push(`Çıkarıldı: ${from}`);
    else lines.push(`Kick: ${kicked.error || 'olmadı'}`);
    if (locked.ok) lines.push('Sohbet kilitlendi — sadece adminler yazabilir.');
    else if (!locked.skipped) lines.push(`Kilit: ${locked.error || locked.res?.reason || 'olmadı'}`);
    lines.push(`Açmak için: ${(state.mainPrefix || '!')}guard yaz`);
    if (!kicked.ok && !locked.ok) return null;
    return { chatId, reply: lines.join('\n') };
  }
  // Bazı webhook'larda sadece arayan gelir: korumalı gruplarda bu kişiyi ara
  if (!from) return null;
  const targets = Object.keys(g.groups || {}).filter((id) => g.groups[id]);
  const groupIds = targets.length ? targets : [];
  if (!groupIds.length) return null;
  let first = null;
  for (const gid of groupIds) {
    if (!guardApplies(state, gid)) continue;
    const kicked = await guardKick.call(this, state, gid, from, 'call-offer');
    const locked = await guardLockAfterIncident.call(this, state, gid, 'call-offer');
    if (kicked.ok || locked.ok) {
      first = { chatId: gid, kicked, locked };
      break;
    }
  }
  if (!first) return null;
  const lines = ['🛡️ Guard: arama', `Çıkarıldı/kilit: ${from}`];
  if (first.locked.ok) lines.push('Sohbet kilitlendi — sadece adminler yazabilir.');
  lines.push(`Açmak için: ${(state.mainPrefix || '!')}guard yaz`);
  return { chatId: first.chatId, reply: lines.join('\n') };
}

function normalizePrefix(raw) {
  let px = String(raw || '').trim();
  if (!px) return '';
  if ((px.startsWith('"') && px.endsWith('"')) || (px.startsWith("'") && px.endsWith("'"))) px = px.slice(1, -1);
  px = px.replace(/[()]/g, '').trim();
  return px;
}

function matchPrefix(text, prefixes) {
  const sorted = [...prefixes].sort((a, b) => b.length - a.length);
  for (const px of sorted) {
    if (text.startsWith(px)) return px;
  }
  return null;
}


function dayKeyTR() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}

function ensureDaily(state) {
  const key = dayKeyTR();
  if (!state.daily || state.daily.dayKey !== key) {
    state.daily = { dayKey: key, broadcastSent: 0, dmSent: 0, errors: 0, starts: 0, stops: 0, events: [] };
  }
  return state.daily;
}

function parseWindow(args) {
  const m = String(args || '').trim().match(/^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$/);
  if (!m) return null;
  const norm = (x) => {
    const [h, mi] = x.split(':').map((n) => parseInt(n, 10));
    if (!Number.isFinite(h) || !Number.isFinite(mi) || h > 23 || mi > 59) return null;
    return String(h).padStart(2, '0') + ':' + String(mi).padStart(2, '0');
  };
  const a = norm(m[1]);
  const b = norm(m[2]);
  if (!a || !b) return null;
  return { start: a, end: b };
}

function inTimeWindow(startHHMM, endHHMM) {
  if (!startHHMM || !endHHMM) return true;
  const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Istanbul', hour: '2-digit', minute: '2-digit', hour12: false });
  const parts = fmt.formatToParts(new Date());
  const hh = parseInt(parts.find((p) => p.type === 'hour').value, 10);
  const mm = parseInt(parts.find((p) => p.type === 'minute').value, 10);
  const cur = hh * 60 + mm;
  const [sh, sm] = startHHMM.split(':').map(Number);
  const [eh, em] = endHHMM.split(':').map(Number);
  const start = sh * 60 + sm;
  const end = eh * 60 + em;
  if (start <= end) return cur >= start && cur <= end;
  return cur >= start || cur <= end;
}

async function pushLog(state, type, message) {
  const daily = ensureDaily(state);
  const row = { t: Date.now(), type, message: String(message || '').slice(0, 300) };
  daily.events.unshift(row);
  daily.events = daily.events.slice(0, 200);
  if (type === 'broadcast') daily.broadcastSent += 1;
  if (type === 'dm') daily.dmSent += 1;
  if (type === 'error') daily.errors += 1;
  if (type === 'start') daily.starts += 1;
  if (type === 'stop') daily.stops += 1;
  if (state.logGroupId) {
    try {
      await api.call(this, 'POST', 'sendMessage', {
        chatId: state.logGroupId,
        message: `🧾 *LOG* [${type}]\\n${message}`,
      });
    } catch (e) {}
  }
}

function setPending(state, pending) {
  const ttl = pending && pending.ttlMs ? pending.ttlMs : 15 * 60 * 1000;
  const copy = Object.assign({}, pending);
  delete copy.ttlMs;
  state.pending = Object.assign({ expiresAt: Date.now() + ttl }, copy);
}

function broadcastTextsFromData(d) {
  if (Array.isArray(d?.texts) && d.texts.length) {
    return d.texts.map((t) => String(t || '').trim()).filter(Boolean);
  }
  const one = String(d?.text || '').trim();
  return one ? [one] : [];
}

function summarizeTexts(texts) {
  return texts.map((t, i) => `${i + 1}. ${String(t).slice(0, 80)}`).join('\n');
}

function clearPending(state) { state.pending = null; }

function pendingValid(state, sender) {
  const p = state.pending;
  if (!p) return false;
  if (p.expiresAt && Date.now() > p.expiresAt) { clearPending(state); return false; }
  if (p.by && normId(p.by) !== normId(sender)) return false;
  return true;
}

function normId(raw) {
  if (!raw) return '';
  let v = String(raw).trim().replace(/^@/, '').replace(/[()]/g, '');
  if (!v) return '';
  if (v.includes('@')) return v;
  const digits = v.replace(/\D/g, '');
  if (!digits) return v;
  let d = digits;
  if (d.startsWith('0') && d.length === 11) d = '90' + d.slice(1);
  return d + '@c.us';
}

function extractInviteLinks(text) {
  const re = /https?:\/\/chat\.whatsapp\.com\/[A-Za-z0-9_-]+/g;
  return Array.from(new Set((text || '').match(re) || []));
}

let CURRENT_CREDS = {
  instanceId: String($env.ID_INSTANCE || ''),
  apiToken: String($env.API_TOKEN || ''),
};

async function api(method, endpoint, body) {
  const instance = CURRENT_CREDS.instanceId;
  const token = CURRENT_CREDS.apiToken;
  if (!instance || !token) throw new Error('numara credentials yok');
  let url = `https://api.green-api.com/waInstance${instance}/${endpoint}/${token}`;
  if (method === 'GET' && body && typeof body === 'object') {
    const qs = new URLSearchParams(body).toString();
    if (qs) url += `?${qs}`;
    body = undefined;
  }
  const opts = { method, url, json: true };
  if (body !== undefined) opts.body = body;
  return this.helpers.httpRequest(opts);
}

function setCredsFromNumber(num) {
  if (!num) return;
  CURRENT_CREDS = { instanceId: String(num.instanceId), apiToken: String(num.apiToken) };
}

async function ensureBotAdmin(state, incomingWid, num) {
  const envAdmins = String($env.BOT_ADMINS || '')
    .split(/[,;\s]+/)
    .map((x) => normId(x))
    .filter(Boolean);
  for (const a of envAdmins) {
    if (!state.admins.includes(a)) state.admins.push(a);
  }
  if (incomingWid) {
    const wid = normId(incomingWid);
    state.botWid = wid || state.botWid;
    if (num && wid) num.wid = wid;
  }
  if (!(num && num.wid) && !state.botWid) {
    try {
      const settings = await api.call(this, 'GET', 'getSettings');
      const wid = settings.wid || settings.phone || '';
      state.botWid = wid;
      if (num) num.wid = wid;
    } catch (e) {}
  } else if (num && num.wid) {
    state.botWid = num.wid;
  }
  const bot = normId(state.botWid);
  if (bot && !state.admins.includes(bot)) state.admins.push(bot);
}

function isAdmin(state, sender, chatId) {
  const s = normId(sender);
  const c = normId(chatId);
  return state.admins.includes(s) || state.admins.includes(c);
}

function parseDm(args) {
  const m = args.match(/^(?:\()?([\s\S]+?)(?:\))?\.\s*(?:\()?([^\s)]+@g\.us)(?:\))?\s*$/);
  if (m) return { text: m[1].trim(), groupId: m[2].trim() };
  const parts = args.trim().split(/\s+/);
  const last = (parts[parts.length - 1] || '').replace(/[()]/g, '');
  if (last.endsWith('@g.us')) {
    return { text: parts.slice(0, -1).join(' ').replace(/^\(|\)$/g, ''), groupId: last };
  }
  return null;
}

async function listGroupsPage(state, page) {
  const PAGE = 10;
  let chats;
  try {
    chats = await api.call(this, 'GET', 'getChats', { count: '500' });
  } catch (e) {
    chats = await api.call(this, 'POST', 'getChats', { count: 500 });
  }
  if (Array.isArray(chats) === false && chats && Array.isArray(chats.chats)) chats = chats.chats;
  const groups = (Array.isArray(chats) ? chats : [])
    .filter((c) => c && (c.type === 'group' || String(c.id || '').endsWith('@g.us')))
    .map((c) => ({ id: c.id, name: c.name || c.id }));
  groups.sort((a, b) => String(a.name).localeCompare(String(b.name), 'tr'));

  const total = groups.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE) || 1);
  const safe = Math.min(Math.max(1, page), totalPages);
  const start = (safe - 1) * PAGE;
  const slice = groups.slice(start, start + PAGE);
  const enriched = [];
  for (let i = 0; i < slice.length; i++) {
    const g = slice[i];
    let members = '?';
    let subject = g.name;
    try {
      const data = await api.call(this, 'POST', 'getGroupData', { groupId: g.id });
      subject = data.subject || g.name;
      members = typeof data.size === 'number' ? data.size : (data.participants || []).length;
    } catch (e) {}
    enriched.push({
      no: start + i + 1,
      id: g.id,
      name: subject,
      members,
      blocked: state.blacklist.includes(g.id),
    });
  }
  state.lastGroupsPage = { page: safe, totalPages, items: enriched, total };
  return { enriched, safe, totalPages, total };
}

const body = $json.body && typeof $json.body === 'object' ? $json.body : $json;
const state = ensureState();
const incomingInstance = String(
  body.instanceData?.idInstance || body.idInstance || $env.ID_INSTANCE || ''
);
let sessionNumber =
  state.numbers.find((n) => String(n.instanceId) === String(incomingInstance)) ||
  getActiveNumber(state);
if (sessionNumber) setCredsFromNumber(sessionNumber);
else {
  CURRENT_CREDS = {
    instanceId: String($env.ID_INSTANCE || ''),
    apiToken: String($env.API_TOKEN || ''),
  };
}
await ensureBotAdmin.call(this, state, body.instanceData?.wid, sessionNumber);

// Guard: grup araması / gelen arama
if (body.typeWebhook === 'incomingCall') {
  const guardReply = await handleGuardCall.call(this, state, body);
  saveState(state);
  if (guardReply) {
    return [{
      json: {
        chatId: guardReply.chatId,
        reply: guardReply.reply,
        instanceId: CURRENT_CREDS.instanceId,
        apiToken: CURRENT_CREDS.apiToken,
      },
    }];
  }
  return [];
}

// Capture invite links + guard stickers / call messages
if (body.typeWebhook === 'incomingMessageReceived') {
  const md0 = body.messageData || {};
  let text0 = '';
  if (md0.typeMessage === 'textMessage') text0 = md0.textMessageData?.textMessage || '';
  if (md0.typeMessage === 'extendedTextMessage') text0 = md0.extendedTextMessageData?.text || '';
  if (md0.typeMessage === 'groupInviteMessage') {
    const d = md0.groupInviteMessageData || {};
    const link = d.inviteCode ? `https://chat.whatsapp.com/${d.inviteCode}` : '';
    if (link) {
      state.invites.unshift({
        link,
        groupName: d.groupName || '',
        groupJid: d.groupJid || '',
        from: body.senderData?.sender || '',
        at: Date.now(),
      });
      state.invites = state.invites.slice(0, 200);
    }
  }
  for (const link of extractInviteLinks(text0)) {
    if (!state.invites.some((x) => x.link === link)) {
      state.invites.unshift({ link, groupName: '', groupJid: '', from: body.senderData?.sender || '', at: Date.now() });
    }
  }
  state.invites = state.invites.slice(0, 200);

  // sticker spam guard
  if (md0.typeMessage === 'stickerMessage') {
    const guardReply = await handleGuardSticker.call(this, state, body);
    saveState(state);
    if (guardReply) {
      return [{
        json: {
          chatId: guardReply.chatId,
          reply: guardReply.reply,
          instanceId: CURRENT_CREDS.instanceId,
          apiToken: CURRENT_CREDS.apiToken,
        },
      }];
    }
    return [];
  }

  // grup içi arama mesajı (varsa)
  const tmsg = String(md0.typeMessage || '').toLowerCase();
  if (tmsg.includes('call') && state.guard?.kickOnCall) {
    const chatId = body.senderData?.chatId || '';
    const sender = body.senderData?.sender || '';
    if (guardApplies(state, chatId)) {
      const kicked = await guardKick.call(this, state, chatId, sender, 'call-message');
      const locked = await guardLockAfterIncident.call(this, state, chatId, 'call-message');
      saveState(state);
      if (kicked.ok || locked.ok) {
        const lines = ['🛡️ Guard: grup araması'];
        if (kicked.ok) lines.push(`Çıkarıldı: ${normId(sender)}`);
        if (locked.ok) lines.push('Sohbet kilitlendi — sadece adminler yazabilir.');
        lines.push(`Açmak için: ${(state.mainPrefix || '!')}guard yaz`);
        return [{
          json: {
            chatId,
            reply: lines.join('\n'),
            instanceId: CURRENT_CREDS.instanceId,
            apiToken: CURRENT_CREDS.apiToken,
          },
        }];
      }
      return [];
    }
  }
}

if (body.typeWebhook && body.typeWebhook !== 'incomingMessageReceived') {
  saveState(state);
  return [];
}

const md = body.messageData || {};
let text = '';
if (md.typeMessage === 'textMessage') text = md.textMessageData?.textMessage || '';
else if (md.typeMessage === 'extendedTextMessage') text = md.extendedTextMessageData?.text || '';
else {
  saveState(state);
  return [];
}
text = String(text || '').trim();
const usedPrefix = matchPrefix(text, state.prefixes);
if (!usedPrefix) {
  saveState(state);
  return [];
}
const prefix = state.mainPrefix || usedPrefix;

const rest = text.slice(usedPrefix.length).trim();
const parts = rest.split(/\s+/);
let command = (parts[0] || '').toLowerCase();
let args = rest.slice(parts[0].length).trim();
// support "!prefix cikar x" as prefix-cikar
if (command === 'prefix' && args) {
  const a0 = (args.split(/\s+/)[0] || '').toLowerCase();
  if (['cikar', 'çıkar', 'ekle', 'main', 'liste'].includes(a0)) {
    command = 'prefix-' + (a0 === 'çıkar' ? 'cikar' : a0);
    args = args.slice(a0.length).trim();
  }
}
if (command === 'numara' && args) {
  const a0 = (args.split(/\s+/)[0] || '').toLowerCase();
  if (['ekle', 'sil', 'aktif', 'liste', 'yenile'].includes(a0)) {
    command = 'numara-' + a0;
    args = args.slice(a0.length).trim();
  }
}
if (command === 'guard' && args) {
  const a0 = (args.split(/\s+/)[0] || '').toLowerCase();
  if (['ac', 'aç', 'kapat', 'liste', 'sticker', 'grup', 'durum', 'yaz', 'kilit'].includes(a0)) {
    command = 'guard-' + (a0 === 'aç' ? 'ac' : a0);
    args = args.slice(a0.length).trim();
  }
}
const chatId = body.senderData?.chatId || '';
const sender = body.senderData?.sender || chatId;

if (!isAdmin(state, sender, chatId)) {
  saveState(state);
  return [{
    json: {
      chatId,
      reply: '⛔ Yetkisiz. Sadece adminler Ototext kullanabilir.',
      instanceId: CURRENT_CREDS.instanceId,
      apiToken: CURRENT_CREDS.apiToken,
    },
  }];
}

state.stats.commands = (state.stats.commands || 0) + 1;
let reply = '';

try {
  switch (command) {
    case 'yardim':
    case 'help': {
      reply = [
        '*Ototext — Ana Menü*',
        '',
        `${prefix}otox — yayın (rotasyon sorulur)`,
        `${prefix}onay / ${prefix}iptal / ${prefix}evet / ${prefix}hayir`,
        `${prefix}panic — her şeyi anında durdur`,
        `${prefix}durdur / ${prefix}durum / ${prefix}sure N`,
        `${prefix}zaman-otox 22:00-01:00 — zamanlı yayın`,
        `${prefix}zaman-dm 22:00-01:00 — zamanlı DM`,
        `${prefix}metin (yazı) — beklenen metni gir`,
        `${prefix}dm (metin). (grupId) — DM (onay ister)`,
        `${prefix}dm-durdur / ${prefix}dm-sure / ${prefix}dm-durum`,
        `${prefix}log-grup (id) — log grubu`,
        `${prefix}rapor — günlük rapor`,
        `${prefix}gruplar [sayfa]`,
        `${prefix}davetler / ${prefix}filtre / ${prefix}black / ${prefix}mining`,
        `${prefix}katil / ${prefix}tumkatil / ${prefix}karakter ayarla`,
        `${prefix}admin / ${prefix}prefix / ${prefix}istatistik`,
        `${prefix}numara — çoklu WhatsApp numarası`,
        `${prefix}guard — grup koruma (sticker spam / arama)`,
        `${prefix}lisans — lisans durumu`,
      ].join('\n');
      break;
    }
    case 'guard': {
      const g = state.guard;
      const gcount = Object.keys(g.groups || {}).filter((k) => g.groups[k]).length;
      const lockedN = Object.keys(g.lockedGroups || {}).length;
      reply = [
        '*🛡️ Guard Menü*',
        `${prefix}guard ac — tüm admin olduğun gruplarda aç`,
        `${prefix}guard kapat — kapat`,
        `${prefix}guard grup ac — sadece bu grupta aç`,
        `${prefix}guard grup kapat — bu grubu çıkar`,
        `${prefix}guard liste — korunan gruplar`,
        `${prefix}guard sticker 4 — sticker spam limiti`,
        `${prefix}guard yaz — bu sohbeti tekrar aç (herkes yazabilir)`,
        `${prefix}guard kilit — bu sohbeti kilitle (sadece admin)`,
        '',
        `Durum: ${g.enabled ? 'AÇIK' : 'KAPALI'}`,
        `Sticker spam kick: ${g.kickOnStickerSpam ? 'on' : 'off'} (limit ${g.stickerLimit}/${Math.round((g.stickerWindowMs||15000)/1000)}sn)`,
        `Arama kick: ${g.kickOnCall ? 'on' : 'off'}`,
        `Olayda otomatik kilit: ${g.lockOnIncident ? 'on' : 'off'}`,
        `Şu an kilitli: ${lockedN}`,
        `Özel grup listesi: ${gcount ? gcount + ' grup' : 'yok (tüm gruplar)'}`,
        '',
        'Spam/arama olunca: kick + sohbet kilit (sadece admin yazar).',
      ].join('\n');
      break;
    }
    case 'guard-yaz': {
      let gid = (args || '').trim().replace(/[()]/g, '');
      if (!gid && String(chatId).endsWith('@g.us')) gid = chatId;
      if (!gid.endsWith('@g.us')) { reply = `Grupta yaz: ${prefix}guard yaz`; break; }
      const r = await guardSetMembersCanWrite.call(this, state, gid, true);
      reply = r.ok
        ? `🔓 Sohbet açıldı — herkes yazabilir.\n${gid}`
        : `Açılamadı: ${r.error || r.res?.reason || 'bilinmeyen'} (bot admin mi?)`;
      break;
    }
    case 'guard-kilit': {
      let gid = (args || '').trim().replace(/[()]/g, '');
      if (!gid && String(chatId).endsWith('@g.us')) gid = chatId;
      if (!gid.endsWith('@g.us')) { reply = `Grupta yaz: ${prefix}guard kilit`; break; }
      const r = await guardSetMembersCanWrite.call(this, state, gid, false);
      reply = r.ok
        ? `🔒 Sohbet kilitlendi — sadece adminler yazabilir.\n${gid}`
        : `Kilitlenemedi: ${r.error || r.res?.reason || 'bilinmeyen'} (bot admin mi?)`;
      break;
    }
    case 'guard-ac': {
      state.guard.enabled = true;
      reply = '🛡️ Guard AÇIK.\nSticker spam + grup araması → çıkarma.\nBotun admin olduğu gruplarda çalışır.';
      break;
    }
    case 'guard-kapat': {
      state.guard.enabled = false;
      reply = '🛡️ Guard KAPALI.';
      break;
    }
    case 'guard-liste':
    case 'guard-durum': {
      const g = state.guard;
      const ids = Object.keys(g.groups || {}).filter((k) => g.groups[k]);
      reply = [
        `*🛡️ Guard* ${g.enabled ? 'AÇIK' : 'KAPALI'}`,
        `Sticker: ${g.kickOnStickerSpam ? 'on' : 'off'} limit=${g.stickerLimit}`,
        `Arama: ${g.kickOnCall ? 'on' : 'off'}`,
        ids.length ? ('Gruplar:\n' + ids.map((id, i) => `${i + 1}. ${id}`).join('\n')) : 'Özel liste yok → tüm gruplar (adminlik şart).',
      ].join('\n');
      break;
    }
    case 'guard-grup': {
      const a0 = (args.split(/\s+/)[0] || '').toLowerCase();
      const restG = args.slice(a0.length).trim().replace(/[()]/g, '');
      let gid = restG;
      if (!gid && String(chatId).endsWith('@g.us')) gid = chatId;
      if (!gid.endsWith('@g.us')) {
        reply = `Kullanım (grupta yaz): ${prefix}guard grup ac\nveya ${prefix}guard grup ac 120363...@g.us`;
        break;
      }
      if (a0 === 'ac' || a0 === 'aç' || a0 === 'on') {
        state.guard.enabled = true;
        state.guard.groups[gid] = true;
        reply = `🛡️ Bu grup korumada:\n${gid}`;
      } else if (a0 === 'kapat' || a0 === 'off') {
        delete state.guard.groups[gid];
        reply = `🛡️ Grup korumadan çıkarıldı:\n${gid}`;
      } else {
        reply = `Kullanım: ${prefix}guard grup ac | ${prefix}guard grup kapat`;
      }
      break;
    }
    case 'guard-sticker': {
      const n = parseInt(args, 10);
      if (!Number.isFinite(n) || n < 2 || n > 30) {
        reply = `Kullanım: ${prefix}guard sticker 4\n(2-30 arası, pencere 15 sn)`;
        break;
      }
      state.guard.stickerLimit = n;
      state.guard.kickOnStickerSpam = true;
      reply = `✅ Sticker spam limiti: ${n} / 15 sn → kick`;
      break;
    }
    case 'numara': {
      const active = getActiveNumber(state);
      reply = [
        '*📱 Numara Menü*',
        `${prefix}numara-liste`,
        `${prefix}numara-ekle (isim) (idInstance) (apiToken)`,
        `${prefix}numara-aktif (no|isim)`,
        `${prefix}numara-sil (no|isim)`,
        `${prefix}numara-yenile — aktif numaranın wid bilgisini yenile`,
        '',
        `Kayıtlı: ${state.numbers.length}`,
        `Aktif: ${active ? (active.name + ' / ' + active.instanceId) : '-'}`,
        `Bu mesajın geldiği instance: ${incomingInstance || '-'}`,
      ].join('\n');
      break;
    }
    case 'numara-liste': {
      if (!state.numbers.length) { reply = 'Kayıtlı numara yok. .env veya !numara-ekle ile ekle.'; break; }
      reply = ['*📱 Numaralar*', ...state.numbers.map((n, i) => formatNumberLine(n, i, state.activeNumberId))].join('\n');
      break;
    }
    case 'numara-ekle': {
      const bits = String(args || '').trim().split(/\s+/).filter(Boolean);
      if (bits.length < 3) {
        reply = `Kullanım: ${prefix}numara-ekle Bot2 1101xxxx tokenxxxx`;
        break;
      }
      const apiToken = bits[bits.length - 1];
      const instanceId = bits[bits.length - 2];
      const name = bits.slice(0, -2).join(' ') || ('Bot' + (state.numbers.length + 1));
      if (!/^\d+$/.test(instanceId) || apiToken.length < 10) {
        reply = 'idInstance sayı, apiToken uzun olmalı.';
        break;
      }
      if (state.numbers.some((n) => String(n.instanceId) === instanceId)) {
        reply = 'Bu instance zaten kayıtlı.';
        break;
      }
      const row = {
        id: 'n-' + Date.now().toString(36),
        name,
        instanceId,
        apiToken,
        wid: '',
        addedAt: Date.now(),
      };
      const prev = { ...CURRENT_CREDS };
      setCredsFromNumber(row);
      try {
        const st = await api.call(this, 'GET', 'getStateInstance');
        const settings = await api.call(this, 'GET', 'getSettings');
        row.wid = settings.wid || settings.phone || '';
        state.numbers.push(row);
        if (!state.activeNumberId) state.activeNumberId = row.id;
        reply = [
          '✅ Numara eklendi',
          `İsim: ${name}`,
          `Instance: ${instanceId}`,
          `State: ${st.stateInstance || '?'}`,
          `Wid: ${row.wid || '-'}`,
          '',
          `Aktif yapmak için: ${prefix}numara-aktif ${state.numbers.length}`,
          'Not: Bu instance’ın Green API webhook’u da aynı Ototext adresine bakmalı.',
        ].join('\n');
      } catch (e) {
        reply = `Eklenemedi (API kontrol): ${e.message || e}`;
      } finally {
        CURRENT_CREDS = prev;
        if (sessionNumber) setCredsFromNumber(sessionNumber);
      }
      break;
    }
    case 'numara-aktif': {
      const n = getNumberByRef(state, args);
      if (!n) { reply = `Kullanım: ${prefix}numara-aktif 1`; break; }
      state.activeNumberId = n.id;
      setCredsFromNumber(n);
      sessionNumber = n;
      if (n.wid) state.botWid = n.wid;
      reply = `✅ Aktif numara: ${n.name}\nInstance: ${n.instanceId}\nYayın/DM/mining bu numaradan gider.`;
      break;
    }
    case 'numara-sil': {
      const n = getNumberByRef(state, args);
      if (!n) { reply = `Kullanım: ${prefix}numara-sil 2`; break; }
      if (state.numbers.length <= 1) { reply = 'En az 1 numara kalmalı.'; break; }
      state.numbers = state.numbers.filter((x) => x.id !== n.id);
      if (state.activeNumberId === n.id) state.activeNumberId = state.numbers[0].id;
      reply = `🗑 Silindi: ${n.name}\nAktif: ${getActiveNumber(state)?.name || '-'}`;
      break;
    }
    case 'numara-yenile': {
      const n = getActiveNumber(state);
      if (!n) { reply = 'Aktif numara yok.'; break; }
      setCredsFromNumber(n);
      try {
        const settings = await api.call(this, 'GET', 'getSettings');
        const st = await api.call(this, 'GET', 'getStateInstance');
        n.wid = settings.wid || settings.phone || n.wid || '';
        state.botWid = n.wid;
        reply = `🔄 Yenilendi\n${n.name}\nWid: ${n.wid || '-'}\nState: ${st.stateInstance || '?'}`;
      } catch (e) {
        reply = `Yenilenemedi: ${e.message || e}`;
      }
      break;
    }
    case 'lisans': {
      const key = (($env.LICENSE_KEY || '') + '').trim();
      if (!key || !key.includes('.')) {
        reply = 'Lisans anahtarı yok (LICENSE_KEY). Satıcı paketini kontrol et.';
        break;
      }
      try {
        const body = key.split('.')[0];
        const pad = body.length % 4 === 0 ? '' : '='.repeat(4 - (body.length % 4));
        const jsonStr = Buffer.from(body.replace(/-/g, '+').replace(/_/g, '/') + pad, 'base64').toString('utf8');
        const p = JSON.parse(jsonStr);
        const left = Math.max(0, Math.floor((Number(p.exp || 0) - Date.now() / 1000) / 86400));
        reply = [
          '*Lisans*',
          `Müşteri: ${p.name || '-'}`,
          `Plan: ${p.plan || '-'}`,
          `Kalan gün: ${left}`,
          `Ürün: ${p.product || 'ototext'}`,
        ].join('\n');
      } catch (e) {
        reply = 'Lisans anahtarı okunamadı.';
      }
      break;
    }
    case 'otox': {
      // Eski kısayol: !otox (metin) → tek metin onayı
      // Yeni akış: !otox → rotasyon sor
      if (args && args.trim()) {
        setPending(state, {
          type: 'ask_otox_rotate',
          by: sender,
          chatId,
          data: {
            seedText: args.trim(),
            windowStart: state.broadcast.windowStart || '',
            windowEnd: state.broadcast.windowEnd || '',
          },
          ttlMs: 15 * 60 * 1000,
        });
        reply = [
          '❓ *Mesaj rotasyonu kullanmak ister misin?*',
          'Birden fazla metin sırayla gönderilir.',
          '',
          `Evet: ${prefix}evet`,
          `Hayır (tek metin): ${prefix}hayir`,
          `Vazgeç: ${prefix}iptal`,
          '',
          `Not: yazdığın metin saklandı (tek metin seçersen kullanılır).`,
        ].join('\n');
        break;
      }
      setPending(state, {
        type: 'ask_otox_rotate',
        by: sender,
        chatId,
        data: {
          windowStart: state.broadcast.windowStart || '',
          windowEnd: state.broadcast.windowEnd || '',
        },
        ttlMs: 15 * 60 * 1000,
      });
      reply = [
        '❓ *Mesaj rotasyonu kullanmak ister misin?*',
        'Rotasyon: her gönderimde sıradaki metin kullanılır.',
        '',
        `Evet: ${prefix}evet`,
        `Hayır (tek metin): ${prefix}hayir`,
        `Vazgeç: ${prefix}iptal`,
      ].join('\n');
      break;
    }
    case 'adet': {
      if (!pendingValid(state, sender) || state.pending.type !== 'ask_otox_count') {
        reply = `Önce ${prefix}otox yaz, rotasyona evet de, sonra ${prefix}adet 3`;
        break;
      }
      const n = parseInt(String(args || '').trim(), 10);
      if (!Number.isFinite(n) || n < 2 || n > 10) {
        reply = `Kaç metin? 2-10 arası.\nÖrnek: ${prefix}adet 3`;
        break;
      }
      const base = state.pending.data || {};
      setPending(state, {
        type: 'await_otox_rotate_text',
        by: sender,
        chatId,
        data: {
          ...base,
          count: n,
          texts: [],
          next: 1,
        },
        ttlMs: 20 * 60 * 1000,
      });
      reply = `✅ ${n} metin isteniyor.\nŞimdi *1/${n}* metni gir:\n${prefix}metin (yazı)`;
      break;
    }
    case 'panic': {
      state.broadcast.running = false;
      state.dm.running = false;
      state.mining.running = false;
      clearPending(state);
      await pushLog.call(this, state, 'stop', `PANIC — otox/dm/mining/pending durduruldu`);
      reply = [
        '🛑 *PANIC*',
        'OTOX: DURDU',
        'DM: DURDU',
        'Mining: DURDU',
        'Bekleyen onay: temizlendi',
      ].join('\n');
      break;
    }
    case 'durdur': {
      state.broadcast.running = false;
      await pushLog.call(this, state, 'stop', `OTOX durduruldu | gönderilen ${state.broadcast.sent}`);
      reply = `⏹ Yayın durduruldu.\nGönderilen: ${state.broadcast.sent}`;
      break;
    }
    case 'durum': {
      const b = state.broadcast;
      const texts = Array.isArray(b.texts) && b.texts.length ? b.texts : (b.text ? [b.text] : []);
      reply = [
        '*📡 Yayın Durumu*',
        `Durum: ${b.running ? 'ÇALIŞIYOR' : 'DURDU'}`,
        `Süre aralığı: ${b.intervalMin} dk`,
        `Gönderilen: ${b.sent}`,
        `Grup index: ${b.index}`,
        `Rotasyon: ${texts.length > 1 ? (texts.length + ' metin') : 'tek metin'}`,
        texts.length > 1 ? `Sıradaki metin #: ${((b.textIndex || 0) % texts.length) + 1}` : '',
        `Metin: ${(texts[(b.textIndex || 0) % Math.max(texts.length, 1)] || b.text || '-').slice(0, 160)}`,
        `Pencere: ${(b.windowStart && b.windowEnd) ? (b.windowStart + '-' + b.windowEnd) : 'sürekli'}`,
        `Min üye filtresi: ${state.filters.minUye || 0}`,
        `Blacklist: ${state.blacklist.length}`,
      ].filter(Boolean).join('\n');
      break;
    }
    case 'sure': {
      const mins = parseFloat(String(args).replace(',', '.').replace(/\.$/, ''));
      if (!Number.isFinite(mins) || mins <= 0) { reply = `Kullanım: ${prefix}sure 3`; break; }
      state.broadcast.intervalMin = mins;
      reply = `⏱ Yayın aralığı ${mins} dakika olarak ayarlandı.`;
      break;
    }
    case 'dm': {
      const parsed = parseDm(args);
      if (!parsed || !parsed.text || !parsed.groupId) {
        reply = `Kullanım: ${prefix}dm (metin). (grupId)\nÖrnek: ${prefix}dm Merhaba. 120363xxx@g.us`;
        break;
      }
      setPending(state, {
        type: 'confirm_dm',
        by: sender,
        chatId,
        data: {
          text: parsed.text,
          groupId: parsed.groupId,
          windowStart: state.dm.windowStart || '',
          windowEnd: state.dm.windowEnd || '',
        },
      });
      reply = [
        '❓ *DM onayı*',
        `Grup: ${parsed.groupId}`,
        `Metin: ${parsed.text.slice(0, 160)}`,
        `Aralık: ${state.dm.intervalMin} dk`,
        `Pencere: ${(state.dm.windowStart && state.dm.windowEnd) ? (state.dm.windowStart + '-' + state.dm.windowEnd) : 'sürekli'}`,
        '',
        `Onayla: ${prefix}onay`,
        `İptal: ${prefix}iptal`,
      ].join('\n');
      break;
    }
    case 'dm-durdur': {
      state.dm.running = false;
      await pushLog.call(this, state, 'stop', `DM durduruldu | sent ${state.dm.sent} fail ${state.dm.failed}`);
      reply = `⏹ DM durduruldu.\nGönderilen: ${state.dm.sent}/${(state.dm.queue || []).length}\nHata: ${state.dm.failed}`;
      break;
    }
    case 'dm-sure': {
      const mins = parseFloat(String(args).replace(',', '.').replace(/\.$/, ''));
      if (!Number.isFinite(mins) || mins <= 0) { reply = `Kullanım: ${prefix}dm-sure 3`; break; }
      state.dm.intervalMin = mins;
      reply = `⏱ DM aralığı ${mins} dakika.`;
      break;
    }
    case 'dm-durum': {
      const d = state.dm;
      const total = (d.queue || []).length;
      reply = [
        '*✉️ DM Durumu*',
        `Durum: ${d.running ? 'ÇALIŞIYOR' : 'DURDU'}`,
        `Grup: ${d.groupId || '-'}`,
        `Gönderilen DM: ${d.sent}`,
        `Kalan: ${Math.max(0, total - d.index)}`,
        `Hata: ${d.failed}`,
        `Aralık: ${d.intervalMin} dk`,
        `Metin: ${(d.text || '-').slice(0, 120)}`,
      ].join('\n');
      break;
    }
    case 'gruplar': {
      const page = Math.max(1, parseInt(args || '1', 10) || 1);
      const { enriched, safe, totalPages, total } = await listGroupsPage.call(this, state, page);
      if (!total) { reply = '📋 Grup bulunamadı.'; break; }
      const lines = [`📋 *Gruplar* ${safe}/${totalPages} (toplam ${total})`, ''];
      for (const g of enriched) {
        lines.push(`${g.no}. ${g.name}${g.blocked ? ' 🚫' : ''}`);
        lines.push(`   👥 ${g.members}  |  🆔 ${g.id}`);
      }
      if (safe < totalPages) lines.push('', `Sonraki: ${prefix}gruplar ${safe + 1}`);
      if (safe > 1) lines.push(`Önceki: ${prefix}gruplar ${safe - 1}`);
      reply = lines.join('\n');
      break;
    }
    case 'davetler': {
      if (!state.invites.length) { reply = '🔗 Kayıtlı davet linki yok.'; break; }
      const lines = [`🔗 *Davetler* (${state.invites.length})`, ''];
      state.invites.slice(0, 30).forEach((inv, i) => {
        lines.push(`${i + 1}. ${inv.groupName || 'Grup'}`);
        lines.push(`   ${inv.link}`);
      });
      reply = lines.join('\n');
      break;
    }
    case 'filtre': {
      reply = [
        '*🧪 Filtre Menüsü*',
        `${prefix}min-uye 500 — minimum üye`,
        `${prefix}min-uye 30`,
        `${prefix}temizlik — filtreleri sıfırla`,
        '',
        `Aktif min-uye: ${state.filters.minUye || 0}`,
      ].join('\n');
      break;
    }
    case 'min-uye': {
      const n = parseInt(args, 10);
      if (!Number.isFinite(n) || n < 0) { reply = `Kullanım: ${prefix}min-uye 500`; break; }
      state.filters.minUye = n;
      reply = `✅ Minimum üye filtresi: ${n}`;
      break;
    }
    case 'temizlik': {
      state.filters = { minUye: 0 };
      reply = '🧹 Filtreler temizlendi.';
      break;
    }
    case 'black': {
      reply = [
        '*🚫 Black Menü*',
        `${prefix}black-ekle (id)`,
        `${prefix}black-cikar (id)`,
        `${prefix}black-liste`,
      ].join('\n');
      break;
    }
    case 'black-ekle': {
      let id = (args || '').trim().replace(/[()]/g, '');
      if (/^\d+$/.test(id) && state.lastGroupsPage?.items) {
        const hit = state.lastGroupsPage.items.find((x) => x.no === parseInt(id, 10));
        if (hit) id = hit.id;
      }
      if (!id.endsWith('@g.us')) { reply = `Kullanım: ${prefix}black-ekle 120363...@g.us`; break; }
      if (!state.blacklist.includes(id)) state.blacklist.push(id);
      reply = `🚫 Eklendi:\n${id}`;
      break;
    }
    case 'black-cikar': {
      let id = (args || '').trim().replace(/[()]/g, '');
      if (/^\d+$/.test(id)) {
        const n = parseInt(id, 10);
        if (state.blacklist[n - 1]) id = state.blacklist[n - 1];
      }
      state.blacklist = state.blacklist.filter((x) => x !== id);
      reply = `✅ Çıkarıldı:\n${id}`;
      break;
    }
    case 'black-liste': {
      if (!state.blacklist.length) { reply = '🚫 Black list boş.'; break; }
      const lines = [`🚫 *Black List* (${state.blacklist.length})`, ''];
      for (let i = 0; i < state.blacklist.length; i++) {
        const id = state.blacklist[i];
        let name = id;
        try {
          const data = await api.call(this, 'POST', 'getGroupData', { groupId: id });
          name = data.subject || id;
        } catch (e) {}
        lines.push(`${i + 1}. ${name}`);
        lines.push(`   🆔 ${id}`);
      }
      reply = lines.join('\n');
      break;
    }
    case 'mining': {
      reply = [
        '*⛏️ Mining Menü*',
        `${prefix}mining-baslat (hedefGrupId)`,
        `${prefix}mining-durdur`,
        `${prefix}mining-durum`,
      ].join('\n');
      break;
    }
    case 'mining-baslat': {
      const id = (args || '').trim().replace(/[()]/g, '');
      if (!id.endsWith('@g.us')) { reply = `Kullanım: ${prefix}mining-baslat 120363...@g.us`; break; }
      let name = id;
      let members = 0;
      try {
        const data = await api.call(this, 'POST', 'getGroupData', { groupId: id });
        name = data.subject || id;
        members = typeof data.size === 'number' ? data.size : (data.participants || []).length;
      } catch (e) {}
      const dayKey = new Date().toISOString().slice(0, 10);
      state.mining = {
        running: true,
        targetGroupId: id,
        targetName: name,
        members,
        addedToday: state.mining.dayKey === dayKey ? (state.mining.addedToday || 0) : 0,
        pending: 0,
        totalTarget: Math.max(members + 50, 100),
        durationMin: 0,
        startedAt: Date.now(),
        lastAddAt: 0,
        dayKey,
      };
      reply = `⛏️ Mining başladı.\nHedef: ${name}\nÜye: ${members}`;
      break;
    }
    case 'mining-durdur': {
      state.mining.running = false;
      reply = '⏹ Mining durduruldu.';
      break;
    }
    case 'mining-durum': {
      const m = state.mining;
      const dur = m.startedAt ? Math.round((Date.now() - m.startedAt) / 60000) : 0;
      reply = [
        '*⛏️ Mining Durum*',
        `Durum: ${m.running ? 'ÇALIŞIYOR' : 'DURDU'}`,
        `Hedef: ${m.targetName || '-'}`,
        `Üye: ${m.members}`,
        `Bugün eklenen: ${m.addedToday}`,
        `Eklenecek (pending): ${m.pending}`,
        `Toplam hedef: ${m.totalTarget}`,
        `Süre: ${dur} dk`,
        `ID: ${m.targetGroupId || '-'}`,
      ].join('\n');
      break;
    }
    case 'katil': {
      const link = extractInviteLinks(args)[0] || args.trim();
      if (!link.includes('chat.whatsapp.com')) { reply = `Kullanım: ${prefix}katil https://chat.whatsapp.com/...`; break; }
      try {
        const res = await api.call(this, 'POST', 'joinGroup', { inviteLink: link });
        state.stats.joins += 1;
        reply = `✅ Katılma isteği gönderildi.\n${link}\n${JSON.stringify(res).slice(0, 180)}`;
      } catch (e) {
        reply = `⚠️ joinGroup başarısız: ${e.message || e}\nLink kaydedildi (!davetler).`;
        if (!state.invites.some((x) => x.link === link)) {
          state.invites.unshift({ link, groupName: '', groupJid: '', from: sender, at: Date.now() });
        }
      }
      break;
    }
    case 'tumkatil': {
      const links = extractInviteLinks(args);
      if (!links.length) { reply = `Kullanım: ${prefix}tumkatil (link) (link) ...`; break; }
      const results = [];
      for (const link of links) {
        try {
          await api.call(this, 'POST', 'joinGroup', { inviteLink: link });
          state.stats.joins += 1;
          results.push(`✅ ${link}`);
        } catch (e) {
          results.push(`⚠️ ${link} → ${e.message || e}`);
        }
      }
      reply = `*Toplu katıl* (${links.length})\n` + results.join('\n');
      break;
    }
    case 'karakter': {
      const m = args.match(/^ayarla\s+(.+)$/i);
      if (!m) { reply = `Kullanım: ${prefix}karakter ayarla (isim)`; break; }
      const name = m[1].trim();
      try {
        const res = await api.call(this, 'POST', 'setProfileName', { name });
        reply = `✅ İsim güncellendi: ${name}\n${JSON.stringify(res).slice(0, 120)}`;
      } catch (e1) {
        try {
          const res = await api.call(this, 'POST', 'setSettings', { name });
          reply = `✅ setSettings ile isim denendi: ${name}`;
        } catch (e2) {
          reply = `⚠️ İsim değiştirilemedi: ${e1.message || e1}`;
        }
      }
      break;
    }
    case 'admin': {
      reply = [
        '*👑 Admin Menü*',
        `${prefix}admin-ekle @kullanici`,
        `${prefix}admin-cikar @kullanici`,
        `${prefix}admin-list`,
        '',
        'Bot numarası otomatik admindir.',
      ].join('\n');
      break;
    }
    case 'admin-ekle': {
      const id = normId(args);
      if (!id) { reply = `Kullanım: ${prefix}admin-ekle 905xxxxxxxxx`; break; }
      if (!state.admins.includes(id)) state.admins.push(id);
      reply = `👑 Admin eklendi:\n${id}`;
      break;
    }
    case 'admin-cikar': {
      const id = normId(args);
      if (id && id === state.botWid) { reply = 'Bot numarası adminlikten çıkarılamaz.'; break; }
      state.admins = state.admins.filter((x) => x !== id);
      reply = `✅ Admin çıkarıldı:\n${id}`;
      break;
    }
    case 'admin-list': {
      const lines = [`*👑 Adminler* (${state.admins.length})`, ''];
      state.admins.forEach((a, i) => lines.push(`${i + 1}. ${a}${a === state.botWid ? ' (bot)' : ''}`));
      reply = lines.join('\n');
      break;
    }


    case 'onay':
    case 'evet': {
      if (!pendingValid(state, sender)) { reply = '⏳ Onay bekleyen işlem yok / süresi doldu.'; break; }
      const p = state.pending;
      if (p.type === 'ask_otox_rotate') {
        // Rotasyon istiyor
        setPending(state, {
          type: 'ask_otox_count',
          by: sender,
          chatId,
          data: p.data || {},
          ttlMs: 15 * 60 * 1000,
        });
        reply = [
          '🔢 Kaç farklı metin kullanılsın?',
          `Örnek: ${prefix}adet 3`,
          '(2 ile 10 arası)',
          `Vazgeç: ${prefix}iptal`,
        ].join('\n');
        break;
      }
      if (p.type === 'confirm_otox') {
        const d = p.data || {};
        const texts = broadcastTextsFromData(d);
        if (!texts.length) { reply = 'Metin yok. Tekrar !otox ile başla.'; break; }
        state.broadcast.running = true;
        state.broadcast.texts = texts;
        state.broadcast.text = texts[0];
        state.broadcast.textIndex = 0;
        state.broadcast.index = 0;
        state.broadcast.sent = 0;
        state.broadcast.startedAt = Date.now();
        state.broadcast.lastSendAt = 0;
        state.broadcast.windowStart = d.windowStart || state.broadcast.windowStart || '';
        state.broadcast.windowEnd = d.windowEnd || state.broadcast.windowEnd || '';
        clearPending(state);
        await pushLog.call(this, state, 'start', `OTOX başladı | metin=${texts.length} | aralık ${state.broadcast.intervalMin}dk | ${texts[0].slice(0,80)}`);
        reply = [
          '▶️ Yayın onaylandı ve başladı.',
          `Metin sayısı: ${texts.length}${texts.length > 1 ? ' (rotasyon)' : ''}`,
          `Aralık: ${state.broadcast.intervalMin} dk`,
          `Pencere: ${(state.broadcast.windowStart && state.broadcast.windowEnd) ? (state.broadcast.windowStart + '-' + state.broadcast.windowEnd) : 'sürekli'}`,
        ].join('\n');
      } else if (p.type === 'confirm_dm') {
        const d = p.data || {};
        const data = await api.call(this, 'POST', 'getGroupData', { groupId: d.groupId });
        const participants = (data.participants || []).map((x) => x.id).filter(Boolean);
        const me = state.botWid;
        const queue = participants.filter((id) => id !== me && String(id).endsWith('@c.us'));
        state.dm.running = true;
        state.dm.text = d.text || '';
        state.dm.groupId = d.groupId;
        state.dm.queue = queue;
        state.dm.index = 0;
        state.dm.sent = 0;
        state.dm.failed = 0;
        state.dm.lastSendAt = 0;
        state.dm.startedAt = Date.now();
        state.dm.windowStart = d.windowStart || state.dm.windowStart || '';
        state.dm.windowEnd = d.windowEnd || state.dm.windowEnd || '';
        clearPending(state);
        await pushLog.call(this, state, 'start', `DM başladı | grup ${d.groupId} | kuyruk ${queue.length}`);
        reply = `✉️ DM onaylandı.\nGrup: ${data.subject || d.groupId}\nKuyruk: ${queue.length}\nPencere: ${(state.dm.windowStart && state.dm.windowEnd) ? (state.dm.windowStart + '-' + state.dm.windowEnd) : 'sürekli'}`;
      } else {
        reply = 'Bu adımda !onay/!evet geçerli değil. Akıştaki soruya cevap ver.';
      }
      break;
    }
    case 'hayir': {
      if (!pendingValid(state, sender)) { reply = '⏳ Bekleyen işlem yok / süresi doldu.'; break; }
      const p = state.pending;
      if (p.type === 'ask_otox_rotate') {
        const seed = String(p.data?.seedText || '').trim();
        if (seed) {
          setPending(state, {
            type: 'confirm_otox',
            by: sender,
            chatId,
            data: {
              text: seed,
              texts: [seed],
              windowStart: p.data?.windowStart || '',
              windowEnd: p.data?.windowEnd || '',
            },
          });
          reply = [
            '❓ *Tek metin — yayın onayı*',
            seed.slice(0, 160),
            `Aralık: ${state.broadcast.intervalMin} dk`,
            '',
            `Onayla: ${prefix}onay`,
            `İptal: ${prefix}iptal`,
          ].join('\n');
        } else {
          setPending(state, {
            type: 'await_otox_text',
            by: sender,
            chatId,
            data: {
              windowStart: p.data?.windowStart || '',
              windowEnd: p.data?.windowEnd || '',
            },
            ttlMs: 15 * 60 * 1000,
          });
          reply = `Tek metin seçildi.\nŞimdi yaz:\n${prefix}metin (mesajın)`;
        }
        break;
      }
      // diğer durumlarda hayır = iptal
      clearPending(state);
      reply = '❎ İşlem iptal edildi.';
      break;
    }
    case 'iptal': {
      if (!state.pending) { reply = 'İptal edilecek işlem yok.'; break; }
      clearPending(state);
      reply = '❎ İşlem iptal edildi.';
      break;
    }
    case 'zaman-otox': {
      const w = parseWindow(args);
      if (!w) { reply = `Kullanım: ${prefix}zaman-otox 22:00-01:00`; break; }
      state.broadcast.windowStart = w.start;
      state.broadcast.windowEnd = w.end;
      setPending(state, { type: 'await_otox_text', by: sender, chatId, data: { windowStart: w.start, windowEnd: w.end } });
      reply = `🕒 OTOX zamanı kaydedildi: ${w.start}-${w.end}\nŞimdi metni gir:\n${prefix}metin (yazın)\nSonra ${prefix}onay ile başlar.`;
      break;
    }
    case 'zaman-dm': {
      const w = parseWindow(args);
      if (!w) { reply = `Kullanım: ${prefix}zaman-dm 22:00-01:00`; break; }
      state.dm.windowStart = w.start;
      state.dm.windowEnd = w.end;
      setPending(state, { type: 'await_dm_group', by: sender, chatId, data: { windowStart: w.start, windowEnd: w.end } });
      reply = `🕒 DM zamanı kaydedildi: ${w.start}-${w.end}\nŞimdi grup id gir:\n${prefix}dmgrup 120363...@g.us\nSonra ${prefix}metin (yazı) ve ${prefix}onay`;
      break;
    }
    case 'dmgrup': {
      if (!pendingValid(state, sender) || state.pending.type !== 'await_dm_group') {
        reply = `Önce ${prefix}zaman-dm 22:00-01:00 yaz.`;
        break;
      }
      const gid = (args || '').trim().replace(/[()]/g, '');
      if (!gid.endsWith('@g.us')) { reply = `Kullanım: ${prefix}dmgrup 120363...@g.us`; break; }
      const data = state.pending.data || {};
      setPending(state, { type: 'await_dm_text', by: sender, chatId, data: { ...data, groupId: gid } });
      reply = `✅ DM grup: ${gid}\nŞimdi metni gir:\n${prefix}metin (yazın)`;
      break;
    }
    case 'metin': {
      if (!args) { reply = `Kullanım: ${prefix}metin (yazı)`; break; }
      if (!pendingValid(state, sender)) { reply = 'Bekleyen metin adımı yok. Önce !otox / zaman-otox / zaman-dm.'; break; }
      const p = state.pending;
      if (p.type === 'await_otox_rotate_text') {
        const d = p.data || {};
        const count = Number(d.count) || 0;
        const texts = Array.isArray(d.texts) ? d.texts.slice() : [];
        texts.push(args.trim());
        if (texts.length < count) {
          setPending(state, {
            type: 'await_otox_rotate_text',
            by: sender,
            chatId,
            data: { ...d, texts, next: texts.length + 1 },
            ttlMs: 20 * 60 * 1000,
          });
          reply = `✅ ${texts.length}/${count} alındı.\nŞimdi *${texts.length + 1}/${count}* metni gir:\n${prefix}metin (yazı)`;
        } else {
          setPending(state, {
            type: 'confirm_otox',
            by: sender,
            chatId,
            data: {
              texts,
              text: texts[0],
              windowStart: d.windowStart || '',
              windowEnd: d.windowEnd || '',
            },
          });
          reply = [
            '❓ *Rotasyon — yayın onayı*',
            `Metin sayısı: ${texts.length}`,
            summarizeTexts(texts),
            `Aralık: ${state.broadcast.intervalMin} dk`,
            '',
            `Onayla: ${prefix}onay`,
            `İptal: ${prefix}iptal`,
          ].join('\n');
        }
      } else if (p.type === 'await_otox_text') {
        setPending(state, {
          type: 'confirm_otox',
          by: sender,
          chatId,
          data: {
            text: args,
            texts: [args],
            windowStart: p.data?.windowStart || '',
            windowEnd: p.data?.windowEnd || '',
          },
        });
        reply = `❓ OTOX metni alındı.\n${args.slice(0,160)}\nPencere: ${p.data?.windowStart || '-'}-${p.data?.windowEnd || '-'}\n${prefix}onay / ${prefix}iptal`;
      } else if (p.type === 'await_dm_text') {
        setPending(state, {
          type: 'confirm_dm',
          by: sender,
          chatId,
          data: { text: args, groupId: p.data?.groupId, windowStart: p.data?.windowStart || '', windowEnd: p.data?.windowEnd || '' },
        });
        reply = `❓ DM metni alındı.\nGrup: ${p.data?.groupId}\n${args.slice(0,160)}\n${prefix}onay / ${prefix}iptal`;
      } else {
        reply = 'Şu an metin beklenmiyor. Önce !otox yaz.';
      }
      break;
    }
    case 'log-grup': {
      const id = (args || '').trim().replace(/[()]/g, '');
      if (!id.endsWith('@g.us')) { reply = `Kullanım: ${prefix}log-grup 120363...@g.us`; break; }
      state.logGroupId = id;
      await pushLog.call(this, state, 'info', `Log grubu ayarlandı: ${id}`);
      reply = `✅ Log grubu:\n${id}\nArtık olaylar buraya düşer.`;
      break;
    }
    case 'rapor': {
      const daily = ensureDaily(state);
      const lines = [
        `📊 *Günlük Rapor* (${daily.dayKey})`,
        `Yayın mesajı: ${daily.broadcastSent}`,
        `DM: ${daily.dmSent}`,
        `Başlatma: ${daily.starts}`,
        `Durdurma: ${daily.stops}`,
        `Hata: ${daily.errors}`,
        `Log grup: ${state.logGroupId || '-'}`,
        '',
        '*Son olaylar:*',
      ];
      for (const ev of (daily.events || []).slice(0, 15)) {
        const hh = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Istanbul', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(ev.t));
        lines.push(`• ${hh} [${ev.type}] ${ev.message}`);
      }
      reply = lines.join('\n');
      if (state.logGroupId) {
        try { await api.call(this, 'POST', 'sendMessage', { chatId: state.logGroupId, message: reply }); } catch (e) {}
      }
      break;
    }

    case 'prefix': {
      reply = [
        '*🔤 Prefix Menü*',
        `${prefix}prefix-main (prefix) — ana prefix yap`,
        `${prefix}prefix-ekle (prefix) — ek prefix ekle`,
        `${prefix}prefix-cikar (prefix) — prefix çıkar`,
        `${prefix}prefix cikar (prefix) — aynı komut`,
        '',
        `Ana prefix: ${state.mainPrefix}`,
        `Aktif: ${state.prefixes.join('  ')}`,
      ].join('\n');
      break;
    }
    case 'prefix-main': {
      const px = normalizePrefix(args);
      if (!px) { reply = `Kullanım: ${prefix}prefix-main !`; break; }
      state.mainPrefix = px;
      if (!state.prefixes.includes(px)) state.prefixes.unshift(px);
      else {
        state.prefixes = [px, ...state.prefixes.filter((x) => x !== px)];
      }
      reply = `✅ Ana prefix: ${px}\nAktif: ${state.prefixes.join('  ')}`;
      break;
    }
    case 'prefix-ekle': {
      const px = normalizePrefix(args);
      if (!px) { reply = `Kullanım: ${prefix}prefix-ekle /`; break; }
      if (!state.prefixes.includes(px)) state.prefixes.push(px);
      reply = `✅ Prefix eklendi: ${px}\nAktif: ${state.prefixes.join('  ')}\nAna: ${state.mainPrefix}`;
      break;
    }
    case 'prefix-cikar': {
      const px = normalizePrefix(args);
      if (!px) { reply = `Kullanım: ${prefix}prefix-cikar /`; break; }
      if (px === state.mainPrefix) {
        reply = `⚠️ Ana prefix çıkarılamaz. Önce ${prefix}prefix-main ile başka ana seç.`;
        break;
      }
      if (state.prefixes.length <= 1) {
        reply = '⚠️ En az 1 prefix kalmalı.';
        break;
      }
      state.prefixes = state.prefixes.filter((x) => x !== px);
      reply = `✅ Prefix çıkarıldı: ${px}\nAktif: ${state.prefixes.join('  ')}`;
      break;
    }
    case 'prefix-liste': {
      reply = [
        '*🔤 Prefix Listesi*',
        `Ana: ${state.mainPrefix}`,
        ...state.prefixes.map((x, i) => `${i + 1}. ${x}${x === state.mainPrefix ? ' (ana)' : ''}`),
      ].join('\n');
      break;
    }

    case 'istatistik': {
      const s = state.stats;
      const active = getActiveNumber(state);
      reply = [
        '*📊 Ototext İstatistik*',
        `Komutlar: ${s.commands}`,
        `Yayın mesajı: ${s.broadcastSent}`,
        `DM: ${s.dmSent}`,
        `Katılma: ${s.joins}`,
        `Blacklist: ${state.blacklist.length}`,
        `Davet kaydı: ${state.invites.length}`,
        `Numaralar: ${state.numbers.length} | aktif: ${active ? active.name : '-'}`,
        `Yayın: ${state.broadcast.running ? 'ON' : 'OFF'}`,
        `DM: ${state.dm.running ? 'ON' : 'OFF'}`,
        `Mining: ${state.mining.running ? 'ON' : 'OFF'}`,
      ].join('\n');
      break;
    }
    default:
      reply = `❓ Bilinmeyen komut: ${command}\n${prefix}yardim`;
  }
} catch (e) {
  reply = `⚠️ Hata: ${e.message || e}`;
}

saveState(state);
return [{
  json: {
    chatId,
    reply,
    command,
    sender,
    instanceId: CURRENT_CREDS.instanceId,
    apiToken: CURRENT_CREDS.apiToken,
  },
}];
'''.replace('__STATE_PATH__', STATE_PATH)

WORKER_JS = r'''
const STATE_PATH = '__STATE_PATH__';
const fs = require('fs');

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8')); }
  catch (e) { return null; }
}
function saveState(state) {
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
}

let stateRef = null;

function getActiveNumber(state) {
  const nums = Array.isArray(state.numbers) ? state.numbers : [];
  let n = nums.find((x) => x.id === state.activeNumberId);
  if (!n) n = nums[0];
  if (n) return n;
  const envId = String($env.ID_INSTANCE || '');
  const envTok = String($env.API_TOKEN || '');
  if (envId && envTok && envId !== 'YOUR_INSTANCE_ID') {
    return { id: 'env', name: 'Ana', instanceId: envId, apiToken: envTok };
  }
  return null;
}

async function api(method, endpoint, body) {
  const active = getActiveNumber(stateRef || {});
  const instance = active ? active.instanceId : $env.ID_INSTANCE;
  const token = active ? active.apiToken : $env.API_TOKEN;
  if (!instance || !token || instance === 'YOUR_INSTANCE_ID') {
    throw new Error('missing credentials');
  }
  let url = `https://api.green-api.com/waInstance${instance}/${endpoint}/${token}`;
  if (method === 'GET' && body && typeof body === 'object') {
    const qs = new URLSearchParams(body).toString();
    if (qs) url += `?${qs}`;
    body = undefined;
  }
  const opts = { method, url, json: true };
  if (body !== undefined) opts.body = body;
  return this.helpers.httpRequest(opts);
}

function dayKeyTR() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}
function ensureDaily(state) {
  const key = dayKeyTR();
  if (!state.daily || state.daily.dayKey !== key) {
    state.daily = { dayKey: key, broadcastSent: 0, dmSent: 0, errors: 0, starts: 0, stops: 0, events: [] };
  }
  return state.daily;
}
function inTimeWindow(startHHMM, endHHMM) {
  if (!startHHMM || !endHHMM) return true;
  const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Istanbul', hour: '2-digit', minute: '2-digit', hour12: false });
  const parts = fmt.formatToParts(new Date());
  const hh = parseInt(parts.find((p) => p.type === 'hour').value, 10);
  const mm = parseInt(parts.find((p) => p.type === 'minute').value, 10);
  const cur = hh * 60 + mm;
  const [sh, sm] = startHHMM.split(':').map(Number);
  const [eh, em] = endHHMM.split(':').map(Number);
  const start = sh * 60 + sm;
  const end = eh * 60 + em;
  if (start <= end) return cur >= start && cur <= end;
  return cur >= start || cur <= end;
}
async function pushLog(state, type, message) {
  const daily = ensureDaily(state);
  daily.events.unshift({ t: Date.now(), type, message: String(message || '').slice(0, 300) });
  daily.events = daily.events.slice(0, 200);
  if (type === 'broadcast') daily.broadcastSent += 1;
  if (type === 'dm') daily.dmSent += 1;
  if (type === 'error') daily.errors += 1;
  if (state.logGroupId) {
    try {
      await api.call(this, 'POST', 'sendMessage', { chatId: state.logGroupId, message: `🧾 *LOG* [${type}]\n${message}` });
    } catch (e) {}
  }
}

const state = loadState();
if (!state) return [];
stateRef = state;
if (!Array.isArray(state.numbers)) state.numbers = [];
const logs = [];
const now = Date.now();
ensureDaily(state);
const activeNum = getActiveNumber(state);
if (activeNum) logs.push(`activeNumber=${activeNum.name || activeNum.instanceId}`);

// --- Broadcast worker ---
const bTexts = Array.isArray(state.broadcast?.texts) && state.broadcast.texts.length
  ? state.broadcast.texts
  : (state.broadcast?.text ? [state.broadcast.text] : []);
if (state.broadcast?.running && bTexts.length) {
  if (!inTimeWindow(state.broadcast.windowStart, state.broadcast.windowEnd)) {
    logs.push('broadcast: outside time window');
  } else {
  const intervalMs = Math.max(0.1, Number(state.broadcast.intervalMin) || 3) * 60 * 1000;
  if (now - (state.broadcast.lastSendAt || 0) >= intervalMs) {
    try {
      let chats;
      try { chats = await api.call(this, 'GET', 'getChats', { count: '500' }); }
      catch (e) { chats = await api.call(this, 'POST', 'getChats', { count: 500 }); }
      if (!Array.isArray(chats)) chats = [];
      let groups = chats
        .filter((c) => c && (c.type === 'group' || String(c.id || '').endsWith('@g.us')))
        .map((c) => c.id)
        .filter(Boolean);
      const bl = new Set(state.blacklist || []);
      groups = groups.filter((g) => !bl.has(g));

      // min-uye filter (best-effort for next candidate)
      const minUye = Number(state.filters?.minUye || 0);
      const eligible = [];
      for (const gid of groups) {
        if (eligible.length >= 30) break; // limit lookups per tick
        if (minUye <= 0) { eligible.push(gid); continue; }
        try {
          const data = await api.call(this, 'POST', 'getGroupData', { groupId: gid });
          const size = typeof data.size === 'number' ? data.size : (data.participants || []).length;
          if (size >= minUye) eligible.push(gid);
        } catch (e) {}
      }
      const list = eligible.length ? eligible : (minUye > 0 ? [] : groups);
      if (list.length) {
        if (state.broadcast.index >= list.length) {
          state.broadcast.index = 0;
          state.broadcast.cycle = (state.broadcast.cycle || 0) + 1;
        }
        const target = list[state.broadcast.index];
        const tIdx = (Number(state.broadcast.textIndex) || 0) % bTexts.length;
        const message = bTexts[tIdx];
        await api.call(this, 'POST', 'sendMessage', { chatId: target, message });
        state.broadcast.text = message;
        state.broadcast.textIndex = (tIdx + 1) % bTexts.length;
        state.broadcast.index += 1;
        state.broadcast.sent += 1;
        state.broadcast.lastSendAt = now;
        state.stats.broadcastSent = (state.stats.broadcastSent || 0) + 1;
        logs.push(`broadcast -> ${target} text#${tIdx + 1}/${bTexts.length}`);
        await pushLog.call(this, state, 'broadcast', `grup ${target} | metin ${tIdx + 1}/${bTexts.length} | #${state.broadcast.sent}`);
      } else {
        logs.push('broadcast: no eligible groups');
        state.broadcast.lastSendAt = now;
      }
    } catch (e) {
      logs.push(`broadcast error: ${e.message || e}`);
      state.broadcast.lastSendAt = now;
      await pushLog.call(this, state, 'error', `broadcast: ${e.message || e}`);
    }
  }
  } // time window
}

// --- DM worker ---
if (state.dm?.running && Array.isArray(state.dm.queue) && state.dm.queue.length) {
  if (!inTimeWindow(state.dm.windowStart, state.dm.windowEnd)) {
    logs.push('dm: outside time window');
  } else {
  const intervalMs = Math.max(0.1, Number(state.dm.intervalMin) || 3) * 60 * 1000;
  if (now - (state.dm.lastSendAt || 0) >= intervalMs) {
    if (state.dm.index >= state.dm.queue.length) {
      state.dm.running = false;
      logs.push('dm finished');
    } else {
      const target = state.dm.queue[state.dm.index];
      try {
        await api.call(this, 'POST', 'sendMessage', { chatId: target, message: state.dm.text });
        state.dm.sent += 1;
        state.stats.dmSent = (state.stats.dmSent || 0) + 1;
        logs.push(`dm -> ${target}`);
        await pushLog.call(this, state, 'dm', `dm ${target} | #${state.dm.sent}`);
      } catch (e) {
        state.dm.failed += 1;
        logs.push(`dm fail ${target}: ${e.message || e}`);
        await pushLog.call(this, state, 'error', `dm fail ${target}: ${e.message || e}`);
      }
      state.dm.index += 1;
      state.dm.lastSendAt = now;
      if (state.dm.index >= state.dm.queue.length) {
        state.dm.running = false;
        await pushLog.call(this, state, 'stop', `DM bitti | sent ${state.dm.sent} fail ${state.dm.failed}`);
      }
    }
  }
  } // dm time window
}

// --- Mining worker: pull members from recent groups into target ---
if (state.mining?.running && state.mining.targetGroupId) {
  const intervalMs = 3 * 60 * 1000;
  if (now - (state.mining.lastAddAt || 0) >= intervalMs) {
    const dayKey = new Date().toISOString().slice(0, 10);
    if (state.mining.dayKey !== dayKey) {
      state.mining.dayKey = dayKey;
      state.mining.addedToday = 0;
    }
    try {
      let chats;
      try { chats = await api.call(this, 'GET', 'getChats', { count: '500' }); }
      catch (e) { chats = await api.call(this, 'POST', 'getChats', { count: 500 }); }
      if (!Array.isArray(chats)) chats = [];
      const sources = chats
        .filter((c) => c && (c.type === 'group' || String(c.id || '').endsWith('@g.us')))
        .map((c) => c.id)
        .filter((id) => id && id !== state.mining.targetGroupId && !(state.blacklist || []).includes(id))
        .slice(0, 5);
      let candidate = null;
      for (const sid of sources) {
        try {
          const data = await api.call(this, 'POST', 'getGroupData', { groupId: sid });
          const parts = (data.participants || []).map((p) => p.id).filter((id) => id && id.endsWith('@c.us'));
          candidate = parts.find(Boolean);
          if (candidate) break;
        } catch (e) {}
      }
      if (candidate) {
        try {
          await api.call(this, 'POST', 'addGroupParticipant', {
            groupId: state.mining.targetGroupId,
            participantChatId: candidate,
          });
          state.mining.addedToday += 1;
          state.mining.pending = Math.max(0, (state.mining.totalTarget || 0) - (state.mining.members || 0) - state.mining.addedToday);
          logs.push(`mining add ${candidate}`);
        } catch (e) {
          logs.push(`mining add fail: ${e.message || e}`);
        }
      } else {
        state.mining.pending = 0;
        logs.push('mining: no candidate');
      }
      try {
        const td = await api.call(this, 'POST', 'getGroupData', { groupId: state.mining.targetGroupId });
        state.mining.targetName = td.subject || state.mining.targetName;
        state.mining.members = typeof td.size === 'number' ? td.size : (td.participants || []).length;
      } catch (e) {}
      state.mining.lastAddAt = now;
      state.mining.durationMin = Math.round((now - (state.mining.startedAt || now)) / 60000);
    } catch (e) {
      logs.push(`mining error: ${e.message || e}`);
      state.mining.lastAddAt = now;
    }
  }
}

saveState(state);
return [{ json: { ok: true, logs, at: now } }];
'''.replace('__STATE_PATH__', STATE_PATH)


def wf_command():
    wid = "7e4cfc9c-fce6-417b-bec1-e938275b944b"
    return {
        "name": "Ototext Bot — Prefix Komutlar",
        "active": False,
        "id": wid,
        "versionId": str(uuid.uuid4()),
        "nodes": [
            {
                "parameters": {
                    "content": "## Ototext ! komut botu\nPrefix: `!`\nState: `/workspace/data/ototext-state.json`\nWorker her 1 dk yayın/DM/mining işler.\nBot numarası otomatik admin.",
                    "height": 320,
                    "width": 400,
                    "color": 5,
                },
                "id": "sticky-bot",
                "name": "Ototext",
                "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1,
                "position": [-420, 160],
            },
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "ototext-bot",
                    "responseMode": "onReceived",
                    "options": {},
                },
                "id": "webhook-bot",
                "name": "Green API Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 360],
                "webhookId": "ototext-bot-webhook",
            },
            {
                "parameters": {"jsCode": COMMAND_JS},
                "id": "handle-cmd",
                "name": "Handle ! Commands",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [280, 360],
            },
            {
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                        "conditions": [{
                            "id": "has-reply",
                            "leftValue": "={{ $json.reply }}",
                            "rightValue": "",
                            "operator": {"type": "string", "operation": "notEmpty"},
                        }],
                        "combinator": "and",
                    },
                    "options": {},
                },
                "id": "if-reply",
                "name": "Has Reply?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.2,
                "position": [540, 360],
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "=https://api.green-api.com/waInstance{{ $json.instanceId || $env.ID_INSTANCE }}/sendMessage/{{ $json.apiToken || $env.API_TOKEN }}",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ chatId: $json.chatId, message: $json.reply }) }}",
                    "options": {"timeout": 30000},
                },
                "id": "http-reply",
                "name": "Reply sendMessage",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [820, 280],
                "onError": "continueRegularOutput",
            },
        ],
        "connections": {
            "Green API Webhook": {"main": [[{"node": "Handle ! Commands", "type": "main", "index": 0}]]},
            "Handle ! Commands": {"main": [[{"node": "Has Reply?", "type": "main", "index": 0}]]},
            "Has Reply?": {
                "main": [
                    [{"node": "Reply sendMessage", "type": "main", "index": 0}],
                    [],
                ]
            },
        },
        "pinData": {},
        "settings": {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"},
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True},
    }


def wf_worker():
    return {
        "name": "Ototext Bot — Worker",
        "active": False,
        "id": str(uuid.uuid4()),
        "versionId": str(uuid.uuid4()),
        "nodes": [
            {
                "parameters": {
                    "content": "## Ototext Worker\nHer 1 dakikada:\n- !otox yayını\n- !dm kuyruğu\n- !mining ekleme\nState dosyasını okur/yazar.",
                    "height": 260,
                    "width": 360,
                    "color": 4,
                },
                "id": "sticky-worker",
                "name": "Worker Info",
                "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1,
                "position": [-360, 200],
            },
            {
                "parameters": {
                    "rule": {
                        "interval": [{"field": "minutes", "minutesInterval": 1}]
                    }
                },
                "id": "sched-worker",
                "name": "Every Minute",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 360],
            },
            {
                "parameters": {"jsCode": WORKER_JS},
                "id": "worker-code",
                "name": "Process Queues",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [280, 360],
            },
        ],
        "connections": {
            "Every Minute": {"main": [[{"node": "Process Queues", "type": "main", "index": 0}]]},
        },
        "pinData": {},
        "settings": {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"},
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True},
    }


def main():
    out1 = ROOT / "n8n-workflows" / "ototext-bot-commands.json"
    out2 = ROOT / "n8n-workflows" / "ototext-bot-worker.json"
    w1, w2 = wf_command(), wf_worker()
    # persist worker id for imports
    (ROOT / "data" / "worker-workflow-id.txt").write_text(w2["id"] + "\n")
    out1.write_text(json.dumps(w1, indent=2, ensure_ascii=False) + "\n")
    out2.write_text(json.dumps(w2, indent=2, ensure_ascii=False) + "\n")
    print("wrote", out1)
    print("wrote", out2, "id=", w2["id"])


if __name__ == "__main__":
    main()
