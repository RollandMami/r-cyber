from django.contrib import admin
from .models import (Patrimoine, Etage, Piece, TypeDocument, Document,
                     Site, DocumentGED, RevetementMur, EquipementOuverture)


class EtageInline(admin.TabularInline):
    model  = Etage
    extra  = 0
    fields = ['nom', 'niveau', 'ifc_guid']


class DocumentInline(admin.TabularInline):
    model  = Document
    extra  = 0
    fields = ['titre', 'type_doc', 'etage', 'fichier', 'version']


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'adresse', 'cree_le']
    search_fields = ['nom', 'adresse']


@admin.register(Patrimoine)
class PatrimoineAdmin(admin.ModelAdmin):
    list_display    = ['nom', 'site', 'adresse', 'statut_conversion', 'surface_totale', 'cree_le']
    list_filter     = ['statut_conversion', 'site']
    search_fields   = ['nom', 'adresse']
    readonly_fields = ['statut_conversion', 'erreur_conversion', 'fichier_json', 'cree_le', 'modifie_le']
    inlines         = [EtageInline, DocumentInline]
    fieldsets = [
        ('Informations', {'fields': ['site', 'nom', 'adresse', 'description',
                                      'annee_construction', 'surface_totale', 'photo']}),
        ('Modèle 3D',    {'fields': ['fichier_ifc', 'fichier_json', 'statut_conversion', 'erreur_conversion']}),
        ('Méta',         {'fields': ['cree_par', 'cree_le', 'modifie_le']}),
    ]


@admin.register(Etage)
class EtageAdmin(admin.ModelAdmin):
    list_display  = ['patrimoine', 'nom', 'niveau']
    list_filter   = ['patrimoine']
    search_fields = ['nom', 'patrimoine__nom']


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'etage', 'surface', 'usage']
    list_filter   = ['etage__patrimoine']
    search_fields = ['nom', 'etage__nom']


@admin.register(TypeDocument)
class TypeDocumentAdmin(admin.ModelAdmin):
    list_display = ['nom', 'icone', 'ordre']
    ordering     = ['ordre']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display    = ['titre', 'patrimoine', 'etage', 'type_doc', 'version', 'uploade_le']
    list_filter     = ['type_doc', 'patrimoine']
    search_fields   = ['titre', 'patrimoine__nom']
    readonly_fields = ['uploade_le', 'uploade_par']


@admin.register(DocumentGED)
class DocumentGEDAdmin(admin.ModelAdmin):
    list_display    = ['titre', 'patrimoine', 'corps', 'dossier', 'version', 'uploade_le']
    list_filter     = ['corps', 'patrimoine']
    search_fields   = ['titre', 'patrimoine__nom']
    readonly_fields = ['uploade_le', 'uploade_par']


@admin.register(RevetementMur)
class RevetementMurAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'patrimoine', 'etage', 'materiau', 'surface', 'type_ifc']
    list_filter   = ['patrimoine']
    search_fields = ['nom', 'patrimoine__nom']


@admin.register(EquipementOuverture)
class EquipementOuvertureAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'patrimoine', 'etage', 'type_element', 'type_ifc']
    list_filter   = ['type_element', 'patrimoine']
    search_fields = ['nom', 'patrimoine__nom']
