/**
 * viewer.js — Moteur Three.js pour la visualisation IFC
 * Gère : chargement JSON, rendu, orbite caméra, filtres étage / pièce
 */

// ── Variables globales du viewer ─────────────────────────────
let scene, camera, renderer, controls;
let raycaster, mouse;
let allMeshes   = [];      // { mesh, ifcGuid, typeIfc, etageId, etageGuid }
let apiBaseUrl  = '';
let currentMode = 'perspective';

// Couleurs par type IFC
const TYPE_COLORS = {
    IfcWall:              0xc8b8a2,
    IfcWallStandardCase:  0xc8b8a2,
    IfcSlab:              0x9e9e9e,
    IfcColumn:            0xa0522d,
    IfcBeam:              0x8b6914,
    IfcDoor:              0x6d4c41,
    IfcWindow:            0x90caf9,
    IfcStair:             0xbcaaa4,
    IfcRoof:              0x795548,
    IfcCovering:          0xd7ccc8,
    IfcSpace:             0x80cbc4,
    default:              0xaaaaaa,
};

const COLOR_ACTIVE   = 0xe57c2a;   // surbrillance étage/pièce actif
const COLOR_INACTIVE = 0x333344;   // éléments hors filtre (semi-transparent)

// ── Init principale ───────────────────────────────────────────
function initViewer(canvasId, jsonUrl, apiUrl) {
    apiBaseUrl = apiUrl;
    const canvas = document.getElementById(canvasId);

    // Scène
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    scene.fog = new THREE.FogExp2(0x1a1a2e, 0.002);

    // Caméra
    camera = new THREE.PerspectiveCamera(
        50,
        canvas.clientWidth / canvas.clientHeight,
        0.1,
        5000
    );
    camera.position.set(20, 20, 30);

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type    = THREE.PCFSoftShadowMap;

    // Lumières
    _setupLights();

    // Grille de sol
    const grid = new THREE.GridHelper(200, 40, 0x333355, 0x222233);
    scene.add(grid);

    // Axes (petits, discrets)
    const axesHelper = new THREE.AxesHelper(3);
    scene.add(axesHelper);

    // OrbitControls — chargé via CDN dans le template
    _setupOrbitControls();

    // Raycaster pour le survol
    raycaster = new THREE.Raycaster();
    mouse     = new THREE.Vector2();
    canvas.addEventListener('mousemove', _onMouseMove);

    // Resize
    window.addEventListener('resize', _onResize);

    // Charge le modèle
    _loadModel(jsonUrl);

    // Loop de rendu
    _animate();
}

// ── Chargement du JSON ────────────────────────────────────────
function _loadModel(jsonUrl) {
    fetch(jsonUrl)
        .then(r => {
            if (!r.ok) throw new Error('Impossible de charger le fichier JSON du modèle.');
            return r.json();
        })
        .then(data => {
            _buildScene(data);
            document.getElementById('loading-overlay').style.display = 'none';
        })
        .catch(err => {
            const overlay = document.getElementById('loading-overlay');
            overlay.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="font-size:2rem;color:#e57c2a;margin-bottom:1rem;"></i>
                <p style="color:rgba(255,255,255,0.7);font-size:0.9rem;">${err.message}</p>`;
        });
}

function _buildScene(data) {
    allMeshes = [];

    data.etages.forEach(etage => {
        const etageGroup = new THREE.Group();
        etageGroup.name  = `etage_${etage.id || etage.ifc_guid}`;
        etageGroup.userData = { etageId: etage.id, etageGuid: etage.ifc_guid };

        if (etage.geometrie && etage.geometrie.meshes) {
            etage.geometrie.meshes.forEach(meshData => {
                const mesh = _buildMesh(meshData, etage);
                if (mesh) {
                    etageGroup.add(mesh);
                    allMeshes.push({
                        mesh,
                        ifcGuid:   meshData.ifc_guid,
                        typeIfc:   meshData.type_ifc,
                        etageId:   etage.id,
                        etageGuid: etage.ifc_guid,
                        etageNom:  etage.nom,
                    });
                }
            });
        }
        scene.add(etageGroup);
    });

    // Centre la caméra sur le modèle
    _fitCameraToScene();
}

function _buildMesh(meshData, etage) {
    const verts   = meshData.vertices;
    const indices = meshData.indices;
    if (!verts || !indices || verts.length === 0 || indices.length === 0) return null;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    const color    = TYPE_COLORS[meshData.type_ifc] || TYPE_COLORS.default;
    const isWindow = meshData.type_ifc === 'IfcWindow';

    const material = new THREE.MeshLambertMaterial({
        color,
        transparent: isWindow,
        opacity:     isWindow ? 0.35 : 1.0,
        side:        THREE.DoubleSide,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow    = true;
    mesh.receiveShadow = true;
    mesh.userData      = {
        ifcGuid:  meshData.ifc_guid,
        typeIfc:  meshData.type_ifc,
        etageId:  etage.id,
        etageNom: etage.nom,
        baseColor: color,
        isWindow,
    };
    return mesh;
}

// ── Filtres ───────────────────────────────────────────────────

// Appelé depuis le HTML — filtre par étage
function filtrerEtage(etagePk, btn) {
    // Reset boutons
    document.querySelectorAll('.etage-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-tout').classList.remove('active');

    if (btn) btn.classList.add('active');

    if (!etagePk) {
        // Tout afficher
        allMeshes.forEach(({ mesh }) => _showMesh(mesh, true));
        document.getElementById('btn-tout').classList.add('active');
        return;
    }

    allMeshes.forEach(({ mesh }) => {
        const visible = String(mesh.userData.etageId) === String(etagePk);
        _showMesh(mesh, visible);
        if (!visible) _dimMesh(mesh);
    });
}

// Appelé depuis le HTML — filtre par pièce (via ifc_guid)
function filtrerPiece(btn, pieceGuid) {
    document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    if (!pieceGuid) return;

    allMeshes.forEach(({ mesh }) => {
        const match = mesh.userData.ifcGuid === pieceGuid;
        _showMesh(mesh, match);
        if (!match) _dimMesh(mesh);
    });
}

// Toggle ouverture/fermeture d'un étage dans le panneau
function toggleEtage(btn, etagePk) {
    const piecesEl = document.getElementById(`pieces-${etagePk}`);

    // Active le filtre 3D
    filtrerEtage(etagePk, btn);

    // Toggle arborescence
    const isOpen = btn.classList.toggle('open');
    if (piecesEl) piecesEl.classList.toggle('open', isOpen);
}

function _showMesh(mesh, show) {
    mesh.visible = true;
    if (show) {
        mesh.material.color.setHex(mesh.userData.baseColor);
        mesh.material.opacity = mesh.userData.isWindow ? 0.35 : 1.0;
    }
}

function _dimMesh(mesh) {
    mesh.material.color.setHex(COLOR_INACTIVE);
    mesh.material.opacity  = 0.08;
    mesh.material.transparent = true;
}

// ── Caméra ────────────────────────────────────────────────────
function setCameraMode(mode) {
    currentMode = mode;
    document.getElementById('btn-perspective').classList.toggle('active', mode === 'perspective');
    document.getElementById('btn-top').classList.toggle('active', mode === 'top');

    if (mode === 'top') {
        camera.position.set(0, 80, 0.01);
        camera.lookAt(0, 0, 0);
    } else {
        camera.position.set(20, 20, 30);
        camera.lookAt(0, 0, 0);
    }
    if (controls) controls.update();
}

function resetCamera() {
    _fitCameraToScene();
    document.querySelectorAll('.etage-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-tout').classList.add('active');
    allMeshes.forEach(({ mesh }) => _showMesh(mesh, true));
}

function _fitCameraToScene() {
    if (allMeshes.length === 0) return;
    const box = new THREE.Box3();
    allMeshes.forEach(({ mesh }) => box.expandByObject(mesh));
    const center = box.getCenter(new THREE.Vector3());
    const size   = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    camera.position.set(center.x + maxDim, center.y + maxDim * 0.6, center.z + maxDim);
    camera.lookAt(center);
    if (controls) { controls.target.copy(center); controls.update(); }
}

// ── OrbitControls (inline minimal) ───────────────────────────
function _setupOrbitControls() {
    // OrbitControls simplifié — si tu veux la version complète,
    // inclus OrbitControls.js depuis CDN dans le template.
    controls = {
        target: new THREE.Vector3(),
        update: () => {},
    };

    // Orbite basique via events
    let isDragging = false, prevX = 0, prevY = 0;
    const canvas = renderer.domElement;

    let spherical = { theta: Math.PI / 4, phi: Math.PI / 3, radius: 50 };

    function updateCameraFromSpherical() {
        camera.position.set(
            controls.target.x + spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta),
            controls.target.y + spherical.radius * Math.cos(spherical.phi),
            controls.target.z + spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta)
        );
        camera.lookAt(controls.target);
    }

    controls.update = updateCameraFromSpherical;

    canvas.addEventListener('mousedown', e => { isDragging = true; prevX = e.clientX; prevY = e.clientY; });
    canvas.addEventListener('mouseup',   () => { isDragging = false; });
    canvas.addEventListener('mousemove', e => {
        if (!isDragging) return;
        const dx = (e.clientX - prevX) * 0.01;
        const dy = (e.clientY - prevY) * 0.01;
        spherical.theta -= dx;
        spherical.phi    = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy));
        prevX = e.clientX; prevY = e.clientY;
        updateCameraFromSpherical();
    });
    canvas.addEventListener('wheel', e => {
        spherical.radius = Math.max(2, spherical.radius + e.deltaY * 0.05);
        updateCameraFromSpherical();
    });

    // Touch support
    let lastTouchDist = 0;
    canvas.addEventListener('touchstart', e => {
        if (e.touches.length === 1) { isDragging = true; prevX = e.touches[0].clientX; prevY = e.touches[0].clientY; }
        if (e.touches.length === 2) { lastTouchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); }
    });
    canvas.addEventListener('touchend',   () => { isDragging = false; });
    canvas.addEventListener('touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 1 && isDragging) {
            const dx = (e.touches[0].clientX - prevX) * 0.01;
            const dy = (e.touches[0].clientY - prevY) * 0.01;
            spherical.theta -= dx; spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy));
            prevX = e.touches[0].clientX; prevY = e.touches[0].clientY;
            updateCameraFromSpherical();
        }
        if (e.touches.length === 2) {
            const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
            spherical.radius = Math.max(2, spherical.radius - (dist - lastTouchDist) * 0.1);
            lastTouchDist = dist;
            updateCameraFromSpherical();
        }
    }, { passive: false });

    updateCameraFromSpherical();
}

// ── Lumières ──────────────────────────────────────────────────
function _setupLights() {
    const ambient = new THREE.AmbientLight(0xffffff, 0.55);
    scene.add(ambient);

    const dirLight = new THREE.DirectionalLight(0xfff5e0, 1.0);
    dirLight.position.set(50, 80, 50);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width  = 2048;
    dirLight.shadow.mapSize.height = 2048;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0xc8d8ff, 0.3);
    fillLight.position.set(-30, 20, -30);
    scene.add(fillLight);
}

// ── Raycasting (survol) ───────────────────────────────────────
function _onMouseMove(event) {
    const canvas = renderer.domElement;
    const rect   = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width)  * 2 - 1;
    mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const meshList = allMeshes.map(m => m.mesh).filter(m => m.visible);
    const intersects = raycaster.intersectObjects(meshList);

    const infoEl  = document.getElementById('hover-info');
    const infoTxt = document.getElementById('hover-info-text');

    if (intersects.length > 0) {
        const obj  = intersects[0].object;
        const data = obj.userData;
        infoEl.style.display = 'block';
        infoTxt.textContent  = `${data.typeIfc || '—'} — ${data.etageNom || ''}`;
    } else {
        infoEl.style.display = 'none';
    }
}

// ── Resize ────────────────────────────────────────────────────
function _onResize() {
    const canvas = renderer.domElement;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
}

// ── Boucle de rendu ───────────────────────────────────────────
function _animate() {
    requestAnimationFrame(_animate);
    renderer.render(scene, camera);
}
