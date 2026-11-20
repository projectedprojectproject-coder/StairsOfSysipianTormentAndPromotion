(function () {
'use strict';

/* =====================================================================
 * CONFIG - 모든 수치는 여기에 모은다.
 * "기획서 초안" = 기획서 04 주요 수치에 있는 값 (초안)
 * "기획서 미정" = 기획서에 수치가 없어 임시로 정한 값
 * ===================================================================== */
const CONFIG = {
  // ---- 기획서 초안 (04 주요 수치) ----
  maxHearts: 3,            // 하트 3
  maxDays: 30,             // 남은 일수 최대 30일
  startDays: 30,           // 시작 D-30 (05-2 요소 2)
  dayDuration: 0.33,       // 1일 = 약 0.33초
  stepDays: 1,             // 계단 1칸 +1일
  parryDays: 1.5,          // 패링 성공 +1.5일
  parryWindow: 0.20,       // 패링 판정 0.20초
  warnTime: 1.0,           // 공격 예고 1.0초 전 표시 (서류 비행 시간과 같음)
  promoteFloor: 20,        // 승급 20층
  promoteHeal: 1,          // 승급 시 하트 1 회복
  floorHeal: 1,            // 플레이테스트 반영: 새 층에 오를 때마다 하트 1 회복 (최대 maxHearts)

  // ---- 기획서 미정 ----
  stairsPerFloor: 6,       // 기획서 미정: 한 층당 계단 수
  comboStep2: 3,           // 기획서 미정: 연속 패링 몇 회에 x2
  comboStep3: 6,           // 기획서 미정: 연속 패링 몇 회에 x3
  stepPoints: 10,          // 기획서 미정: 계단 1칸 점수 (콤보 배수 적용)
  parryPoints: 50,         // 기획서 미정: 패링 성공 점수 (콤보 배수 적용)
  floorPoints: 100,        // 기획서 미정: 층 도달 점수 (콤보 배수 적용)
  drainStart: 1.0,         // 기획서 미정: 1층 일수 감소 배속
  drainEnd: 1.35,          // 기획서 미정: 20층 일수 감소 배속 (구간 안에서 선형 증가)
  attackIntervalStart: 2.4,// 기획서 미정: 1층 서류 투척 평균 간격(초)
  attackIntervalEnd: 1.1,  // 기획서 미정: 20층 서류 투척 평균 간격(초)
  attackJitter: 0.2,       // 기획서 미정: 간격 무작위 폭(±비율)
  minAttackGap: 0.8,       // 기획서 미정: 공격 도착 사이 최소 간격(초)
  firstAttackDelay: 3.0,   // 기획서 미정: 첫 공격까지 유예(초). 튜토리얼 대신 숨 돌릴 시간
  parryCooldown: 0.15,     // 기획서 미정: 패링 종료 후 재입력 대기(연타 방지)
  tenseFloor: 11,          // 기획서 미정: bgm_loop -> bgm_loop_tense(불협화음) 전환 층
  stairRunMax: 4,          // 기획서 미정: 같은 방향 계단 최대 연속 수
  stairKeepProb: 0.5,      // 기획서 미정: 같은 방향이 이어질 확률
  endDelay: 1.0,           // 기획서 미정: 종료 연출 후 결과 화면까지(초)
  botStepInterval: 0.19,   // bot=1 자동 이동 간격(초)
  botParryLead: 0.10,      // bot=1 도착 몇 초 전에 패링을 누를지

  // ---- 표현 ----
  stepW: 22,               // 계단 한 칸의 가로 이동(px)
  stepH: 12,               // 계단 한 칸의 세로 이동(px)
  showRivalCameo: true,    // 05-3 요소 5 경쟁 사원 장식: 경쟁 사원이 공격하기 전 층(rivalFromFloor 미만)에서만 배치
  rivalFromFloor: 11,      // 결정(2026-11-19): 기획서상 21층 위협인 경쟁 사원을 PoC 11층부터 미리 등장
  rivalShare: 0.4,         // 기획서 미정: 11층부터 공격 중 경쟁 사원 비율
  rivalWalk: 0.6,          // 기획서 미정: 화면 끝에서 걸어 들어오는 시간(초). 이후 예고 1.0초 뒤 근접 공격
  bgmVolume: 0.45,
  ambVolume: 0.15,         // 환경음은 낮은 볼륨 (03)
  sfxVolume: 0.8,
  rankNames: ['사원', '대리', '과장', '간부', 'CEO'],
  zoneNames: ['파티션 사무실', '개방형 오피스', '텅 빈 회의실', '임원층', 'CEO실'],
};

const PAL = { gray: '#5A5F66', green: '#8A9A5B', red: '#A13D3D', bg: '#1E1F22', text: '#E8E6DF' };
const RANK_COLORS = [PAL.gray, PAL.green, PAL.red, PAL.text, PAL.text];
const W = 320, H = 180;
const STEP = 1 / 60;
const ONCE = new Set(['step', 'parry_left', 'parry_right', 'hit', 'box_exit', 'proud', 'attack', 'leave']);

const params = new URLSearchParams(location.search);
const BOT = params.get('bot') === '1';
const MUTE_PARAM = params.get('mute') === '1';
let SEED = params.has('seed') ? parseInt(params.get('seed'), 10) : NaN;
if (!isFinite(SEED)) SEED = (Date.now() & 0x7fffffff);

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;

/* ---------------------------------------------------------------------
 * 시험용 장치
 * ------------------------------------------------------------------- */
const assetErrors = [];
const logArr = [];
const S = window.__stairs = {
  ready: false, screen: 'title', floor: 1, rank: CONFIG.rankNames[0], hearts: CONFIG.maxHearts,
  days: CONFIG.startDays, score: 0, maxMult: 1, steps: 0,
  assetErrors: assetErrors, audioFormat: 'none', log: logArr,
};
function log(msg) {
  logArr.push((run ? run.time.toFixed(2) : '0.00') + ' ' + msg);
  if (logArr.length > 500) logArr.shift();
}

/* ---------------------------------------------------------------------
 * 캔버스
 * ------------------------------------------------------------------- */
// 에셋 밀도: 2면 논리 해상도(320x180)의 2배로 그린 픽셀 아트를 절반 크기로 그린다 (sprite_definition.pixel_scale)
const PX = (window.SPRITE_DEF && window.SPRITE_DEF.pixel_scale) || 1;
const canvas = document.getElementById('game');
let ctx = canvas.getContext('2d');
let scale = 1;
function resize() {
  // 아트 픽셀이 화면 픽셀에 딱 맞도록 배율을 PX의 배수로 고른다 (창이 너무 작으면 1배)
  const k = Math.floor(Math.min(window.innerWidth / (W * PX), window.innerHeight / (H * PX)));
  scale = k >= 1 ? k * PX : Math.max(1, Math.floor(Math.min(window.innerWidth / W, window.innerHeight / H)));
  canvas.width = W * scale; canvas.height = H * scale;
  canvas.style.width = (W * scale) + 'px'; canvas.style.height = (H * scale) + 'px';
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.imageSmoothingEnabled = false;
}
window.addEventListener('resize', resize);
resize();

/* ---------------------------------------------------------------------
 * 에셋 로딩 (실패해도 멈추지 않음)
 * ------------------------------------------------------------------- */
const DEF = window.SPRITE_DEF || null;
if (!DEF) assetErrors.push('SPRITE_DEF:missing');
const D = DEF || { sprites: {}, images: {}, sounds: {} };
const ASSET_DIR = (D.assets_dir || 'assets').replace(/\/$/, '');
const SPRITE_IDS = ['player', 'rival', 'projectiles', 'warning', 'stairs', 'hud_icons'];
const IMAGE_IDS = ['bg_zone1', 'bg_zone2', 'bg_zone3', 'bg_zone4', 'bg_zone5', 'title_bg', 'logo'];
const SOUND_IDS = ['bgm_loop', 'bgm_loop_tense', 'amb_office', 'sfx_step', 'sfx_parry', 'sfx_hit', 'sfx_warning', 'sfx_promote', 'sfx_gameover', 'sfx_click'];
const A = { sprites: {}, images: {} };
let pending = 0;
let assetsReady = false;
function assetDone() {
  pending--;
  if (pending <= 0) { assetsReady = true; }
}
function loadImage(kind, id, def, store) {
  if (!def || !def.file) { assetErrors.push(kind + ':' + id + (def ? ':no-file' : ':no-def')); return; }
  const rec = { img: new Image(), ok: false, def: def, fw: def.frame_w || 0, fh: def.frame_h || 0 };
  store[id] = rec;
  pending++;
  rec.img.onload = function () {
    rec.ok = true;
    if (kind === 'sprite' && !(rec.fw > 0 && rec.fh > 0)) { rec.ok = false; assetErrors.push('sprite:' + id + ':no-frame-size'); }
    assetDone();
  };
  rec.img.onerror = function () { assetErrors.push(kind + ':' + id + ':' + def.file); assetDone(); };
  rec.img.src = ASSET_DIR + '/' + def.file;
}
SPRITE_IDS.forEach(function (id) { loadImage('sprite', id, D.sprites && D.sprites[id], A.sprites); });
IMAGE_IDS.forEach(function (id) { loadImage('image', id, D.images && D.images[id], A.images); });
if (pending === 0) assetsReady = true;
setTimeout(function () { assetsReady = true; }, 8000);

function rowOf(def, variant) {
  const v = def.variants;
  if (!v) return 0;
  if (Array.isArray(v)) { const i = v.indexOf(variant); return i < 0 ? 0 : i; }
  return (variant in v) ? v[variant] : 0;
}

/* drawSprite: 로드 실패 시 색 사각형(fallback) */
function drawSprite(id, variant, anim, t, x, y, o) {
  o = o || {};
  const sc = o.scale || 1;
  const rec = A.sprites[id];
  const usable = !!(rec && rec.ok && rec.fw > 0 && rec.fh > 0);
  let dw, dh;
  if (usable) { dw = o.dw || rec.fw * sc / PX; dh = o.dh || rec.fh * sc / PX; }
  else { dw = o.dw || (o.fw || 10) * sc; dh = o.dh || (o.fh || 10) * sc; }
  let dx = x, dy = y;
  const anc = o.anchor || 'bc';
  if (anc === 'bc') { dx = x - dw / 2; dy = y - dh; }
  else if (anc === 'c') { dx = x - dw / 2; dy = y - dh / 2; }
  else if (anc === 'tc') { dx = x - dw / 2; }
  dx = Math.round(dx * PX) / PX; dy = Math.round(dy * PX) / PX;
  if (!usable) {
    if (!o.nofb) { ctx.fillStyle = o.color || PAL.gray; ctx.fillRect(dx, dy, Math.round(dw), Math.round(dh)); }
    return false;
  }
  const row = rowOf(rec.def, variant);
  const an = rec.def.animations && rec.def.animations[anim];
  let col = 0;
  if (an && an.frames && an.frames.length) {
    let n = Math.floor(Math.max(0, t) * (an.fps || 1));
    if (ONCE.has(anim)) n = Math.min(n, an.frames.length - 1); else n = n % an.frames.length;
    col = an.frames[n];
  }
  if (o.flip) {
    ctx.save();
    ctx.translate(dx + dw, dy); ctx.scale(-1, 1);
    ctx.drawImage(rec.img, col * rec.fw, row * rec.fh, rec.fw, rec.fh, 0, 0, dw, dh);
    ctx.restore();
  } else {
    ctx.drawImage(rec.img, col * rec.fw, row * rec.fh, rec.fw, rec.fh, dx, dy, dw, dh);
  }
  return true;
}
function drawImg(id, x, y, w, h, fallback) {
  const rec = A.images[id];
  if (rec && rec.ok) { ctx.drawImage(rec.img, x, y, w, h); return true; }
  if (fallback) { ctx.fillStyle = fallback; ctx.fillRect(x, y, w, h); }
  return false;
}
function spScale(id, maxH) {
  const rec = A.sprites[id];
  if (!rec || !rec.ok) return 2;
  return Math.max(1, Math.floor(maxH / (rec.fh / PX)));
}

/* ---------------------------------------------------------------------
 * 사운드 (첫 입력 이후 재생, ogg 불가 시 mp3)
 * ------------------------------------------------------------------- */
const Snd = {
  unlocked: false, muted: MUTE_PARAM, vol: 1, format: 'none', loops: {}, pools: {}, rr: {},
};
(function detectFormat() {
  try {
    const a = document.createElement('audio');
    if (a.canPlayType('audio/ogg; codecs="vorbis"')) Snd.format = 'ogg';
    else if (a.canPlayType('audio/mpeg')) Snd.format = 'mp3';
  } catch (e) { Snd.format = 'none'; }
  S.audioFormat = Snd.format;
})();
function makeAudio(id) {
  if (Snd.format === 'none') return null;
  const d = D.sounds && D.sounds[id];
  if (!d || !d.files) { assetErrors.push('sound:' + id + (d ? ':no-files' : ':no-def')); return null; }
  const order = Snd.format === 'mp3' ? ['mp3', 'ogg'] : ['ogg', 'mp3'];
  const srcs = [];
  order.forEach(function (k) { if (d.files[k]) srcs.push(ASSET_DIR + '/' + d.files[k]); });
  if (!srcs.length) { assetErrors.push('sound:' + id + ':no-files'); return null; }
  const a = new Audio();
  a.preload = 'auto'; a.loop = !!d.loop;
  let i = 0;
  a.addEventListener('error', function () {
    if (i + 1 < srcs.length) { i++; a.src = srcs[i]; }
    else { a._failed = true; assetErrors.push('sound:' + id + ':' + srcs[i]); }
  });
  a.src = srcs[0];
  return a;
}
function loopEl(id) {
  if (!(id in Snd.loops)) Snd.loops[id] = makeAudio(id);
  return Snd.loops[id];
}
function sfx(id) {
  if (!Snd.unlocked || Snd.muted) return;
  try {
    if (!Snd.pools[id]) { Snd.pools[id] = [makeAudio(id), makeAudio(id), makeAudio(id)]; Snd.rr[id] = 0; }
    const pool = Snd.pools[id];
    const a = pool[Snd.rr[id] = (Snd.rr[id] + 1) % pool.length];
    if (!a || a._failed) return;
    a.volume = clamp(CONFIG.sfxVolume * Snd.vol, 0, 1);
    try { a.currentTime = 0; } catch (e) {}
    const p = a.play(); if (p && p.catch) p.catch(function () {});
  } catch (e) {}
}
let audioKey = null, audioSyncT = 0;
function desiredBgm() {
  if (screen === 'result') return null;
  if ((screen === 'play' || screen === 'pause') && run && run.floor >= CONFIG.tenseFloor) return 'bgm_loop_tense';
  return 'bgm_loop';
}
function syncAudio(force) {
  if (!Snd.unlocked) return;
  const key = desiredBgm() + '|' + Snd.muted + '|' + Snd.vol + '|' + (screen === 'pause');
  if (!force && key === audioKey && time - audioSyncT < 1) return;
  audioKey = key; audioSyncT = time;
  const want = {};
  if (!Snd.muted) {
    const b = desiredBgm();
    if (b) want[b] = CONFIG.bgmVolume * (screen === 'pause' ? 0.4 : 1);
    want.amb_office = CONFIG.ambVolume;
  }
  ['bgm_loop', 'bgm_loop_tense', 'amb_office'].forEach(function (id) {
    const a = loopEl(id);
    if (!a || a._failed) return;
    if (id in want) {
      a.volume = clamp(want[id] * Snd.vol, 0, 1);
      if (a.paused) { const p = a.play(); if (p && p.catch) p.catch(function () {}); }
    } else if (!a.paused) a.pause();
  });
}
function unlockAudio() {
  if (Snd.unlocked) return;
  Snd.unlocked = true;
  syncAudio(true);
}

/* ---------------------------------------------------------------------
 * 저장
 * ------------------------------------------------------------------- */
const save = { floor: 1, score: 0 };
try {
  save.floor = parseInt(localStorage.getItem('stairs_best_floor'), 10) || 1;
  save.score = parseInt(localStorage.getItem('stairs_best_score'), 10) || 0;
} catch (e) {}
function writeSave() {
  try {
    localStorage.setItem('stairs_best_floor', String(save.floor));
    localStorage.setItem('stairs_best_score', String(save.score));
  } catch (e) {}
}

/* ---------------------------------------------------------------------
 * 상태
 * ------------------------------------------------------------------- */
let screen = 'title';
let time = 0;
let focus = 0;
let run = null;
let result = null;
let resultLock = 0;
let settingsOpen = false;
let helpOpen = false; // 조작법 화면
let runCount = 0;
let toastText = '', toastUntil = 0;
const padUntil = [0, 0, 0, 0]; // ←, →, Q, E 키 아이콘 발광
let st = null; // 계단 생성기

function newStairs(seed) {
  st = { rng: mulberry32(seed ^ 0x9e3779b1), dirs: [], x: [0], runLen: 0 };
}
function ensureStairs(n) {
  while (st.dirs.length < n) {
    let d;
    if (st.dirs.length === 0) { d = st.rng() < 0.5 ? -1 : 1; st.runLen = 1; }
    else {
      const last = st.dirs[st.dirs.length - 1];
      if (st.runLen >= CONFIG.stairRunMax || st.rng() >= CONFIG.stairKeepProb) { d = -last; st.runLen = 1; }
      else { d = last; st.runLen++; }
    }
    st.dirs.push(d);
    st.x.push(st.x[st.x.length - 1] + d * CONFIG.stepW);
  }
}
function dirAt(i) { ensureStairs(i + 1); return st.dirs[i]; }
function stairX(i) { ensureStairs(i + 1); return st.x[i]; }
function floorOfSteps(n) { return 1 + Math.floor(n / CONFIG.stairsPerFloor); }
function zoneOf(f) { return f <= 20 ? 1 : f <= 40 ? 2 : f <= 60 ? 3 : f <= 99 ? 4 : 5; }

function startRun() {
  const seed = SEED + runCount; runCount++;
  newStairs(seed);
  run = {
    seed: seed, rng: mulberry32(seed), decor: mulberry32(seed ^ 0x5bd1e995),
    time: 0, steps: 0, floor: 1, rankIdx: 0,
    hearts: CONFIG.maxHearts, days: CONFIG.startDays,
    score: 0, combo: 0, mult: 1, maxMult: 1, maxCombo: 0, parries: 0,
    nextAttack: CONFIG.firstAttackDelay, lastImpact: -9,
    projs: [], sparks: [], texts: [], leavers: [],
    parryStart: [-9, -9], parryEnd: [-9, -9], parryCd: [0, 0],
    hitTimer: 0, stepTimer: 0, shake: 0, flash: 0,
    pvx: 0, pvy: 0, camX: 0, camY: 0,
    facing: dirAt(0), animState: '', animStart: 0,
    botT: 0, ended: null, endTimer: 0, rivalIdx: 8,
  };
  screen = 'play'; focus = 0; settingsOpen = false;
  log('run start seed=' + seed);
}

/* ---------------------------------------------------------------------
 * 게임 규칙
 * ------------------------------------------------------------------- */
function diffT(r) { return clamp((r.floor - 1) / (CONFIG.promoteFloor - 1), 0, 1); }
function drainMult(r) { return lerp(CONFIG.drainStart, CONFIG.drainEnd, diffT(r)); }
function attackInterval(r) {
  const base = lerp(CONFIG.attackIntervalStart, CONFIG.attackIntervalEnd, diffT(r));
  return base * (1 + (r.rng() * 2 - 1) * CONFIG.attackJitter);
}
function addText(s, x, y, color) { run.texts.push({ s: s, x: x, y: y, t: 0, color: color || PAL.text }); }
function playerScreenX() { return Math.round(160 + (run.pvx - run.camX)); }
const PLAYER_Y = 128;

function keyStep(dir) {
  padUntil[dir < 0 ? 0 : 1] = time + 0.12;
  doStep(dir);
}
function keyParry(side) {
  padUntil[side < 0 ? 2 : 3] = time + 0.12;
  doParry(side);
}
function doStep(dir) {
  const r = run;
  if (!r || r.ended || screen !== 'play') return;
  const need = dirAt(r.steps);
  if (dir !== need) {
    log('wrong direction');
    r.facing = need;
    loseHeart('wrong');
    return;
  }
  r.steps++;
  r.days = Math.min(CONFIG.maxDays, r.days + CONFIG.stepDays);
  r.score += CONFIG.stepPoints * r.mult;
  r.stepTimer = 0.14;
  r.facing = dirAt(r.steps);
  sfx('sfx_step');
  const nf = floorOfSteps(r.steps);
  if (nf > r.floor) {
    r.floor = nf;
    r.score += CONFIG.floorPoints * r.mult;
    log('floor ' + nf);
    if (r.hearts < CONFIG.maxHearts) {  // 새 층 도착: 하트 회복 (층 표시와 한 줄로 보여 겹치지 않게)
      r.hearts = Math.min(CONFIG.maxHearts, r.hearts + CONFIG.floorHeal);
      addText(nf + 'F · 하트 +1', 160, 70, PAL.green);
      log('heart +1 (floor) hearts=' + r.hearts);
    } else {
      addText(nf + 'F', 160, 70, PAL.text);
    }
    if (nf >= CONFIG.promoteFloor) promote();
  }
}
function doParry(side) {
  const r = run;
  if (!r || r.ended || screen !== 'play') return;
  const s = side < 0 ? 0 : 1;
  if (r.time < r.parryCd[s]) return;
  r.parryStart[s] = r.time;
  r.parryEnd[s] = r.time + CONFIG.parryWindow;
  r.parryCd[s] = r.parryEnd[s] + CONFIG.parryCooldown;
}
function loseHeart(reason) {
  const r = run;
  r.hearts--; r.combo = 0; r.mult = 1;
  r.hitTimer = 0.35; r.shake = 0.25; r.flash = 0.35;
  sfx('sfx_hit');
  log('heart -1 (' + reason + ') hearts=' + r.hearts);
  if (r.hearts <= 0) { r.hearts = 0; sfx('sfx_gameover'); endRun('gameover', 'hearts'); }
}
function promote() {
  const r = run;
  r.hearts = Math.min(CONFIG.maxHearts, r.hearts + CONFIG.promoteHeal);
  r.rankIdx = 1;
  sfx('sfx_promote');
  log('promote -> ' + CONFIG.rankNames[1]);
  endRun('promote', 'floor20');
}
function endRun(kind, cause) {
  const r = run;
  r.ended = { kind: kind, cause: cause };
  r.endTimer = CONFIG.endDelay;
  r.projs.forEach(function (p) { p.done = true; });
  if (kind === 'gameover') log('gameover ' + cause);
}
function spawnAttack() {
  const r = run;
  const side = r.rng() < 0.5 ? -1 : 1;
  const rival = r.floor >= CONFIG.rivalFromFloor && r.rng() < CONFIG.rivalShare;
  let impact = r.time + CONFIG.warnTime + (rival ? CONFIG.rivalWalk : 0);
  if (impact - r.lastImpact < CONFIG.minAttackGap) impact = r.lastImpact + CONFIG.minAttackGap;
  r.lastImpact = impact;
  // 경쟁 사원: 걸어 들어와(enterT~spawnT) 멈춘 뒤 "!" 1.0초 후 근접 공격, 한 번 막으면 퇴장 (04, 05-3 요소 5)
  r.projs.push({ side: side, type: rival ? 'rival' : 'document', enterT: impact - CONFIG.warnTime - (rival ? CONFIG.rivalWalk : 0), spawnT: impact - CONFIG.warnTime, impactT: impact, done: false });
  if (rival) log('rival spawn');
  sfx('sfx_warning');
}
function botTick(dt) {
  const r = run;
  r.botT += dt;
  if (r.botT >= CONFIG.botStepInterval) { r.botT -= CONFIG.botStepInterval; keyStep(dirAt(r.steps)); }
  if (r.ended) return;
  r.projs.forEach(function (p) {
    if (p.done) return;
    const tti = p.impactT - r.time;
    const s = p.side < 0 ? 0 : 1;
    if (tti > 0 && tti <= CONFIG.botParryLead && r.time >= r.parryCd[s]) keyParry(p.side);
  });
}
function updatePlay(dt) {
  const r = run;
  r.time += dt;
  r.hitTimer = Math.max(0, r.hitTimer - dt);
  r.stepTimer = Math.max(0, r.stepTimer - dt);
  r.shake = Math.max(0, r.shake - dt);
  r.flash = Math.max(0, r.flash - dt);
  const tx = stairX(r.steps), ty = -r.steps * CONFIG.stepH;
  const k1 = Math.min(1, dt * 22);
  r.pvx += (tx - r.pvx) * k1; r.pvy += (ty - r.pvy) * k1;
  r.camX += (r.pvx - r.camX) * Math.min(1, dt * 8); r.camY = r.pvy;
  r.sparks.forEach(function (s) { s.x += s.vx * dt; s.y += s.vy * dt; s.vy += 120 * dt; s.t += dt; });
  r.sparks = r.sparks.filter(function (s) { return s.t < 0.4; });
  r.texts.forEach(function (t) { t.t += dt; t.y -= 14 * dt; });
  r.texts = r.texts.filter(function (t) { return t.t < 0.8; });
  r.leavers = r.leavers.filter(function (l) { return r.time - l.t0 < 0.5; });
  if (CONFIG.showRivalCameo && r.rivalIdx < r.steps - 3) r.rivalIdx = r.steps + 8 + Math.floor(r.decor() * 6);

  if (r.ended) {
    r.endTimer -= dt;
    if (r.endTimer <= 0) finishRun();
    return;
  }
  if (BOT) botTick(dt);
  if (r.ended) return;

  r.days -= dt / CONFIG.dayDuration * drainMult(r);
  if (r.days <= 0) { r.days = 0; sfx('sfx_gameover'); endRun('gameover', 'days'); return; }

  if (r.time >= r.nextAttack) { spawnAttack(); r.nextAttack = r.time + attackInterval(r); }

  for (let i = 0; i < r.projs.length; i++) {
    const p = r.projs[i];
    if (p.done || r.time < p.impactT) continue;
    p.done = true;
    if (p.type === 'rival') r.leavers.push({ side: p.side, t0: r.time });
    const s = p.side < 0 ? 0 : 1;
    if (r.parryStart[s] <= p.impactT && p.impactT <= r.parryEnd[s]) {
      r.parries++; r.combo++;
      r.mult = r.combo >= CONFIG.comboStep3 ? 3 : r.combo >= CONFIG.comboStep2 ? 2 : 1;
      r.maxMult = Math.max(r.maxMult, r.mult);
      r.maxCombo = Math.max(r.maxCombo, r.combo);
      r.days = Math.min(CONFIG.maxDays, r.days + CONFIG.parryDays);
      r.score += CONFIG.parryPoints * r.mult;
      sfx('sfx_parry');
      const px = playerScreenX() + p.side * 10;
      for (let k = 0; k < 8; k++) {
        const a = r.decor() * Math.PI * 2;
        r.sparks.push({ x: px, y: PLAYER_Y - 14, vx: Math.cos(a) * 50, vy: Math.sin(a) * 50 - 20, t: 0, color: k % 2 ? PAL.text : PAL.green });
      }
      addText('+' + CONFIG.parryDays, px, PLAYER_Y - 30, PAL.green);
      log('parry ok combo=' + r.combo + ' x' + r.mult);
    } else {
      loseHeart('attack');
      if (r.ended) break;
    }
  }
  r.projs = r.projs.filter(function (p) { return !p.done; });
}
function finishRun() {
  const r = run;
  const kind = r.ended.kind;
  const newBest = r.floor > save.floor || r.score > save.score;
  if (r.floor > save.floor) save.floor = r.floor;
  if (r.score > save.score) save.score = r.score;
  writeSave();
  result = {
    kind: kind, cause: r.ended.cause, floor: r.floor, rankIdx: r.rankIdx,
    score: r.score, maxMult: r.maxMult, maxCombo: r.maxCombo, newBest: newBest,
  };
  screen = 'result'; focus = 0; resultLock = 0.5;
  log('result ' + kind);
}

/* ---------------------------------------------------------------------
 * UI 보조
 * ------------------------------------------------------------------- */
function rect(x, y, w, h, c, a) {
  if (a !== undefined) ctx.globalAlpha = a;
  ctx.fillStyle = c; ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
  if (a !== undefined) ctx.globalAlpha = 1;
}
function frameRect(x, y, w, h, c) {
  rect(x, y, w, 1, c); rect(x, y + h - 1, w, 1, c); rect(x, y, 1, h, c); rect(x + w - 1, y, 1, h, c);
}
function txt(s, x, y, o) {
  o = o || {};
  ctx.font = (o.bold ? 'bold ' : '') + (o.size || 8) + 'px "Noto Sans KR", sans-serif';
  ctx.textAlign = o.align || 'left';
  ctx.textBaseline = o.base || 'top';
  x = Math.round(x); y = Math.round(y);
  if (o.shadow !== false) { ctx.fillStyle = PAL.bg; ctx.fillText(s, x + 1, y + 1); }
  ctx.fillStyle = o.color || PAL.text;
  ctx.fillText(s, x, y);
}
function btn(id, label, x, y, w, h, fn, size) { return { id: id, label: label, x: x, y: y, w: w, h: h, fn: fn, size: size }; }

function openSettings() { settingsOpen = true; focus = 0; }
function closeSettings() { settingsOpen = false; focus = 0; }
function openHelp() { helpOpen = true; focus = 0; }
function closeHelp() { helpOpen = false; focus = 0; }
function toast(s) { toastText = s; toastUntil = time + 2.5; }
function toTitle() { screen = 'title'; focus = 0; settingsOpen = false; helpOpen = false; }

function getButtons() {
  if (helpOpen) return [btn('close', '닫기', 110, 146, 100, 14, closeHelp)];
  if (settingsOpen) {
    return [
      btn('snd', Snd.muted ? '꺼짐' : '켜짐', 170, 42, 88, 14, function () { Snd.muted = !Snd.muted; syncAudio(true); }),
      btn('vdn', '-', 170, 60, 24, 14, function () { Snd.vol = clamp(Math.round((Snd.vol - 0.1) * 10) / 10, 0, 1); syncAudio(true); }),
      btn('vup', '+', 234, 60, 24, 14, function () { Snd.vol = clamp(Math.round((Snd.vol + 0.1) * 10) / 10, 0, 1); syncAudio(true); }),
      btn('fs', '전체화면', 170, 78, 88, 14, function () {
        try {
          if (document.fullscreenElement) document.exitFullscreen();
          else { const p = document.documentElement.requestFullscreen(); if (p && p.catch) p.catch(function () {}); }
        } catch (e) {}
      }),
      btn('help', '보기', 170, 104, 88, 14, openHelp),
      btn('close', '닫기', 110, 136, 100, 16, closeSettings),
    ];
  }
  switch (screen) {
    case 'title':
      return [
        Object.assign(btn('start', '시작하기', 122, 98, 76, 18, function () { screen = 'lobby'; focus = 0; }, 10), { tone: 'red' }),
        Object.assign(btn('settings', '', 298, 4, 18, 18, openSettings), { icon: 'gear' }),
      ];
    case 'lobby':
      return [
        btn('work', '업무 시작', 190, 104, 114, 24, startRun, 11),
        btn('back', '타이틀로', 190, 134, 114, 16, toTitle),
      ];
    case 'pause':
      return [
        btn('resume', '계속하기', 100, 66, 120, 14, function () { screen = 'play'; focus = 0; }),
        btn('help', '조작법', 100, 84, 120, 14, openHelp),
        btn('settings', '설정', 100, 102, 120, 14, openSettings),
        btn('main', '메인으로', 100, 120, 120, 14, function () { log('quit to title'); toTitle(); }),
      ];
    case 'result':
      return [
        btn('again', result && result.kind === 'promote' ? '1층부터 다시' : '다시 하기', 104, 134, 100, 18, startRun, 9),
        btn('share', '기록 공유', 212, 134, 100, 18, shareResult, 9),
        btn('lobby', '로비로', 104, 156, 100, 16, function () { screen = 'lobby'; focus = 0; }),
      ];
  }
  return [];
}
function activate(b) {
  if (!b) return;
  sfx('sfx_click');
  b.fn();
}

/* ---------------------------------------------------------------------
 * 입력
 * ------------------------------------------------------------------- */
function menuMode() { return screen !== 'play' || settingsOpen || helpOpen; }
window.addEventListener('keydown', function (e) {
  unlockAudio();
  const c = e.code;
  if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Space', 'Tab'].indexOf(c) >= 0) e.preventDefault();
  if (e.repeat) return;

  if (c === 'Escape') {
    if (helpOpen) { closeHelp(); return; }
    if (settingsOpen) { closeSettings(); return; }
    if (screen === 'play') { screen = 'pause'; focus = 0; return; }
    if (screen === 'pause') { screen = 'play'; focus = 0; return; }
    if (screen === 'lobby') { toTitle(); return; }
    if (screen === 'result') { screen = 'lobby'; focus = 0; return; }
    return;
  }
  if (!menuMode()) {
    if (c === 'ArrowLeft') keyStep(-1);
    else if (c === 'ArrowRight') keyStep(1);
    else if (c === 'KeyQ') keyParry(-1);
    else if (c === 'KeyE') keyParry(1);
    return;
  }
  const bs = getButtons();
  if (!bs.length) return;
  if (c === 'ArrowUp' || c === 'ArrowLeft') focus = (focus + bs.length - 1) % bs.length;
  else if (c === 'ArrowDown' || c === 'ArrowRight' || c === 'Tab') focus = (focus + 1) % bs.length;
  else if (c === 'Enter' || c === 'NumpadEnter' || c === 'Space') {
    if (screen === 'result' && resultLock > 0) return;
    activate(bs[focus % bs.length]);
  }
});
function logicalPos(e) {
  const r = canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left) / r.width * W, y: (e.clientY - r.top) / r.height * H };
}
function hitButton(p) {
  const bs = getButtons();
  for (let i = 0; i < bs.length; i++) {
    const b = bs[i];
    if (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) return i;
  }
  return -1;
}
canvas.addEventListener('mousemove', function (e) {
  if (!menuMode()) return;
  const i = hitButton(logicalPos(e));
  if (i >= 0) focus = i;
});
canvas.addEventListener('mousedown', function (e) {
  unlockAudio();
  canvas.focus();
  if (!menuMode()) return;
  const i = hitButton(logicalPos(e));
  if (i >= 0) {
    focus = i;
    if (screen === 'result' && resultLock > 0) return;
    activate(getButtons()[i]);
  }
});
document.addEventListener('visibilitychange', function () {
  if (document.hidden && screen === 'play') { screen = 'pause'; focus = 0; }
});

/* ---------------------------------------------------------------------
 * 그리기 - 공통
 * ------------------------------------------------------------------- */
function drawButtons() {
  const bs = getButtons();
  if (focus >= bs.length) focus = 0;
  bs.forEach(function (b, i) {
    const f = i === focus;
    if (b.icon) {   // 아이콘만 있는 버튼 (타이틀의 톱니바퀴)
      rect(b.x, b.y, b.w, b.h, PAL.bg, f ? 0.9 : 0.6);
      frameRect(b.x, b.y, b.w, b.h, f ? PAL.text : PAL.gray);
      if (!drawSprite('hud_icons', 'default', b.icon, 0, b.x + (b.w - 12) / 2, b.y + (b.h - 12) / 2, { anchor: 'tl', dw: 12, dh: 12, nofb: true })) txt('설정', b.x + b.w / 2, b.y + b.h / 2, { align: 'center', base: 'middle', size: 6 });
      return;
    }
    const red = b.tone === 'red';
    rect(b.x, b.y, b.w, b.h, red ? (f ? '#B84545' : PAL.red) : (f ? PAL.green : PAL.gray));
    frameRect(b.x, b.y, b.w, b.h, f ? PAL.text : PAL.bg);
    if (red) frameRect(b.x + 1, b.y + 1, b.w - 2, b.h - 2, '#6E2626');
    txt(b.label, b.x + b.w / 2, b.y + b.h / 2 + 0.5, { align: 'center', base: 'middle', size: b.size || 8, color: f && !red ? PAL.bg : PAL.text, shadow: !f || red });
  });
}
function drawHeart(x, y, full) {
  const ok = drawSprite('hud_icons', 'default', full ? 'heart' : 'heart_empty', 0, x, y, { anchor: 'tl', dw: 12, dh: 12, nofb: true });
  if (!ok) { rect(x, y, 10, 10, full ? PAL.red : PAL.gray, full ? 1 : 0.5); }
}
function drawBadgeIcon(x, y, size) {
  const ok = drawSprite('hud_icons', 'default', 'badge', 0, x, y, { anchor: 'tl', dw: size, dh: size, nofb: true });
  if (!ok) rect(x, y, size, size, PAL.green);
}

/* ---------------------------------------------------------------------
 * 05-1 타이틀
 * ------------------------------------------------------------------- */
function drawTitle() {
  if (!drawImg('title_bg', 0, 0, W, H, PAL.bg)) {
    // 어두운 빌딩 숲 + 가운데 본사 꼭대기만 불빛
    const hs = [60, 90, 50, 110, 70, 130, 55, 95, 65];
    for (let i = 0; i < hs.length; i++) rect(i * 36 - 4, H - hs[i], 30, hs[i], PAL.gray, 0.35);
    rect(136, 40, 48, 140, PAL.gray, 0.6);
    rect(150, 52, 20, 10, PAL.text);
  }
  const lg = A.images.logo;
  if (lg && lg.ok) {
    const iw = lg.img.naturalWidth, ih = lg.img.naturalHeight;
    const s = Math.min(1 / PX, 280 / iw, 70 / ih);
    ctx.drawImage(lg.img, Math.round((W - iw * s) / 2), 34, iw * s, ih * s); // 05-1 컨셉: 본사 앞 가운데 명판
  } else {
    rect(50, 20, 220, 48, PAL.bg, 0.8);
    frameRect(50, 20, 220, 48, PAL.red);
    txt('승급의 계단', 160, 30, { align: 'center', size: 26, bold: true });
    txt('구조조정까지 D-30', 160, 58, { align: 'center', size: 8, color: PAL.green });
  }
  drawButtons();
  txt('v0.1 PoC · 승급의 계단 제작팀', 160, 172, { align: 'center', size: 6, color: PAL.gray });
}

/* ---------------------------------------------------------------------
 * 05-2 로비
 * ------------------------------------------------------------------- */
function drawLobby() {
  drawImg('bg_zone1', 0, 0, W, H, PAL.bg);
  rect(0, 0, W, H, PAL.bg, 0.72);
  // 1 현재 층수
  txt('1F', 16, 12, { size: 28, bold: true });
  txt('파티션 사무실 · 사원 구간', 16, 46, { size: 8, color: PAL.green });
  // 2 남은 일수
  rect(16, 64, 160, 28, PAL.bg, 0.7); frameRect(16, 64, 160, 28, PAL.gray);
  const ok = drawSprite('hud_icons', 'default', 'calendar', 0, 24, 72, { anchor: 'tl', dw: 12, dh: 12, nofb: true });
  if (!ok) rect(22, 70, 16, 16, PAL.gray);
  txt('구조조정까지 D-' + CONFIG.startDays, 44, 72, { size: 10, bold: true, color: PAL.text });
  // 3 사원증
  const rIdx = save.floor >= CONFIG.promoteFloor ? 1 : 0;
  rect(190, 12, 114, 84, PAL.text);
  rect(190, 12, 114, 16, RANK_COLORS[rIdx]);
  frameRect(190, 12, 114, 84, PAL.bg);
  drawBadgeIcon(194, 14, 12);
  txt('사원증', 210, 14, { size: 9, bold: true, color: rIdx === 0 ? PAL.text : PAL.bg, shadow: false });
  drawSprite('player', CONFIG.rankNames[rIdx], 'idle', time, 220, 92, { scale: spScale('player', 56), fw: 16, fh: 28, color: RANK_COLORS[rIdx] });
  txt('○○○', 196, 34, { size: 9, color: PAL.bg, shadow: false, bold: true });
  txt(CONFIG.rankNames[rIdx], 196, 48, { size: 8, color: PAL.bg, shadow: false });
  txt('총무팀', 196, 60, { size: 8, color: PAL.gray, shadow: false });
  // 5 누적 기록
  rect(16, 100, 160, 64, PAL.bg, 0.7); frameRect(16, 100, 160, 64, PAL.gray);
  txt('누적 기록', 24, 104, { size: 8, color: PAL.green, bold: true });
  txt('최고 ' + save.floor + 'F', 24, 118, { size: 9 });
  txt('최고 점수 ' + save.score, 24, 131, { size: 9 });
  txt('전체 랭킹 #-- (오프라인)', 24, 144, { size: 8, color: PAL.gray });
  // 4 업무 시작 + 뒤로
  drawButtons();
}

/* ---------------------------------------------------------------------
 * 05-3 플레이
 * ------------------------------------------------------------------- */
function playerAnim(r) {
  let s = 'idle';
  if (r.ended) s = r.ended.kind === 'promote' ? 'proud' : 'hit';
  else if (r.hitTimer > 0) s = 'hit';
  else if (r.time >= r.parryStart[0] && r.time < r.parryEnd[0]) s = 'parry_left';
  else if (r.time >= r.parryStart[1] && r.time < r.parryEnd[1]) s = 'parry_right';
  else if (r.stepTimer > 0) s = 'step';
  if (r.animState !== s) { r.animState = s; r.animStart = r.time; }
  return s;
}
function drawPlayWorld() {
  const r = run;
  const zone = zoneOf(r.floor);
  drawImg('bg_zone' + zone, 0, 0, W, H, PAL.bg);
  if (!A.images['bg_zone' + zone] || !A.images['bg_zone' + zone].ok) {
    // 아래로 흐르는 가로줄로 위로 오르는 느낌
    const off = (-r.camY) % 24;
    for (let y = -24; y < H + 24; y += 24) rect(0, y + off, W, 1, PAL.gray, 0.25);
  }
  rect(0, 0, W, H, PAL.bg, 0.15);

  const spf = CONFIG.stairsPerFloor;
  const RAIL = ['#4E5733', '#44484E', '#5C4F3B', '#5E2323', '#8A6A2E'][zone - 1];
  const PROPS = ['cooler', 'boxes', 'plant', 'cabinet'];
  // 층 바닥(콘크리트 슬래브)과 그 위 소품: 층이 바뀌는 칸 높이에 화면 끝까지 깐다
  for (let i = Math.floor((r.steps - 6) / spf) * spf; i <= r.steps + 14; i += spf) {
    if (i <= 0) continue;
    const sy = PLAYER_Y + (-i * CONFIG.stepH - r.camY);
    if (sy > H + 10 || sy < -40) continue;
    const h = (i * 2654435761) >>> 0, cx = 160 + (stairX(i) - r.camX);
    [-1, 1].forEach(function (side, k) {
      const px = cx + side * (64 + ((h >>> (k * 8)) % 50));
      drawSprite('props', 'default', PROPS[(h >>> (16 + k * 4)) % PROPS.length], 0, px, sy, { anchor: 'bc', fw: 16, fh: 24, nofb: true });
    });
    rect(0, sy, W, 7, '#4E5259'); rect(0, sy, W, 1, '#7B8088'); rect(0, sy + 7, W, 2, '#141518', 0.55);
  }
  // 계단 받침(stringer): 디딤판 아래를 계단 기울기대로 비스듬히 깎아, 아래가 뚫린 계단처럼 보이게 한다 (컨셉 05-3)
  const tileW = CONFIG.stepW * 2, tileH = CONFIG.stepH;
  const STR = ["#3A4226", "#33363C", "#463A2B", "#461A1A", "#5E4820"], STR_EDGE = ["#2C3320", "#26282C", "#352C20", "#341313", "#463618"];
  for (let i = r.steps + 14; i >= Math.max(0, r.steps - 6); i--) {
    const sx = 160 + (stairX(i) - r.camX);
    const sy = PLAYER_Y + (-i * CONFIG.stepH - r.camY);
    if (sy > H + 10 || sy < -30) continue;
    const d = Math.sign(stairX(i + 1) - stairX(i)) || 1, half = CONFIG.stepW / 2;
    for (let c = 0; c < half * 2 * PX; c++) {
      const x = sx - half + c / PX, u = Math.round((tileH * 0.6 - d * (x + 0.5 / PX - sx) * (tileH / (half * 2))) * PX) / PX;
      rect(x, sy + tileH, 1 / PX, u, STR[zone - 1]);
      rect(x, sy + tileH + u - 1 / PX, 1 / PX, 1 / PX, STR_EDGE[zone - 1]);
    }
  }
  // 계단 디딤판
  for (let i = r.steps + 14; i >= Math.max(0, r.steps - 6); i--) {
    const sx = 160 + (stairX(i) - r.camX);
    const sy = PLAYER_Y + (-i * CONFIG.stepH - r.camY);
    if (sy > H + 10 || sy < -10) continue;
    const landing = i % spf === 0;
    const ok = drawSprite('stairs', 'zone' + zone, 'tile', time, sx, sy, { anchor: 'tc', dw: tileW, dh: tileH, nofb: true });
    if (!ok) {
      rect(sx - tileW / 2, sy, tileW, tileH, landing ? PAL.red : PAL.gray);
      rect(sx - tileW / 2, sy, tileW, 2, landing ? PAL.text : PAL.green);
    }
    if (landing && i > 0) txt((i / spf + 1) + 'F', sx, sy + 8, { size: 6, align: 'center', color: PAL.text });
  }
  // 난간: 칸마다 기둥, 이웃 칸 기둥끼리 손잡이로 잇는다 (아트 픽셀 단위로 그려 계단처럼 각지게)
  for (let i = Math.max(0, r.steps - 6); i < r.steps + 14; i++) {
    const ax = 160 + (stairX(i) - r.camX), ay = PLAYER_Y + (-i * CONFIG.stepH - r.camY);
    const bx = 160 + (stairX(i + 1) - r.camX), by = ay - CONFIG.stepH;
    if (ay > H + 20 || ay < -20) continue;
    rect(ax - 0.5, ay - 12, 1, 12, RAIL, 0.9);
    const n = Math.max(1, Math.round(Math.max(Math.abs(bx - ax), Math.abs(by - ay)) * PX));
    for (let s = 0; s <= n; s++) rect(Math.round((ax + (bx - ax) * s / n) * PX) / PX - 0.5, Math.round((ay - 12 + (by - ay) * s / n) * PX) / PX, 1, 1 / PX * 2, RAIL);
  }
  // 경쟁 사원 (장식)
  if (CONFIG.showRivalCameo && r.floor < CONFIG.rivalFromFloor && r.rivalIdx >= r.steps - 3 && r.rivalIdx <= r.steps + 14) {
    const sx = 160 + (stairX(r.rivalIdx) - r.camX);
    const sy = PLAYER_Y + (-r.rivalIdx * CONFIG.stepH - r.camY);
    ctx.globalAlpha = 0.75;
    drawSprite('rival', 'default', 'walk', time, sx, sy + 1, { fw: 14, fh: 26, color: PAL.red, flip: dirAt(r.rivalIdx) < 0 });
    ctx.globalAlpha = 1;
  }
  // 플레이어
  const px = playerScreenX();
  const anim = playerAnim(r);
  const rc = RANK_COLORS[r.rankIdx];
  drawSprite('player', CONFIG.rankNames[r.rankIdx], anim, r.time - r.animStart, px, PLAYER_Y + 2,
    { fw: 16, fh: 28, color: rc, flip: r.facing < 0 && anim !== 'parry_left' && anim !== 'parry_right' });
  // 투척물 + 예고
  r.leavers.forEach(function (l) {
    const k = (r.time - l.t0) / 0.5;
    ctx.globalAlpha = clamp(1 - k, 0, 1);
    drawSprite('rival', 'default', 'leave', r.time - l.t0, px + l.side * 14 + l.side * k * 90, PLAYER_Y + 1, { fw: 14, fh: 26, color: PAL.red, flip: l.side < 0 });
    ctx.globalAlpha = 1;
  });
  r.projs.forEach(function (p) {
    if (p.type === 'rival') {
      const stand = px + p.side * 14, edge = p.side < 0 ? -16 : W + 16, left = p.impactT - r.time;
      let x = lerp(edge, stand, clamp((r.time - p.enterT) / CONFIG.rivalWalk, 0, 1)), anim = 'walk';
      if (left < 0.25) { x = stand - p.side * (0.25 - left) * 24; anim = 'attack'; }
      drawSprite('rival', 'default', anim, r.time - p.enterT, x, PLAYER_Y + 1, { fw: 14, fh: 26, color: PAL.red, flip: p.side > 0 });
      if (r.time >= p.spawnT) {
        const wk = drawSprite('warning', 'default', 'blink', r.time - p.spawnT, x, PLAYER_Y - 34, { anchor: 'c', fw: 8, fh: 12, nofb: true });
        if (!wk && Math.floor(time * 8) % 2 === 0) { rect(x - 5, PLAYER_Y - 41, 10, 14, PAL.red); txt('!', x, PLAYER_Y - 34, { align: 'center', base: 'middle', size: 10, bold: true, shadow: false }); }
      }
      return;
    }
    const prog = clamp((r.time - p.spawnT) / CONFIG.warnTime, 0, 1);
    const startX = p.side < 0 ? -16 : W + 16;
    const tx = px + p.side * 8;
    const x = lerp(startX, tx, prog);
    const y = PLAYER_Y - 16 - Math.sin(prog * Math.PI) * 6;
    drawSprite('projectiles', 'default', p.type, r.time - p.spawnT, x, y, { anchor: 'c', fw: 12, fh: 9, color: PAL.text, flip: p.side > 0 });
    const wx = clamp(x, 8, W - 8), wy = y - 16;
    const wk = drawSprite('warning', 'default', 'blink', r.time - p.spawnT, wx, wy, { anchor: 'c', fw: 8, fh: 12, nofb: true });
    if (!wk && Math.floor(time * 8) % 2 === 0) {
      rect(wx - 5, wy - 7, 10, 14, PAL.red);
      txt('!', wx, wy, { align: 'center', base: 'middle', size: 10, bold: true, shadow: false });
    }
  });
  // 효과
  r.sparks.forEach(function (s) { rect(s.x, s.y, 2, 2, s.color, 1 - s.t / 0.4); });
  r.texts.forEach(function (t) {
    ctx.globalAlpha = clamp(1 - t.t / 0.8, 0, 1);
    txt(t.s, t.x, t.y, { align: 'center', size: 9, bold: true, color: t.color });
    ctx.globalAlpha = 1;
  });
  if (r.flash > 0) rect(0, 0, W, H, PAL.red, clamp(r.flash / 0.35, 0, 1) * 0.35);
}
function plate(x, y, w, h) {   // 05-3 컨셉의 이중 테두리 명판
  rect(x, y, w, h, PAL.bg, 0.92); frameRect(x, y, w, h, '#9AA0A8'); frameRect(x + 2, y + 2, w - 4, h - 4, '#5A5F66');
}
function drawKeyCap(x, y, idx, iconName, label) {
  const lit = time < padUntil[idx];
  rect(x, y, 18, 18, lit ? PAL.green : PAL.bg, lit ? 1 : 0.85);
  frameRect(x, y, 18, 18, lit ? PAL.text : '#9AA0A8');
  const ok = drawSprite('hud_icons', 'default', iconName, time, x + 3, y + 3, { anchor: 'tl', dw: 12, dh: 12, nofb: true });
  if (!ok) txt(label, x + 11, y + 11, { align: 'center', base: 'middle', size: 10, bold: true, color: lit ? PAL.bg : PAL.text, shadow: false });
}
function drawHud() {
  const r = run;
  // 1 층수·직급 명판
  plate(6, 5, 86, 19);
  drawBadgeIcon(10, 9, 12);
  txt(r.floor + 'F · ' + CONFIG.rankNames[r.rankIdx], 56, 14.5, { align: 'center', base: 'middle', size: 9, bold: true });
  // 2 남은 일수 명판 + 하트
  const dayInt = Math.ceil(r.days);
  const low = r.days <= 7;
  plate(W - 92, 5, 86, 19);
  const ok = drawSprite('hud_icons', 'default', 'calendar', 0, W - 88, 9, { anchor: 'tl', dw: 12, dh: 12, nofb: true });
  if (!ok) rect(W - 88, 9, 12, 12, PAL.gray);
  txt('D-' + dayInt, W - 44, 14.5, { align: 'center', base: 'middle', size: 10, bold: true, color: low ? PAL.red : PAL.text });
  rect(W - 89, 21, 80 * clamp(r.days / CONFIG.maxDays, 0, 1), 1, low ? PAL.red : PAL.green);   // 일수 게이지
  for (let i = 0; i < CONFIG.maxHearts; i++) drawHeart(W - 8 - (CONFIG.maxHearts - i) * 13, 27, i < r.hearts);
  // 콤보 (가운데 위, 금색)
  if (r.combo > 0) {
    txt('×' + r.mult + ' COMBO', 160, 10, { align: 'center', size: 10, bold: true, color: '#E3B65C' });
    txt(r.combo + '연속', 160, 22, { align: 'center', size: 6, color: PAL.text });
  }
  // 4 조작 키 (아래 가운데)
  drawKeyCap(114, 158, 0, 'arrow_left', '←');
  drawKeyCap(136, 158, 1, 'arrow_right', '→');
  drawKeyCap(166, 158, 2, 'shield_q', 'Q');
  drawKeyCap(188, 158, 3, 'shield_e', 'E');
}
function drawPlay() {
  const r = run;
  let ox = 0, oy = 0;
  if (r.shake > 0) { ox = Math.round((Math.random() * 2 - 1) * 2); oy = Math.round((Math.random() * 2 - 1) * 2); }
  ctx.save(); ctx.translate(ox, oy);
  drawPlayWorld();
  ctx.restore();
  drawHud();
}

/* ---------------------------------------------------------------------
 * 05-4 일시정지 / 설정
 * ------------------------------------------------------------------- */
function drawPause() {
  drawPlay();
  rect(0, 0, W, H, PAL.bg, 0.65);                       // 5 반투명 오버레이
  rect(80, 38, 160, 100, PAL.bg, 0.95); frameRect(80, 38, 160, 100, PAL.gray);
  txt('일시정지', 160, 48, { align: 'center', size: 12, bold: true });   // 1 제목
  drawButtons();
}
function drawSettings() {
  rect(0, 0, W, H, PAL.bg, 0.6);
  rect(50, 22, 220, 136, PAL.bg, 0.97); frameRect(50, 22, 220, 136, PAL.gray);
  txt('설정', 160, 27, { align: 'center', size: 10, bold: true });
  txt('사운드', 62, 45, { size: 8 });
  txt('볼륨', 62, 63, { size: 8 });
  txt(Math.round(Snd.vol * 100) + '%', 214, 63, { align: 'center', size: 8 });
  txt('화면', 62, 81, { size: 8 });
  txt('배율 ×' + scale + ' (창 크기에 맞춰 자동)', 62, 96, { size: 7, color: PAL.green });
  txt('조작법', 62, 107, { size: 8 });
  txt('← → 이동 · Q E 패링 · ESC 일시정지 (키 변경 불가)', 62, 124, { size: 6, color: PAL.gray });
  drawButtons();
}

function drawHelp() {
  rect(0, 0, W, H, PAL.bg, 0.7);
  rect(50, 16, 220, 150, PAL.bg, 0.97); frameRect(50, 16, 220, 150, PAL.gray);
  txt('조작법', 160, 21, { align: 'center', size: 10, bold: true });
  const rows = [
    ['← →', '다음 계단 방향으로 한 칸 오르기'],
    ['Q', '왼쪽 패링'],
    ['E', '오른쪽 패링'],
    ['ESC', '일시정지'],
    ['Enter', '메뉴 결정 (방향키 선택·클릭)'],
  ];
  rows.forEach(function (row, i) {
    const y = 38 + i * 16;
    rect(60, y, 36, 13, PAL.gray); frameRect(60, y, 36, 13, PAL.text);
    txt(row[0], 78, y + 7, { align: 'center', base: 'middle', size: 7, bold: true });
    txt(row[1], 104, y + 7, { base: 'middle', size: 7 });
  });
  txt('서류 위 "!"는 1초 뒤 도착 신호. 도착 직전 0.2초 안에', 160, 120, { align: 'center', size: 6, color: PAL.green });
  txt('날아오는 쪽 패링 키를 누르면 막습니다.', 160, 129, { align: 'center', size: 6, color: PAL.green });
  txt('틀린 방향·놓친 공격은 하트 -1, 새 층마다 하트 +1', 160, 138, { align: 'center', size: 6, color: PAL.text });
  drawButtons();
}

/* ---------------------------------------------------------------------
 * 05-5 결과
 * ------------------------------------------------------------------- */
function drawVerdict(x, y, w, h, promo, subtext) {
  ctx.save();
  ctx.translate(x + w / 2, y + h / 2); ctx.rotate(-0.04);
  rect(-w / 2, -h / 2, w, h, promo ? PAL.green : PAL.red);
  frameRect(-w / 2 + 2, -h / 2 + 2, w - 4, h - 4, promo ? PAL.bg : PAL.text);
  txt(promo ? '승급' : '구조조정 대상', 0, -6, { align: 'center', base: 'middle', size: 18, bold: true, color: promo ? PAL.bg : PAL.text, shadow: false });
  txt(subtext, 0, 12, { align: 'center', base: 'middle', size: 7, color: promo ? PAL.bg : PAL.text, shadow: false });
  ctx.restore();
}
function resultRows() {
  const r = result;
  return [
    ['도달 층수', r.floor + 'F'],
    ['직급', r.kind === 'promote' ? '사원 → ' + CONFIG.rankNames[r.rankIdx] : CONFIG.rankNames[r.rankIdx]],
    ['점수', String(r.score)],
    ['최고 콤보', '×' + r.maxMult + ' (' + r.maxCombo + '연속)'],
    ['전체 랭킹', '#-- (오프라인)'],
  ];
}
function drawResult() {
  const r = result, promo = r.kind === 'promote';
  rect(0, 0, W, H, PAL.bg);
  drawImg('bg_zone1', 0, 0, W, H, null);
  rect(0, 0, W, H, PAL.bg, 0.75);
  // 1 캐릭터 반응
  const rk = promo ? CONFIG.rankNames[1] : CONFIG.rankNames[0];
  drawSprite('player', rk, promo ? 'proud' : 'box_exit', time, 54, 150, { scale: spScale('player', 100), fw: 16, fh: 28, color: RANK_COLORS[promo ? 1 : 0] });
  // 3 판정 문구
  drawVerdict(104, 8, 208, 42, promo, promo ? '사원 → 대리 · 20층 승급 심사 통과 (PoC 종료)' : (r.cause === 'days' ? '남은 일수 소진' : '하트 소진'));
  // 4 기록 요약
  rect(104, 56, 208, 72, PAL.bg, 0.85); frameRect(104, 56, 208, 72, PAL.gray);
  txt('인사 평가표', 112, 58, { size: 8, bold: true, color: PAL.green });
  const rows = resultRows();
  rows.forEach(function (row, i) {
    const y = 71 + i * 11;
    txt(row[0], 112, y, { size: 8, color: PAL.text });
    txt(row[1], 304, y, { size: 8, align: 'right' });
  });
  if (r.newBest) txt('NEW', 240, 94, { size: 7, bold: true, color: PAL.red });
  // 2, 5 버튼
  drawButtons();
  if (time < toastUntil) txt(toastText, 262, 158, { size: 7, align: 'center', color: PAL.green });
}
function shareResult() {
  if (!result) return;
  const prev = ctx;
  const c = document.createElement('canvas');
  c.width = W * 2; c.height = H * 2;
  const g = c.getContext('2d');
  g.scale(2, 2); g.imageSmoothingEnabled = false;
  ctx = g;
  try {
    const promo = result.kind === 'promote';
    rect(0, 0, W, H, PAL.bg);
    txt('승급의 계단', 160, 12, { align: 'center', size: 16, bold: true });
    drawVerdict(60, 38, 200, 42, promo, promo ? '사원 → 대리 · 20층 승급' : (result.cause === 'days' ? '남은 일수 소진' : '하트 소진'));
    rect(60, 92, 200, 72, PAL.bg); frameRect(60, 92, 200, 72, PAL.gray);
    txt('인사 평가표', 68, 95, { size: 8, bold: true, color: PAL.green });
    resultRows().forEach(function (row, i) {
      txt(row[0], 68, 108 + i * 10, { size: 8 });
      txt(row[1], 252, 108 + i * 10, { size: 8, align: 'right' });
    });
    txt('v0.1 PoC', 160, 168, { align: 'center', size: 7, color: PAL.gray });
  } finally { ctx = prev; }
  try {
    const url = c.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url; a.download = 'stairs_result.png';
    document.body.appendChild(a); a.click(); a.remove();
    toast('결과 이미지를 저장했습니다');
  } catch (e) { toast('이미지 저장에 실패했습니다'); }
}

/* ---------------------------------------------------------------------
 * 메인 루프
 * ------------------------------------------------------------------- */
function update(dt) {
  time += dt;
  if (resultLock > 0) resultLock -= dt;
  if (screen === 'play' && run && !settingsOpen) updatePlay(dt);
  syncAudio(false);
}
function draw() {
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.globalAlpha = 1;
  rect(0, 0, W, H, PAL.bg);
  switch (screen) {
    case 'title': drawTitle(); break;
    case 'lobby': drawLobby(); break;
    case 'play': if (run) drawPlay(); break;
    case 'pause': if (run) drawPause(); break;
    case 'result': if (result) drawResult(); break;
  }
  if (settingsOpen) {
    if (screen === 'pause' || screen === 'play') { /* 뒤 화면은 이미 그려짐 */ }
    drawSettings();
  }
  if (helpOpen) drawHelp();
}
function publish() {
  S.ready = assetsReady;
  S.screen = screen;
  S.audioFormat = Snd.format;
  if (run) {
    S.floor = run.floor;
    S.rank = CONFIG.rankNames[run.rankIdx];
    S.hearts = run.hearts;
    S.days = Math.round(run.days * 100) / 100;
    S.score = run.score;
    S.maxMult = run.maxMult;
    S.steps = run.steps;
  }
}
let last = performance.now(), acc = 0;
function frame(now) {
  let dt = (now - last) / 1000; last = now;
  if (dt > 0.1) dt = 0.1;
  acc += dt;
  while (acc >= STEP) { update(STEP); acc -= STEP; }
  draw();
  publish();
  requestAnimationFrame(frame);
}
publish();
requestAnimationFrame(frame);
})();