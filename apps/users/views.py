from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import LoginForm, RegisterForm, ProfileForm
from django.contrib.auth import get_user_model
from django.db.models import Q


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user     = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get('next', 'home:index')
                messages.success(request, f'Bienvenue, {user.first_name or user.username} !')
                return redirect(next_url)
            else:
                messages.error(request, 'Identifiant ou mot de passe incorrect.')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home:index')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            messages.success(request, f'Compte créé ! Bienvenue, {user.first_name or user.username} !')
            return redirect('home:index')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour.')
            return redirect('users:profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'users/profile.html', {'form': form})

User = get_user_model()

@login_required
@user_passes_test(lambda u: u.is_staff)  # Sécurité : réservé au staff / admin
def user_list(request):
    """
    Affiche la liste de tous les utilisateurs inscrits sur la plateforme
    avec une option de recherche.
    """
    q = request.GET.get('q', '').strip()
    
    # On récupère tous les utilisateurs en triant par date d'inscription (les plus récents en premier)
    users = User.objects.all().order_by('-date_joined')
    
    # Si une recherche est effectuée, on filtre par nom, prénom ou email
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).distinct()
        
    return render(request, 'users/user_list.html', {
        'users': users,
        'q': q
    })