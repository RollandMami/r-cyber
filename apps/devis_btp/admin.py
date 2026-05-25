"""
MOREX Devis BTP — admin.py
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Materiau, Dosage, Devis, LigneAvantMetre, RecapAvantMetre,
    EquipePHMO, TacheForfaitMO, FraisChantier,
    LigneDEPS, BonCommandeMateriaux, LigneBonCommande, LigneNomenclature,
)


@admin.register(Materiau)
class MateriauAdmin(admin.ModelAdmin):
    list_display  = ('code', 'designation', 'unite', 'prix_fournisseur',
                     'frais_manutention', 'frais_transport', 'taux_chute',
                     'prix_rendu_chantier_display', 'actif')
    list_filter   = ('actif', 'unite')
    search_fields = ('code', 'designation')
    ordering      = ('code',)

    def prix_rendu_chantier_display(self, obj):
        return f'{obj.prix_rendu_chantier:,.0f} Ar'
    prix_rendu_chantier_display.short_description = 'Rendu chantier'


@admin.register(Dosage)
class DosageAdmin(admin.ModelAdmin):
    list_display  = ('code', 'categorie', 'dosage_kg', 'choix_liant',
                     'sable_m3', 'gravillon_m3', 'eau_litres', 'ciment_kg', 'actif')
    list_filter   = ('categorie', 'actif')
    search_fields = ('code', 'choix_liant')


class LigneAvantMetreInline(admin.TabularInline):
    model  = LigneAvantMetre
    extra  = 1
    fields = ('ouvrage_num', 'designation', 'repere', 'unite', 'signe',
              'nps', 'longueur', 'largeur', 'hauteur', 'partiel', 'qam')
    readonly_fields = ('partiel', 'qam')


class RecapAvantMetreInline(admin.TabularInline):
    model  = RecapAvantMetre
    extra  = 0
    fields = ('numero', 'designation', 'unite', 'qam', 'dosage', 'ordre')


class EquipePHMOInline(admin.TabularInline):
    model  = EquipePHMO
    extra  = 1
    fields = ('designation', 'categorie', 'salaire_base', 'taux_charges',
              'nb_jours_mois', 'heures_par_jour', 'heures_total')


class TacheForfaitMOInline(admin.TabularInline):
    model  = TacheForfaitMO
    extra  = 1
    fields = ('designation', 'unite', 'quantite', 'pu_mo', 'montant_mo')
    readonly_fields = ('montant_mo',)


class FraisChantierInline(admin.TabularInline):
    model  = FraisChantier
    extra  = 1
    fields = ('categorie', 'designation', 'unite', 'quantite', 'prix_unitaire', 'montant')
    readonly_fields = ('montant',)


class LigneDEPSInline(admin.TabularInline):
    model  = LigneDEPS
    extra  = 0
    fields = ('numero', 'designation', 'unite', 'qam',
              'pu_materiaux', 'pu_mo', 'pu_frais', 'montant_total')
    readonly_fields = ('montant_total',)


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display  = ('reference', 'titre', 'client_nom', 'source', 'statut',
                     'date_devis', 'montant_ttc_display', 'cree_par')
    list_filter   = ('statut', 'source', 'mode_mo')
    search_fields = ('reference', 'client_nom', 'titre')
    ordering      = ('-date_devis',)
    readonly_fields = ('reference', 'montant_debourse_sec', 'montant_ht',
                       'montant_tva', 'montant_ttc', 'coefficient_k_display')
    inlines = [
        LigneAvantMetreInline, RecapAvantMetreInline,
        EquipePHMOInline, TacheForfaitMOInline,
        FraisChantierInline, LigneDEPSInline,
    ]
    fieldsets = (
        ('Identité', {
            'fields': ('reference', 'titre', 'statut', 'source',
                       'mission_id_ref', 'projet_id_ref')
        }),
        ('Client', {
            'fields': ('client_nom', 'client_adresse', 'client_tel',
                       'client_email', 'maitre_ouvrage')
        }),
        ('Chantier', {
            'fields': ('adresse_chantier', 'duree_chantier_mois', 'mode_mo')
        }),
        ('Coefficient K', {
            'fields': ('taux_aleas', 'taux_benefice', 'taux_tva', 'coefficient_k_display')
        }),
        ('Montants calculés', {
            'fields': ('montant_debourse_sec', 'montant_ht', 'montant_tva', 'montant_ttc'),
            'classes': ('collapse',),
        }),
        ('Émetteur', {
            'fields': ('emetteur_nom', 'emetteur_adresse', 'emetteur_tel',
                       'emetteur_email', 'emetteur_nif'),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('date_devis', 'date_validite')
        }),
        ('Textes', {
            'fields': ('conditions', 'notes'),
            'classes': ('collapse',),
        }),
    )

    def montant_ttc_display(self, obj):
        return format_html('<strong>{:,.0f} Ar</strong>', obj.montant_ttc)
    montant_ttc_display.short_description = 'Montant TTC'

    def coefficient_k_display(self, obj):
        return f'{obj.coefficient_k:.4f}'
    coefficient_k_display.short_description = 'Coefficient K'


class LigneBonCommandeInline(admin.TabularInline):
    model  = LigneBonCommande
    extra  = 1
    fields = ('materiau', 'designation', 'unite', 'quantite', 'prix_unitaire', 'montant_ht')
    readonly_fields = ('montant_ht',)


@admin.register(BonCommandeMateriaux)
class BonCommandeAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'fournisseur_nom', 'date_commande', 'statut',
                     'montant_ht', 'montant_ttc')
    list_filter   = ('statut',)
    search_fields = ('numero', 'fournisseur_nom')
    inlines       = [LigneBonCommandeInline]
    readonly_fields = ('numero', 'montant_ttc')
