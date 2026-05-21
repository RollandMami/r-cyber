from django.contrib import admin
from .models import Mission, DocumentEntree, PlanLivrable, Devis, LigneDevis, NoteCalcul, Reunion


class DocEntreeInline(admin.TabularInline):
    model = DocumentEntree
    extra = 0

class LivrableInline(admin.TabularInline):
    model = PlanLivrable
    extra = 0

class LigneDevisInline(admin.TabularInline):
    model = LigneDevis
    extra = 1


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'titre', 'type_mission', 'client_nom', 'statut', 'date_rendu']
    list_filter   = ['statut', 'type_mission']
    search_fields = ['titre', 'client_nom', 'reference']
    inlines       = [DocEntreeInline, LivrableInline]
    readonly_fields = ['reference', 'cree_le', 'modifie_le']


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'mission', 'client_nom', 'statut', 'montant_ttc', 'date_devis']
    list_filter   = ['statut']
    inlines       = [LigneDevisInline]
    readonly_fields = ['numero', 'cree_le']


@admin.register(NoteCalcul)
class NoteCalculAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'mission', 'domaine', 'version', 'valide']
    list_filter   = ['domaine', 'valide']
    search_fields = ['titre', 'mission__titre']


admin.site.register(DocumentEntree)
admin.site.register(PlanLivrable)
admin.site.register(Reunion)
