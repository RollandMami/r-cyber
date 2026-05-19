from django.urls import path
from . import views

app_name = 'construction'

urlpatterns = [

    # ── Vitrine (publique) ────────────────────────────────────────────────────
    path('vitrine/',                    views.vitrine,              name='vitrine'),
    path('vitrine/<int:pk>/',           views.vitrine_detail,       name='vitrine_detail'),

    # ── Dashboard production ──────────────────────────────────────────────────
    path('',                            views.dashboard,            name='dashboard'),

    # ── Projets ───────────────────────────────────────────────────────────────
    path('projets/',                    views.projet_list,          name='projet_list'),
    path('projets/nouveau/',            views.projet_create,        name='projet_create'),
    path('projets/<int:pk>/',           views.projet_detail,        name='projet_detail'),
    path('projets/<int:pk>/modifier/',  views.projet_edit,          name='projet_edit'),

    # ── Photos ────────────────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/photos/ajouter/', views.photo_add,    name='photo_add'),
    path('photos/<int:pk>/supprimer/',              views.photo_delete,  name='photo_delete'),

    # ── Documents client ─────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/docs-client/ajouter/', views.doc_client_add,    name='doc_client_add'),
    path('docs-client/<int:pk>/supprimer/',               views.doc_client_delete, name='doc_client_delete'),

    # ── Documents chantier ────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/docs-chantier/ajouter/', views.doc_chantier_add,    name='doc_chantier_add'),
    path('docs-chantier/<int:pk>/supprimer/',               views.doc_chantier_delete, name='doc_chantier_delete'),

    # ── Planning Gantt ────────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/gantt/',               views.gantt_view,           name='gantt'),
    path('projets/<int:projet_pk>/taches/nouvelle/',     views.tache_create,         name='tache_create'),
    path('taches/<int:pk>/modifier/',                    views.tache_edit,           name='tache_edit'),
    path('taches/<int:pk>/supprimer/',                   views.tache_delete,         name='tache_delete'),
    path('taches/<int:pk>/avancement/',                  views.tache_avancement_ajax,name='tache_avancement'),

    # ── Budget ────────────────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/budget/',              views.budget_view,          name='budget'),
    path('projets/<int:projet_pk>/budget/ajouter/',      views.budget_ligne_add,     name='budget_ligne_add'),
    path('budget/<int:pk>/modifier/',                    views.budget_ligne_edit,    name='budget_ligne_edit'),
    path('budget/<int:pk>/supprimer/',                   views.budget_ligne_delete,  name='budget_ligne_delete'),

    # ── Bons de commande ──────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/commandes/',            views.bon_commande_list,   name='bon_list'),
    path('projets/<int:projet_pk>/commandes/nouveau/',    views.bon_commande_create, name='bon_create'),
    path('commandes/<int:pk>/',                           views.bon_commande_detail, name='bon_detail'),
    path('commandes/<int:pk>/statut/',                    views.bon_commande_statut, name='bon_statut'),

    # ── Rapports d'activité ───────────────────────────────────────────────────
    path('projets/<int:projet_pk>/rapports/',             views.rapport_list,        name='rapport_list'),
    path('projets/<int:projet_pk>/rapports/nouveau/',     views.rapport_create,      name='rapport_create'),
    path('rapports/<int:pk>/',                            views.rapport_detail,      name='rapport_detail'),
    path('rapports/<int:pk>/modifier/',                   views.rapport_edit,        name='rapport_edit'),

    # ── Facturation ───────────────────────────────────────────────────────────
    path('projets/<int:projet_pk>/factures/',             views.facture_list,        name='facture_list'),
    path('projets/<int:projet_pk>/factures/nouvelle/',    views.facture_create,      name='facture_create'),
    path('factures/<int:pk>/',                            views.facture_detail,      name='facture_detail'),
    path('factures/<int:pk>/modifier/',                   views.facture_edit,        name='facture_edit'),
    path('factures/<int:pk>/statut/',                     views.facture_statut,      name='facture_statut'),
    path('factures/<int:pk>/imprimer/',                   views.facture_print,       name='facture_print'),
]
