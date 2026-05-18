from django import forms
from django.contrib.auth.models import User

INPUT = 'form-control'
SEL   = 'form-select'

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Nom d\'utilisateur', 'autofocus': True}),
        label='Identifiant'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT, 'placeholder': '••••••••'}),
        label='Mot de passe'
    )


class RegisterForm(forms.ModelForm):
    password  = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT, 'placeholder': 'Choisissez un mot de passe'}),
        label='Mot de passe'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT, 'placeholder': 'Confirmez le mot de passe'}),
        label='Confirmer'
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username':   forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Nom d\'utilisateur'}),
            'first_name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Prénom'}),
            'last_name':  forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Nom'}),
            'email':      forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'Email'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Le mot de passe doit contenir au moins 8 caractères.')
        return p2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Ce nom d\'utilisateur est déjà pris.')
        return username


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT}),
            'last_name':  forms.TextInput(attrs={'class': INPUT}),
            'email':      forms.EmailInput(attrs={'class': INPUT}),
        }
