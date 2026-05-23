from django.contrib import admin
from .models import (
    Client, Projet, Tache, Bug, Livrable,
    Documentation, Devis, LigneDevis, Facture, LigneFacture,
)


class TacheInline(admin.TabularInline):
    model = Tache
    extra = 0

class BugInline(admin.TabularInline):
    model = Bug
    extra = 0

class LigneDevisInline(admin.TabularInline):
    model = LigneDevis
    extra = 1

class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'entreprise', 'email', 'telephone']
    search_fields = ['nom', 'entreprise', 'email']


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'titre', 'type_projet', 'statut', 'priorite', 'client', 'date_fin_prevue']
    list_filter   = ['statut', 'type_projet', 'priorite']
    search_fields = ['titre', 'reference', 'client__nom']
    inlines       = [TacheInline, BugInline]
    readonly_fields = ['reference', 'cree_le', 'modifie_le']


@admin.register(Bug)
class BugAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'projet', 'type_bug', 'severite', 'statut', 'date_ouvert']
    list_filter   = ['statut', 'severite', 'type_bug']
    search_fields = ['titre', 'projet__titre']


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'projet', 'client_nom', 'statut', 'montant_ttc', 'date_devis']
    list_filter   = ['statut']
    inlines       = [LigneDevisInline]
    readonly_fields = ['numero']


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'projet', 'client_nom', 'type_facture', 'statut', 'montant_ttc', 'date_emission']
    list_filter   = ['statut', 'type_facture']
    inlines       = [LigneFactureInline]
    readonly_fields = ['numero']


admin.site.register(Tache)
admin.site.register(Livrable)
admin.site.register(Documentation)
