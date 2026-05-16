from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    path('<int:patrimoine_pk>/',              views.viewer,        name='viewer'),
    path('<int:patrimoine_pk>/geometrie/',    views.api_geometrie, name='api_geometrie'),
]
