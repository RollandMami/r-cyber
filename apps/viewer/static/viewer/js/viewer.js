/**
 * viewer.js — Moteur Three.js corrigé
 * - Axe IFC Z→Y (rotation -90° X sur le groupe racine)
 * - OrbitControls complet (orbite, pan shift+drag, zoom molette, pinch touch)
 * - Types IFC étendus (sanitaire, mobilier, MEP, etc.)
 */

let scene, camera, renderer, orbitControls;
let navMode = 'orbit'; // 'orbit' | 'pan'
let raycaster, mouse;
let allMeshes = [];
let apiBaseUrl = '';

const TYPE_COLORS = {
    IfcWall:0xd4c5b0,IfcWallStandardCase:0xd4c5b0,IfcSlab:0x9e9e9e,
    IfcRoof:0x8d6e63,IfcColumn:0xa0522d,IfcBeam:0x8b6914,
    IfcFooting:0x757575,IfcPile:0x616161,IfcMember:0x795548,
    IfcDoor:0x6d4c41,IfcWindow:0x90caf9,
    IfcStair:0xbcaaa4,IfcStairFlight:0xbcaaa4,IfcRamp:0xb0bec5,IfcRampFlight:0xb0bec5,
    IfcSanitaryTerminal:0xe0f7fa,IfcFlowTerminal:0xb2ebf2,
    IfcFurnishingElement:0xffe082,IfcFurniture:0xffd54f,
    IfcFlowSegment:0xef9a9a,IfcFlowFitting:0xef9a9a,IfcFlowController:0xf48fb1,
    IfcEnergyConversionDevice:0xce93d8,IfcDistributionControlElement:0xb39ddb,
    IfcElectricAppliance:0xffe0b2,IfcLightFixture:0xfff9c4,
    IfcCovering:0xd7ccc8,IfcCurtainWall:0xb3e5fc,
    IfcSpace:0x80cbc4,IfcBuildingElementProxy:0xaaaaaa,
    default:0xcccccc,
};

const COLOR_DIM = 0x334455;

function initViewer(canvasId, jsonUrl, apiUrl) {
    apiBaseUrl = apiUrl;
    const canvas = document.getElementById(canvasId);

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    scene.fog = new THREE.FogExp2(0x1a1a2e, 0.0015);

    // Groupe racine — correction axe IFC (Z up) → Three.js (Y up)
    const root = new THREE.Group();
    root.rotation.x = -Math.PI / 2;
    scene.add(root);
    window._viewerRoot = root;

    camera = new THREE.PerspectiveCamera(50, canvas.clientWidth / canvas.clientHeight, 0.01, 10000);
    camera.position.set(15, 12, 20);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    _setupLights();
    scene.add(new THREE.GridHelper(500, 50, 0x333355, 0x222233));
    _setupOrbitControls(canvas);

    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    canvas.addEventListener('mousemove', _onMouseMove);
    window.addEventListener('resize', _onResize);

    _loadModel(jsonUrl);
    _animate();
}

function _loadModel(jsonUrl) {
    fetch(jsonUrl)
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(data => { _buildScene(data); document.getElementById('loading-overlay').style.display = 'none'; })
        .catch(err => {
            document.getElementById('loading-overlay').innerHTML =
                '<i class="fas fa-exclamation-triangle" style="font-size:2rem;color:#e57c2a;margin-bottom:1rem;"></i>' +
                '<p style="color:rgba(255,255,255,0.7);font-size:0.9rem;text-align:center;">' + err.message + '</p>';
        });
}

function _buildScene(data) {
    allMeshes = [];
    const root = window._viewerRoot;
    data.etages.forEach(etage => {
        const g = new THREE.Group();
        g.userData = { etageId: etage.id, etageGuid: etage.ifc_guid };
        if (etage.geometrie && etage.geometrie.meshes) {
            etage.geometrie.meshes.forEach(md => {
                const mesh = _buildMesh(md, etage);
                if (mesh) { g.add(mesh); allMeshes.push({ mesh, ifcGuid: md.ifc_guid, typeIfc: md.type_ifc, etageId: etage.id, etageNom: etage.nom }); }
            });
        }
        root.add(g);
    });
    _fitCameraToScene();
}

function _buildMesh(md, etage) {
    if (!md.vertices || !md.indices || md.vertices.length < 9 || md.indices.length < 3) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(md.vertices, 3));
    geo.setIndex(md.indices);
    geo.computeVertexNormals();
    const color = TYPE_COLORS[md.type_ifc] || TYPE_COLORS.default;
    const isWin = md.type_ifc === 'IfcWindow';
    const isSpc = md.type_ifc === 'IfcSpace';
    const mat = new THREE.MeshLambertMaterial({
        color, transparent: isWin || isSpc,
        opacity: isWin ? 0.3 : isSpc ? 0.1 : 1.0,
        side: THREE.DoubleSide, depthWrite: !(isWin || isSpc),
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.castShadow = !isSpc; mesh.receiveShadow = true;
    mesh.userData = { ifcGuid: md.ifc_guid, typeIfc: md.type_ifc, etageId: etage.id, etageNom: etage.nom,
        baseColor: color, baseOpacity: isWin ? 0.3 : isSpc ? 0.1 : 1.0, baseTrans: isWin || isSpc };
    return mesh;
}

// ── Filtres ───────────────────────────────────────────────────
function filtrerEtage(etagePk, btn) {
    document.querySelectorAll('.etage-btn,.piece-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-tout').classList.remove('active');
    if (btn) btn.classList.add('active');
    if (!etagePk) { allMeshes.forEach(({ mesh }) => _restoreMesh(mesh)); document.getElementById('btn-tout').classList.add('active'); return; }
    allMeshes.forEach(({ mesh }) => String(mesh.userData.etageId) === String(etagePk) ? _restoreMesh(mesh) : _dimMesh(mesh));
}

function filtrerPiece(btn, pieceGuid) {
    document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!pieceGuid) return;
    allMeshes.forEach(({ mesh }) => mesh.userData.ifcGuid === pieceGuid ? _restoreMesh(mesh) : _dimMesh(mesh));
}

function toggleEtage(btn, etagePk) {
    const el = document.getElementById('pieces-' + etagePk);
    filtrerEtage(etagePk, btn);
    const open = btn.classList.toggle('open');
    if (el) el.classList.toggle('open', open);
}

function _restoreMesh(m) {
    m.visible = true;
    m.material.color.setHex(m.userData.baseColor);
    m.material.opacity = m.userData.baseOpacity;
    m.material.transparent = m.userData.baseTrans;
    m.material.depthWrite = !m.userData.baseTrans;
}

function _dimMesh(m) {
    m.material.color.setHex(COLOR_DIM);
    m.material.opacity = 0.04;
    m.material.transparent = true;
    m.material.depthWrite = false;
}

// ── Caméra ────────────────────────────────────────────────────
function setCameraMode(mode) {
    document.getElementById('btn-perspective').classList.toggle('active', mode === 'perspective');
    document.getElementById('btn-top').classList.toggle('active', mode === 'top');
    const t = orbitControls.target;
    if (mode === 'top') { camera.position.set(t.x, t.y + 80, t.z + 0.01); }
    else                { camera.position.set(t.x + 15, t.y + 12, t.z + 20); }
    camera.lookAt(t); orbitControls._sync();
}

function resetCamera() {
    document.querySelectorAll('.etage-btn,.piece-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-tout').classList.add('active');
    allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
    _fitCameraToScene();
}

function setNavMode(mode) {
    navMode = mode;
    const btnOrbit = document.getElementById('btn-orbit');
    const btnPan   = document.getElementById('btn-pan');
    if (btnOrbit) btnOrbit.classList.toggle('active', mode === 'orbit');
    if (btnPan)   btnPan.classList.toggle('active',   mode === 'pan');
    // Change le curseur du canvas
    const canvas = renderer ? renderer.domElement : null;
    if (canvas) canvas.style.cursor = mode === 'pan' ? 'grab' : 'default';
}

function _fitCameraToScene() {
    if (!allMeshes.length) return;
    const box = new THREE.Box3();
    allMeshes.forEach(({ mesh }) => { mesh.geometry.computeBoundingBox(); const b = mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld); box.union(b); });
    const center = box.getCenter(new THREE.Vector3());
    const size   = box.getSize(new THREE.Vector3());
    const dist   = Math.max(size.x, size.y, size.z) * 1.5;
    orbitControls.target.copy(center);
    camera.position.set(center.x + dist * 0.6, center.y + dist * 0.5, center.z + dist * 0.8);
    camera.near = dist * 0.001; camera.far = dist * 100; camera.updateProjectionMatrix();
    camera.lookAt(center); orbitControls._sync();
}

// ── OrbitControls ─────────────────────────────────────────────
function _setupOrbitControls(canvas) {
    const s = { target: new THREE.Vector3(), radius: 30, theta: Math.PI/4, phi: Math.PI/3, drag: false, mid: false, px: 0, py: 0, pinch: 0 };

    function update() {
        camera.position.set(
            s.target.x + s.radius * Math.sin(s.phi) * Math.sin(s.theta),
            s.target.y + s.radius * Math.cos(s.phi),
            s.target.z + s.radius * Math.sin(s.phi) * Math.cos(s.theta)
        );
        camera.lookAt(s.target);
    }

    function sync() {
        const d = camera.position.clone().sub(s.target);
        s.radius = d.length();
        s.phi    = Math.acos(Math.max(-1, Math.min(1, d.y / s.radius)));
        s.theta  = Math.atan2(d.x, d.z);
        update();
    }

    orbitControls = { target: s.target, _sync: sync };

    canvas.addEventListener('mousedown', e => { s.drag = true; s.mid = e.button === 1; s.px = e.clientX; s.py = e.clientY; e.preventDefault(); });
    window.addEventListener('mouseup',   () => { s.drag = false; });
    window.addEventListener('mousemove', e => {
        if (!s.drag) return;
        const dx = e.clientX - s.px, dy = e.clientY - s.py;
        s.px = e.clientX; s.py = e.clientY;
        if (s.mid || e.shiftKey || navMode === 'pan') {
            // Mode PAN — déplace le point cible
            const right = new THREE.Vector3(), up = new THREE.Vector3();
            camera.matrix.extractBasis(right, up, new THREE.Vector3());
            const sp = s.radius * 0.001;
            s.target.addScaledVector(right, -dx * sp);
            s.target.addScaledVector(up,     dy * sp);
        } else {
            // Mode ORBIT
            s.theta -= dx * 0.008;
            s.phi = Math.max(0.05, Math.min(Math.PI - 0.05, s.phi + dy * 0.008));
        }
        update();
    });
    canvas.addEventListener('wheel', e => { e.preventDefault(); s.radius = Math.max(0.1, s.radius * (e.deltaY > 0 ? 1.12 : 0.89)); update(); }, { passive: false });
    canvas.addEventListener('touchstart', e => {
        if (e.touches.length === 1) { s.drag = true; s.px = e.touches[0].clientX; s.py = e.touches[0].clientY; }
        if (e.touches.length === 2) s.pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    }, { passive: true });
    canvas.addEventListener('touchend', () => { s.drag = false; });
    canvas.addEventListener('touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 1 && s.drag) {
            const dx = e.touches[0].clientX - s.px;
            const dy = e.touches[0].clientY - s.py;
            if (navMode === 'pan') {
                // Pan tactile
                const right = new THREE.Vector3(), up = new THREE.Vector3();
                camera.matrix.extractBasis(right, up, new THREE.Vector3());
                const sp = s.radius * 0.002;
                s.target.addScaledVector(right, -dx * sp);
                s.target.addScaledVector(up,     dy * sp);
            } else {
                s.theta -= dx * 0.01;
                s.phi = Math.max(0.05, Math.min(Math.PI - 0.05, s.phi + dy * 0.01));
            }
            s.px = e.touches[0].clientX; s.py = e.touches[0].clientY; update();
        }
        if (e.touches.length === 2) {
            const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
            s.radius = Math.max(0.1, s.radius * (1 + (s.pinch - d) * 0.01));
            s.pinch = d; update();
        }
    }, { passive: false });
    update();
}

// ── Lumières ──────────────────────────────────────────────────
function _setupLights() {
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const sun = new THREE.DirectionalLight(0xfff5e0, 1.2);
    sun.position.set(50, 80, 50); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = sun.shadow.camera.bottom = -100;
    sun.shadow.camera.right = sun.shadow.camera.top = 100;
    sun.shadow.camera.far = 500;
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0xc8d8ff, 0.35);
    fill.position.set(-30, 20, -30); scene.add(fill);
}

// ── Raycasting ────────────────────────────────────────────────
function _onMouseMove(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
    mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(allMeshes.map(m => m.mesh).filter(m => m.visible));
    const info = document.getElementById('hover-info');
    if (hits.length) {
        const d = hits[0].object.userData;
        info.style.display = 'block';
        document.getElementById('hover-info-text').textContent = (d.typeIfc || '—') + '  ·  ' + (d.etageNom || '');
    } else { info.style.display = 'none'; }
}

function _onResize() {
    const c = renderer.domElement;
    camera.aspect = c.clientWidth / c.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(c.clientWidth, c.clientHeight, false);
}

function _animate() { requestAnimationFrame(_animate); renderer.render(scene, camera); }

// ── Réception des filtres depuis la page parent (onglet Plan du site) ─────────
window.addEventListener('message', function(event) {
    if (!event.data || event.data.type !== 'FILTER_ETAGE') return;
    const { etage, piece } = event.data;

    if (etage === 'ext') {
        // Espace extérieur / plan de masse → vue de dessus, tout visible
        allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
        setCameraMode('top');
        return;
    }

    if (piece) {
        filtrerPiece(null, piece);
    } else if (etage) {
        // Cherche l'etagePk depuis le guid
        const m = allMeshes.find(x => x.mesh.userData.etageGuid === etage || String(x.etageId) === String(etage));
        if (m) {
            filtrerEtage(m.etageId, null);
        } else {
            allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
        }
    } else {
        // Tout afficher
        allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
    }
});
