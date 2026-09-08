<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import * as THREE from "three";

const props = defineProps({
  variant: { type: String, default: "energy" }, // "energy" | "pc"
  interactive: { type: Boolean, default: false },
});
const emit = defineEmits(["select"]);

const canvasHost = ref(null);
let renderer, scene, camera, animationId, resizeObserver;
let group, particles;
let raycaster, pointer;

function glassMaterial() {
  return new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.08,
    roughness: 0.05,
    metalness: 0,
    transmission: 0.6,
    side: THREE.DoubleSide,
  });
}

function frameEdges(geo, color = 0xd8d0c4) {
  const edges = new THREE.EdgesGeometry(geo);
  return new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color }));
}

function makeFan(radius = 0.26) {
  const fanGroup = new THREE.Group();

  const glowGeo = new THREE.CircleGeometry(radius * 0.82, 24);
  const glowMat = new THREE.MeshStandardMaterial({
    color: 0xff8a3d,
    emissive: 0xff8a3d,
    emissiveIntensity: 0.9,
    roughness: 0.6,
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  fanGroup.add(glow);

  const ringGeo = new THREE.TorusGeometry(radius, 0.02, 10, 32);
  const ringMat = new THREE.MeshStandardMaterial({ color: 0xe8e1d6, roughness: 0.4, metalness: 0.3 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  fanGroup.add(ring);

  const hubGeo = new THREE.CircleGeometry(radius * 0.22, 16);
  const hubMat = new THREE.MeshStandardMaterial({ color: 0xf3efe8, roughness: 0.5 });
  const hub = new THREE.Mesh(hubGeo, hubMat);
  hub.position.z = 0.01;
  fanGroup.add(hub);

  return fanGroup;
}

function buildEnergyScene() {
  group = new THREE.Group();

  const coreGeo = new THREE.IcosahedronGeometry(1.15, 1);
  const coreMat = new THREE.MeshStandardMaterial({
    color: 0xff5a1f,
    emissive: 0xff8a3d,
    emissiveIntensity: 0.35,
    roughness: 0.25,
    metalness: 0.15,
    flatShading: true,
  });
  const core = new THREE.Mesh(coreGeo, coreMat);
  group.add(core);

  const ringGeo = new THREE.TorusGeometry(1.75, 0.035, 16, 100);
  const ringMat = new THREE.MeshStandardMaterial({ color: 0xffb03a, roughness: 0.4, metalness: 0.3 });
  const ring1 = new THREE.Mesh(ringGeo, ringMat);
  ring1.rotation.x = Math.PI / 2.4;
  const ring2 = new THREE.Mesh(ringGeo, ringMat.clone());
  ring2.rotation.x = Math.PI / 1.6;
  ring2.scale.setScalar(0.75);
  group.add(ring1, ring2);

  return { bob: true };
}

/* Stylized low-poly version of the demo unit's actual PC case: white
 * tempered-glass tower, amber/orange fan lighting, GPU + RAM + a bent
 * liquid-cooler tube - not a literal photoreal model, but recognizable as
 * "this PC" rather than a generic industrial motif. */
function buildPCScene() {
  group = new THREE.Group();

  const caseW = 1.5, caseH = 2.0, caseD = 1.3;

  const glassGeo = new THREE.BoxGeometry(caseW, caseH, caseD);
  const glass = new THREE.Mesh(glassGeo, glassMaterial());
  glass.name = "pc-case";
  group.add(glass);
  group.add(frameEdges(glassGeo));

  // Right-side fan bank (3 fans stacked)
  const rightFans = new THREE.Group();
  for (let i = 0; i < 3; i++) {
    const fan = makeFan(0.24);
    fan.rotation.y = Math.PI / 2;
    fan.position.set(caseW / 2 + 0.01, 0.55 - i * 0.5, 0);
    rightFans.add(fan);
  }
  group.add(rightFans);

  // Bottom-front fan row
  const bottomFans = new THREE.Group();
  for (let i = 0; i < 2; i++) {
    const fan = makeFan(0.24);
    fan.position.set(-0.3 + i * 0.6, -caseH / 2 + 0.05, caseD / 2 - 0.35);
    bottomFans.add(fan);
  }
  group.add(bottomFans);

  // GPU block with a red accent stripe
  const gpuGeo = new THREE.BoxGeometry(1.0, 0.24, 0.55);
  const gpuMat = new THREE.MeshStandardMaterial({ color: 0xf1ede5, roughness: 0.4, metalness: 0.25 });
  const gpu = new THREE.Mesh(gpuGeo, gpuMat);
  gpu.position.set(-0.1, -0.15, 0.15);
  group.add(gpu);

  const stripeGeo = new THREE.BoxGeometry(1.0, 0.045, 0.02);
  const stripeMat = new THREE.MeshStandardMaterial({ color: 0xe5432c, emissive: 0xe5432c, emissiveIntensity: 0.4 });
  const stripe = new THREE.Mesh(stripeGeo, stripeMat);
  stripe.position.set(-0.1, -0.05, 0.42);
  group.add(stripe);

  // RAM sticks
  const ramMat = new THREE.MeshStandardMaterial({ color: 0xf5f1ea, roughness: 0.5 });
  for (let i = 0; i < 2; i++) {
    const ram = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.55, 0.32), ramMat);
    ram.position.set(0.35 + i * 0.09, 0.35, -0.05);
    group.add(ram);
  }

  // CPU liquid-cooler tube (bent) + radiator block up top
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.0, 0.75, 0.1),
    new THREE.Vector3(0.25, 0.55, 0.3),
    new THREE.Vector3(0.15, 0.25, 0.15),
    new THREE.Vector3(-0.05, 0.15, -0.05),
  ]);
  const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.035, 8, false);
  const tubeMat = new THREE.MeshStandardMaterial({ color: 0xf3efe8, roughness: 0.35, metalness: 0.15 });
  group.add(new THREE.Mesh(tubeGeo, tubeMat));

  // Small "readout" glow panel (echoes the case's real temp LCD)
  const panelGeo = new THREE.CircleGeometry(0.14, 24);
  const panelMat = new THREE.MeshStandardMaterial({ color: 0x6fb0ff, emissive: 0x6fb0ff, emissiveIntensity: 0.8 });
  const panel = new THREE.Mesh(panelGeo, panelMat);
  panel.position.set(-0.05, 0.15, caseD / 2 + 0.001);
  group.add(panel);

  // Top intake fans
  const topFans = new THREE.Group();
  for (let i = 0; i < 2; i++) {
    const fan = makeFan(0.24);
    fan.rotation.x = Math.PI / 2;
    fan.position.set(-0.3 + i * 0.6, caseH / 2 - 0.02, 0);
    topFans.add(fan);
  }
  group.add(topFans);

  group.rotation.y = -0.5;
  return { bob: true };
}

function buildParticles() {
  const count = 60;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = 2.2 + Math.random() * 1.4;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.6;
    positions[i * 3 + 2] = r * Math.cos(phi);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({ color: 0xffb03a, size: 0.035, transparent: true, opacity: 0.7 });
  return new THREE.Points(geo, mat);
}

function onPointerDown(event) {
  if (!props.interactive) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(group.children, true);
  if (hits.length > 0) {
    emit("select");
  }
}

onMounted(() => {
  const host = canvasHost.value;
  const width = host.clientWidth;
  const height = host.clientHeight;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
  camera.position.set(0, 0.4, 5.5);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  if (props.interactive) renderer.domElement.style.cursor = "pointer";
  host.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(3, 4, 5);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffb03a, 0.5);
  rim.position.set(-3, -2, -4);
  scene.add(rim);

  const opts = props.variant === "pc" ? buildPCScene() : buildEnergyScene();
  scene.add(group);

  particles = buildParticles();
  scene.add(particles);

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();
  renderer.domElement.addEventListener("pointerdown", onPointerDown);

  let t = 0;
  const animate = () => {
    t += 0.01;
    group.rotation.y += 0.004;
    if (opts.bob) group.position.y = Math.sin(t) * 0.08;
    particles.rotation.y -= 0.0015;
    renderer.render(scene, camera);
    animationId = requestAnimationFrame(animate);
  };
  animate();

  resizeObserver = new ResizeObserver(() => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  resizeObserver.observe(host);
});

onUnmounted(() => {
  cancelAnimationFrame(animationId);
  resizeObserver?.disconnect();
  renderer?.domElement?.removeEventListener("pointerdown", onPointerDown);
  renderer?.dispose();
  if (renderer?.domElement?.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
});
</script>

<template>
  <div ref="canvasHost" class="three-hero" aria-hidden="true"></div>
</template>

<style scoped>
.three-hero {
  width: 100%;
  height: 100%;
  min-height: 220px;
}

.three-hero :deep(canvas) {
  display: block;
}
</style>
