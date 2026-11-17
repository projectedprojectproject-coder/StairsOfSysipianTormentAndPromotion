/* 승급의 계단 PoC (1~20층) — Developer 에이전트 작성
 * 근거: 기획서 01 게임 컨셉, 04 게임 메카니즘, 05 화면 설계서
 * 실행 시 window.SPRITE_DEF (Publisher가 만든 assets/sprite_definition.js)를 읽는다.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ CONFIG
  const CONFIG = {
    // 04 주요 수치 (기획서 초안 값)
    HEARTS: 3,
    DAYS_MAX: 30,
    SEC_PER_DAY: 0.33,
    STEP_DAYS: 1,
    PARRY_DAYS: 1.5,
    PARRY_WINDOW: 0.20,
    TELEGRAPH: 1.0,
    PROMO_FLOOR: 20,          // 04: 승급 20층 (PoC 종료 지점)
    PROMO_HEAL: 1,            // 04 난이도 곡선: 승급 심사에서 하트 1 회복
    FLOOR_HEAL: 1,            // 플레이테스트 반영: 새 층에 오를 때마다 하트 1 회복 (최대 HEARTS)
    RANKS: ["사원", "대리", "과장", "간부", "CEO"],
    // 기획서 미정 (PoC 가정값)
    STEPS_PER_FLOOR: 5,       // 기획서 미정: 한 층을 오르는 계단 칸 수
    COMBO_PER_MULT: 5,        // 기획서 미정: 배수가 한 단계 오르는 연속 패링 횟수
    MAX_MULT: 3,
    STEP_SCORE: 10,           // 기획서 미정: 계단 한 칸 점수
    PARRY_SCORE: 50,          // 기획서 미정: 패링 한 번 점수
    DRAIN_RAMP: 0.5,          // 기획서 미정: 구간 끝에서 일수 감소 속도 +50%
    ATTACK_GAP_START: 2.6,    // 기획서 미정: 구간 시작 공격 간격(초)
    ATTACK_GAP_END: 1.3,      // 기획서 미정: 구간 끝 공격 간격(초)
    TENSE_FROM_FLOOR: 11,     // 기획서 미정: 불협화음 루프로 바꾸는 층
    TEAM: "총무팀",           // 05-2 화면 예시 값
    VERSION: "v0.1",          // 05-1 화면 예시 값
  };
  const PAL = { main: "#5A5F66", sub: "#8A9A5B", accent: "#A13D3D", bg: "#1E1F22", text: "#E8E6DF", dark: "#141518", warm: "#E3B65C" };
  const LW = 320, LH = 180;
  const FONT = '"Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';

  // ------------------------------------------------------------------ 환경
  const params = new URLSearchParams(location.search);
  const BOT = params.get("bot") === "1";
  let muted = params.get("mute") === "1";
  let seed = parseInt(params.get("seed") || String(Date.now() % 100000), 10);
  function rand() { // mulberry32
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  const DEF = window.SPRITE_DEF || { assets_dir: "assets", sprites: {}, images: {}, sounds: {} };
  const DIR = (DEF.assets_dir || "assets") + "/";
  const T = window.__stairs = {
    ready: false, screen: "boot", floor: 1, rank: "사원", hearts: CONFIG.HEARTS, days: CONFIG.DAYS_MAX,
    score: 0, maxMult: 1, steps: 0, assetErrors: [], audioFormat: null, log: [],
  };
  if (!window.SPRITE_DEF) T.assetErrors.push("sprite_definition.js 없음");

  // ------------------------------------------------------------------ 캔버스
  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  let S = 1;
  function resize() {
    S = Math.max(1, Math.floor(Math.min(window.innerWidth / LW, window.innerHeight / LH)));
    canvas.width = LW * S; canvas.height = LH * S;
    canvas.style.width = LW * S + "px"; canvas.style.height = LH * S + "px";
  }
  window.addEventListener("resize", resize); resize();

  // ------------------------------------------------------------------ 에셋
  const IMG = {};
  let pending = 0;
  function loadImage(id, file) {
    pending++;
    const im = new Image();
    im.onload = () => { IMG[id] = im; pending--; };
    im.onerror = () => { T.assetErrors.push("image:" + id); pending--; };
    im.src = DIR + file;
  }
  for (const [id, s] of Object.entries(DEF.sprites || {})) s && s.file ? loadImage(id, s.file) : T.assetErrors.push("sprite정의:" + id);
  for (const [id, s] of Object.entries(DEF.images || {})) s && s.file ? loadImage(id, s.file) : T.assetErrors.push("image정의:" + id);

  const probe = document.createElement("audio");
  const canOgg = probe.canPlayType('audio/ogg; codecs="vorbis"') !== "";
  const canMp3 = probe.canPlayType("audio/mpeg") !== "";
  const SND = {};
  for (const [id, s] of Object.entries(DEF.sounds || {})) {
    const files = (s && s.files) || {};
    const file = (canOgg && files.ogg) || (canMp3 && files.mp3) || files.ogg || files.mp3;
    if (!file) { T.assetErrors.push("sound정의:" + id); continue; }
    T.audioFormat = T.audioFormat || file.split(".").pop();
    const a = new Audio(DIR + file);
    a.preload = "auto"; a.loop = !!s.loop;
    a.addEventListener("error", () => T.assetErrors.push("sound:" + id));
    SND[id] = a;
  }
  let audioUnlocked = false;
  function play(id, vol = 0.6) {
    if (muted || !audioUnlocked || !SND[id]) return;
    const a = SND[id].loop ? SND[id] : SND[id].cloneNode();
    a.volume = vol; a.currentTime = 0;
    a.play().catch(() => {});
  }
  let bgmId = null;
  function setBgm(id) {
    if (bgmId === id) return;
    let pos = 0;
    if (bgmId && SND[bgmId]) { pos = SND[bgmId].currentTime; SND[bgmId].pause(); }
    bgmId = id;
    if (!id || muted || !audioUnlocked || !SND[id]) return;
    const a = SND[id];
    a.volume = 0.45;
    if (a.duration && pos < a.duration) a.currentTime = pos; // 두 루프의 길이가 같아 이어서 재생
    a.play().catch(() => {});
  }
  function setAmb(on) {
    const a = SND.amb_office; if (!a) return;
    if (on && !muted && audioUnlocked) { a.volume = 0.18; a.play().catch(() => {}); } else a.pause();
  }
  function stopAllAudio() { for (const a of Object.values(SND)) a.pause(); }
  function unlockAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    if (bgmId) { const id = bgmId; bgmId = null; setBgm(id); }
  }

  // ------------------------------------------------------------------ 그리기 도구
  function sprite(id, anim, variant, t, x, y, opt = {}) {
    // (x, y) = 발 아래 가운데
    const s = DEF.sprites && DEF.sprites[id], im = IMG[id];
    const a = s && s.animations[anim];
    if (!s || !im || !a) { // 대체 사각형
      ctx.fillStyle = opt.fallback || PAL.accent; ctx.fillRect(Math.round(x - 6), Math.round(y - 20), 12, 20); return;
    }
    const col = a.frames[Math.floor(t * (a.fps || 1)) % a.frames.length];
    const row = (s.variants[variant] !== undefined ? s.variants[variant] : 0);
    const dx = Math.round(x - s.frame_w / 2), dy = Math.round(y - s.frame_h);
    if (opt.flip) {
      ctx.save(); ctx.translate(dx + s.frame_w, dy); ctx.scale(-1, 1);
      ctx.drawImage(im, col * s.frame_w, row * s.frame_h, s.frame_w, s.frame_h, 0, 0, s.frame_w, s.frame_h);
      ctx.restore();
    } else {
      ctx.drawImage(im, col * s.frame_w, row * s.frame_h, s.frame_w, s.frame_h, dx, dy, s.frame_w, s.frame_h);
    }
  }
  function icon(name, x, y) { // 왼쪽 위 기준
    const s = DEF.sprites && DEF.sprites.hud_icons;
    sprite("hud_icons", name, "default", 0, x + (s ? s.frame_w / 2 : 6), y + (s ? s.frame_h : 12), { fallback: PAL.main });
  }
  function image(id, x, y) {
    if (IMG[id]) ctx.drawImage(IMG[id], Math.round(x), Math.round(y));
    else { ctx.fillStyle = PAL.bg; ctx.fillRect(x, y, LW, LH); }
  }
  function text(str, x, y, size = 8, color = PAL.text, align = "left", weight = 700) {
    ctx.font = `${weight} ${size}px ${FONT}`;
    ctx.textAlign = align; ctx.textBaseline = "top"; ctx.fillStyle = color;
    ctx.fillText(str, x, y);
  }
  function panel(x, y, w, h, fill = PAL.bg, line = PAL.main) {
    ctx.fillStyle = fill; ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = line; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  }

  // ------------------------------------------------------------------ 메뉴 버튼
  let buttons = [], focus = 0;
  function setButtons(list) { buttons = list; focus = 0; }
  function drawButtons() {
    buttons.forEach((b, i) => {
      const on = i === focus;
      panel(b.x, b.y, b.w, b.h, on ? PAL.accent : PAL.bg, on ? PAL.text : PAL.main);
      text(b.label, b.x + b.w / 2, b.y + (b.h - 9) / 2, 8, PAL.text, "center");
    });
  }
  function pressButton(i) { if (buttons[i]) { play("sfx_click", 0.5); buttons[i].on(); } }

  // ------------------------------------------------------------------ 저장 기록
  const best = (() => { try { return JSON.parse(localStorage.getItem("stairs_best") || "{}"); } catch (e) { return {}; } })();
  function saveBest(floor, score) {
    best.floor = Math.max(best.floor || 0, floor); best.score = Math.max(best.score || 0, score);
    try { localStorage.setItem("stairs_best", JSON.stringify(best)); } catch (e) {}
  }

  // ------------------------------------------------------------------ 게임 상태
  let screen = "title", prevScreen = "title", settingsOpen = false, clock = 0;
  let G = null;
  const keysDown = {}, keyGlow = { ArrowLeft: 0, ArrowRight: 0, KeyQ: 0, KeyE: 0 };

  function newRun() {
    const dirs = [];
    let d = rand() < 0.5 ? -1 : 1;
    for (let i = 0; i < CONFIG.PROMO_FLOOR * CONFIG.STEPS_PER_FLOOR + 40; i++) {
      if (i > 2 && rand() < 0.35) d = -d;
      dirs.push(d);
    }
    G = {
      dirs, step: 0, hearts: CONFIG.HEARTS, days: CONFIG.DAYS_MAX, score: 0, combo: 0, mult: 1, maxMult: 1,
      rankIdx: 0, t: 0, nextAttack: 1.5, attacks: [], facing: 1, pose: "idle", poseT: 0,
      camX: 0, camY: 0, result: null, botCool: 0, flash: 0, popups: [],
    };
  }
  const floorOf = (step) => 1 + Math.floor(step / CONFIG.STEPS_PER_FLOOR);
  const zoneOf = (floor) => (floor <= 20 ? 1 : floor <= 40 ? 2 : floor <= 60 ? 3 : floor <= 99 ? 4 : 5);
  const zoneProgress = (floor) => ((floor - 1) % 20) / 19;
  // 계단 i의 월드 좌표 (계단 윗면 가운데)
  function stairPos(i) {
    const st = DEF.sprites && DEF.sprites.stairs;
    const dx = st ? Math.floor(st.frame_w / 2) : 16, dy = st ? st.frame_h : 8;
    let x = 0;
    for (let k = 0; k < i; k++) x += G.dirs[k] * dx;
    return { x, y: -i * dy };
  }

  function go(next) {
    prevScreen = screen; screen = next; settingsOpen = false;
    if (next === "title") {
      setBgm("bgm_loop"); setAmb(false);
      setButtons([
        { label: "시작하기", x: 120, y: 112, w: 80, h: 16, on: () => go("lobby") },
        { label: "설정", x: 120, y: 132, w: 80, h: 14, on: () => (settingsOpen = true, setButtons(settingsButtons())) },
      ]);
    } else if (next === "lobby") {
      newRun(); setAmb(true);
      setButtons([{ label: "업무 시작", x: 196, y: 136, w: 96, h: 18, on: () => go("play") }]);
    } else if (next === "play") {
      setButtons([]); setAmb(true);
      setBgm(floorOf(G.step) >= CONFIG.TENSE_FROM_FLOOR ? "bgm_loop_tense" : "bgm_loop");
    } else if (next === "pause") {
      setButtons([
        { label: "계속하기", x: 120, y: 74, w: 80, h: 16, on: () => go("play") },
        { label: "설정", x: 120, y: 94, w: 80, h: 16, on: () => (settingsOpen = true, setButtons(settingsButtons())) },
        { label: "메인으로", x: 120, y: 114, w: 80, h: 16, on: () => go("title") },
      ]);
    } else if (next === "result") {
      setAmb(false); setBgm(null);
      setButtons([
        { label: "다시 하기", x: 196, y: 150, w: 56, h: 16, on: () => go("lobby") },
        { label: "기록 공유", x: 256, y: 150, w: 56, h: 16, on: shareResult },
      ]);
    }
    T.log.push("screen:" + next);
  }
  function settingsButtons() {
    return [
      { label: muted ? "사운드: 끔" : "사운드: 켬", x: 110, y: 80, w: 100, h: 16, on: () => { muted = !muted; if (muted) stopAllAudio(); else { setAmb(screen !== "title" && screen !== "result"); const id = bgmId; bgmId = null; setBgm(id); } setButtons(settingsButtons()); } },
      { label: "닫기", x: 110, y: 120, w: 100, h: 16, on: () => go(screen) },
    ];
  }
  function shareResult() {
    const a = document.createElement("a");
    a.download = `승급의계단_${floorOf(G.step)}F.png`;
    a.href = canvas.toDataURL("image/png");
    a.click();
  }

  // ------------------------------------------------------------------ 플레이 규칙
  function hurt(reason) {
    G.hearts -= 1; G.combo = 0; G.mult = 1; G.pose = "hit"; G.poseT = 0.35; G.flash = 0.25;
    play("sfx_hit", 0.6); T.log.push("hurt:" + reason);
    if (G.hearts <= 0) endRun("gameover");
  }
  function tryStep(dir) {
    if (screen !== "play") return;
    G.facing = dir;
    if (G.dirs[G.step] === dir) {
      G.step += 1;
      G.days = Math.min(CONFIG.DAYS_MAX, G.days + CONFIG.STEP_DAYS);
      G.score += CONFIG.STEP_SCORE * G.mult;
      G.pose = "step"; G.poseT = 0.12;
      play("sfx_step", 0.35);
      const f = floorOf(G.step);
      if (f > floorOf(G.step - 1) && G.hearts < CONFIG.HEARTS) { // 새 층 도착: 하트 회복
        G.hearts = Math.min(CONFIG.HEARTS, G.hearts + CONFIG.FLOOR_HEAL);
        G.popups.push({ text: "하트 +1", t: 0.6, side: 0 });
        T.log.push("heal:floor" + f);
      }
      if (f >= CONFIG.TENSE_FROM_FLOOR) setBgm("bgm_loop_tense");
      if (f >= CONFIG.PROMO_FLOOR) promote();
    } else {
      hurt("wrong-step");
    }
  }
  function tryParry(side) { // side: -1 왼쪽(Q), +1 오른쪽(E)
    if (screen !== "play") return;
    G.pose = side < 0 ? "parry_left" : "parry_right"; G.poseT = 0.18;
    const a = G.attacks.find((k) => !k.done && k.side === side && G.t >= k.hitAt - CONFIG.PARRY_WINDOW && G.t <= k.hitAt);
    if (!a) return; // 판정 시간 밖의 패링은 효과 없음
    a.done = true; a.parried = true; a.fade = 0.25;
    G.combo += 1;
    G.mult = Math.min(CONFIG.MAX_MULT, 1 + Math.floor(G.combo / CONFIG.COMBO_PER_MULT));
    G.maxMult = Math.max(G.maxMult, G.mult);
    G.days = Math.min(CONFIG.DAYS_MAX, G.days + CONFIG.PARRY_DAYS);
    G.score += CONFIG.PARRY_SCORE * G.mult;
    G.popups.push({ text: G.mult > 1 ? `×${G.mult}` : "막았다!", t: 0.6, side });
    play("sfx_parry", 0.5);
  }
  function promote() {
    G.rankIdx = 1;
    G.hearts = Math.min(CONFIG.HEARTS, G.hearts + CONFIG.PROMO_HEAL);
    play("sfx_promote", 0.6);
    endRun("promote");
  }
  function endRun(kind) {
    G.result = kind;
    G.pose = kind === "promote" ? "proud" : "box_exit";
    saveBest(floorOf(G.step), G.score);
    if (kind === "gameover") play("sfx_gameover", 0.6);
    go("result");
  }
  function spawnAttack() {
    const side = rand() < 0.5 ? -1 : 1;
    G.attacks.push({ side, spawn: G.t, hitAt: G.t + CONFIG.TELEGRAPH, kind: "document", done: false });
    play("sfx_warning", 0.3);
  }

  function updatePlay(dt) {
    G.t += dt;
    const floor = floorOf(G.step), p = zoneProgress(floor);
    G.days -= (dt / CONFIG.SEC_PER_DAY) * (1 + CONFIG.DRAIN_RAMP * p);
    if (G.days <= 0) { G.days = 0; endRun("gameover"); return; }
    G.nextAttack -= dt;
    if (G.nextAttack <= 0) {
      spawnAttack();
      const gap = CONFIG.ATTACK_GAP_START + (CONFIG.ATTACK_GAP_END - CONFIG.ATTACK_GAP_START) * p;
      G.nextAttack = gap * (0.8 + rand() * 0.4);
    }
    for (const a of G.attacks) {
      if (!a.done && G.t > a.hitAt) { a.done = true; a.fade = 0.2; hurt("attack"); if (screen !== "play") return; }
      if (a.fade !== undefined) a.fade -= dt;
    }
    G.attacks = G.attacks.filter((a) => !a.done || a.fade > 0);
    if (G.poseT > 0) { G.poseT -= dt; if (G.poseT <= 0) G.pose = "idle"; }
    G.flash = Math.max(0, G.flash - dt);
    G.popups.forEach((q) => (q.t -= dt)); G.popups = G.popups.filter((q) => q.t > 0);
    // 카메라: 플레이어를 화면 (160, 120)에 둔다
    const sp = stairPos(G.step);
    G.camX += (sp.x - G.camX) * Math.min(1, dt * 12);
    G.camY += (sp.y - G.camY) * Math.min(1, dt * 12);
    if (BOT) botThink(dt);
  }
  function botThink(dt) {
    G.botCool -= dt;
    for (const a of G.attacks) {
      if (!a.done && a.hitAt - G.t <= 0.08) { pressKey(a.side < 0 ? "KeyQ" : "KeyE"); }
    }
    if (G.botCool <= 0 && screen === "play") { G.botCool = 0.14; pressKey(G.dirs[G.step] < 0 ? "ArrowLeft" : "ArrowRight"); }
  }

  // ------------------------------------------------------------------ 입력
  function pressKey(code) {
    if (code in keyGlow) keyGlow[code] = 0.15;
    if (screen === "play") {
      if (code === "ArrowLeft") tryStep(-1);
      else if (code === "ArrowRight") tryStep(1);
      else if (code === "KeyQ") tryParry(-1);
      else if (code === "KeyE") tryParry(1);
      else if (code === "Escape") go("pause");
      return;
    }
    if (screen === "pause" && code === "Escape" && !settingsOpen) { go("play"); return; }
    if (!buttons.length) return;
    if (code === "ArrowLeft" || code === "ArrowUp") focus = (focus + buttons.length - 1) % buttons.length;
    else if (code === "ArrowRight" || code === "ArrowDown") focus = (focus + 1) % buttons.length;
    else if (code === "Enter" || code === "Space") pressButton(focus);
  }
  window.addEventListener("keydown", (e) => {
    unlockAudio();
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Space"].includes(e.code)) e.preventDefault();
    if (keysDown[e.code]) return; // 키 반복 무시
    keysDown[e.code] = true;
    pressKey(e.code);
  });
  window.addEventListener("keyup", (e) => { keysDown[e.code] = false; });
  function toLogical(e) {
    const r = canvas.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * LW, y: ((e.clientY - r.top) / r.height) * LH };
  }
  const hit = (b, p) => p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
  canvas.addEventListener("mousemove", (e) => { const p = toLogical(e); buttons.forEach((b, i) => hit(b, p) && (focus = i)); });
  canvas.addEventListener("click", (e) => { unlockAudio(); const p = toLogical(e); buttons.forEach((b, i) => hit(b, p) && pressButton(i)); });

  // ------------------------------------------------------------------ 화면 그리기
  function drawTitle() {
    image("title_bg", 0, 0);
    if (IMG.logo) ctx.drawImage(IMG.logo, Math.round((LW - IMG.logo.width) / 2), 34); // 05-1 요소 1
    else text("승급의 계단", LW / 2, 40, 20, PAL.text, "center");
    drawButtons();                                                                      // 요소 2, 3
    text(`${CONFIG.VERSION} · 승급의 계단 PoC`, LW / 2, 168, 6, PAL.main, "center", 400); // 요소 5
  }
  function rankName() { return CONFIG.RANKS[G ? G.rankIdx : 0]; }
  function drawLobby() {
    image("bg_zone1", 0, 0);
    ctx.fillStyle = "rgba(20,21,24,0.55)"; ctx.fillRect(0, 0, LW, LH);
    text("1F", 16, 12, 22);                                                              // 05-2 요소 1
    text("파티션 사무실", 16, 40, 8, PAL.sub);
    icon("calendar", 228, 12); text("구조조정까지", 244, 10, 6, PAL.main, "left", 400);   // 요소 2
    text(`D-${CONFIG.DAYS_MAX}`, 244, 17, 12, PAL.accent);
    // 요소 3: 사원증
    panel(16, 62, 132, 82, PAL.text, PAL.main);
    ctx.fillStyle = PAL.sub; ctx.fillRect(17, 63, 130, 12);
    text("사원증", 22, 64, 7, PAL.bg);
    ctx.fillStyle = "#C9CCD1"; ctx.fillRect(24, 82, 36, 52);
    sprite("player", "idle", rankName(), clock, 42, 134);
    text("신입 사원", 70, 86, 9, PAL.bg);
    text(rankName(), 70, 102, 8, PAL.accent);
    text(CONFIG.TEAM, 70, 116, 7, PAL.main, "left", 400);
    // 요소 5: 누적 기록
    panel(196, 62, 108, 64, PAL.bg, PAL.main);
    text("누적 기록", 204, 68, 7, PAL.sub);
    text(`최고 ${best.floor || 0}F`, 204, 82, 8);
    text(`점수 ${(best.score || 0).toLocaleString()}`, 204, 96, 8);
    text("전체 랭킹 서버 미구현", 204, 110, 6, PAL.main, "left", 400);
    drawButtons();                                                                         // 요소 4
  }
  function drawWorld() {
    const floor = floorOf(G.step), zone = zoneOf(floor);
    image("bg_zone" + zone, 0, 0);
    const ox = 160 - G.camX, oy = 128 - G.camY;
    const st = DEF.sprites && DEF.sprites.stairs;
    const tw = st ? st.frame_w : 32;
    for (let i = Math.max(0, G.step - 12); i < G.step + 16; i++) {
      const p = stairPos(i);
      const sx = ox + p.x, sy = oy + p.y;
      if (sy < -10 || sy > LH + 10) continue;
      const tf = floorOf(i);
      sprite("stairs", "tile", "zone" + zoneOf(tf), 0, sx, sy + (st ? st.frame_h : 8), { fallback: PAL.main });
      if (i % CONFIG.STEPS_PER_FLOOR === 0 && i > 0) text(`${tf}F`, sx + tw / 2 + 2, sy - 1, 6, PAL.main, "left", 400);
    }
    // 플레이어
    const pp = stairPos(G.step);
    const px = ox + pp.x, py = oy + pp.y;
    const pose = screen === "result" ? (G.result === "promote" ? "proud" : "box_exit") : G.pose;
    if (screen === "result") return; // 결과 화면은 캐릭터 반응을 따로 그린다 (05-5 요소 1)
    if (G.flash > 0 && Math.floor(G.flash * 30) % 2 === 0) { /* 피격 깜박임 */ }
    else sprite("player", pose, rankName(), clock, px, py, { flip: pose === "step" && G.facing < 0 });
    // 서류 투척 (05-3 요소 3, 4)
    for (const a of G.attacks) {
      const k = Math.min(1, (G.t - a.spawn) / CONFIG.TELEGRAPH);
      const startX = a.side < 0 ? -8 : LW + 8;
      const ax = startX + (px - 10 * a.side - startX) * k;
      const ay = py - 14 - Math.sin(k * Math.PI) * 10;
      ctx.globalAlpha = a.fade !== undefined ? Math.max(0, a.fade / 0.25) : 1;
      sprite("projectiles", a.kind, "default", 0, a.parried ? ax - a.side * (0.25 - a.fade) * 160 : ax, ay + 6);
      ctx.globalAlpha = 1;
      if (!a.done) sprite("warning", "blink", "default", G.t, ax, ay - 8);
    }
    for (const q of G.popups) text(q.text, px + q.side * 22, py - 34 - (0.6 - q.t) * 20, 8, PAL.warm, "center");
  }
  function drawHud() {
    const floor = floorOf(G.step);
    // 05-3 요소 1
    panel(4, 4, 74, 16, "rgba(20,21,24,0.85)", PAL.main);
    icon("badge", 6, 6); text(`${floor}F · ${rankName()}`, 20, 8, 7);
    // 요소 2
    panel(LW - 104, 4, 100, 16, "rgba(20,21,24,0.85)", PAL.main);
    icon("calendar", LW - 102, 6);
    text(`D-${Math.ceil(G.days)}`, LW - 88, 8, 7, G.days < 8 ? PAL.accent : PAL.text);
    for (let i = 0; i < CONFIG.HEARTS; i++) icon(i < G.hearts ? "heart" : "heart_empty", LW - 56 + i * 13, 6);
    // 콤보
    if (G.mult > 1) text(`×${G.mult} COMBO`, LW / 2, 8, 9, PAL.warm, "center");
    // 요소 4: 조작 키
    const keys = [["ArrowLeft", "arrow_left", "←"], ["ArrowRight", "arrow_right", "→"], ["KeyQ", "shield_q", "Q"], ["KeyE", "shield_e", "E"]];
    keys.forEach(([code, ic, label], i) => {
      const x = 104 + i * 30 + (i >= 2 ? 6 : 0), y = 160;
      panel(x, y, 22, 16, keyGlow[code] > 0 ? PAL.sub : "rgba(20,21,24,0.85)", PAL.main);
      icon(ic, x + 1, y + 2); text(label, x + 15, y + 4, 6, PAL.text, "center");
    });
  }
  function drawPause() {
    drawWorld(); drawHud();
    ctx.fillStyle = "rgba(20,21,24,0.7)"; ctx.fillRect(0, 0, LW, LH);                   // 05-4 요소 5
    panel(100, 40, 120, 100, PAL.bg, PAL.main);
    text("일시정지", LW / 2, 50, 11, PAL.text, "center");                               // 요소 1
    drawButtons();                                                                       // 요소 2, 3, 4
  }
  function drawResult() {
    drawWorld();
    ctx.fillStyle = "rgba(20,21,24,0.6)"; ctx.fillRect(0, 0, LW, LH);
    const promo = G.result === "promote";
    // 05-5 요소 3: 선전포스터 스타일 판정 문구
    panel(14, 14, 160, 34, promo ? PAL.sub : PAL.accent, PAL.text);
    text(promo ? "승급" : "구조조정 대상", 94, 19, 16, PAL.text, "center");
    text(promo ? "사원 → 대리" : "짐을 챙겨 주십시오", 94, 38, 6, PAL.text, "center", 400);
    // 요소 1: 캐릭터 반응
    sprite("player", promo ? "proud" : "box_exit", rankName(), clock, 94, 140);
    // 요소 4: 인사 평가표
    panel(188, 14, 124, 128, PAL.text, PAL.main);
    text("인사 평가 결과", 250, 20, 8, PAL.bg, "center");
    const rows = [["도달 층수", `${floorOf(G.step)}F`], ["직급", rankName()], ["점수", G.score.toLocaleString()],
                  ["최고 콤보", `×${G.maxMult}`], ["전체 랭킹", "서버 미구현"]];
    rows.forEach(([k, v], i) => {
      text(k, 196, 38 + i * 19, 7, PAL.main, "left", 400);
      text(v, 304, 38 + i * 19, 8, PAL.bg, "right");
    });
    if (promo) text("PoC 범위(1~20층) 종료", 94, 150, 6, PAL.text, "center", 400);
    drawButtons();                                                                       // 요소 2, 5
  }
  function drawSettings() {
    ctx.fillStyle = "rgba(20,21,24,0.75)"; ctx.fillRect(0, 0, LW, LH);
    panel(96, 56, 128, 90, PAL.bg, PAL.main);
    text("설정", LW / 2, 62, 9, PAL.text, "center");
    text("화면 · 키 설정은 PoC 미구현", LW / 2, 102, 6, PAL.main, "center", 400);
    drawButtons();
  }

  // ------------------------------------------------------------------ 루프
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    clock += dt;
    for (const k in keyGlow) keyGlow[k] = Math.max(0, keyGlow[k] - dt);
    if (screen === "play" && !settingsOpen) updatePlay(dt);

    ctx.setTransform(S, 0, 0, S, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, LW, LH);
    if (screen === "title") drawTitle();
    else if (screen === "lobby") drawLobby();
    else if (screen === "play") { drawWorld(); drawHud(); }
    else if (screen === "pause") drawPause();
    else if (screen === "result") drawResult();
    if (settingsOpen) drawSettings();

    if (G) Object.assign(T, {
      floor: floorOf(G.step), rank: rankName(), hearts: G.hearts, days: G.days,
      score: G.score, maxMult: G.maxMult, steps: G.step,
    });
    T.screen = settingsOpen ? screen + ":settings" : screen;
    requestAnimationFrame(frame);
  }

  function start() {
    if (pending > 0) { setTimeout(start, 30); return; }
    newRun();
    go("title");
    T.ready = true;
    requestAnimationFrame(frame);
  }
  start();
})();