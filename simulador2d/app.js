"use strict";

// Posiciones en % del ancho de la escena
const X_CAMARA = 45, X_ACTUADOR = 68, X_FIN = 91, SEPARACION = 15;
const V_BANDA = 12;                       // % por segundo simulado
const T = { captura: 0.4, inferencia: 0.7, decision: 0.4 };
const INTERVALO_SPAWN = 0.4;
const DEFECTOS = ["mancha", "costura", "pegado"];

const $ = (id) => document.getElementById(id);
const el = {
  pieces: $("pieces"), belt: $("belt"), beam: $("beam"), frame: $("frame"), arm: $("arm"),
  states: [...document.querySelectorAll("#states li")], cap: $("cap"), json: $("json"), log: $("log"),
  btnRun: $("btnRun"), speed: $("speed"), prob: $("prob"), sens: $("sens"),
};

let S;
function nuevoEstado() {
  return {
    running: true, piezas: [], nextId: 0, spawnT: 0, forceDefect: false,
    estado: "espera", timer: 0, actual: null,
    ok: 0, bad: 0, escapes: 0, rejBin: 0, okBin: 0, lat: 0,
  };
}

/* ---------- Piezas ---------- */
function shoeSVG(defecto) {
  const d = {
    mancha: '<ellipse class="d-mancha" cx="46" cy="22" rx="9" ry="6"/>',
    costura: '<path class="d-costura" d="M26 12 L64 12"/>',
    pegado: '<circle class="d-pegado" cx="56" cy="31" r="4"/><circle class="d-pegado" cx="64" cy="29" r="3"/>',
  }[defecto] || "";
  return `<svg viewBox="0 0 84 44" aria-hidden="true">
    <path class="sole" d="M4 22 C4 8 20 4 42 4 C66 4 80 12 80 22 C80 32 66 40 42 40 C20 40 4 36 4 22Z"/>
    <path class="upper" d="M10 22 C10 13 24 10 42 10 C60 10 72 15 72 22 C72 29 60 34 42 34 C24 34 10 31 10 22Z"/>
    <path class="lace" d="M40 14 L40 30 M47 13 L47 31 M54 14 L54 30"/>
    ${d}</svg>`;
}

function crearPieza() {
  const p = { id: S.nextId++, x: 0, defecto: null, decision: null, fase: "banda", t: 0 };
  if (S.forceDefect || Math.random() < el.prob.value / 100) {
    p.defecto = DEFECTOS[Math.floor(Math.random() * DEFECTOS.length)];
  }
  S.forceDefect = false;
  const d = document.createElement("div");
  d.className = "piece";
  d.innerHTML = shoeSVG(p.defecto) + `<div class="id">#${p.id}</div>`;
  el.pieces.appendChild(d);
  p.dom = d;
  S.piezas.push(p);
}

/* ---------- Captura (imagen sintética, igual que simulator/main.py) ---------- */
function dibujarCaptura(defecto) {
  const c = el.cap.getContext("2d"), n = 64, img = c.createImageData(n, n);
  for (let i = 0; i < n * n; i++) {
    const v = Math.max(0, Math.min(255, 180 + (Math.random() - 0.5) * 30));
    img.data.set([v, v, v, 255], i * 4);
  }
  c.putImageData(img, 0, 0);
  if (defecto) {
    c.fillStyle = "rgb(25,25,25)";
    c.fillRect(10 + Math.random() * 28, 10 + Math.random() * 28, 14, 14);
  }
}

/* ---------- Controlador SIL ---------- */
function setEstado(e) {
  S.estado = e; S.timer = 0;
  el.states.forEach((li) => li.classList.toggle("active", li.dataset.s === e));
  el.belt.classList.toggle("stopped", e !== "espera");
  el.beam.classList.toggle("on", e === "captura");
  el.frame.className = "frame" + (e === "captura" ? " on" : e === "inferencia" ? " on infer" : "");
}

function decidir(p) {
  const detecta = p.defecto && Math.random() < el.sens.value / 100;
  p.decision = detecta ? "RECHAZO" : "OK";
  const falloDeteccion = p.defecto && !detecta;
  const label = detecta ? p.defecto : "ok";
  const score = detecta ? 0.75 + Math.random() * 0.24 : 0.02 + Math.random() * 0.2;
  S.lat = Math.round(90 + Math.random() * 60);

  if (detecta) S.bad++; else S.ok++;
  if (falloDeteccion) S.escapes++;

  p.dom.classList.add(detecta ? "flag-bad" : "flag-ok");
  el.frame.classList.add(detecta ? "bad" : "ok");

  const msg = {
    pieza_id: p.id, timestamp: +(Date.now() / 1000).toFixed(3),
    decision: p.decision, label, score: +score.toFixed(2), latencia_ms: S.lat,
  };
  el.json.textContent = JSON.stringify(msg, null, 2);

  const li = document.createElement("li");
  li.innerHTML = `<span>Pieza #${p.id} · ${label}${falloDeteccion ? ' <span class="esc">(defecto no detectado)</span>' : ""}</span>
    <span class="${detecta ? "tagBAD" : "tagOK"}">${p.decision}</span>`;
  el.log.prepend(li);
  while (el.log.children.length > 8) el.log.lastChild.remove();
}

/* ---------- Bucle ---------- */
function paso(dt) {
  S.spawnT += dt;
  const ultima = S.piezas[S.piezas.length - 1];
  if (S.estado === "espera" && S.spawnT > INTERVALO_SPAWN && (!ultima || ultima.x >= SEPARACION)) {
    crearPieza(); S.spawnT = 0;
  }

  if (S.estado === "espera") {
    for (const p of S.piezas) {
      if (p.fase === "banda") p.x += V_BANDA * dt;
      if (p.fase === "banda" && p.decision === "RECHAZO" && p.x >= X_ACTUADOR) {
        p.x = X_ACTUADOR; p.fase = "empuje"; p.t = 0; el.arm.classList.add("push");
        p.dom.classList.add("slide");
      }
      if (p.fase === "banda" && p.x >= X_FIN) { p.fase = "fin"; p.t = 0; S.okBin++; p.dom.classList.add("gone"); }
    }
    const candidata = S.piezas.find((p) => p.fase === "banda" && !p.decision && p.x >= X_CAMARA);
    if (candidata) {
      candidata.x = X_CAMARA; S.actual = candidata;
      dibujarCaptura(candidata.defecto); setEstado("captura");
    }
  } else {
    S.timer += dt;
    const p = S.actual;
    if (S.estado === "captura" && S.timer >= T.captura) setEstado("inferencia");
    else if (S.estado === "inferencia" && S.timer >= T.inferencia) { setEstado("decision"); decidir(p); }
    else if (S.estado === "decision" && S.timer >= T.decision) { S.actual = null; setEstado("espera"); }
  }

  // Empuje del actuador (continúa aunque la banda esté detenida)
  for (const p of S.piezas) {
    if (p.fase === "empuje") {
      p.t += dt;
      if (p.t > 0.55) { p.fase = "fin"; S.rejBin++; p.dom.classList.add("gone"); el.arm.classList.remove("push"); }
    } else if (p.fase === "fin") {
      p.t += dt;
      if (p.t > 0.5) p.borrar = true;
    }
  }
  S.piezas = S.piezas.filter((p) => { if (p.borrar) p.dom.remove(); return !p.borrar; });
}

function pintar() {
  for (const p of S.piezas) p.dom.style.left = p.x + "%";
  const total = S.ok + S.bad;
  $("kTotal").textContent = total;
  $("kOk").textContent = S.ok;
  $("kBad").textContent = S.bad;
  $("kRate").textContent = total ? Math.round((S.bad / total) * 100) + "%" : "0%";
  $("kEsc").textContent = S.escapes;
  $("kLat").textContent = S.lat;
  $("binOkN").textContent = S.okBin;
  $("binRejectN").textContent = S.rejBin;
}

let ultimo = performance.now();
function bucle(ahora) {
  const dt = Math.min(0.05, (ahora - ultimo) / 1000);
  ultimo = ahora;
  if (S.running) paso(dt * el.speed.value);
  pintar();
  requestAnimationFrame(bucle);
}

/* ---------- Controles ---------- */
function reiniciar() {
  el.pieces.innerHTML = ""; el.log.innerHTML = "";
  el.json.textContent = "Esperando primera pieza…";
  el.arm.classList.remove("push");
  S = nuevoEstado(); setEstado("espera");
  el.btnRun.textContent = "Pausar";
}

el.btnRun.onclick = () => {
  S.running = !S.running;
  el.btnRun.textContent = S.running ? "Pausar" : "Reanudar";
  el.belt.style.animationPlayState = S.running && S.estado === "espera" ? "running" : "paused";
};
$("btnReset").onclick = reiniciar;
$("btnForce").onclick = () => { S.forceDefect = true; };

function sincronizarSliders() {
  $("oSpeed").textContent = (+el.speed.value).toFixed(1) + "×";
  $("oProb").textContent = el.prob.value + "%";
  $("oSens").textContent = el.sens.value + "%";
  document.documentElement.style.setProperty("--speed", (0.6 / el.speed.value).toFixed(2) + "s");
}
[el.speed, el.prob, el.sens].forEach((s) => s.addEventListener("input", sincronizarSliders));

sincronizarSliders();
reiniciar();
requestAnimationFrame(bucle);
