from django.urls import path
from . import views

app_name = 'info_dev'

urlpatterns = [

    # ── Clients ───────────────────────────────────────────────────────────────
    path('clients/',                              views.client_list,   name='client_list'),
    path('clients/nouveau/',                      views.client_create, name='client_create'),
    path('clients/<int:pk>/modifier/',            views.client_edit,   name='client_edit'),

    # ── Projets ───────────────────────────────────────────────────────────────
    path('',                                      views.projet_list,   name='projet_list'),
    path('nouveau/',                              views.projet_create, name='projet_create'),
    path('<int:pk>/',                             views.projet_detail, name='projet_detail'),
    path('<int:pk>/modifier/',                    views.projet_edit,   name='projet_edit'),

    # ── Tâches (Kanban) ───────────────────────────────────────────────────────
    path('<int:projet_pk>/taches/',               views.tache_list,        name='tache_list'),
    path('<int:projet_pk>/taches/nouvelle/',      views.tache_create,      name='tache_create'),
    path('taches/<int:pk>/modifier/',             views.tache_edit,        name='tache_edit'),
    path('taches/<int:pk>/supprimer/',            views.tache_delete,      name='tache_delete'),
    path('taches/<int:pk>/statut/',               views.tache_statut_ajax, name='tache_statut'),

    # ── Bugs / Demandes ───────────────────────────────────────────────────────
    path('<int:projet_pk>/bugs/',                 views.bug_list,   name='bug_list'),
    path('<int:projet_pk>/bugs/nouveau/',         views.bug_create, name='bug_create'),
    path('bugs/<int:pk>/',                        views.bug_detail, name='bug_detail'),
    path('bugs/<int:pk>/modifier/',               views.bug_edit,   name='bug_edit'),

    # ── Livrables ─────────────────────────────────────────────────────────────
    path('<int:projet_pk>/livrables/',            views.livrable_list,   name='livrable_list'),
    path('<int:projet_pk>/livrables/ajouter/',    views.livrable_add,    name='livrable_add'),
    path('livrables/<int:pk>/supprimer/',         views.livrable_delete, name='livrable_delete'),

    # ── Documentation ─────────────────────────────────────────────────────────
    path('<int:projet_pk>/docs/',                 views.doc_list,   name='doc_list'),
    path('<int:projet_pk>/docs/nouvelle/',        views.doc_create, name='doc_create'),
    path('docs/<int:pk>/',                        views.doc_detail, name='doc_detail'),
    path('docs/<int:pk>/modifier/',               views.doc_edit,   name='doc_edit'),

    # ── Devis ─────────────────────────────────────────────────────────────────
    path('<int:projet_pk>/devis/',                views.devis_list,   name='devis_list'),
    path('<int:projet_pk>/devis/nouveau/',        views.devis_create, name='devis_create'),
    path('devis/<int:pk>/',                       views.devis_detail, name='devis_detail'),
    path('devis/<int:pk>/statut/',                views.devis_statut, name='devis_statut'),
    path('devis/<int:pk>/imprimer/',              views.devis_print,  name='devis_print'),

    # ── Facturation ───────────────────────────────────────────────────────────
    path('<int:projet_pk>/factures/',             views.facture_list,   name='facture_list'),
    path('<int:projet_pk>/factures/nouvelle/',    views.facture_create, name='facture_create'),
    path('factures/<int:pk>/',                    views.facture_detail, name='facture_detail'),
    path('factures/<int:pk>/statut/',             views.facture_statut, name='facture_statut'),
    path('factures/<int:pk>/imprimer/',           views.facture_print,  name='facture_print'),
]
