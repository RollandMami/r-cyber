# ─────────────────────────────────────────────────────────────────────────────
# Routes PERT à ajouter dans apps/construction/urls.py
# ─────────────────────────────────────────────────────────────────────────────
#
# Ajoute ces lignes dans ton urlpatterns existant :

"""
from django.urls import path
from . import views

app_name = 'construction'

urlpatterns = [
    # ... tes URLs existantes ...

    # ── PERT ────────────────────────────────────────────────
    # PERT standalone (sans projet)
    path('pert/',
         views.pert_editor,
         name='pert_editor'),

    # PERT d'un projet — ouvre le réseau actif ou en crée un
    path('projets/<int:projet_pk>/pert/',
         views.pert_projet,
         name='pert_projet'),

    # Liste de toutes les versions PERT d'un projet
    path('projets/<int:projet_pk>/pert/versions/',
         views.pert_list,
         name='pert_list'),

    # Ouvre une version PERT spécifique
    path('projets/<int:projet_pk>/pert/<int:reseau_pk>/',
         views.pert_version,
         name='pert_version'),

    # Sauvegarde PERT — réseau existant
    path('projets/<int:projet_pk>/pert/<int:reseau_pk>/sauvegarder/',
         views.pert_save,
         name='pert_save'),

    # Sauvegarde PERT — nouveau réseau
    path('projets/<int:projet_pk>/pert/nouveau/sauvegarder/',
         views.pert_save,
         name='pert_save_new'),

    # Suppression d'une version PERT
    path('projets/<int:projet_pk>/pert/<int:reseau_pk>/supprimer/',
         views.pert_delete,
         name='pert_delete'),
]
"""

# ─────────────────────────────────────────────────────────────────────────────
# Admin — ajoute dans apps/construction/admin.py
# ─────────────────────────────────────────────────────────────────────────────

"""
from django.contrib import admin
from .models import ReseauPert, NoeudPert, LienPert


class NoeudPertInline(admin.TabularInline):
    model  = NoeudPert
    extra  = 0
    fields = ['label', 'early', 'late', 'marge', 'est_critique', 'pos_x', 'pos_y']
    readonly_fields = ['late', 'marge', 'est_critique']


class LienPertInline(admin.TabularInline):
    model  = LienPert
    extra  = 0
    fields = ['noeud_from', 'noeud_to', 'poids', 'est_critique']
    readonly_fields = ['est_critique']


@admin.register(ReseauPert)
class ReseauPertAdmin(admin.ModelAdmin):
    list_display    = ['projet', 'nom', 'version', 'est_actif', 'duree_totale', 'cree_le']
    list_filter     = ['est_actif', 'projet']
    search_fields   = ['nom', 'projet__titre']
    readonly_fields = ['cree_le', 'modifie_le', 'calcule_le']
    inlines         = [NoeudPertInline, LienPertInline]
"""

# ─────────────────────────────────────────────────────────────────────────────
# Migration — crée les tables PERT
# ─────────────────────────────────────────────────────────────────────────────

"""
# Sur le serveur :
cd /var/www/rcyber/app
source env/bin/activate

python manage.py makemigrations construction
python manage.py migrate

sudo systemctl restart r-cyber
"""

# ─────────────────────────────────────────────────────────────────────────────
# Lien depuis projet_detail.html — bouton PERT
# ─────────────────────────────────────────────────────────────────────────────

"""
<!-- Dans projet_detail.html, dans les boutons d'action du projet : -->
<a href="{% url 'construction:pert_projet' projet.pk %}"
   class="btn btn-outline-primary btn-sm">
    <i class="fas fa-project-diagram me-1"></i> Réseau PERT
</a>

<!-- Compteur PERT dans les stats du projet : -->
{% with nb_pert=projet.reseaux_pert.count %}
{% if nb_pert %}
<span class="badge bg-info">{{ nb_pert }} version{{ nb_pert|pluralize }} PERT</span>
{% endif %}
{% endwith %}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Lien depuis gantt.html — bouton PERT dans la toolbar
# ─────────────────────────────────────────────────────────────────────────────

"""
<!-- Dans gantt.html, dans la barre d'outils : -->
<a href="{% url 'construction:pert_projet' projet.pk %}"
   class="btn btn-outline-secondary btn-sm" title="Ouvrir l'éditeur PERT">
    <i class="fas fa-project-diagram me-1"></i> PERT
</a>
"""
