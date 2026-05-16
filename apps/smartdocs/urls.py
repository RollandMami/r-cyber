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

    # Documents
    path('<int:patrimoine_pk>/documents/ajouter/', views.document_upload,   name='document_upload'),
    path('documents/<int:pk>/telecharger/',        views.document_download, name='document_download'),
    path('documents/<int:pk>/supprimer/',          views.document_delete,   name='document_delete'),

    # API
    path('api/<int:pk>/arborescence/', views.api_patrimoine_arborescence, name='api_arborescence'),
]
