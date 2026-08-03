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
    broadcast: { running: false, text: '', intervalMin: 3, index: 0, sent: 0, lastSendAt: 0, startedAt: 0, cycle: 0 },
    dm: { running: false, text: '', groupId: '', intervalMin: 3, queue: [], index: 0, sent: 0, failed: 0, lastSendAt: 0, startedAt: 0 },
    mining: { running: false, targetGroupId: '', targetName: '', members: 0, addedToday: 0, pending: 0, totalTarget: 0, durationMin: 0, startedAt: 0, lastAddAt: 0, dayKey: '' },
    filters: { minUye: 0 },
    blacklist: [],
    invites: [],
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
  return s;
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

async function api(method, endpoint, body) {
  const instance = $env.ID_INSTANCE;
  const token = $env.API_TOKEN;
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

async function ensureBotAdmin(state, incomingWid) {
  const envAdmins = String($env.BOT_ADMINS || '')
    .split(/[,;\s]+/)
    .map((x) => normId(x))
    .filter(Boolean);
  for (const a of envAdmins) {
    if (!state.admins.includes(a)) state.admins.push(a);
  }
  if (incomingWid) state.botWid = normId(incomingWid) || state.botWid;
  if (!state.botWid) {
    try {
      const settings = await api.call(this, 'GET', 'getSettings');
      state.botWid = settings.wid || settings.phone || '';
    } catch (e) {}
  }
  if (state.botWid && !state.admins.includes(state.botWid)) {
    state.admins.push(state.botWid);
  }
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
await ensureBotAdmin.call(this, state, body.instanceData?.wid);

// Capture invite links from any incoming message
if (body.typeWebhook === 'incomingMessageReceived') {
  const md = body.messageData || {};
  let text = '';
  if (md.typeMessage === 'textMessage') text = md.textMessageData?.textMessage || '';
  if (md.typeMessage === 'extendedTextMessage') text = md.extendedTextMessageData?.text || '';
  if (md.typeMessage === 'groupInviteMessage') {
    const d = md.groupInviteMessageData || {};
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
      saveState(state);
    }
  }
  for (const link of extractInviteLinks(text)) {
    if (!state.invites.some((x) => x.link === link)) {
      state.invites.unshift({ link, groupName: '', groupJid: '', from: body.senderData?.sender || '', at: Date.now() });
    }
  }
  state.invites = state.invites.slice(0, 200);
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
const chatId = body.senderData?.chatId || '';
const sender = body.senderData?.sender || chatId;

if (!isAdmin(state, sender, chatId)) {
  saveState(state);
  return [{ json: { chatId, reply: '⛔ Yetkisiz. Sadece adminler Ototext kullanabilir.' } }];
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
        `${prefix}otox (metin) — otomatik yayını başlat`,
        `${prefix}durdur / ${prefix}durum / ${prefix}sure N`,
        `${prefix}dm (metin). (grupId) — gruptakilere DM`,
        `${prefix}dm-durdur / ${prefix}dm-sure / ${prefix}dm-durum`,
        `${prefix}gruplar [sayfa] — 10’ar grup`,
        `${prefix}davetler — gelen davet linkleri`,
        `${prefix}filtre / ${prefix}min-uye N / ${prefix}temizlik`,
        `${prefix}black — kara liste menüsü`,
        `${prefix}mining — üye ekleme menüsü`,
        `${prefix}katil (link) / ${prefix}tumkatil (link...)`,
        `${prefix}karakter ayarla (isim)`,
        `${prefix}admin — admin menüsü`,
        `${prefix}prefix — prefix menüsü`,
        `${prefix}istatistik`,
      ].join('\n');
      break;
    }
    case 'otox': {
      if (!args) { reply = `Kullanım: ${prefix}otox (metin)`; break; }
      state.broadcast.running = true;
      state.broadcast.text = args;
      state.broadcast.index = 0;
      state.broadcast.sent = 0;
      state.broadcast.startedAt = Date.now();
      state.broadcast.lastSendAt = 0;
      reply = `▶️ Otomatik yayın başladı.\nSüre: ${state.broadcast.intervalMin} dk\nMetin: ${args.slice(0, 120)}`;
      break;
    }
    case 'durdur': {
      state.broadcast.running = false;
      reply = `⏹ Yayın durduruldu.\nGönderilen: ${state.broadcast.sent}`;
      break;
    }
    case 'durum': {
      const b = state.broadcast;
      reply = [
        '*📡 Yayın Durumu*',
        `Durum: ${b.running ? 'ÇALIŞIYOR' : 'DURDU'}`,
        `Süre aralığı: ${b.intervalMin} dk`,
        `Gönderilen: ${b.sent}`,
        `Index: ${b.index}`,
        `Metin: ${(b.text || '-').slice(0, 160)}`,
        `Min üye filtresi: ${state.filters.minUye || 0}`,
        `Blacklist: ${state.blacklist.length}`,
      ].join('\n');
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
      const data = await api.call(this, 'POST', 'getGroupData', { groupId: parsed.groupId });
      const participants = (data.participants || []).map((p) => p.id).filter(Boolean);
      const me = state.botWid;
      const queue = participants.filter((id) => id !== me && String(id).endsWith('@c.us'));
      state.dm = {
        running: true,
        text: parsed.text,
        groupId: parsed.groupId,
        intervalMin: state.dm.intervalMin || 3,
        queue,
        index: 0,
        sent: 0,
        failed: 0,
        lastSendAt: 0,
        startedAt: Date.now(),
      };
      reply = `✉️ DM başladı.\nGrup: ${data.subject || parsed.groupId}\nKuyruk: ${queue.length}\nAralık: ${state.dm.intervalMin} dk`;
      break;
    }
    case 'dm-durdur': {
      state.dm.running = false;
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
      reply = [
        '*📊 Ototext İstatistik*',
        `Komutlar: ${s.commands}`,
        `Yayın mesajı: ${s.broadcastSent}`,
        `DM: ${s.dmSent}`,
        `Katılma: ${s.joins}`,
        `Blacklist: ${state.blacklist.length}`,
        `Davet kaydı: ${state.invites.length}`,
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
return [{ json: { chatId, reply, command, sender } }];
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

async function api(method, endpoint, body) {
  const instance = $env.ID_INSTANCE;
  const token = $env.API_TOKEN;
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

const state = loadState();
if (!state) return [];
const logs = [];
const now = Date.now();

// --- Broadcast worker ---
if (state.broadcast?.running && state.broadcast.text) {
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
        await api.call(this, 'POST', 'sendMessage', { chatId: target, message: state.broadcast.text });
        state.broadcast.index += 1;
        state.broadcast.sent += 1;
        state.broadcast.lastSendAt = now;
        state.stats.broadcastSent = (state.stats.broadcastSent || 0) + 1;
        logs.push(`broadcast -> ${target}`);
      } else {
        logs.push('broadcast: no eligible groups');
        state.broadcast.lastSendAt = now;
      }
    } catch (e) {
      logs.push(`broadcast error: ${e.message || e}`);
      state.broadcast.lastSendAt = now;
    }
  }
}

// --- DM worker ---
if (state.dm?.running && Array.isArray(state.dm.queue) && state.dm.queue.length) {
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
      } catch (e) {
        state.dm.failed += 1;
        logs.push(`dm fail ${target}: ${e.message || e}`);
      }
      state.dm.index += 1;
      state.dm.lastSendAt = now;
      if (state.dm.index >= state.dm.queue.length) state.dm.running = false;
    }
  }
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
                    "url": "=https://api.green-api.com/waInstance{{ $env.ID_INSTANCE }}/sendMessage/{{ $env.API_TOKEN }}",
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
