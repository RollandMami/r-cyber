from django.urls import path
from . import views

app_name = 'smartdocs'

urlpatterns = [
    # Patrimoines
    path('',                          views.patrimoine_list,   name='patrimoine_list'),
    path('nouveau/',                   views.patrimoine_create, name='patrimoine_create'),
    path('<int:pk>/',                  views.patrimoine_detail, name='patrimoine_detail'),
    path('<int:pk>/modifier/',         views.patrimoine_edit,   name='patrimoine_edit'),
    path('<int:pk>/supprimer/',        views.patrimoine_delete, name='patrimoine_delete'),

    # Documents (ancien système)
    path('<int:patrimoine_pk>/documents/ajouter/', views.document_upload,   name='document_upload'),
    path('documents/<int:pk>/telecharger/',        views.document_download, name='document_download'),
    path('documents/<int:pk>/supprimer/',          views.document_delete,   name='document_delete'),

    # GED
    path('<int:patrimoine_pk>/ged/upload/',         views.ged_upload,   name='ged_upload'),
    path('ged/<int:pk>/telecharger/',               views.ged_download, name='ged_download'),
    path('ged/<int:pk>/supprimer/',                 views.ged_delete,   name='ged_delete'),

    # Composition site
    path('<int:patrimoine_pk>/site/gerer/',         views.site_ajouter_batiment, name='site_gerer'),

    # API
    path('api/<int:pk>/arborescence/',             views.api_patrimoine_arborescence, name='api_arborescence'),
    path('api/patrimoines-sans-site/',             views.api_tous_patrimoines,        name='api_sans_site'),
]
