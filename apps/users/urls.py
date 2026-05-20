from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('connexion/',    views.login_view,    name='login'),
    path('deconnexion/',  views.logout_view,   name='logout'),
    path('inscription/',  views.register_view, name='register'),
    path('profil/',       views.profile_view,  name='profile'),
	path('liste/', views.user_list, name='user_list'),
]
