"""
MOREX Devis BTP — urls.py
Inclure dans votre projet avec :
    path('devis/', include('devis_btp.urls', namespace='devis_btp')),
"""

from django.urls import path
from . import views

app_name = 'devis_btp'

urlpatterns = [
    # ── Dashboard ────────────────────────────────────────────────
    path('',                        views.dashboard,          name='dashboard'),

    # ── Devis CRUD ───────────────────────────────────────────────
    path('devis/',                  views.devis_list,         name='devis_list'),
    path('devis/nouveau/',          views.devis_create,       name='devis_create'),
    path('devis/<int:pk>/',         views.devis_detail,       name='devis_detail'),
    path('devis/<int:pk>/modifier/',views.devis_edit,         name='devis_edit'),
    path('devis/<int:pk>/supprimer/',views.devis_delete,      name='devis_delete'),
    path('devis/<int:pk>/imprimer/',views.devis_print,        name='devis_print'),

    # ── Base matériaux ───────────────────────────────────────────
    path('materiaux/',                      views.materiaux_list,   name='materiaux_list'),
    path('materiaux/nouveau/',              views.materiau_create,  name='materiau_create'),
    path('materiaux/<int:pk>/modifier/',    views.materiau_edit,    name='materiau_edit'),
    path('materiaux/<int:pk>/supprimer/',   views.materiau_delete,  name='materiau_delete'),

    # ── Base dosages ─────────────────────────────────────────────
    path('dosages/',                        views.dosages_list,     name='dosages_list'),
    path('dosages/nouveau/',                views.dosage_create,    name='dosage_create'),
    path('dosages/<int:pk>/modifier/',      views.dosage_edit,      name='dosage_edit'),
    path('dosages/<int:pk>/supprimer/',     views.dosage_delete,    name='dosage_delete'),

    # ── Étapes du devis ──────────────────────────────────────────
    path('devis/<int:pk>/avant-metre/',
         views.avantmetre,                  name='avantmetre'),
    path('devis/<int:pk>/avant-metre/<int:ligne_pk>/modifier/',
         views.avantmetre_edit_ligne,       name='avantmetre_edit_ligne'),
    path('devis/<int:pk>/avant-metre/<int:ligne_pk>/supprimer/',
         views.avantmetre_delete_ligne,     name='avantmetre_delete_ligne'),

    path('devis/<int:pk>/nomenclature/',    views.nomenclature,     name='nomenclature'),

    path('devis/<int:pk>/phmo/',            views.phmo,             name='phmo'),
    path('devis/<int:pk>/phmo/equipe/ajouter/',
         views.phmo_add_equipe,             name='phmo_add_equipe'),
    path('devis/<int:pk>/phmo/equipe/<int:equipe_pk>/supprimer/',
         views.phmo_delete_equipe,          name='phmo_delete_equipe'),
    path('devis/<int:pk>/phmo/forfait/ajouter/',
         views.phmo_add_forfait,            name='phmo_add_forfait'),
    path('devis/<int:pk>/phmo/forfait/<int:forfait_pk>/supprimer/',
         views.phmo_delete_forfait,         name='phmo_delete_forfait'),

    path('devis/<int:pk>/frais/',           views.frais_chantier,   name='frais_chantier'),
    path('devis/<int:pk>/frais/<int:frais_pk>/supprimer/',
         views.frais_delete,                name='frais_delete'),

    path('devis/<int:pk>/prix-unitaires/',  views.prix_unitaires,   name='prix_unitaires'),
    path('devis/<int:pk>/debourse-sec/',    views.debourse_sec,     name='debourse_sec'),
    path('devis/<int:pk>/recap/',           views.recap_final,      name='recap_final'),

    # ── API JSON ─────────────────────────────────────────────────
    path('api/materiaux/',                  views.api_materiaux,    name='api_materiaux'),
    path('api/dosages/',                    views.api_dosages,      name='api_dosages'),
    path('api/devis/<int:pk>/state/',       views.api_devis_state,  name='api_devis_state'),
]
