from django.contrib import admin
from .models import Patrimoine, Etage, Piece, TypeDocument, Document


class EtageInline(admin.TabularInline):
    model  = Etage
    extra  = 0
    fields = ['nom', 'niveau', 'ifc_guid']


class DocumentInline(admin.TabularInline):
    model  = Document
    extra  = 0
    fields = ['titre', 'type_doc', 'etage', 'fichier', 'version']


@admin.register(Patrimoine)
class PatrimoineAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'adresse', 'statut_conversion', 'has_viewer', 'cree_le']
    list_filter   = ['statut_conversion']
    search_fields = ['nom', 'adresse']
    readonly_fields = ['statut_conversion', 'erreur_conversion', 'fichier_json', 'cree_le', 'modifie_le']
    inlines       = [EtageInline, DocumentInline]
    fieldsets = [
        ('Informations', {'fields': ['nom', 'adresse', 'description', 'annee_construction', 'surface_totale', 'photo']}),
        ('Modèle 3D',    {'fields': ['fichier_ifc', 'fichier_json', 'statut_conversion', 'erreur_conversion']}),
        ('Méta',         {'fields': ['cree_par', 'cree_le', 'modifie_le']}),
    ]


@admin.register(Etage)
class EtageAdmin(admin.ModelAdmin):
    list_display  = ['patrimoine', 'nom', 'niveau', 'ifc_guid']
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
    list_display  = ['titre', 'patrimoine', 'etage', 'type_doc', 'version', 'uploade_le']
    list_filter   = ['type_doc', 'patrimoine']
    search_fields = ['titre', 'patrimoine__nom']
    readonly_fields = ['uploade_le', 'uploade_par']
