/**
 * viewer.js — Moteur Three.js enrichi v2
 * - Matériaux PBR procéduraux fidèles ArchiCAD (béton, bois, verre, brique, métal…)
 * - Modes soleil : crépuscule, matin, jour, midi, soir, nuit
 * - Météo : nuages, orage, pluie, ciel bleu, coucher de soleil
 * - Particules pluie
 * - Brouillard atmosphérique dynamique
 */

let scene, camera, renderer, orbitControls;
let navMode = 'orbit';
let raycaster, mouse;
let allMeshes = [];
let apiBaseUrl = '';

// Éléments environnement
let _sunLight, _fillLight, _ambientLight;
let _skyMesh, _cloudsMesh;
let _rainParticles, _rainGeometry, _rainActive = false;
let _lightningTimeout = null;
let _currentSkyMode = 'jour';
let _currentWeather  = 'clear';

// Étoiles, lune, luminaires IFC
let _starsMesh   = null;   // Points() étoiles
let _moonMesh    = null;   // Mesh lune
let _moonLight   = null;   // PointLight lune
let _starsGeo    = null;
let _luminaireRegistry = []; // [{ mesh, pointLight, position }]
let _starsVisible = false;
let _animFrame   = 0;      // compteur pour scintillement
let _animFrameId = null;

// ── Matériaux ArchiCAD → PBR procédural ──────────────────────────────────────

/**
 * Crée un matériau Three.js enrichi en fonction du type IFC et du matériau ArchiCAD.
 * Utilise MeshStandardMaterial pour roughness/metalness quand disponible.
 */
function _buildMaterial(typeIfc, materiauName, isWindow, isSpace) {
    if (isWindow || isSpace) {
        return new THREE.MeshStandardMaterial({
            color: isWindow ? 0x90caf9 : 0x80cbc4,
            transparent: true,
            opacity: isWindow ? 0.22 : 0.06,
            roughness: 0.05, metalness: 0.1,
            side: THREE.DoubleSide,
            depthWrite: false,
        });
    }

    const mat_l = (materiauName || '').toLowerCase();
    const type_l = (typeIfc || '').toLowerCase();

    // ── Béton / Structural ────────────────────────────────────────────
    if (mat_l.includes('concrete') || mat_l.includes('béton') || mat_l.includes('beton')
        || mat_l.includes('structural') || mat_l.includes('struct')) {
        const shade = _randShade(0xb0b0b0, 0xd0d0d0);
        return new THREE.MeshStandardMaterial({
            color: shade, roughness: 0.9, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Bois / Parquet / Boiserie ─────────────────────────────────────
    if (mat_l.includes('wood') || mat_l.includes('bois') || mat_l.includes('timber')
        || mat_l.includes('oak') || mat_l.includes('parquet') || mat_l.includes('chene')) {
        return new THREE.MeshStandardMaterial({
            color: 0xc19a6b, roughness: 0.75, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Métal / Acier / Aluminium ─────────────────────────────────────
    if (mat_l.includes('steel') || mat_l.includes('metal') || mat_l.includes('acier')
        || mat_l.includes('alum') || mat_l.includes('iron') || mat_l.includes('fer')) {
        return new THREE.MeshStandardMaterial({
            color: 0x8d9db0, roughness: 0.35, metalness: 0.85,
            side: THREE.DoubleSide,
        });
    }

    // ── Verre (non-fenêtre : mur-rideau, garde-corps verre) ───────────
    if (mat_l.includes('glass') || mat_l.includes('verre') || mat_l.includes('glazing')
        || typeIfc === 'IfcCurtainWall') {
        return new THREE.MeshStandardMaterial({
            color: 0xb3e5fc, transparent: true, opacity: 0.3,
            roughness: 0.05, metalness: 0.1,
            side: THREE.DoubleSide, depthWrite: false,
        });
    }

    // ── Brique ────────────────────────────────────────────────────────
    if (mat_l.includes('brick') || mat_l.includes('brique')) {
        return new THREE.MeshStandardMaterial({
            color: 0xb5603a, roughness: 0.88, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Pierre / Marbre / Granit ──────────────────────────────────────
    if (mat_l.includes('stone') || mat_l.includes('pierre') || mat_l.includes('marble')
        || mat_l.includes('marbre') || mat_l.includes('granite')) {
        return new THREE.MeshStandardMaterial({
            color: 0xc8c0b8, roughness: 0.6, metalness: 0.05,
            side: THREE.DoubleSide,
        });
    }

    // ── Plâtre / Enduit / Peinture ────────────────────────────────────
    if (mat_l.includes('plaster') || mat_l.includes('enduit') || mat_l.includes('gypsum')
        || mat_l.includes('placo') || mat_l.includes('paint') || mat_l.includes('peinture')) {
        const shade = _randShade(0xe8e4de, 0xf5f2ee);
        return new THREE.MeshStandardMaterial({
            color: shade, roughness: 0.82, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Carrelage ─────────────────────────────────────────────────────
    if (mat_l.includes('tile') || mat_l.includes('carrelage') || mat_l.includes('ceramic')) {
        return new THREE.MeshStandardMaterial({
            color: 0xddd8d0, roughness: 0.2, metalness: 0.05,
            side: THREE.DoubleSide,
        });
    }

    // ── Toiture ───────────────────────────────────────────────────────
    if (typeIfc === 'IfcRoof' || mat_l.includes('roof') || mat_l.includes('toiture')
        || mat_l.includes('tuile') || mat_l.includes('tile roofing')) {
        return new THREE.MeshStandardMaterial({
            color: 0x7d4e3e, roughness: 0.85, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Revêtement sol ────────────────────────────────────────────────
    if (typeIfc === 'IfcSlab' || mat_l.includes('floor') || mat_l.includes('flooring')) {
        return new THREE.MeshStandardMaterial({
            color: 0xbcb8b0, roughness: 0.75, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Sanitaires ────────────────────────────────────────────────────
    if (typeIfc === 'IfcSanitaryTerminal' || typeIfc === 'IfcFlowTerminal') {
        return new THREE.MeshStandardMaterial({
            color: 0xf5f5f0, roughness: 0.1, metalness: 0.15,
            side: THREE.DoubleSide,
        });
    }

    // ── Luminaires ────────────────────────────────────────────────────
    if (typeIfc === 'IfcLightFixture') {
        return new THREE.MeshStandardMaterial({
            color: 0xfff9c4, roughness: 0.1, metalness: 0.6,
            emissive: new THREE.Color(0xfff176), emissiveIntensity: 0.4,
            side: THREE.DoubleSide,
        });
    }

    // ── Garde-corps ───────────────────────────────────────────────────
    if (typeIfc === 'IfcRailing') {
        return new THREE.MeshStandardMaterial({
            color: 0x9e9e9e, roughness: 0.3, metalness: 0.8,
            side: THREE.DoubleSide,
        });
    }

    // ── Mobilier ─────────────────────────────────────────────────────
    if (typeIfc === 'IfcFurniture' || typeIfc === 'IfcFurnishingElement') {
        return new THREE.MeshStandardMaterial({
            color: 0xd4b483, roughness: 0.6, metalness: 0.0,
            side: THREE.DoubleSide,
        });
    }

    // ── Couleurs IFC par défaut (fallback) ────────────────────────────
    const TYPE_COLORS = {
        IfcWall: 0xd4c5b0, IfcWallStandardCase: 0xd4c5b0,
        IfcSlab: 0x9e9e9e, IfcColumn: 0xa0522d, IfcBeam: 0x8b6914,
        IfcDoor: 0x6d4c41, IfcStair: 0xbcaaa4, IfcStairFlight: 0xbcaaa4,
        IfcRamp: 0xb0bec5, IfcCovering: 0xd7ccc8,
        IfcFlowSegment: 0xef9a9a, IfcElectricAppliance: 0xffe0b2,
        IfcBuildingElementProxy: 0xaaaaaa, default: 0xcccccc,
    };
    const color = TYPE_COLORS[typeIfc] || TYPE_COLORS.default;
    return new THREE.MeshStandardMaterial({
        color, roughness: 0.75, metalness: 0.0,
        side: THREE.DoubleSide,
    });
}

function _randShade(min, max) {
    const t = Math.random() * 0.15;
    const minC = new THREE.Color(min), maxC = new THREE.Color(max);
    return new THREE.Color(
        minC.r + (maxC.r - minC.r) * t,
        minC.g + (maxC.g - minC.g) * t,
        minC.b + (maxC.b - minC.b) * t,
    );
}

// ── Modes atmosphériques ─────────────────────────────────────────────────────

const SKY_PRESETS = {
    nuit:       { bg: 0x050810, fog: 0x050810, fogDensity: 0.004, ambient: 0x0a0e1f, ambInt: 0.15, sunColor: 0x102040, sunInt: 0.05, fillColor: 0x051020, fillInt: 0.0,  sunPos: [20,-30,10],   skyTop: 0x020510, skyBot: 0x050810 },
    crepuscule: { bg: 0x0a0a1a, fog: 0x0f0f20, fogDensity: 0.003, ambient: 0x1a1030, ambInt: 0.2,  sunColor: 0xff4500, sunInt: 0.3,  fillColor: 0x200830, fillInt: 0.1,  sunPos: [-60,-5,40],   skyTop: 0x050520, skyBot: 0x220a08 },
    matin:      { bg: 0x1a2a3e, fog: 0x1a2a3e, fogDensity: 0.0018, ambient: 0x3d5c78, ambInt: 0.45, sunColor: 0xffd090, sunInt: 0.7,  fillColor: 0x6090c0, fillInt: 0.25, sunPos: [-80,30,30],   skyTop: 0x1a2a4a, skyBot: 0xd49060 },
    jour:       { bg: 0x4488cc, fog: 0x6699cc, fogDensity: 0.0008, ambient: 0xffffff, ambInt: 0.65, sunColor: 0xfff5e0, sunInt: 1.3,  fillColor: 0xc8d8ff, fillInt: 0.35, sunPos: [50,80,50],    skyTop: 0x1a55a0, skyBot: 0x6aaee8 },
    midi:       { bg: 0x5599dd, fog: 0x77aadd, fogDensity: 0.0006, ambient: 0xffffff, ambInt: 0.8,  sunColor: 0xfffde8, sunInt: 1.6,  fillColor: 0xddeeff, fillInt: 0.4,  sunPos: [5,100,5],     skyTop: 0x2266bb, skyBot: 0x88ccff },
    soir:       { bg: 0x1e1830, fog: 0x251828, fogDensity: 0.002,  ambient: 0x4a2820, ambInt: 0.35, sunColor: 0xff7733, sunInt: 0.6,  fillColor: 0x8030a0, fillInt: 0.2,  sunPos: [80,8,40],     skyTop: 0x0e0820, skyBot: 0xff4a18 },
    coucher:    { bg: 0x0d0818, fog: 0x150a10, fogDensity: 0.003,  ambient: 0x2a1010, ambInt: 0.25, sunColor: 0xff3300, sunInt: 0.45, fillColor: 0x600030, fillInt: 0.15, sunPos: [90,2,20],     skyTop: 0x080410, skyBot: 0xcc2200 },
};

const WEATHER_PRESETS = {
    clear:  { fogMult: 1.0,  cloudOpacity: 0.0, rainActive: false, lightning: false },
    nuages: { fogMult: 1.4,  cloudOpacity: 0.7, rainActive: false, lightning: false },
    orage:  { fogMult: 2.2,  cloudOpacity: 1.0, rainActive: true,  lightning: true  },
    pluie:  { fogMult: 1.8,  cloudOpacity: 0.85,rainActive: true,  lightning: false },
};

// ── Sky dome ──────────────────────────────────────────────────────────────────

function _buildSkyDome() {
    // Dôme avec shader gradient simple
    const skyGeo  = new THREE.SphereGeometry(4000, 32, 16);
    const skyMat  = new THREE.ShaderMaterial({
        uniforms: {
            topColor:    { value: new THREE.Color(0x1a55a0) },
            bottomColor: { value: new THREE.Color(0x6aaee8) },
            offset:      { value: 300 },
            exponent:    { value: 0.5 },
        },
        vertexShader: `
            varying vec3 vWorldPosition;
            void main() {
                vec4 worldPos = modelMatrix * vec4(position, 1.0);
                vWorldPosition = worldPos.xyz;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }`,
        fragmentShader: `
            uniform vec3 topColor;
            uniform vec3 bottomColor;
            uniform float offset;
            uniform float exponent;
            varying vec3 vWorldPosition;
            void main() {
                float h = normalize(vWorldPosition + offset).y;
                gl_FragColor = vec4(mix(bottomColor, topColor, max(pow(max(h, 0.0), exponent), 0.0)), 1.0);
            }`,
        side: THREE.BackSide,
    });
    _skyMesh = new THREE.Mesh(skyGeo, skyMat);
    scene.add(_skyMesh);
}

function _updateSkyColors(preset) {
    if (!_skyMesh) return;
    _skyMesh.material.uniforms.topColor.value.setHex(preset.skyTop);
    _skyMesh.material.uniforms.bottomColor.value.setHex(preset.skyBot);
}

// ── Nuages procéduraux ────────────────────────────────────────────────────────

function _buildClouds() {
    const cloudGroup = new THREE.Group();
    for (let i = 0; i < 18; i++) {
        const puffs = Math.floor(Math.random() * 5) + 3;
        const cloudMini = new THREE.Group();
        for (let p = 0; p < puffs; p++) {
            const r  = Math.random() * 80 + 40;
            const sg = new THREE.SphereGeometry(r, 8, 6);
            const sm = new THREE.MeshLambertMaterial({
                color: 0xffffff,
                transparent: true,
                opacity: 0.0,
                depthWrite: false,
            });
            const sphere = new THREE.Mesh(sg, sm);
            sphere.position.set(
                (Math.random() - 0.5) * 180,
                (Math.random() - 0.5) * 30,
                (Math.random() - 0.5) * 80
            );
            cloudMini.add(sphere);
        }
        cloudMini.position.set(
            (Math.random() - 0.5) * 2400,
            Math.random() * 200 + 300,
            (Math.random() - 0.5) * 2400
        );
        cloudGroup.add(cloudMini);
    }
    _cloudsMesh = cloudGroup;
    scene.add(cloudGroup);
}

function _setCloudsOpacity(opacity) {
    if (!_cloudsMesh) return;
    _cloudsMesh.children.forEach(cloud => {
        cloud.children.forEach(puff => {
            puff.material.opacity = opacity * (0.5 + Math.random() * 0.5);
        });
    });
}

// ── Pluie particules ──────────────────────────────────────────────────────────

function _buildRain() {
    const COUNT = 8000;
    _rainGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
        positions[i * 3]     = (Math.random() - 0.5) * 600;
        positions[i * 3 + 1] = Math.random() * 400 + 50;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 600;
    }
    _rainGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const rainMat = new THREE.PointsMaterial({
        color: 0xaaccff, size: 0.8, transparent: true, opacity: 0.55,
        depthWrite: false, sizeAttenuation: true,
    });
    _rainParticles = new THREE.Points(_rainGeometry, rainMat);
    _rainParticles.visible = false;
    scene.add(_rainParticles);
}

function _animateRain() {
    if (!_rainActive || !_rainParticles || !_rainParticles.visible) return;
    const pos = _rainGeometry.attributes.position.array;
    for (let i = 0; i < pos.length; i += 3) {
        pos[i + 1] -= 4.5 + Math.random() * 2;
        if (pos[i + 1] < -20) {
            pos[i + 1] = Math.random() * 400 + 200;
            pos[i]     = (Math.random() - 0.5) * 600;
            pos[i + 2] = (Math.random() - 0.5) * 600;
        }
    }
    _rainGeometry.attributes.position.needsUpdate = true;
}

// ── Étoiles ───────────────────────────────────────────────────────────────────

function _buildStars() {
    const COUNT = 4000;
    _starsGeo = new THREE.BufferGeometry();
    const positions  = new Float32Array(COUNT * 3);
    const sizes      = new Float32Array(COUNT);
    const colors     = new Float32Array(COUNT * 3);

    // Palette de couleurs d'étoiles réalistes (blanc, bleuté, jaunâtre, rougeâtre)
    const starPalette = [
        [1.0, 1.0, 1.0],   // blanc pur
        [0.9, 0.95, 1.0],  // blanc bleuté
        [1.0, 0.97, 0.85], // blanc jaunâtre
        [0.8, 0.88, 1.0],  // bleu-blanc
        [1.0, 0.85, 0.75], // orangé (géante)
    ];

    for (let i = 0; i < COUNT; i++) {
        // Distribution sphérique — rayon entre 1800 et 3800 pour rester derrière le dôme
        const r     = 1800 + Math.random() * 2000;
        const theta = Math.random() * Math.PI * 2;
        const phi   = Math.acos(2 * Math.random() - 1);
        positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.abs(Math.cos(phi));  // hémisphère supérieure uniquement
        positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

        sizes[i] = Math.random() < 0.05 ? 2.2 + Math.random() * 1.5   // 5% étoiles brillantes
                 : Math.random() < 0.25 ? 1.2 + Math.random() * 0.8   // 20% moyennes
                 : 0.4 + Math.random() * 0.6;                           // 75% petites

        const col = starPalette[Math.floor(Math.random() * starPalette.length)];
        colors[i * 3]     = col[0];
        colors[i * 3 + 1] = col[1];
        colors[i * 3 + 2] = col[2];
    }
    _starsGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    _starsGeo.setAttribute('color',    new THREE.BufferAttribute(colors,    3));
    _starsGeo.setAttribute('size',     new THREE.BufferAttribute(sizes,     1));

    const starsMat = new THREE.ShaderMaterial({
        uniforms: {
            opacity:   { value: 0.0 },
            time:      { value: 0.0 },
        },
        vertexShader: `
            attribute float size;
            attribute vec3 color;
            varying vec3 vColor;
            uniform float time;
            // scintillement léger basé sur position
            float flicker(vec3 p, float t) {
                return 0.85 + 0.15 * sin(t * 2.0 + dot(p, vec3(0.017, 0.031, 0.023)));
            }
            void main() {
                vColor = color;
                vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = size * flicker(position, time) * (300.0 / -mvPos.z);
                gl_Position  = projectionMatrix * mvPos;
            }`,
        fragmentShader: `
            uniform float opacity;
            varying vec3 vColor;
            void main() {
                // Forme ronde douce
                vec2 c = gl_PointCoord - vec2(0.5);
                float d = dot(c, c);
                if (d > 0.25) discard;
                float alpha = opacity * (1.0 - smoothstep(0.1, 0.25, d));
                gl_FragColor = vec4(vColor, alpha);
            }`,
        transparent: true,
        depthWrite:  false,
        blending:    THREE.AdditiveBlending,
        vertexColors: true,
    });

    _starsMesh = new THREE.Points(_starsGeo, starsMat);
    _starsMesh.visible = false;
    // Ne pas appliquer la rotation du root IFC — les étoiles restent dans le repère monde
    scene.add(_starsMesh);
}

// ── Lune ──────────────────────────────────────────────────────────────────────

function _buildMoon() {
    const moonGeo = new THREE.SphereGeometry(55, 32, 24);
    const moonMat = new THREE.MeshStandardMaterial({
        color:     0xdde8f0,
        roughness: 0.9,
        metalness: 0.0,
        emissive:  new THREE.Color(0xb0c8e0),
        emissiveIntensity: 0.0,
    });
    _moonMesh = new THREE.Mesh(moonGeo, moonMat);
    _moonMesh.position.set(-900, 800, -1200);
    _moonMesh.visible = false;
    scene.add(_moonMesh);

    // Lumière douce de la lune (bleu-blanc froid)
    _moonLight = new THREE.PointLight(0xb0d0f8, 0.0, 0, 2);
    _moonLight.position.copy(_moonMesh.position);
    scene.add(_moonLight);
}



// ── Éclairs ───────────────────────────────────────────────────────────────────

function _triggerLightning() {
    if (!_currentWeather === 'orage') return;
    const flash = new THREE.PointLight(0xffffff, 25, 2000);
    flash.position.set(
        (Math.random() - 0.5) * 500,
        300 + Math.random() * 100,
        (Math.random() - 0.5) * 500
    );
    scene.add(flash);
    setTimeout(() => { scene.remove(flash); }, 80);
    if (_lightningTimeout) clearTimeout(_lightningTimeout);
    const nextDelay = 3000 + Math.random() * 7000;
    _lightningTimeout = setTimeout(_triggerLightning, nextDelay);
}

// ── Appliquer un preset atmosphérique ────────────────────────────────────────

// Intensité nuit = 1.0 (nuit complète), 0.0 (plein jour)
const SKY_NIGHT_LEVEL = {
    nuit: 1.0, crepuscule: 0.65, soir: 0.5, coucher: 0.4,
    matin: 0.1, jour: 0.0, midi: 0.0,
};

function _applyAtmosphere(skyKey, weatherKey) {
    const sky = SKY_PRESETS[skyKey]         || SKY_PRESETS.jour;
    const wth = WEATHER_PRESETS[weatherKey] || WEATHER_PRESETS.clear;
    _currentSkyMode = skyKey;
    _currentWeather = weatherKey;

    // Fond + brouillard
    scene.background = new THREE.Color(sky.bg);
    scene.fog = new THREE.FogExp2(sky.fog, sky.fogDensity * wth.fogMult);

    // Lumières solaires
    _ambientLight.color.setHex(sky.ambient);
    _ambientLight.intensity = sky.ambInt;
    _sunLight.color.setHex(sky.sunColor);
    _sunLight.intensity = sky.sunInt;
    _sunLight.position.set(...sky.sunPos).normalize().multiplyScalar(150);
    _fillLight.color.setHex(sky.fillColor);
    _fillLight.intensity = sky.fillInt;

    // Ciel dôme
    _updateSkyColors(sky);

    // Nuages
    _setCloudsOpacity(wth.cloudOpacity);

    // Pluie
    _rainActive = wth.rainActive;
    if (_rainParticles) _rainParticles.visible = _rainActive;

    // Éclairs
    if (_lightningTimeout) { clearTimeout(_lightningTimeout); _lightningTimeout = null; }
    if (wth.lightning) _triggerLightning();

    // ── Étoiles & Lune ───────────────────────────────────────────────
    const nightLevel = SKY_NIGHT_LEVEL[skyKey] ?? 0;
    const starsOpacity = Math.max(0, nightLevel - wth.fogMult * 0.1);

    if (_starsMesh) {
        const wasVisible = _starsVisible;
        _starsVisible = starsOpacity > 0.05;
        _starsMesh.visible = _starsVisible;
        if (_starsVisible) _starsMesh.material.uniforms.opacity.value = starsOpacity;
    }
    if (_moonMesh) {
        _moonMesh.visible = nightLevel > 0.3;
        if (_moonMesh.material) {
            _moonMesh.material.emissiveIntensity = nightLevel * 0.6;
        }
    }
    if (_moonLight) {
        _moonLight.intensity = nightLevel * 0.45;
        // Lune moins visible si nuages/orage
        if (wth.cloudOpacity > 0.5) _moonLight.intensity *= 0.3;
    }

    // ── Luminaires IFC ───────────────────────────────────────────────
    // S'allument progressivement à partir de "soir" et sont à pleine
    // puissance la nuit. Phasage aléatoire léger pour effet naturel.
    _updateLuminaires(nightLevel);

    _updateEnvButtons();
}

// ── Boutons UI environnement ──────────────────────────────────────────────────

function setSkyMode(mode) {
    _applyAtmosphere(mode, _currentWeather);
}
function setWeather(mode) {
    _applyAtmosphere(_currentSkyMode, mode);
}

// ── Système luminaires IFC ────────────────────────────────────────────────────

/**
 * Appelé après _buildScene : pour chaque mesh IfcLightFixture,
 * on crée un PointLight associé positionné au centroïde du mesh.
 * Le PointLight est éteint le jour et s'allume la nuit.
 */
function _registerLuminaires() {
    // Nettoyer les anciens
    _luminaireRegistry.forEach(({ pointLight }) => scene.remove(pointLight));
    _luminaireRegistry = [];

    allMeshes.forEach(({ mesh }) => {
        if (mesh.userData.typeIfc !== 'IfcLightFixture') return;

        // Centroïde du mesh en coordonnées monde
        mesh.geometry.computeBoundingBox();
        const center = new THREE.Vector3();
        mesh.geometry.boundingBox.getCenter(center);
        center.applyMatrix4(mesh.matrixWorld);

        // La lumière est légèrement en dessous du fixture (spot vers le bas)
        const lightPos = center.clone();
        lightPos.y -= 0.3;

        // PointLight chaude (ampoule)
        const pl = new THREE.PointLight(0xffdd88, 0.0, 18, 2);
        pl.position.copy(lightPos);
        pl.castShadow = false; // perf : pas d'ombre par défaut
        scene.add(pl);

        // Décalage de phase pour que les lumières ne s'allument pas toutes en même temps
        const phase = Math.random() * Math.PI * 2;

        _luminaireRegistry.push({ mesh, pointLight: pl, phase });
    });
}

/**
 * Met à jour l'intensité de tous les luminaires en fonction du niveau de nuit.
 * nightLevel : 0 = jour plein, 1 = nuit complète.
 */
function _updateLuminaires(nightLevel) {
    _luminaireRegistry.forEach(({ mesh, pointLight }) => {
        // Allumage à partir de 0.3 (soir), pleine puissance à 0.7 (nuit)
        const t = Math.max(0, Math.min(1, (nightLevel - 0.3) / 0.4));
        const intensity = t * 2.2;  // intensité max 2.2

        pointLight.intensity = intensity;

        // Émissive du mesh miroir
        if (mesh.material && mesh.material.emissiveIntensity !== undefined) {
            mesh.material.emissiveIntensity = 0.15 + t * 1.2;
        }
    });
}

/**
 * Scintillement subtil des luminaires dans _animate().
 * Simule les variations d'une ampoule ou d'un néon.
 */
function _flickerLuminaires(time) {
    _luminaireRegistry.forEach(({ pointLight, mesh, phase }) => {
        if (pointLight.intensity < 0.05) return;
        // Oscillation très légère — max ±8%
        const flicker = 1.0 + 0.08 * Math.sin(time * 11.3 + phase)
                            + 0.04 * Math.sin(time * 37.1 + phase * 1.7);
        pointLight.intensity *= flicker;
        // Limiter pour éviter dérive
        pointLight.intensity = Math.max(0, Math.min(3.5, pointLight.intensity));
    });
}



function _updateEnvButtons() {
    document.querySelectorAll('.env-sky-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === _currentSkyMode);
    });
    document.querySelectorAll('.env-weather-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === _currentWeather);
    });
}

// ── Init principal ────────────────────────────────────────────────────────────

function initViewer(canvasId, jsonUrl, apiUrl) {
    apiBaseUrl = apiUrl;
    const canvas = document.getElementById(canvasId);

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x4488cc);

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
    renderer.physicallyCorrectLights = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;

    _setupLights();
    _buildSkyDome();
    _buildClouds();
    _buildRain();
    _buildStars();
    _buildMoon();
    scene.add(new THREE.GridHelper(500, 50, 0x333355, 0x222233));
    _setupOrbitControls(canvas);
    _applyAtmosphere('jour', 'clear');

    raycaster = new THREE.Raycaster();
    mouse     = new THREE.Vector2();
    canvas.addEventListener('mousemove', _onMouseMove);
    window.addEventListener('resize', _onResize);

    _loadModel(jsonUrl);
    _animate();
}

function _loadModel(jsonUrl) {
    const overlay = document.getElementById('loading-overlay');
    fetch(jsonUrl, { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(data => {
            _buildScene(data);
            if (overlay) overlay.style.display = 'none';
        })
        .catch(err => {
            if (overlay) overlay.innerHTML =
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
        (etage.geometrie?.meshes || []).forEach(md => {
            const mesh = _buildMesh(md, etage);
            if (mesh) {
                g.add(mesh);
                allMeshes.push({ mesh, ifcGuid: md.ifc_guid, typeIfc: md.type_ifc, etageId: etage.id, etageNom: etage.nom });
            }
        });
        root.add(g);
    });
    _fitCameraToScene();
    // Enregistre les luminaires IFC pour le système jour/nuit
    _registerLuminaires();
    // Applique l'état courant (ex: si on est déjà en mode nuit avant le chargement)
    const nightLevel = SKY_NIGHT_LEVEL[_currentSkyMode] ?? 0;
    _updateLuminaires(nightLevel);
}

function _buildMesh(md, etage) {
    if (!md.vertices || !md.indices || md.vertices.length < 9 || md.indices.length < 3) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(md.vertices, 3));
    geo.setIndex(md.indices);
    geo.computeVertexNormals();

    const isWin  = md.type_ifc === 'IfcWindow';
    const isSpc  = md.type_ifc === 'IfcSpace';
    const mat    = _buildMaterial(md.type_ifc, md.materiau || '', isWin, isSpc);
    const mesh   = new THREE.Mesh(geo, mat);

    mesh.castShadow    = !isSpc;
    mesh.receiveShadow = true;

    // Stocker couleur de base pour restore
    const baseColor = mat.color.getHex();
    mesh.userData = {
        ifcGuid:     md.ifc_guid,
        typeIfc:     md.type_ifc,
        materiauNom: md.materiau || '',
        etageId:     etage.id,
        etageNom:    etage.nom,
        etageGuid:   etage.ifc_guid,
        baseColor,
        baseOpacity: mat.opacity,
        baseTrans:   mat.transparent,
        baseRoughness: mat.roughness,
        baseMetalness: mat.metalness,
    };
    return mesh;
}

// ── Filtres ───────────────────────────────────────────────────────────────────
function filtrerEtage(etagePk, btn) {
    document.querySelectorAll('.etage-btn,.piece-btn').forEach(b => b.classList.remove('active'));
    const btnTout = document.getElementById('btn-tout');
    if (btnTout) btnTout.classList.remove('active');
    if (btn) btn.classList.add('active');
    if (!etagePk) {
        allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
        if (btnTout) btnTout.classList.add('active');
        return;
    }
    allMeshes.forEach(({ mesh }) =>
        String(mesh.userData.etageId) === String(etagePk) ? _restoreMesh(mesh) : _dimMesh(mesh)
    );
}

function filtrerPiece(btn, pieceGuid) {
    document.querySelectorAll('.piece-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!pieceGuid) return;
    allMeshes.forEach(({ mesh }) =>
        mesh.userData.ifcGuid === pieceGuid ? _restoreMesh(mesh) : _dimMesh(mesh)
    );
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
    m.material.opacity     = m.userData.baseOpacity;
    m.material.transparent = m.userData.baseTrans;
    m.material.depthWrite  = !m.userData.baseTrans;
    if (m.material.roughness !== undefined) m.material.roughness = m.userData.baseRoughness;
    if (m.material.metalness !== undefined) m.material.metalness = m.userData.baseMetalness;
}

function _dimMesh(m) {
    m.material.color.setHex(0x1a2233);
    m.material.opacity     = 0.04;
    m.material.transparent = true;
    m.material.depthWrite  = false;
}

// ── Caméra ────────────────────────────────────────────────────────────────────
function setCameraMode(mode) {
    const btnP = document.getElementById('btn-perspective');
    const btnT = document.getElementById('btn-top');
    if (btnP) btnP.classList.toggle('active', mode === 'perspective');
    if (btnT) btnT.classList.toggle('active', mode === 'top');
    const t = orbitControls.target;
    if (mode === 'top') { camera.position.set(t.x, t.y + 80, t.z + 0.01); }
    else                { camera.position.set(t.x + 15, t.y + 12, t.z + 20); }
    camera.lookAt(t); orbitControls._sync();
}

function resetCamera() {
    document.querySelectorAll('.etage-btn,.piece-btn').forEach(b => b.classList.remove('active'));
    const btnTout = document.getElementById('btn-tout');
    if (btnTout) btnTout.classList.add('active');
    allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
    _fitCameraToScene();
}

function setNavMode(mode) {
    navMode = mode;
    const btnOrbit = document.getElementById('btn-orbit');
    const btnPan   = document.getElementById('btn-pan');
    if (btnOrbit) btnOrbit.classList.toggle('active', mode === 'orbit');
    if (btnPan)   btnPan.classList.toggle('active', mode === 'pan');
    if (renderer) renderer.domElement.style.cursor = mode === 'pan' ? 'grab' : 'default';
}

function _fitCameraToScene() {
    if (!allMeshes.length) return;
    const box = new THREE.Box3();
    allMeshes.forEach(({ mesh }) => {
        mesh.geometry.computeBoundingBox();
        const b = mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld);
        box.union(b);
    });
    const center = box.getCenter(new THREE.Vector3());
    const size   = box.getSize(new THREE.Vector3());
    const dist   = Math.max(size.x, size.y, size.z) * 1.5;
    orbitControls.target.copy(center);
    camera.position.set(center.x + dist * 0.6, center.y + dist * 0.5, center.z + dist * 0.8);
    camera.near = dist * 0.001; camera.far = dist * 100;
    camera.updateProjectionMatrix();
    camera.lookAt(center); orbitControls._sync();
}

// ── OrbitControls ─────────────────────────────────────────────────────────────
function _setupOrbitControls(canvas) {
    const s = { target: new THREE.Vector3(), radius: 30, theta: Math.PI/4, phi: Math.PI/3,
                drag: false, mid: false, px: 0, py: 0, pinch: 0 };

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
    window.addEventListener('mouseup', () => { s.drag = false; });
    window.addEventListener('mousemove', e => {
        if (!s.drag) return;
        const dx = e.clientX - s.px, dy = e.clientY - s.py;
        s.px = e.clientX; s.py = e.clientY;
        if (s.mid || e.shiftKey || navMode === 'pan') {
            const right = new THREE.Vector3(), up = new THREE.Vector3();
            camera.matrix.extractBasis(right, up, new THREE.Vector3());
            const sp = s.radius * 0.001;
            s.target.addScaledVector(right, -dx * sp);
            s.target.addScaledVector(up, dy * sp);
        } else {
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
            const dx = e.touches[0].clientX - s.px, dy = e.touches[0].clientY - s.py;
            if (navMode === 'pan') {
                const right = new THREE.Vector3(), up = new THREE.Vector3();
                camera.matrix.extractBasis(right, up, new THREE.Vector3());
                const sp = s.radius * 0.002;
                s.target.addScaledVector(right, -dx * sp);
                s.target.addScaledVector(up, dy * sp);
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

// ── Lumières ──────────────────────────────────────────────────────────────────
function _setupLights() {
    _ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    scene.add(_ambientLight);

    _sunLight = new THREE.DirectionalLight(0xfff5e0, 1.3);
    _sunLight.position.set(50, 80, 50);
    _sunLight.castShadow = true;
    _sunLight.shadow.mapSize.set(2048, 2048);
    _sunLight.shadow.camera.left = _sunLight.shadow.camera.bottom = -150;
    _sunLight.shadow.camera.right = _sunLight.shadow.camera.top  =  150;
    _sunLight.shadow.camera.far   = 600;
    _sunLight.shadow.bias = -0.001;
    scene.add(_sunLight);

    _fillLight = new THREE.DirectionalLight(0xc8d8ff, 0.35);
    _fillLight.position.set(-30, 20, -30);
    scene.add(_fillLight);
}

// ── Raycasting ────────────────────────────────────────────────────────────────
function _onMouseMove(event) {
    if (!renderer) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
    mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(allMeshes.map(m => m.mesh).filter(m => m.visible));
    const info = document.getElementById('hover-info');
    const text = document.getElementById('hover-info-text');
    if (!info || !text) return;
    if (hits.length) {
        const d = hits[0].object.userData;
        const matStr = d.materiauNom ? ` — ${d.materiauNom}` : '';
        info.style.display = 'block';
        text.textContent = (d.typeIfc || '—') + matStr + '  ·  ' + (d.etageNom || '');
    } else {
        info.style.display = 'none';
    }
}

function _onResize() {
    if (!renderer) return;
    const c = renderer.domElement;
    camera.aspect = c.clientWidth / c.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(c.clientWidth, c.clientHeight, false);
}

function _animate() {
    requestAnimationFrame(_animate);
    _animFrame++;
    const time = _animFrame * 0.016; // ~temps en secondes à 60fps

    // Pluie
    _animateRain();

    // Nuages — rotation lente
    if (_cloudsMesh) _cloudsMesh.rotation.y += 0.00008;

    // Étoiles — scintillement via uniform time
    if (_starsMesh && _starsVisible) {
        _starsMesh.material.uniforms.time.value = time;
        // Rotation très lente du ciel étoilé (mouvement apparent)
        _starsMesh.rotation.y += 0.000015;
    }

    // Lune — rotation sur elle-même (face synchronisée simulée)
    if (_moonMesh && _moonMesh.visible) {
        _moonMesh.rotation.y += 0.0001;
    }

    // Scintillement luminaires (toutes les 2 frames pour la perf)
    if (_animFrame % 2 === 0) {
        _flickerLuminaires(time);
    }

    renderer.render(scene, camera);
}

// ── postMessage depuis patrimoine_detail ───────────────────────────────────────
window.addEventListener('message', function(event) {
    if (!event.data || event.data.type !== 'FILTER_ETAGE') return;
    const { etage, piece } = event.data;
    if (etage === 'ext') { allMeshes.forEach(({ mesh }) => _restoreMesh(mesh)); setCameraMode('top'); return; }
    if (piece) { filtrerPiece(null, piece); }
    else if (etage) {
        const m = allMeshes.find(x => x.mesh.userData.etageGuid === etage || String(x.etageId) === String(etage));
        if (m) filtrerEtage(m.etageId, null);
        else allMeshes.forEach(({ mesh }) => _restoreMesh(mesh));
    } else { allMeshes.forEach(({ mesh }) => _restoreMesh(mesh)); }
});
