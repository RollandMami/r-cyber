from django.urls import path
from . import views

app_name = 'bureau_etude'

urlpatterns = [

    # ── Missions ──────────────────────────────────────────────────────────────
    path('',                                    views.mission_list,   name='mission_list'),
    path('nouveau/',                            views.mission_create, name='mission_create'),
    path('<int:pk>/',                           views.mission_detail, name='mission_detail'),
    path('<int:pk>/modifier/',                  views.mission_edit,   name='mission_edit'),

    # ── Documents d'entrée ────────────────────────────────────────────────────
    path('<int:mission_pk>/docs/ajouter/',      views.doc_entree_add,    name='doc_entree_add'),
    path('docs/<int:pk>/supprimer/',            views.doc_entree_delete, name='doc_entree_delete'),

    # ── Livrables ─────────────────────────────────────────────────────────────
    path('<int:mission_pk>/livrables/',         views.livrable_list,   name='livrable_list'),
    path('<int:mission_pk>/livrables/ajouter/', views.livrable_add,    name='livrable_add'),
    path('livrables/<int:pk>/supprimer/',       views.livrable_delete, name='livrable_delete'),

    # ── Devis ─────────────────────────────────────────────────────────────────
    path('<int:mission_pk>/devis/',             views.devis_list,   name='devis_list'),
    path('<int:mission_pk>/devis/nouveau/',     views.devis_create, name='devis_create'),
    path('devis/<int:pk>/',                     views.devis_detail, name='devis_detail'),
    path('devis/<int:pk>/statut/',              views.devis_statut, name='devis_statut'),
    path('devis/<int:pk>/imprimer/',            views.devis_print,  name='devis_print'),

    # ── Notes de calcul ───────────────────────────────────────────────────────
    path('<int:mission_pk>/notes/',             views.note_list,   name='note_list'),
    path('<int:mission_pk>/notes/nouvelle/',    views.note_create, name='note_create'),
    path('notes/<int:pk>/',                     views.note_detail, name='note_detail'),
    path('notes/<int:pk>/modifier/',            views.note_edit,   name='note_edit'),

    # ── Réunions ──────────────────────────────────────────────────────────────
    path('<int:mission_pk>/reunions/',          views.reunion_list,   name='reunion_list'),
    path('<int:mission_pk>/reunions/nouvelle/', views.reunion_create, name='reunion_create'),
    path('reunions/<int:pk>/',                  views.reunion_detail, name='reunion_detail'),
    path('reunions/<int:pk>/modifier/',         views.reunion_edit,   name='reunion_edit'),
]
