from django import forms
from .models import (
    Mission, DocumentEntree, PlanLivrable,
    Devis, LigneDevis, NoteCalcul, Reunion,
)

W   = {'class': 'form-control'}
WS  = {'class': 'form-select'}
WTA = {'class': 'form-control', 'rows': 3}
WD  = {'class': 'form-control', 'type': 'date'}
WN  = {'class': 'form-control', 'type': 'number', 'step': 'any'}


class MissionForm(forms.ModelForm):
    class Meta:
        model  = Mission
        fields = [
            'titre', 'type_mission', 'statut', 'responsable',
            'client_nom', 'client_tel', 'client_email', 'client_adresse',
            'adresse_site', 'description', 'objectifs',
            'date_commande', 'date_rendu',
            'honoraires_ht', 'tva_pct',
        ]
        widgets = {
            'titre':          forms.TextInput(attrs={**W, 'placeholder': 'Intitulé de la mission'}),
            'type_mission':   forms.Select(attrs=WS),
            'statut':         forms.Select(attrs=WS),
            'responsable':    forms.Select(attrs=WS),
            'client_nom':     forms.TextInput(attrs=W),
            'client_tel':     forms.TextInput(attrs=W),
            'client_email':   forms.EmailInput(attrs=W),
            'client_adresse': forms.Textarea(attrs={**WTA, 'rows': 2}),
            'adresse_site':   forms.Textarea(attrs={**WTA, 'rows': 2}),
            'description':    forms.Textarea(attrs=WTA),
            'objectifs':      forms.Textarea(attrs=WTA),
            'date_commande':  forms.DateInput(attrs=WD),
            'date_rendu':     forms.DateInput(attrs=WD),
            'honoraires_ht':  forms.NumberInput(attrs=WN),
            'tva_pct':        forms.NumberInput(attrs=WN),
        }


class DocumentEntreeForm(forms.ModelForm):
    class Meta:
        model  = DocumentEntree
        fields = ['type_doc', 'titre', 'fichier', 'description', 'date_reception']
        widgets = {
            'type_doc':       forms.Select(attrs=WS),
            'titre':          forms.TextInput(attrs=W),
            'description':    forms.Textarea(attrs=WTA),
            'date_reception': forms.DateInput(attrs=WD),
        }


class PlanLivrableForm(forms.ModelForm):
    class Meta:
        model  = PlanLivrable
        fields = ['type_doc', 'phase', 'titre', 'fichier', 'description', 'version', 'indice', 'date_doc', 'valide']
        widgets = {
            'type_doc':    forms.Select(attrs=WS),
            'phase':       forms.Select(attrs=WS),
            'titre':       forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs=WTA),
            'version':     forms.TextInput(attrs={**W, 'placeholder': 'v1.0'}),
            'indice':      forms.TextInput(attrs={**W, 'placeholder': 'A'}),
            'date_doc':    forms.DateInput(attrs=WD),
            'valide':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DevisForm(forms.ModelForm):
    class Meta:
        model  = Devis
        fields = [
            'statut', 'objet',
            'emetteur_nom', 'emetteur_adresse', 'emetteur_tel',
            'emetteur_email', 'emetteur_nif',
            'client_nom', 'client_adresse',
            'date_devis', 'date_validite',
            'tva_pct', 'conditions', 'note',
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
            'unite':         forms.TextInput(attrs=W),
            'quantite':      forms.NumberInput(attrs=WN),
            'prix_unitaire': forms.NumberInput(attrs=WN),
        }


class NoteCalculForm(forms.ModelForm):
    class Meta:
        model  = NoteCalcul
        fields = [
            'domaine', 'titre', 'version',
            'hypotheses', 'methodologie', 'resultats', 'conclusion',
            'norme_ref', 'logiciel', 'valide', 'date_validation', 'fichier',
        ]
        widgets = {
            'domaine':       forms.Select(attrs=WS),
            'titre':         forms.TextInput(attrs=W),
            'version':       forms.TextInput(attrs=W),
            'hypotheses':    forms.Textarea(attrs=WTA),
            'methodologie':  forms.Textarea(attrs=WTA),
            'resultats':     forms.Textarea(attrs=WTA),
            'conclusion':    forms.Textarea(attrs=WTA),
            'norme_ref':     forms.TextInput(attrs={**W, 'placeholder': 'ex. Eurocode 2, BAEL 91…'}),
            'logiciel':      forms.TextInput(attrs={**W, 'placeholder': 'ex. Robot, RDM6, Excel…'}),
            'valide':        forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_validation':forms.DateInput(attrs=WD),
        }


class ReunionForm(forms.ModelForm):
    class Meta:
        model  = Reunion
        fields = [
            'type_reunion', 'titre', 'date_reunion', 'lieu',
            'participants', 'ordre_du_jour', 'compte_rendu', 'actions', 'fichier',
        ]
        widgets = {
            'type_reunion':  forms.Select(attrs=WS),
            'titre':         forms.TextInput(attrs=W),
            'date_reunion':  forms.DateInput(attrs=WD),
            'lieu':          forms.TextInput(attrs=W),
            'participants':  forms.Textarea(attrs={**WTA, 'rows': 3}),
            'ordre_du_jour': forms.Textarea(attrs=WTA),
            'compte_rendu':  forms.Textarea(attrs={**WTA, 'rows': 5}),
            'actions':       forms.Textarea(attrs=WTA),
        }
