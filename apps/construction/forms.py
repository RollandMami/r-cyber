from django import forms
from .models import (
    Projet, PhotoProjet, DocumentClient, DocumentChantier,
    TacheGantt, LigneBudget, BonCommande, LigneBonCommande,
    RapportActivite, Facture, LigneFacture,
)


W = {'class': 'form-control'}
WS = {'class': 'form-select'}
WTA = {'class': 'form-control', 'rows': 3}
WD = {'class': 'form-control', 'type': 'date'}
WN = {'class': 'form-control', 'type': 'number', 'step': 'any'}
WC = {'class': 'form-control', 'type': 'color'}


class ProjetForm(forms.ModelForm):
    class Meta:
        model = Projet
        fields = [
            'titre', 'type_projet', 'statut', 'responsable',
            'client_nom', 'client_contact', 'client_email', 'client_tel', 'client_adresse',
            'adresse_chantier',
            'description_courte', 'cahier_des_charges', 'visible_vitrine',
            'date_debut', 'date_fin_prevue',
            'budget_estime', 'budget_contractuel',
        ]
        widgets = {
            'titre':              forms.TextInput(attrs={**W, 'placeholder': 'Nom du projet'}),
            'type_projet':        forms.Select(attrs=WS),
            'statut':             forms.Select(attrs=WS),
            'responsable':        forms.Select(attrs=WS),
            'client_nom':         forms.TextInput(attrs=W),
            'client_contact':     forms.TextInput(attrs=W),
            'client_email':       forms.EmailInput(attrs=W),
            'client_tel':         forms.TextInput(attrs=W),
            'client_adresse':     forms.Textarea(attrs={**WTA, 'rows': 2}),
            'adresse_chantier':   forms.Textarea(attrs={**WTA, 'rows': 2}),
            'description_courte': forms.TextInput(attrs=W),
            'cahier_des_charges': forms.Textarea(attrs=WTA),
            'visible_vitrine':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_debut':         forms.DateInput(attrs=WD),
            'date_fin_prevue':    forms.DateInput(attrs=WD),
            'budget_estime':      forms.NumberInput(attrs=WN),
            'budget_contractuel': forms.NumberInput(attrs=WN),
        }


class PhotoProjetForm(forms.ModelForm):
    class Meta:
        model = PhotoProjet
        fields = ['image', 'legende', 'principale', 'ordre']
        widgets = {
            'legende':    forms.TextInput(attrs=W),
            'principale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordre':      forms.NumberInput(attrs={**WN, 'min': 0}),
        }


class DocumentClientForm(forms.ModelForm):
    class Meta:
        model = DocumentClient
        fields = ['type_doc', 'titre', 'fichier', 'description', 'version', 'date_reception']
        widgets = {
            'type_doc':       forms.Select(attrs=WS),
            'titre':          forms.TextInput(attrs=W),
            'description':    forms.Textarea(attrs=WTA),
            'version':        forms.TextInput(attrs={**W, 'placeholder': 'v1.0'}),
            'date_reception': forms.DateInput(attrs=WD),
        }


class DocumentChantierForm(forms.ModelForm):
    class Meta:
        model = DocumentChantier
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


class TacheGanttForm(forms.ModelForm):
    class Meta:
        model = TacheGantt
        fields = ['titre', 'description', 'parent', 'statut', 'priorite',
                  'avancement', 'date_debut', 'date_fin', 'assignee_a', 'couleur', 'ordre']
        widgets = {
            'titre':       forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs={**WTA, 'rows': 2}),
            'parent':      forms.Select(attrs=WS),
            'statut':      forms.Select(attrs=WS),
            'priorite':    forms.Select(attrs=WS),
            'avancement':  forms.NumberInput(attrs={**WN, 'min': 0, 'max': 100}),
            'date_debut':  forms.DateInput(attrs=WD),
            'date_fin':    forms.DateInput(attrs=WD),
            'assignee_a':  forms.Select(attrs=WS),
            'couleur':     forms.TextInput(attrs=WC),
            'ordre':       forms.NumberInput(attrs=WN),
        }

    def __init__(self, projet=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            self.fields['parent'].queryset = TacheGantt.objects.filter(projet=projet, parent=None)
            self.fields['parent'].required = False


class LigneBudgetForm(forms.ModelForm):
    class Meta:
        model = LigneBudget
        fields = ['categorie', 'tache', 'designation', 'unite', 'quantite', 'prix_unitaire', 'montant_reel', 'note']
        widgets = {
            'categorie':    forms.Select(attrs=WS),
            'tache':        forms.Select(attrs=WS),
            'designation':  forms.TextInput(attrs=W),
            'unite':        forms.TextInput(attrs={**W, 'placeholder': 'm², ml…'}),
            'quantite':     forms.NumberInput(attrs=WN),
            'prix_unitaire':forms.NumberInput(attrs=WN),
            'montant_reel': forms.NumberInput(attrs=WN),
            'note':         forms.Textarea(attrs={**WTA, 'rows': 2}),
        }

    def __init__(self, projet=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            self.fields['tache'].queryset = TacheGantt.objects.filter(projet=projet)
            self.fields['tache'].required = False


class BonCommandeForm(forms.ModelForm):
    class Meta:
        model = BonCommande
        fields = ['statut', 'fournisseur_nom', 'fournisseur_contact', 'fournisseur_tel',
                  'date_commande', 'date_livraison', 'lieu_livraison', 'tva_pct', 'note']
        widgets = {
            'statut':               forms.Select(attrs=WS),
            'fournisseur_nom':      forms.TextInput(attrs=W),
            'fournisseur_contact':  forms.TextInput(attrs=W),
            'fournisseur_tel':      forms.TextInput(attrs=W),
            'date_commande':        forms.DateInput(attrs=WD),
            'date_livraison':       forms.DateInput(attrs=WD),
            'lieu_livraison':       forms.TextInput(attrs=W),
            'tva_pct':              forms.NumberInput(attrs=WN),
            'note':                 forms.Textarea(attrs=WTA),
        }


class LigneBonCommandeForm(forms.ModelForm):
    class Meta:
        model = LigneBonCommande
        fields = ['designation', 'unite', 'quantite', 'prix_unitaire']
        widgets = {
            'designation':  forms.TextInput(attrs=W),
            'unite':        forms.TextInput(attrs=W),
            'quantite':     forms.NumberInput(attrs=WN),
            'prix_unitaire':forms.NumberInput(attrs=WN),
        }


class RapportActiviteForm(forms.ModelForm):
    class Meta:
        model = RapportActivite
        fields = ['type_rapport', 'titre', 'periode_debut', 'periode_fin',
                  'taches_concernees', 'travaux_realises', 'observations', 'travaux_prevus',
                  'avancement_constate', 'nb_ouvriers', 'nb_journees',
                  'montant_a_facturer', 'fichier']
        widgets = {
            'type_rapport':       forms.Select(attrs=WS),
            'titre':              forms.TextInput(attrs=W),
            'periode_debut':      forms.DateInput(attrs=WD),
            'periode_fin':        forms.DateInput(attrs=WD),
            'taches_concernees':  forms.CheckboxSelectMultiple(),
            'travaux_realises':   forms.Textarea(attrs=WTA),
            'observations':       forms.Textarea(attrs=WTA),
            'travaux_prevus':     forms.Textarea(attrs=WTA),
            'avancement_constate':forms.NumberInput(attrs={**WN, 'min': 0, 'max': 100}),
            'nb_ouvriers':        forms.NumberInput(attrs=WN),
            'nb_journees':        forms.NumberInput(attrs=WN),
            'montant_a_facturer': forms.NumberInput(attrs=WN),
        }

    def __init__(self, projet=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            self.fields['taches_concernees'].queryset = TacheGantt.objects.filter(projet=projet)


class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = [
            'type_facture', 'statut', 'objet',
            'emetteur_nom', 'emetteur_adresse', 'emetteur_tel', 'emetteur_email', 'emetteur_nif',
            'client_nom', 'client_adresse',
            'date_emission', 'date_echeance',
            'tva_pct', 'pct_avancement', 'montant_precedent',
            'conditions_paiement', 'note',
        ]
        widgets = {
            'type_facture':       forms.Select(attrs=WS),
            'statut':             forms.Select(attrs=WS),
            'objet':              forms.TextInput(attrs=W),
            'emetteur_nom':       forms.TextInput(attrs=W),
            'emetteur_adresse':   forms.Textarea(attrs={**WTA, 'rows': 2}),
            'emetteur_tel':       forms.TextInput(attrs=W),
            'emetteur_email':     forms.EmailInput(attrs=W),
            'emetteur_nif':       forms.TextInput(attrs=W),
            'client_nom':         forms.TextInput(attrs=W),
            'client_adresse':     forms.Textarea(attrs={**WTA, 'rows': 2}),
            'date_emission':      forms.DateInput(attrs=WD),
            'date_echeance':      forms.DateInput(attrs=WD),
            'tva_pct':            forms.NumberInput(attrs=WN),
            'pct_avancement':     forms.NumberInput(attrs={**WN, 'min': 0, 'max': 100}),
            'montant_precedent':  forms.NumberInput(attrs=WN),
            'conditions_paiement':forms.Textarea(attrs={**WTA, 'rows': 2}),
            'note':               forms.Textarea(attrs={**WTA, 'rows': 2}),
        }


class LigneFactureForm(forms.ModelForm):
    class Meta:
        model = LigneFacture
        fields = ['designation', 'unite', 'quantite', 'prix_unitaire', 'tache']
        widgets = {
            'designation':  forms.TextInput(attrs=W),
            'unite':        forms.TextInput(attrs=W),
            'quantite':     forms.NumberInput(attrs=WN),
            'prix_unitaire':forms.NumberInput(attrs=WN),
            'tache':        forms.Select(attrs=WS),
        }

    def __init__(self, projet=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            self.fields['tache'].queryset = TacheGantt.objects.filter(projet=projet)
            self.fields['tache'].required = False
