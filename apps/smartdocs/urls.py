from django.urls import path
from . import views

app_name = 'smartdocs'

urlpatterns = [
    # ── Sites ──────────────────────────────────────────────────────
    path('',                              views.site_list,   name='site_list'),
    path('sites/nouveau/',                views.site_create, name='site_create'),
    path('sites/<int:pk>/',               views.site_detail, name='site_detail'),
    path('sites/<int:pk>/modifier/',      views.site_edit,   name='site_edit'),
    path('sites/<int:pk>/supprimer/',     views.site_delete, name='site_delete'),

    # ── Patrimoines (bâtiments) ────────────────────────────────────
    path('nouveau/',                          views.patrimoine_create,          name='patrimoine_create'),
    path('sites/<int:site_pk>/nouveau/',      views.patrimoine_create_in_site,  name='patrimoine_create_in_site'),
    path('<int:pk>/',                         views.patrimoine_detail,           name='patrimoine_detail'),
    path('<int:pk>/modifier/',                views.patrimoine_edit,             name='patrimoine_edit'),
    path('<int:pk>/supprimer/',               views.patrimoine_delete,           name='patrimoine_delete'),

    # ── Documents ─────────────────────────────────────────────────
    path('<int:patrimoine_pk>/documents/ajouter/', views.document_upload,   name='document_upload'),
    path('documents/<int:pk>/telecharger/',        views.document_download, name='document_download'),
    path('documents/<int:pk>/supprimer/',          views.document_delete,   name='document_delete'),

    # ── GED ────────────────────────────────────────────────────────
    path('<int:patrimoine_pk>/ged/upload/',        views.ged_upload,            name='ged_upload'),
    path('<int:patrimoine_pk>/ged/dossier/',       views.ged_download_dossier,  name='ged_download_dossier'),
    path('ged/<int:pk>/telecharger/',              views.ged_download,          name='ged_download'),
    path('ged/<int:pk>/supprimer/',                views.ged_delete,            name='ged_delete'),

    # ── API ────────────────────────────────────────────────────────
    path('api/patrimoines-sans-site/',       views.api_tous_patrimoines, name='api_sans_site'),
]
