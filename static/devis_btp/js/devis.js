/**
 * MOREX Devis BTP — static/devis_btp/js/devis.js
 * Helpers JavaScript côté client : calculs live, UX améliorée.
 */

/* ── Formatage Ariary ────────────────────────────────────── */
function fmtAr(n, dec = 0) {
  const v = parseFloat(n) || 0;
  return v.toLocaleString('fr-FR', {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  }) + '\u202fAr';
}

/* ── Calcul prix rendu chantier (live preview) ───────────── */
function updateRenduChantier(row) {
  const fourn   = parseFloat(row.querySelector('[data-field="prix_fournisseur"]')?.value) || 0;
  const manuten = parseFloat(row.querySelector('[data-field="frais_manutention"]')?.value) || 0;
  const transp  = parseFloat(row.querySelector('[data-field="frais_transport"]')?.value) || 0;
  const chute   = parseFloat(row.querySelector('[data-field="taux_chute"]')?.value) || 0;
  const rc = (fourn + manuten + transp) * (1 + chute / 100);
  const display = row.querySelector('[data-rc]');
  if (display) display.textContent = fmtAr(rc);
}

/* ── Calcul avant-métré live ─────────────────────────────── */
function calcAvantMetre(row) {
  const unite = row.querySelector('[name$="unite"]')?.value || 'm3';
  const nps   = parseFloat(row.querySelector('[name$="nps"]')?.value) || 1;
  const L     = parseFloat(row.querySelector('[name$="longueur"]')?.value) || 0;
  const l     = parseFloat(row.querySelector('[name$="largeur"]')?.value) || 0;
  const H     = parseFloat(row.querySelector('[name$="hauteur"]')?.value) || 0;
  const signe = row.querySelector('[name$="signe"]')?.value || 'ajouter';

  let partiel = 0;
  if (unite === 'm3')      partiel = nps * L * l * H;
  else if (unite === 'm2') partiel = nps * L * (l || H);
  else                     partiel = nps * L;

  const qam = signe === 'deduire' ? -Math.abs(partiel) : Math.abs(partiel);

  const elPartiel = row.querySelector('[data-partiel]');
  const elQam     = row.querySelector('[data-qam]');
  if (elPartiel) elPartiel.textContent = Math.abs(partiel).toFixed(4);
  if (elQam)     elQam.textContent     = qam.toFixed(4);
}

/* ── Calcul taux horaire PHMO live ───────────────────────── */
function calcTauxHoraire(row) {
  const base   = parseFloat(row.querySelector('[data-field="salaire_base"]')?.value) || 0;
  const charge = parseFloat(row.querySelector('[data-field="taux_charges"]')?.value) || 0;
  const jours  = parseFloat(row.querySelector('[data-field="nb_jours_mois"]')?.value) || 26;
  const heures = parseFloat(row.querySelector('[data-field="heures_par_jour"]')?.value) || 8;

  const salCharge = base * (1 + charge / 100);
  const heuresMois = jours * heures;
  const taux = heuresMois > 0 ? salCharge / heuresMois : 0;

  const elTaux = row.querySelector('[data-taux-horaire]');
  if (elTaux) elTaux.textContent = fmtAr(taux) + '/h';
}

/* ── Calcul coefficient K live ───────────────────────────── */
function calcCoeffK() {
  const aleas  = parseFloat(document.getElementById('id_taux_aleas')?.value) || 0;
  const benef  = parseFloat(document.getElementById('id_taux_benefice')?.value) || 0;
  const tva    = parseFloat(document.getElementById('id_taux_tva')?.value) || 0;
  const K = (1 + aleas / 100) * (1 + benef / 100) * (1 + tva / 100);
  const el = document.getElementById('k-value');
  if (el) el.textContent = K.toFixed(4);
}

/* ── Auto-confirm delete (double click protection) ───────── */
function confirmDelete(message) {
  return confirm(message || 'Confirmer la suppression ?');
}

/* ── Toggle visibilité section ───────────────────────────── */
function toggleSection(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

/* ── Initialisation au chargement ────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  // Attacher les calculs live sur les champs matériaux
  document.querySelectorAll('[data-mat-row]').forEach(row => {
    row.querySelectorAll('input').forEach(inp => {
      inp.addEventListener('input', () => updateRenduChantier(row));
    });
    updateRenduChantier(row);
  });

  // Attacher les calculs live sur les lignes avant-métré
  document.querySelectorAll('[data-am-row]').forEach(row => {
    row.querySelectorAll('input, select').forEach(inp => {
      inp.addEventListener('input', () => calcAvantMetre(row));
      inp.addEventListener('change', () => calcAvantMetre(row));
    });
    calcAvantMetre(row);
  });

  // Attacher les calculs PHMO
  document.querySelectorAll('[data-phmo-row]').forEach(row => {
    row.querySelectorAll('input').forEach(inp => {
      inp.addEventListener('input', () => calcTauxHoraire(row));
    });
    calcTauxHoraire(row);
  });

  // Coefficient K live
  ['id_taux_aleas', 'id_taux_benefice', 'id_taux_tva'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', calcCoeffK);
  });
  calcCoeffK();

  // Auto-fermeture des messages flash après 5s
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    }, 5000);
  });

  // Highlight des lignes total
  document.querySelectorAll('tr.total-row td').forEach(td => {
    td.style.fontWeight = '600';
  });
});

/* ── Export utilitaires pour usage inline ────────────────── */
window.MOREX = { fmtAr, updateRenduChantier, calcAvantMetre, calcTauxHoraire, calcCoeffK, toggleSection };
