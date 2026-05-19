from django.contrib import admin
from .models import (
    Projet, PhotoProjet, DocumentClient, DocumentChantier,
    TacheGantt, LigneBudget, BonCommande, LigneBonCommande,
    RapportActivite, Facture, LigneFacture,
)


class PhotoInline(admin.TabularInline):
    model = PhotoProjet
    extra = 1
    max_num = 5

class DocClientInline(admin.TabularInline):
    model = DocumentClient
    extra = 0

class LigneBudgetInline(admin.TabularInline):
    model = LigneBudget
    extra = 0

class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1

class LigneBonInline(admin.TabularInline):
    model = LigneBonCommande
    extra = 1


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'titre', 'client_nom', 'statut', 'avancement_global', 'visible_vitrine']
    list_filter   = ['statut', 'type_projet', 'visible_vitrine']
    search_fields = ['titre', 'client_nom', 'reference']
    inlines       = [PhotoInline, DocClientInline, LigneBudgetInline]
    readonly_fields = ['reference', 'cree_le', 'modifie_le']

@admin.register(TacheGantt)
class TacheAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'projet', 'statut', 'date_debut', 'date_fin', 'avancement']
    list_filter   = ['statut', 'priorite']
    search_fields = ['titre', 'projet__titre']

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'projet', 'client_nom', 'type_facture', 'montant_ttc', 'statut', 'date_emission']
    list_filter   = ['statut', 'type_facture']
    search_fields = ['numero', 'client_nom', 'projet__titre']
    inlines       = [LigneFactureInline]
    readonly_fields = ['numero', 'cree_le']

@admin.register(BonCommande)
class BonAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'projet', 'fournisseur_nom', 'statut', 'montant_ttc', 'date_commande']
    list_filter   = ['statut']
    inlines       = [LigneBonInline]
    readonly_fields = ['numero']

admin.site.register(PhotoProjet)
admin.site.register(DocumentClient)
admin.site.register(DocumentChantier)
admin.site.register(LigneBudget)
admin.site.register(RapportActivite)
