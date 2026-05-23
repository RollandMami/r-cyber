from django import forms
from .models import (
    Client, Projet, Tache, Bug, Livrable,
    Documentation, Devis, LigneDevis, Facture, LigneFacture,
)

W   = {'class': 'form-control'}
WS  = {'class': 'form-select'}
WTA = {'class': 'form-control', 'rows': 3}
WD  = {'class': 'form-control', 'type': 'date'}
WN  = {'class': 'form-control', 'type': 'number', 'step': 'any'}
WU  = {'class': 'form-control', 'type': 'url'}


class ClientForm(forms.ModelForm):
    class Meta:
        model  = Client
        fields = ['nom', 'email', 'telephone', 'adresse', 'entreprise', 'client_ref', 'note']
        widgets = {
            'nom':        forms.TextInput(attrs=W),
            'email':      forms.EmailInput(attrs=W),
            'telephone':  forms.TextInput(attrs=W),
            'adresse':    forms.Textarea(attrs={**WTA, 'rows': 2}),
            'entreprise': forms.TextInput(attrs=W),
            'client_ref': forms.TextInput(attrs={**W, 'placeholder': 'ex. BTP/PROJ-2026-001'}),
            'note':       forms.Textarea(attrs=WTA),
        }


class ProjetForm(forms.ModelForm):
    class Meta:
        model  = Projet
        fields = [
            'titre', 'type_projet', 'statut', 'priorite',
            'client', 'description', 'cahier_charges', 'stack_technique',
            'repo_url', 'url_prod', 'url_recette',
            'date_debut', 'date_fin_prevue',
            'budget_ht', 'tva_pct', 'responsable',
        ]
        widgets = {
            'titre':          forms.TextInput(attrs={**W, 'placeholder': 'Nom du projet'}),
            'type_projet':    forms.Select(attrs=WS),
            'statut':         forms.Select(attrs=WS),
            'priorite':       forms.Select(attrs=WS),
            'client':         forms.Select(attrs=WS),
            'description':    forms.Textarea(attrs=WTA),
            'cahier_charges': forms.Textarea(attrs=WTA),
            'stack_technique':forms.TextInput(attrs={**W, 'placeholder': 'Python, Django, React…'}),
            'repo_url':       forms.URLInput(attrs=WU),
            'url_prod':       forms.URLInput(attrs=WU),
            'url_recette':    forms.URLInput(attrs=WU),
            'date_debut':     forms.DateInput(attrs=WD),
            'date_fin_prevue':forms.DateInput(attrs=WD),
            'budget_ht':      forms.NumberInput(attrs=WN),
            'tva_pct':        forms.NumberInput(attrs=WN),
            'responsable':    forms.Select(attrs=WS),
        }


class TacheForm(forms.ModelForm):
    class Meta:
        model  = Tache
        fields = ['titre', 'description', 'statut', 'priorite', 'assignee', 'date_debut', 'date_fin', 'ordre']
        widgets = {
            'titre':       forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs={**WTA, 'rows': 2}),
            'statut':      forms.Select(attrs=WS),
            'priorite':    forms.Select(attrs=WS),
            'assignee':    forms.Select(attrs=WS),
            'date_debut':  forms.DateInput(attrs=WD),
            'date_fin':    forms.DateInput(attrs=WD),
            'ordre':       forms.NumberInput(attrs=WN),
        }


class BugForm(forms.ModelForm):
    class Meta:
        model  = Bug
        fields = [
            'titre', 'type_bug', 'statut', 'severite',
            'description', 'etapes_repro', 'environnement',
            'solution', 'rapporte_par', 'assigne_a', 'date_ouvert', 'date_resolu',
        ]
        widgets = {
            'titre':        forms.TextInput(attrs=W),
            'type_bug':     forms.Select(attrs=WS),
            'statut':       forms.Select(attrs=WS),
            'severite':     forms.Select(attrs=WS),
            'description':  forms.Textarea(attrs=WTA),
            'etapes_repro': forms.Textarea(attrs=WTA),
            'environnement':forms.TextInput(attrs={**W, 'placeholder': 'Windows 11, Chrome 120…'}),
            'solution':     forms.Textarea(attrs=WTA),
            'rapporte_par': forms.TextInput(attrs=W),
            'assigne_a':    forms.Select(attrs=WS),
            'date_ouvert':  forms.DateInput(attrs=WD),
            'date_resolu':  forms.DateInput(attrs=WD),
        }


class LivrableForm(forms.ModelForm):
    class Meta:
        model  = Livrable
        fields = ['type_livrable', 'titre', 'version', 'fichier', 'url_externe',
                  'description', 'changelog', 'livre_au_client', 'date_livraison']
        widgets = {
            'type_livrable':   forms.Select(attrs=WS),
            'titre':           forms.TextInput(attrs=W),
            'version':         forms.TextInput(attrs={**W, 'placeholder': 'v1.0.0'}),
            'url_externe':     forms.URLInput(attrs=WU),
            'description':     forms.Textarea(attrs=WTA),
            'changelog':       forms.Textarea(attrs=WTA),
            'livre_au_client': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_livraison':  forms.DateInput(attrs=WD),
        }


class DocumentationForm(forms.ModelForm):
    class Meta:
        model  = Documentation
        fields = ['categorie', 'titre', 'contenu', 'version', 'fichier', 'publie']
        widgets = {
            'categorie': forms.Select(attrs=WS),
            'titre':     forms.TextInput(attrs=W),
            'contenu':   forms.Textarea(attrs={**WTA, 'rows': 12}),
            'version':   forms.TextInput(attrs={**W, 'placeholder': 'v1.0'}),
            'publie':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DevisForm(forms.ModelForm):
    class Meta:
        model  = Devis
        fields = [
            'statut', 'objet',
            'emetteur_nom', 'emetteur_adresse', 'emetteur_tel',
            'emetteur_email', 'emetteur_nif',
            'client_nom', 'client_adresse',
            'date_devis', 'date_validite', 'tva_pct',
            'conditions', 'note',
        ]
        widgets = {
            'statut':           forms.Select(attrs=WS),
            'objet':            forms.TextInput(attrs=W),
            'emetteur_nom':     forms.TextInput(attrs=W),
            'emetteur_adresse': forms.Textarea(attrs={**WTA, 'rows': 2}),
            'emetteur_tel':     forms.TextInput(attrs=W),
            'emetteur_email':   forms.EmailInput(attrs=W),
            'emetteur_nif':     forms.TextInput(attrs=W),
            'client_nom':       forms.TextInput(attrs=W),
            'client_adresse':   forms.Textarea(attrs={**WTA, 'rows': 2}),
            'date_devis':       forms.DateInput(attrs=WD),
            'date_validite':    forms.DateInput(attrs=WD),
            'tva_pct':          forms.NumberInput(attrs=WN),
            'conditions':       forms.Textarea(attrs=WTA),
            'note':             forms.Textarea(attrs=WTA),
        }


class LigneDevisForm(forms.ModelForm):
    class Meta:
        model  = LigneDevis
        fields = ['designation', 'unite', 'quantite', 'prix_unitaire']
        widgets = {
            'designation':   forms.TextInput(attrs=W),
            'unite':         forms.TextInput(attrs={**W, 'placeholder': 'forfait, h, j…'}),
            'quantite':      forms.NumberInput(attrs=WN),
            'prix_unitaire': forms.NumberInput(attrs=WN),
        }


class FactureForm(forms.ModelForm):
    class Meta:
        model  = Facture
        fields = [
            'type_facture', 'statut', 'objet', 'jalon',
            'emetteur_nom', 'emetteur_adresse', 'emetteur_tel',
            'emetteur_email', 'emetteur_nif',
            'client_nom', 'client_adresse',
            'date_emission', 'date_echeance', 'tva_pct',
            'conditions', 'note',
        ]
        widgets = {
            'type_facture':     forms.Select(attrs=WS),
            'statut':           forms.Select(attrs=WS),
            'objet':            forms.TextInput(attrs=W),
            'jalon':            forms.TextInput(attrs={**W, 'placeholder': 'Livraison phase 1…'}),
            'emetteur_nom':     forms.TextInput(attrs=W),
            'emetteur_adresse': forms.Textarea(attrs={**WTA, 'rows': 2}),
            'emetteur_tel':     forms.TextInput(attrs=W),
            'emetteur_email':   forms.EmailInput(attrs=W),
            'emetteur_nif':     forms.TextInput(attrs=W),
            'client_nom':       forms.TextInput(attrs=W),
            'client_adresse':   forms.Textarea(attrs={**WTA, 'rows': 2}),
            'date_emission':    forms.DateInput(attrs=WD),
            'date_echeance':    forms.DateInput(attrs=WD),
            'tva_pct':          forms.NumberInput(attrs=WN),
            'conditions':       forms.Textarea(attrs=WTA),
            'note':             forms.Textarea(attrs=WTA),
        }


class LigneFactureForm(forms.ModelForm):
    class Meta:
        model  = LigneFacture
        fields = ['designation', 'unite', 'quantite', 'prix_unitaire']
        widgets = {
            'designation':   forms.TextInput(attrs=W),
            'unite':         forms.TextInput(attrs={**W, 'placeholder': 'forfait, h, j…'}),
            'quantite':      forms.NumberInput(attrs=WN),
            'prix_unitaire': forms.NumberInput(attrs=WN),
        }
