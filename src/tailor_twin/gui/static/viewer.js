// TailorTwin 3D viewer — Three.js scene + measurement overlay toggles.
//
// Picks a scan from a user-chosen results folder (defaults to the
// project's data/results). Each scan = a <prefix>_smplx_fit.npz +
// matching _fit_body.obj pair; the server computes measurement
// polylines on demand from the fit npz.
//
// Keyboard 1..5 → front / 45° front / side / 45° back / back.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";

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
let leadersByCode = {};  // { code: [[[x,y,z],[x,y,z]], ...] }
let polyObjects = {};  // { code: THREE.Line }
let leaderObjects = {};  // { code: [Line2, ...] }
let measurementMeta = [];
let activeCam = 1;
// Codes the user has toggled on. Persists across scan switches so a
// G09 visible on Eric stays visible after picking Oscar (re-applied
// when the new scan finishes loading, if that scan also has G09).
const selectedCodes = new Set();
// Bent-arm pose tracking. The viewer ships two body meshes per scan
// (A-pose + elbow-flexed); polylines are tagged with which pose they
// were computed against. When any bent-arm polyline becomes visible
// the body mesh swaps so the curve lands on the right surface.
let aPoseMesh = null;
let bentArmMesh = null;
const polylinePose = {};  // code -> "a_pose" | "bent_arm"
let currentPose = "a_pose";

function recomputeActivePose() {
  for (const code of selectedCodes) {
    if (polylinePose[code] === "bent_arm") return "bent_arm";
  }
  return "a_pose";
}

function applyPose(newPose) {
  if (newPose === currentPose) return;
  if (newPose === "bent_arm" && !bentArmMesh) return;
  if (aPoseMesh) aPoseMesh.visible = newPose === "a_pose";
  if (bentArmMesh) bentArmMesh.visible = newPose === "bent_arm";
  currentPose = newPose;
}

function showLoader(visible, label = "Loading scan…") {
  const el = $("loader");
  el.querySelector(".loader-label").textContent = label;
  el.hidden = !visible;
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
  // Distance derived from FOV + bounding sphere so the whole figure
  // fits with a small margin regardless of body size. ``radius`` is
  // half the longest bounding-box edge (set in ``frameToBody``).
  const vFov = THREE.MathUtils.degToRad(camera.fov);
  const aspect = camera.aspect || 1;
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
  const limitingFov = Math.min(vFov, hFov);
  const r = (radius / Math.tan(limitingFov / 2)) * 1.25;
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

function disposeMesh(m) {
  if (!m) return;
  scene.remove(m);
  m.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((mat) => mat.dispose());
    }
  });
}

function clearBody() {
  disposeMesh(aPoseMesh);
  disposeMesh(bentArmMesh);
  aPoseMesh = null;
  bentArmMesh = null;
  bodyMesh = null;
  Object.values(polyObjects).forEach((l) => scene.remove(l));
  polyObjects = {};
  Object.values(leaderObjects).flat().forEach((l) => scene.remove(l));
  leaderObjects = {};
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

function smoothMeshes(group) {
  // OBJLoader emits non-indexed geometry with duplicated verts at every
  // face corner; computeVertexNormals on that produces faceted shading.
  // Welding identical positions via mergeVertices gives a shared vertex
  // pool so smooth normals can average across triangles.
  group.traverse((c) => {
    if (c.isMesh) {
      const welded = mergeVertices(c.geometry, 1e-5);
      welded.computeVertexNormals();
      c.geometry.dispose();
      c.geometry = welded;
      c.material = BODY_MATERIAL;
    }
  });
  return group;
}

async function loadObjFromUrl(url) {
  return new Promise((resolve, reject) => {
    new OBJLoader().load(url, (group) => {
      resolve(smoothMeshes(group));
    }, undefined, reject);
  });
}


function showBody(aPoseGroup, bentArmGroup) {
  clearBody();
  aPoseMesh = aPoseGroup;
  scene.add(aPoseMesh);
  if (bentArmGroup) {
    bentArmMesh = bentArmGroup;
    bentArmMesh.visible = false;
    scene.add(bentArmMesh);
  }
  bodyMesh = aPoseMesh;
  currentPose = "a_pose";
  frameToBody();
}

// ---- Polyline overlays ------------------------------------------------

// LineBasicMaterial.linewidth is clamped to 1 on most WebGL drivers,
// so use Line2 + LineMaterial which renders thick lines as screen-space
// triangle strips.
const LINE_RESOLUTION = new THREE.Vector2(
  host.clientWidth, host.clientHeight,
);

function makeLineMaterial() {
  const mat = new LineMaterial({
    color: 0xffd166,
    linewidth: 4,           // pixels
    transparent: true,
    opacity: 0.95,
    depthTest: true,
    worldUnits: false,
  });
  mat.resolution.copy(LINE_RESOLUTION);
  return mat;
}

function makeLeaderMaterial() {
  const mat = new LineMaterial({
    color: 0xffd166,
    linewidth: 1.5,           // pixels
    transparent: true,
    opacity: 0.55,
    dashed: true,
    dashScale: 1,
    dashSize: 0.02,           // world units (line-distance space)
    gapSize: 0.015,
    depthTest: true,
    worldUnits: false,
  });
  mat.resolution.copy(LINE_RESOLUTION);
  return mat;
}

function buildPolylines() {
  Object.values(polyObjects).forEach((l) => scene.remove(l));
  polyObjects = {};
  Object.values(leaderObjects).flat().forEach((l) => scene.remove(l));
  leaderObjects = {};
  for (const [code, pts] of Object.entries(polylines)) {
    if (!pts || pts.length < 2) continue;
    const flat = [];
    for (const [x, y, z] of pts) flat.push(x, y, z);
    const geom = new LineGeometry();
    geom.setPositions(flat);
    const line = new Line2(geom, makeLineMaterial());
    line.computeLineDistances();
    // Re-apply persistent selection so a code that was visible on the
    // previous scan stays visible on this one (when both have it).
    line.visible = selectedCodes.has(code);
    line.userData.code = code;
    scene.add(line);
    polyObjects[code] = line;
  }
  for (const [code, segs] of Object.entries(leadersByCode)) {
    if (!segs) continue;
    const arr = [];
    for (const seg of segs) {
      if (!seg || seg.length < 2) continue;
      const flat = [];
      for (const [x, y, z] of seg) flat.push(x, y, z);
      const geom = new LineGeometry();
      geom.setPositions(flat);
      const line = new Line2(geom, makeLeaderMaterial());
      line.computeLineDistances();
      line.visible = selectedCodes.has(code);
      scene.add(line);
      arr.push(line);
    }
    if (arr.length) leaderObjects[code] = arr;
  }
}

function setPolylineVisible(code, visible) {
  if (visible) selectedCodes.add(code);
  else selectedCodes.delete(code);
  const l = polyObjects[code];
  if (l) l.visible = visible;
  const leads = leaderObjects[code];
  if (leads) leads.forEach((x) => (x.visible = visible));
  applyPose(recomputeActivePose());
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
    let title = `${m.code} — ${m.name}`;
    if (m.formula) {
      title += `\nformula: ${m.formula}`;
    } else if (!m.has_polyline) {
      title += "\nno polyline (extractor did not produce a curve)";
    }
    row.title = title;
    const fxBadge = m.formula
      ? `<span class="fx" title="formula: ${m.formula}">fx</span>` : "";
    const checkedAttr = (m.has_polyline && selectedCodes.has(m.code))
      ? "checked" : "";
    row.innerHTML = `
      <input type="checkbox" data-code="${m.code}"
             ${m.has_polyline ? "" : "disabled"} ${checkedAttr}>
      <span class="code">${m.code}</span>
      <span class="label">${m.name || "—"}</span>
      ${fxBadge}
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

// ---- Results folder + scan picker -------------------------------------

function currentDir() {
  return ($("results-dir").value || "").trim();
}

function dirQuery() {
  const d = currentDir();
  return d ? `?dir=${encodeURIComponent(d)}` : "";
}

async function refreshScans() {
  const status = $("dir-status");
  try {
    const r = await fetch(`/api/scans${dirQuery()}`);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      status.textContent = err.error || `Folder not readable (HTTP ${r.status}).`;
      return;
    }
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
    status.textContent = j.scans.length
      ? `${j.scans.length} scan${j.scans.length === 1 ? "" : "s"} in ${j.dir}`
      : `No scans found in ${j.dir}`;
  } catch (err) {
    status.textContent = "Error: " + (err.message || err);
  }
}

$("scan-picker").addEventListener("change", async (e) => {
  const name = e.target.value;
  if (!name) return;
  await loadScan(name);
});
$("results-dir").addEventListener("change", refreshScans);
$("dir-refresh").addEventListener("click", refreshScans);

// HUD summary measurements — fixed code list (matches Seamly catalog).
const HUD_ROWS = [
  { code: "A01", label: "Height"  },
  { code: "G04", label: "Bust"    },
  { code: "G07", label: "Waist"   },
  { code: "G09", label: "Hip"     },
];

function renderHud(name) {
  const byCode = Object.fromEntries(
    measurementMeta.map((m) => [m.code, m]),
  );
  const lines = HUD_ROWS.map((r) => {
    const m = byCode[r.code];
    const v = m && m.value_cm != null ? m.value_cm.toFixed(1) + " cm" : "—";
    return `<div class="hud-row"><span>${r.label}</span><b>${v}</b></div>`;
  }).join("");
  $("hud").innerHTML = `<div class="hud-name">${name}</div>${lines}`;
}

async function loadScan(name) {
  showLoader(true, `Loading ${name}…`);
  try {
    const q = dirQuery();
    const payload = await fetch(`/api/scan/${name}${q}`).then((r) => r.json());
    const aPoseGroup = await loadObjFromUrl(`/api/scan/${name}/obj${q}`);
    let bentGroup = null;
    if (payload.bent_arm_obj_url) {
      try {
        bentGroup = await loadObjFromUrl(payload.bent_arm_obj_url + q);
      } catch (e) {
        // Bent-arm mesh optional — viewer falls back to A-pose only.
        console.warn("bent-arm mesh missing:", e);
      }
    }
    showBody(aPoseGroup, bentGroup);
    polylines = payload.polylines || {};
    leadersByCode = payload.leaders || {};
    Object.assign(polylinePose, {});  // reset
    for (const k of Object.keys(polylinePose)) delete polylinePose[k];
    Object.assign(polylinePose, payload.polyline_pose || {});
    measurementMeta = payload.measurements || [];
    buildPolylines();
    renderMeasList();
    renderHud(name);
    applyPose(recomputeActivePose());
  } catch (err) {
    console.error(err);
    setHud(`<b style="color:#ff8484">error:</b> ${err.message || err}`);
  } finally {
    showLoader(false);
  }
}

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
  LINE_RESOLUTION.set(host.clientWidth, host.clientHeight);
  Object.values(polyObjects).forEach((l) =>
    l.material.resolution.copy(LINE_RESOLUTION),
  );
  Object.values(leaderObjects).flat().forEach((l) =>
    l.material.resolution.copy(LINE_RESOLUTION),
  );
});

// ---- Boot -------------------------------------------------------------

refreshScans();
applyPreset(1, false);
setHud(`<b>tip:</b> press 1-5 to switch views · drag to orbit · scroll to zoom`);
