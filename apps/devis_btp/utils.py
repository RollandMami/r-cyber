"""
MOREX Devis BTP — utils.py
Fonctions utilitaires : calculs nomenclature, DEPS, coefficient K, montant en lettres.
"""

from decimal import Decimal


# ─────────────────────────────────────────────────────────────────────────────
#  MAPPING MATÉRIAUX (mots-clés → prix rendu chantier)
# ─────────────────────────────────────────────────────────────────────────────

def get_materiaux_map():
    """
    Retourne un dict {type_materiau: prix_rendu_chantier}
    en cherchant par mots-clés dans la designation.
    """
    from .models import Materiau
    result = {}
    keywords = {
        'sable':      ['sable'],
        'gravillon':  ['gravillon', 'gravier'],
        'eau':        ['eau'],
        'ciment':     ['ciment'],
        'chaux':      ['chaux'],
        'acier_ha':   ['fer rond', 'acier ha', 'fer ha'],
        'fil_recuit': ['fil recuit', 'fil de fer'],
        'moellon':    ['moellon'],
        'caillasse':  ['caillasse'],
        'brique':     ['brique'],
        'pointe':     ['pointe'],
        'planche':    ['planche'],
    }
    materiaux = Materiau.objects.filter(actif=True)
    for mat in materiaux:
        desig_lower = mat.designation.lower()
        for key, words in keywords.items():
            if any(w in desig_lower for w in words):
                result[key] = float(mat.prix_rendu_chantier)
                break
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  CALCUL DE NOMENCLATURE
# ─────────────────────────────────────────────────────────────────────────────

def calculer_nomenclature(devis):
    """
    Génère ou met à jour les LigneNomenclature pour un devis.
    Pour chaque RecapAvantMetre ayant un dosage associé,
    calcule la quantité de chaque matériau = QAM × ratio_dosage.
    """
    from .models import LigneNomenclature, Materiau

    # Supprimer l'ancienne nomenclature
    LigneNomenclature.objects.filter(devis=devis).delete()

    materiaux = list(Materiau.objects.filter(actif=True))
    lignes_a_creer = []

    for recap in devis.recap_am.select_related('dosage').all():
        if not recap.dosage:
            continue
        dos = recap.dosage
        qam = float(recap.qam)

        ratios = {
            'sable':      float(dos.sable_m3),
            'gravillon':  float(dos.gravillon_m3),
            'eau':        float(dos.eau_litres),
            'ciment':     float(dos.ciment_kg),
            'chaux':      float(dos.chaux_kg),
            'acier_ha':   float(dos.acier_kg),
            'fil_recuit': float(dos.fil_recuit_kg),
        }

        for mat in materiaux:
            desig_lower = mat.designation.lower()
            qty_nette = 0

            if any(w in desig_lower for w in ['sable']):
                qty_nette = qam * ratios['sable']
            elif any(w in desig_lower for w in ['gravillon', 'gravier']):
                qty_nette = qam * ratios['gravillon']
            elif any(w in desig_lower for w in ['eau']):
                qty_nette = qam * ratios['eau']
            elif any(w in desig_lower for w in ['ciment']):
                qty_nette = qam * ratios['ciment']
            elif any(w in desig_lower for w in ['chaux']):
                qty_nette = qam * ratios['chaux']
            elif any(w in desig_lower for w in ['fer rond', 'acier ha']):
                qty_nette = qam * ratios['acier_ha']
            elif any(w in desig_lower for w in ['fil recuit']):
                qty_nette = qam * ratios['fil_recuit']

            if qty_nette > 0:
                qty_chute = qty_nette * (1 + float(mat.taux_chute) / 100)
                lignes_a_creer.append(LigneNomenclature(
                    devis=devis,
                    recap_am=recap,
                    materiau=mat,
                    quantite_nette=round(qty_nette, 4),
                    quantite_chute=round(qty_chute, 4),
                ))

    if lignes_a_creer:
        LigneNomenclature.objects.bulk_create(lignes_a_creer)


# ─────────────────────────────────────────────────────────────────────────────
#  CALCUL DU DÉBOURSÉ SEC
# ─────────────────────────────────────────────────────────────────────────────

def calculer_deps(devis):
    """
    Génère ou met à jour les LigneDEPS pour un devis.
    Répartit les frais de chantier proportionnellement au montant matériaux.
    """
    from .models import LigneDEPS

    LigneDEPS.objects.filter(devis=devis).delete()

    # Total matériaux (pour ventilation des frais)
    total_mat = sum(
        float(r.montant_materiaux_total)
        for r in devis.recap_am.all()
    )

    # Total frais
    total_frais = sum(
        float(f.montant) for f in devis.frais_chantier.all()
    )

    # MO forfait par tâche
    forfaits = {}
    if devis.mode_mo == 'forfait':
        for t in devis.taches_forfait.all():
            forfaits[t.designation] = float(t.montant_mo)

    lignes = []
    for i, recap in enumerate(devis.recap_am.select_related('dosage').order_by('ordre', 'numero')):
        qam = float(recap.qam)
        pu_mat = recap.montant_materiaux_unitaire if qam else 0

        # Ventilation des frais proportionnelle
        part_frais = 0
        if total_mat > 0:
            part_frais = (float(recap.montant_materiaux_total) / total_mat) * total_frais
        pu_frais = round(part_frais / qam, 2) if qam else 0

        # MO
        mo_montant = forfaits.get(recap.designation, 0)
        pu_mo_calc = round(mo_montant / qam, 2) if qam else 0

        lignes.append(LigneDEPS(
            devis=devis,
            recap_am=recap,
            numero=recap.numero,
            designation=recap.designation,
            unite=recap.unite,
            qam=recap.qam,
            pu_materiaux=pu_mat,
            pu_mo=pu_mo_calc,
            pu_frais=pu_frais,
            ordre=i,
        ))

    for ligne in lignes:
        ligne.montant_materiaux = round(float(ligne.qam) * float(ligne.pu_materiaux), 2)
        ligne.montant_mo        = round(float(ligne.qam) * float(ligne.pu_mo), 2)
        ligne.montant_frais     = round(float(ligne.qam) * float(ligne.pu_frais), 2)
        ligne.montant_total     = round(
            float(ligne.montant_materiaux) + float(ligne.montant_mo) + float(ligne.montant_frais), 2
        )

    if lignes:
        LigneDEPS.objects.bulk_create(lignes)

    # Mettre à jour les totaux du devis
    devis.save_totaux()


# ─────────────────────────────────────────────────────────────────────────────
#  COEFFICIENT K
# ─────────────────────────────────────────────────────────────────────────────

def calcul_recap_financier(devis):
    """
    Retourne un dict avec tous les montants du récapitulatif.
    DS → HT → TVA → TTC
    """
    ds = float(devis.montant_debourse_sec)
    aleas_pct  = float(devis.taux_aleas) / 100
    benef_pct  = float(devis.taux_benefice) / 100
    tva_pct    = float(devis.taux_tva) / 100

    montant_aleas  = round(ds * aleas_pct, 2)
    ds_avec_aleas  = ds + montant_aleas
    montant_benef  = round(ds_avec_aleas * benef_pct, 2)
    ht             = round(ds_avec_aleas + montant_benef, 2)
    tva_montant    = round(ht * tva_pct, 2)
    ttc            = round(ht + tva_montant, 2)
    k              = round((1 + aleas_pct) * (1 + benef_pct) * (1 + tva_pct), 6)

    return {
        'debourse_sec':    ds,
        'taux_aleas':      float(devis.taux_aleas),
        'montant_aleas':   montant_aleas,
        'ds_avec_aleas':   ds_avec_aleas,
        'taux_benefice':   float(devis.taux_benefice),
        'montant_benefice':montant_benef,
        'montant_ht':      ht,
        'taux_tva':        float(devis.taux_tva),
        'montant_tva':     tva_montant,
        'montant_ttc':     ttc,
        'coefficient_k':   k,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MONTANT EN LETTRES (ariary)
# ─────────────────────────────────────────────────────────────────────────────

_UNITES = [
    '', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept',
    'huit', 'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze',
    'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf'
]
_DIZAINES = [
    '', '', 'vingt', 'trente', 'quarante', 'cinquante',
    'soixante', 'soixante', 'quatre-vingt', 'quatre-vingt'
]


def _cents(n):
    if n == 0:
        return ''
    if n < 20:
        return _UNITES[n]
    d, u = divmod(n, 10)
    if d in (7, 9):
        base = _DIZAINES[d] + ('-' if u else '') + (_UNITES[10 + u] if u else _UNITES[10])
    elif u == 1 and d < 8:
        base = _DIZAINES[d] + '-et-un'
    else:
        base = _DIZAINES[d] + ('-' + _UNITES[u] if u else '')
    return base.strip('-')


def _segment(n):
    """Convertit un entier < 1000 en lettres."""
    if n == 0:
        return ''
    c = n // 100
    r = n % 100
    parts = []
    if c == 1:
        parts.append('cent')
    elif c > 1:
        parts.append(_UNITES[c] + ' cent')
    if r:
        parts.append(_cents(r))
    return ' '.join(parts)


def nombre_en_lettres(n: int) -> str:
    """Convertit un entier en toutes lettres (français, ariary)."""
    n = int(round(n))
    if n == 0:
        return 'zéro ariary'
    if n < 0:
        return 'moins ' + nombre_en_lettres(-n)

    milliards = n // 1_000_000_000
    millions  = (n % 1_000_000_000) // 1_000_000
    milliers  = (n % 1_000_000) // 1_000
    reste     = n % 1_000

    parts = []
    if milliards:
        s = _segment(milliards)
        parts.append(s + (' milliard' if milliards == 1 else ' milliards'))
    if millions:
        s = _segment(millions)
        parts.append(s + (' million' if millions == 1 else ' millions'))
    if milliers:
        s = _segment(milliers)
        if milliers == 1:
            parts.append('mille')
        else:
            parts.append(s + ' mille')
    if reste:
        parts.append(_segment(reste))

    return ' '.join(parts) + ' ariary'


# ─────────────────────────────────────────────────────────────────────────────
#  FORMATAGE ARIARY
# ─────────────────────────────────────────────────────────────────────────────

def fmt_ar(n, decimals=0) -> str:
    """Formate un montant en Ariary : '1 234 567 Ar'"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        n = 0
    if decimals == 0:
        return f"{int(round(n)):,} Ar".replace(',', '\u202f')
    return f"{n:,.{decimals}f} Ar".replace(',', '\u202f')
