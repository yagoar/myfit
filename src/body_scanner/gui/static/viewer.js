// MyFit 3D viewer — Three.js scene + measurement overlay toggles.
//
// Loads either:
//   1. A pipeline-generated scan (server-side compute of polylines via
//      /api/scan/<name>); or
//   2. A user-uploaded .obj (mesh only, no measurement polylines).
//
// Keyboard 1..5 → front / 45° front / side / 45° back / back.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";

const $ = (id) => document.getElementById(id);

const ANGLE_PRESETS = {
  1: { az: 0,   el: 0, name: "Front"  },
  2: { az: 45,  el: 0, name: "45° F"  },
  3: { az: 90,  el: 0, name: "Side"   },
  4: { az: 135, el: 0, name: "45° B"  },
  5: { az: 180, el: 0, name: "Back"   },
};

// ---- Three.js scene ---------------------------------------------------

const host = $("canvas-host");
const scene = new THREE.Scene();
scene.background = null;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(host.clientWidth, host.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
host.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(
  35, host.clientWidth / host.clientHeight, 0.05, 50,
);
camera.position.set(0, 1.0, 3.0);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 0.6;
controls.maxDistance = 8;

// Lighting — soft three-point.
scene.add(new THREE.AmbientLight(0xb8b8c8, 0.55));
const key = new THREE.DirectionalLight(0xffffff, 0.95);
key.position.set(2, 3, 4);
scene.add(key);
const rim = new THREE.DirectionalLight(0x9d8bff, 0.45);
rim.position.set(-3, 2, -2);
scene.add(rim);
const fill = new THREE.DirectionalLight(0x6cd4c0, 0.25);
fill.position.set(0, -2, 0);
scene.add(fill);

// Floor disc — subtle reference.
const floor = new THREE.Mesh(
  new THREE.CircleGeometry(1.2, 64),
  new THREE.MeshBasicMaterial({
    color: 0x6f5cf6, transparent: true, opacity: 0.06,
  }),
);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// ---- State ------------------------------------------------------------

let bodyMesh = null;
let centroid = new THREE.Vector3(0, 1.0, 0);
let radius = 2.5;
let polylines = {};    // { code: [[x,y,z],...] }
let polyObjects = {};  // { code: THREE.Line }
let measurementMeta = [];
let activeCam = 1;

function setStatus(text, cls = "") {
  const el = $("viewer-status");
  el.className = "pill " + cls;
  el.textContent = text;
}

function setHud(html) {
  $("hud").innerHTML = html;
}

// ---- Camera presets ---------------------------------------------------

function applyPreset(n, animate = true) {
  const p = ANGLE_PRESETS[n];
  if (!p) return;
  activeCam = n;
  const az = THREE.MathUtils.degToRad(p.az);
  const el = THREE.MathUtils.degToRad(p.el);
  const r = radius * 1.6;
  const target = new THREE.Vector3(
    centroid.x + r * Math.cos(el) * Math.sin(az),
    centroid.y + r * Math.sin(el),
    centroid.z + r * Math.cos(el) * Math.cos(az),
  );
  controls.target.copy(centroid);
  if (animate) {
    // Single-step "snap"; OrbitControls damping smooths the transition.
    camera.position.copy(target);
  } else {
    camera.position.copy(target);
  }
  controls.update();
  document.querySelectorAll(".cam-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.cam === String(n)),
  );
}
document.querySelectorAll(".cam-btn").forEach((b) =>
  b.addEventListener("click", () => applyPreset(Number(b.dataset.cam))),
);
window.addEventListener("keydown", (e) => {
  if (document.activeElement &&
      (document.activeElement.tagName === "INPUT" ||
       document.activeElement.tagName === "TEXTAREA")) return;
  if (ANGLE_PRESETS[e.key]) {
    applyPreset(Number(e.key));
    e.preventDefault();
  }
});

// ---- Mesh loading -----------------------------------------------------

function clearBody() {
  if (bodyMesh) {
    scene.remove(bodyMesh);
    bodyMesh.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        const m = Array.isArray(o.material) ? o.material : [o.material];
        m.forEach((mat) => mat.dispose());
      }
    });
    bodyMesh = null;
  }
  Object.values(polyObjects).forEach((l) => scene.remove(l));
  polyObjects = {};
}

const BODY_MATERIAL = new THREE.MeshPhysicalMaterial({
  color: 0xc7c4d8,
  metalness: 0.05,
  roughness: 0.55,
  clearcoat: 0.15,
  side: THREE.DoubleSide,
  envMapIntensity: 0.5,
});

function frameToBody() {
  if (!bodyMesh) return;
  const box = new THREE.Box3().setFromObject(bodyMesh);
  const size = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(centroid);
  radius = Math.max(size.x, size.y, size.z) / 2;
  floor.position.set(centroid.x, box.min.y + 0.001, centroid.z);
  applyPreset(activeCam, false);
}

async function loadObjFromUrl(url) {
  return new Promise((resolve, reject) => {
    new OBJLoader().load(url, (group) => {
      group.traverse((c) => {
        if (c.isMesh) {
          c.material = BODY_MATERIAL;
          c.geometry.computeVertexNormals();
        }
      });
      resolve(group);
    }, undefined, reject);
  });
}

function loadObjFromText(text) {
  const group = new OBJLoader().parse(text);
  group.traverse((c) => {
    if (c.isMesh) {
      c.material = BODY_MATERIAL;
      c.geometry.computeVertexNormals();
    }
  });
  return group;
}

function showBody(group) {
  clearBody();
  bodyMesh = group;
  scene.add(bodyMesh);
  frameToBody();
}

// ---- Polyline overlays ------------------------------------------------

const LINE_MATERIAL = new THREE.LineBasicMaterial({
  color: 0xffd166,
  linewidth: 2,
  transparent: true,
  opacity: 0.95,
});

function buildPolylines() {
  Object.values(polyObjects).forEach((l) => scene.remove(l));
  polyObjects = {};
  for (const [code, pts] of Object.entries(polylines)) {
    if (!pts || pts.length < 2) continue;
    const geom = new THREE.BufferGeometry().setFromPoints(
      pts.map(([x, y, z]) => new THREE.Vector3(x, y, z)),
    );
    const line = new THREE.Line(geom, LINE_MATERIAL.clone());
    line.visible = false;
    line.userData.code = code;
    scene.add(line);
    polyObjects[code] = line;
  }
}

function setPolylineVisible(code, visible) {
  const l = polyObjects[code];
  if (l) l.visible = visible;
}

// ---- Measurement sidebar ----------------------------------------------

function renderMeasList() {
  const filter = ($("meas-filter").value || "").toLowerCase().trim();
  const host = $("meas-list");
  if (!measurementMeta.length) {
    host.innerHTML = '<div class="help">No measurements available.</div>';
    return;
  }
  host.innerHTML = "";
  let shown = 0;
  measurementMeta.forEach((m) => {
    if (filter && !(`${m.code} ${m.name}`).toLowerCase().includes(filter)) return;
    shown += 1;
    const row = document.createElement("label");
    row.className = "meas-row" + (m.has_polyline ? "" : " unavailable");
    row.title = m.has_polyline
      ? `${m.code} — ${m.name}`
      : `${m.code} — no polyline (extractor did not produce a curve)`;
    row.innerHTML = `
      <input type="checkbox" data-code="${m.code}"
             ${m.has_polyline ? "" : "disabled"}>
      <span class="code">${m.code}</span>
      <span class="label">${m.name || "—"}</span>
      <span class="val">${m.value_cm != null ? m.value_cm.toFixed(1) + " cm" : "—"}</span>
    `;
    const cb = row.querySelector("input");
    if (m.has_polyline) {
      cb.addEventListener("change", () => {
        setPolylineVisible(m.code, cb.checked);
      });
    }
    host.appendChild(row);
  });
  $("meas-count").textContent = `${shown}/${measurementMeta.length}`;
}

$("meas-filter").addEventListener("input", renderMeasList);
$("meas-all").addEventListener("click", () => {
  document.querySelectorAll('.meas-row input:not([disabled])').forEach((cb) => {
    cb.checked = true;
    setPolylineVisible(cb.dataset.code, true);
  });
});
$("meas-none").addEventListener("click", () => {
  document.querySelectorAll('.meas-row input').forEach((cb) => {
    cb.checked = false;
    setPolylineVisible(cb.dataset.code, false);
  });
});

// ---- Scan picker ------------------------------------------------------

async function refreshScans() {
  const r = await fetch("/api/scans");
  const j = await r.json();
  const sel = $("scan-picker");
  sel.innerHTML = '<option value="">— pick a scan —</option>';
  j.scans.forEach((s) => {
    const o = document.createElement("option");
    o.value = s.name;
    o.textContent = s.name + (s.has_obj ? "" : " (no OBJ)");
    o.disabled = !s.has_obj;
    sel.appendChild(o);
  });
}
$("scan-picker").addEventListener("change", async (e) => {
  const name = e.target.value;
  if (!name) return;
  await loadScan(name);
});

async function loadScan(name) {
  setStatus("loading", "run");
  try {
    const [payload, group] = await Promise.all([
      fetch(`/api/scan/${name}`).then((r) => r.json()),
      loadObjFromUrl(`/api/scan/${name}/obj`),
    ]);
    showBody(group);
    polylines = payload.polylines || {};
    measurementMeta = payload.measurements || [];
    buildPolylines();
    renderMeasList();
    setHud(`<b>${name}</b> · ${measurementMeta.length} measurements
            · ${Object.keys(polylines).length} curves`);
    setStatus("loaded", "ok");
  } catch (err) {
    console.error(err);
    setStatus("error", "err");
    setHud(`<b>error:</b> ${err.message || err}`);
  }
}

// ---- Upload -----------------------------------------------------------

$("upload").addEventListener("change", async (e) => {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  $("upload-name").textContent = `Uploaded ${f.name} (mesh only, no measurements).`;
  setStatus("loading", "run");
  try {
    const text = await f.text();
    const group = loadObjFromText(text);
    showBody(group);
    polylines = {};
    measurementMeta = [];
    buildPolylines();
    renderMeasList();
    setHud(`<b>${f.name}</b> · uploaded mesh`);
    setStatus("loaded", "ok");
  } catch (err) {
    setStatus("error", "err");
    setHud(`<b>error:</b> ${err.message || err}`);
  }
});

// ---- Render loop + resize ---------------------------------------------

function tick() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();

window.addEventListener("resize", () => {
  renderer.setSize(host.clientWidth, host.clientHeight);
  camera.aspect = host.clientWidth / host.clientHeight;
  camera.updateProjectionMatrix();
});

// ---- Boot -------------------------------------------------------------

refreshScans();
applyPreset(1, false);
setHud(`<b>tip:</b> press 1-5 to switch views · drag to orbit · scroll to zoom`);
