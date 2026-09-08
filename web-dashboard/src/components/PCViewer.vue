<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/* Product-viewer style 3D model of the demo unit's PC (the "machine" being
 * monitored): dual-glass fishtank case, white frame, amber-lit fans that
 * actually spin, GPU + AIO + motherboard inside. Drag to orbit, click the
 * case to toggle its live readings. All procedural geometry - no external
 * model asset to load. */

const emit = defineEmits(["select"]);

const host = ref(null);
let renderer, scene, camera, controls, animationId, resizeObserver, pmrem;
let pcGroup, raycaster, pointer;
let pointerDownAt = null;
const spinners = []; // fan blade groups
const glowMats = []; // emissive materials that pulse

/* ---------- materials ---------- */
const MAT = {};
function initMaterials() {
  MAT.white = new THREE.MeshStandardMaterial({ color: 0xf2efe9, roughness: 0.45, metalness: 0.12 });
  MAT.whiteSoft = new THREE.MeshStandardMaterial({ color: 0xe9e5dd, roughness: 0.6, metalness: 0.05 });
  MAT.metal = new THREE.MeshStandardMaterial({ color: 0xd9d4ca, roughness: 0.28, metalness: 0.75 });
  MAT.dark = new THREE.MeshStandardMaterial({ color: 0x23262b, roughness: 0.55, metalness: 0.35 });
  MAT.pcb = new THREE.MeshStandardMaterial({ color: 0x1b2430, roughness: 0.7, metalness: 0.2 });
  MAT.glass = new THREE.MeshPhysicalMaterial({
    color: 0xdfe8f0,
    roughness: 0.04,
    metalness: 0,
    transmission: 0.96,
    thickness: 0.04,
    transparent: true,
    opacity: 0.18,
    side: THREE.DoubleSide,
  });
  MAT.amber = new THREE.MeshStandardMaterial({
    color: 0xff7a2f,
    emissive: 0xff7a2f,
    emissiveIntensity: 1.5,
    roughness: 0.4,
  });
  MAT.amberSoft = new THREE.MeshStandardMaterial({
    color: 0xffa153,
    emissive: 0xff8a3d,
    emissiveIntensity: 0.9,
    roughness: 0.6,
  });
  MAT.screen = new THREE.MeshStandardMaterial({
    color: 0x7fc4ff,
    emissive: 0x5fb0ff,
    emissiveIntensity: 1.2,
    roughness: 0.3,
  });
  MAT.accentRed = new THREE.MeshStandardMaterial({
    color: 0xe0402c,
    emissive: 0xe0402c,
    emissiveIntensity: 0.5,
    roughness: 0.5,
  });
  glowMats.push(MAT.amber, MAT.amberSoft);
}

function box(w, h, d, mat, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/* ---------- a single 120mm fan: frame, spinning blades, RGB ring ---------- */
function makeFan(size = 0.42) {
  const g = new THREE.Group();
  const t = size * 0.09;

  // square frame
  const half = size / 2;
  for (const [x, y, w, h] of [
    [0, half - t / 2, size, t],
    [0, -half + t / 2, size, t],
    [-half + t / 2, 0, t, size - t * 2],
    [half - t / 2, 0, t, size - t * 2],
  ]) {
    g.add(box(w, h, size * 0.16, MAT.white, x, y, 0));
  }

  // glowing RGB ring on the intake face
  const ring = new THREE.Mesh(new THREE.TorusGeometry(size * 0.44, size * 0.035, 12, 40), MAT.amber);
  ring.position.z = size * 0.085;
  g.add(ring);

  // inner diffuse glow disc
  const glow = new THREE.Mesh(new THREE.CircleGeometry(size * 0.42, 28), MAT.amberSoft);
  glow.position.z = -size * 0.06;
  g.add(glow);

  // spinning blades
  const blades = new THREE.Group();
  const bladeGeo = new THREE.BoxGeometry(size * 0.36, size * 0.13, size * 0.012);
  for (let i = 0; i < 9; i++) {
    const b = new THREE.Mesh(bladeGeo, MAT.whiteSoft);
    b.position.set(size * 0.21, 0, 0);
    b.rotation.z = 0.5;
    const arm = new THREE.Group();
    arm.add(b);
    arm.rotation.z = (i / 9) * Math.PI * 2;
    blades.add(arm);
  }
  blades.position.z = size * 0.02;
  g.add(blades);
  spinners.push({ obj: blades, speed: 0.06 + Math.random() * 0.02 });

  // hub
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(size * 0.13, size * 0.13, size * 0.06, 20), MAT.white);
  hub.rotation.x = Math.PI / 2;
  hub.position.z = size * 0.04;
  g.add(hub);

  return g;
}

/* ---------- the case ---------- */
function buildPC() {
  const G = new THREE.Group();
  const W = 1.45, H = 1.9, D = 1.5;
  const f = 0.05; // frame bar thickness

  // --- frame bars (12 edges) ---
  const hx = W / 2, hy = H / 2, hz = D / 2;
  const bars = [
    [W, f, f, 0, hy, hz], [W, f, f, 0, hy, -hz], [W, f, f, 0, -hy, hz], [W, f, f, 0, -hy, -hz],
    [f, H, f, hx, 0, hz], [f, H, f, hx, 0, -hz], [f, H, f, -hx, 0, hz], [f, H, f, -hx, 0, -hz],
    [f, f, D, hx, hy, 0], [f, f, D, -hx, hy, 0], [f, f, D, hx, -hy, 0], [f, f, D, -hx, -hy, 0],
  ];
  for (const [w, h, d, x, y, z] of bars) G.add(box(w, h, d, MAT.white, x, y, z));

  // --- panels: front + right glass (fishtank corner), left/back/top/bottom solid ---
  const glassFront = new THREE.Mesh(new THREE.PlaneGeometry(W - f, H - f), MAT.glass);
  glassFront.position.z = hz;
  G.add(glassFront);

  const glassRight = new THREE.Mesh(new THREE.PlaneGeometry(D - f, H - f), MAT.glass);
  glassRight.rotation.y = Math.PI / 2;
  glassRight.position.x = hx;
  G.add(glassRight);

  G.add(box(W, H, 0.03, MAT.white, 0, 0, -hz));           // back
  G.add(box(0.03, H, D, MAT.white, -hx, 0, 0));            // left
  G.add(box(W, 0.06, D, MAT.white, 0, hy, 0));             // top
  G.add(box(W, 0.06, D, MAT.white, 0, -hy, 0));            // bottom

  // feet
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    G.add(box(0.12, 0.07, 0.12, MAT.dark, sx * (hx - 0.16), -hy - 0.05, sz * (hz - 0.16)));
  }

  // --- motherboard on the left inner wall ---
  const mb = box(0.02, 1.15, 1.05, MAT.pcb, -hx + 0.09, 0.12, -0.08);
  G.add(mb);
  // chipset / M.2 heatsinks
  G.add(box(0.05, 0.3, 0.16, MAT.metal, -hx + 0.13, -0.15, 0.1));
  G.add(box(0.05, 0.16, 0.5, MAT.metal, -hx + 0.13, 0.3, -0.3));
  // IO shroud
  G.add(box(0.06, 0.42, 0.2, MAT.whiteSoft, -hx + 0.13, 0.5, -0.42));

  // RAM sticks with lit tops
  for (let i = 0; i < 4; i++) {
    const z = -0.02 + i * 0.075;
    G.add(box(0.045, 0.42, 0.035, MAT.whiteSoft, -hx + 0.17, 0.42, z));
    const lit = box(0.05, 0.03, 0.04, MAT.amber, -hx + 0.17, 0.64, z);
    G.add(lit);
  }

  // --- AIO pump block on CPU + round display ---
  const pump = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.12, 28), MAT.white);
  pump.rotation.z = Math.PI / 2;
  pump.position.set(-hx + 0.25, 0.42, -0.42);
  G.add(pump);
  const disp = new THREE.Mesh(new THREE.CircleGeometry(0.13, 28), MAT.screen);
  disp.rotation.y = Math.PI / 2;
  disp.position.set(-hx + 0.32, 0.42, -0.42);
  G.add(disp);

  // AIO tubes up to the top radiator
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-hx + 0.28, 0.55, -0.36),
    new THREE.Vector3(-hx + 0.34, 0.78, -0.2),
    new THREE.Vector3(-hx + 0.3, 0.92, -0.05),
  ]);
  const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.035, 10, false), MAT.whiteSoft);
  G.add(tube);
  const curve2 = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-hx + 0.28, 0.55, -0.52),
    new THREE.Vector3(-hx + 0.38, 0.8, -0.42),
    new THREE.Vector3(-hx + 0.3, 0.92, -0.3),
  ]);
  G.add(new THREE.Mesh(new THREE.TubeGeometry(curve2, 24, 0.035, 10, false), MAT.whiteSoft));

  // top radiator
  G.add(box(0.55, 0.1, 1.05, MAT.metal, -0.25, hy - 0.14, -0.1));

  // --- fans: 3 top, 3 right-side intake, 2 bottom ---
  for (let i = 0; i < 2; i++) {
    const fan = makeFan(0.42);
    fan.rotation.x = -Math.PI / 2;
    fan.position.set(-0.28, hy - 0.26, -0.42 + i * 0.5);
    G.add(fan);
  }
  for (let i = 0; i < 3; i++) {
    const fan = makeFan(0.44);
    fan.rotation.y = Math.PI / 2;
    fan.position.set(hx - 0.1, 0.6 - i * 0.52, -0.02);
    G.add(fan);
  }
  for (let i = 0; i < 2; i++) {
    const fan = makeFan(0.4);
    fan.rotation.x = Math.PI / 2;
    fan.position.set(-0.3 + i * 0.5, -hy + 0.2, 0.22);
    G.add(fan);
  }

  // --- GPU: shroud + backplate + fans + accent ---
  const gpu = box(0.95, 0.2, 0.5, MAT.whiteSoft, -0.15, -0.28, 0.16);
  G.add(gpu);
  G.add(box(0.95, 0.03, 0.5, MAT.metal, -0.15, -0.39, 0.16)); // backplate
  G.add(box(0.5, 0.035, 0.02, MAT.accentRed, -0.05, -0.19, 0.41)); // logo stripe
  for (let i = 0; i < 2; i++) {
    const c = new THREE.Mesh(new THREE.CircleGeometry(0.11, 22), MAT.dark);
    c.rotation.x = -Math.PI / 2;
    c.position.set(-0.42 + i * 0.42, -0.18, 0.16);
    G.add(c);
  }
  // PCIe riser bracket
  G.add(box(0.06, 0.34, 0.5, MAT.metal, 0.35, -0.42, 0.16));

  // --- PSU shroud + cables ---
  G.add(box(W - 0.12, 0.3, 0.55, MAT.white, 0, -hy + 0.22, -0.42));
  const cableCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.1, -0.5, -0.2),
    new THREE.Vector3(0.05, -0.2, 0.05),
    new THREE.Vector3(-0.3, -0.05, 0.1),
    new THREE.Vector3(-hx + 0.2, 0.15, -0.1),
  ]);
  G.add(new THREE.Mesh(new THREE.TubeGeometry(cableCurve, 30, 0.045, 8, false), MAT.whiteSoft));
  const cable2 = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.15, -0.5, -0.25),
    new THREE.Vector3(0.2, -0.3, 0.15),
    new THREE.Vector3(-0.1, -0.22, 0.3),
  ]);
  G.add(new THREE.Mesh(new THREE.TubeGeometry(cable2, 24, 0.03, 8, false), MAT.accentRed));

  // --- RGB light strips along the front vertical frame ---
  for (const x of [-hx + 0.06, hx - 0.06]) {
    const strip = box(0.02, H - 0.3, 0.02, MAT.amber, x, 0, hz - 0.04);
    G.add(strip);
  }

  return G;
}

/* ---------- click vs drag ---------- */
function onPointerDown(e) {
  pointerDownAt = { x: e.clientX, y: e.clientY };
}
function onPointerUp(e) {
  if (!pointerDownAt) return;
  const moved = Math.hypot(e.clientX - pointerDownAt.x, e.clientY - pointerDownAt.y);
  pointerDownAt = null;
  if (moved > 5) return; // it was a drag, not a click

  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  if (raycaster.intersectObjects(pcGroup.children, true).length > 0) emit("select");
}

onMounted(() => {
  const el = host.value;
  const w = el.clientWidth || 600;
  const h = el.clientHeight || 380;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.style.cursor = "grab";
  el.appendChild(renderer.domElement);

  scene = new THREE.Scene();

  // studio environment for believable glass/metal reflections
  pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  camera = new THREE.PerspectiveCamera(35, w / h, 0.1, 100);
  camera.position.set(2.2, 1.1, 2.7);

  initMaterials();
  pcGroup = buildPC();
  scene.add(pcGroup);

  // lighting
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8cfc2, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 2.1);
  key.position.set(3.5, 5, 4);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far = 20;
  key.shadow.camera.left = -4;
  key.shadow.camera.right = 4;
  key.shadow.camera.top = 4;
  key.shadow.camera.bottom = -4;
  key.shadow.bias = -0.0005;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffd9b0, 0.6);
  fill.position.set(-4, 1.5, 2);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xff8a3d, 0.9);
  rim.position.set(-2, 0.5, -4);
  scene.add(rim);

  // contact shadow floor
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(14, 14),
    new THREE.ShadowMaterial({ opacity: 0.16 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1.05;
  floor.receiveShadow = true;
  scene.add(floor);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enablePan = false;
  controls.minDistance = 2.2;
  controls.maxDistance = 6;
  controls.minPolarAngle = 0.5;
  controls.maxPolarAngle = Math.PI / 1.9;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.9;
  controls.target.set(0, 0.05, 0);
  controls.addEventListener("start", () => {
    controls.autoRotate = false;
    renderer.domElement.style.cursor = "grabbing";
  });
  controls.addEventListener("end", () => {
    renderer.domElement.style.cursor = "grab";
  });

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();
  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);

  let t = 0;
  const animate = () => {
    t += 0.016;
    for (const s of spinners) s.obj.rotation.z += s.speed;
    const pulse = 0.85 + Math.sin(t * 1.6) * 0.25;
    MAT.amber.emissiveIntensity = 1.5 * pulse;
    MAT.amberSoft.emissiveIntensity = 0.9 * pulse;
    controls.update();
    renderer.render(scene, camera);
    animationId = requestAnimationFrame(animate);
  };
  animate();

  resizeObserver = new ResizeObserver(() => {
    const nw = el.clientWidth, nh = el.clientHeight;
    if (!nw || !nh) return;
    camera.aspect = nw / nh;
    camera.updateProjectionMatrix();
    renderer.setSize(nw, nh);
  });
  resizeObserver.observe(el);
});

onUnmounted(() => {
  cancelAnimationFrame(animationId);
  resizeObserver?.disconnect();
  controls?.dispose();
  renderer?.domElement?.removeEventListener("pointerdown", onPointerDown);
  renderer?.domElement?.removeEventListener("pointerup", onPointerUp);
  pmrem?.dispose();
  renderer?.dispose();
  if (renderer?.domElement?.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
});
</script>

<template>
  <div ref="host" class="pc-viewer"></div>
</template>

<style scoped>
.pc-viewer {
  width: 100%;
  height: 100%;
  min-height: 300px;
  touch-action: none;
}

.pc-viewer :deep(canvas) {
  display: block;
}
</style>
