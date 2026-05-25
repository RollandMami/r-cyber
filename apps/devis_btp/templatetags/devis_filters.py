"""
MOREX Devis BTP — templatetags/devis_filters.py
Filtres de template personnalisés pour l'affichage des montants.
"""

from django import template
from ..utils import fmt_ar, nombre_en_lettres

register = template.Library()


@register.filter
def ariary(value, decimals=0):
    """Formate un montant en Ariary : {{ montant|ariary }}"""
    return fmt_ar(value, decimals)


@register.filter
def en_lettres(value):
    """Convertit un montant en toutes lettres : {{ montant|en_lettres }}"""
    try:
        return nombre_en_lettres(int(round(float(value))))
    except (TypeError, ValueError):
        return ''


@register.filter
def multiply(value, arg):
    """Multiplie : {{ qty|multiply:pu }}"""
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0


@register.filter
def pct_of(value, total):
    """Calcule le pourcentage : {{ montant|pct_of:total }}"""
    try:
        return round(float(value) / float(total) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.simple_tag
def calc_k(aleas, benefice, tva):
    """{% calc_k devis.taux_aleas devis.taux_benefice devis.taux_tva %}"""
    try:
        return round(
            (1 + float(aleas) / 100) *
            (1 + float(benefice) / 100) *
            (1 + float(tva) / 100),
            4
        )
    except (TypeError, ValueError):
        return 1
