"""
MOREX Devis BTP — forms.py
"""

from django import forms
from .models import (
    Materiau, Dosage, Devis, LigneAvantMetre, RecapAvantMetre,
    EquipePHMO, TacheForfaitMO, FraisChantier,
)


class MateriauForm(forms.ModelForm):
    class Meta:
        model  = Materiau
        fields = [
            'code', 'designation', 'unite',
            'prix_fournisseur', 'frais_manutention', 'frais_transport',
            'taux_chute', 'note', 'actif',
        ]
        widgets = {
            'note': forms.Textarea(attrs={'rows': 2}),
        }


class DosageForm(forms.ModelForm):
    class Meta:
        model  = Dosage
        fields = [
            'code', 'categorie', 'dosage_kg', 'choix_liant', 'description',
            'sable_m3', 'gravillon_m3', 'eau_litres',
            'ciment_kg', 'chaux_kg', 'acier_kg', 'fil_recuit_kg', 'actif',
        ]


class DevisForm(forms.ModelForm):
    class Meta:
        model  = Devis
        fields = [
            'titre', 'client_nom', 'client_adresse', 'client_tel', 'client_email',
            'maitre_ouvrage', 'source', 'adresse_chantier', 'duree_chantier_mois',
            'mode_mo', 'date_devis', 'date_validite',
            'taux_aleas', 'taux_benefice', 'taux_tva',
            'emetteur_nom', 'emetteur_adresse', 'emetteur_tel',
            'emetteur_email', 'emetteur_nif',
            'conditions', 'notes',
            'mission_id_ref', 'projet_id_ref',
        ]
        widgets = {
            'date_devis':      forms.DateInput(attrs={'type': 'date'}),
            'date_validite':   forms.DateInput(attrs={'type': 'date'}),
            'client_adresse':  forms.Textarea(attrs={'rows': 2}),
            'adresse_chantier': forms.Textarea(attrs={'rows': 2}),
            'emetteur_adresse': forms.Textarea(attrs={'rows': 2}),
            'conditions':      forms.Textarea(attrs={'rows': 3}),
            'notes':           forms.Textarea(attrs={'rows': 3}),
            'mission_id_ref':  forms.HiddenInput(),
            'projet_id_ref':   forms.HiddenInput(),
        }


class LigneAvantMetreForm(forms.ModelForm):
    class Meta:
        model  = LigneAvantMetre
        fields = [
            'ouvrage_num', 'designation', 'repere', 'unite', 'signe',
            'nps', 'longueur', 'largeur', 'hauteur', 'note',
        ]
        widgets = {
            'note': forms.Textarea(attrs={'rows': 1}),
        }


class RecapAvantMetreForm(forms.ModelForm):
    class Meta:
        model  = RecapAvantMetre
        fields = ['numero', 'designation', 'unite', 'qam', 'dosage', 'ordre']


class EquipePHMOForm(forms.ModelForm):
    class Meta:
        model  = EquipePHMO
        fields = [
            'designation', 'categorie',
            'salaire_base', 'taux_charges', 'nb_jours_mois',
            'heures_par_jour', 'heures_total', 'ordre',
        ]


class TacheForfaitMOForm(forms.ModelForm):
    class Meta:
        model  = TacheForfaitMO
        fields = ['numero', 'designation', 'unite', 'quantite', 'pu_mo', 'ordre']


class FraisChantierForm(forms.ModelForm):
    class Meta:
        model  = FraisChantier
        fields = ['categorie', 'designation', 'unite', 'quantite', 'prix_unitaire', 'note', 'ordre']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 1}),
        }
