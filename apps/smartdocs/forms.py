from django import forms
from .models import Patrimoine, Document, Etage, Site


class SiteForm(forms.ModelForm):
    class Meta:
        model  = Site
        fields = ['nom', 'adresse', 'description', 'photo']
        widgets = {
            'nom':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du site'}),
            'adresse':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse du site'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo':       forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class PatrimoineForm(forms.ModelForm):
    class Meta:
        model  = Patrimoine
        fields = ['nom', 'adresse', 'description', 'annee_construction',
                  'surface_totale', 'photo', 'fichier_ifc']
        widgets = {
            'nom':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du bâtiment'}),
            'adresse':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse complète'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'annee_construction': forms.NumberInput(attrs={'class': 'form-control'}),
            'surface_totale':     forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'placeholder': 'Calculé automatiquement depuis IFC si vide',
            }),
            'photo':       forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'fichier_ifc': forms.FileInput(attrs={'class': 'form-control', 'accept': '.ifc'}),
        }

    def clean_fichier_ifc(self):
        fichier = self.cleaned_data.get('fichier_ifc')
        if fichier:
            if not fichier.name.lower().endswith('.ifc'):
                raise forms.ValidationError('Le fichier doit être au format .ifc')
            if fichier.size > 500 * 1024 * 1024:
                raise forms.ValidationError('Le fichier IFC ne doit pas dépasser 500 MB.')
        return fichier


class DocumentForm(forms.ModelForm):
    class Meta:
        model  = Document
        fields = ['titre', 'type_doc', 'etage', 'fichier', 'description', 'version', 'date_doc']
        widgets = {
            'titre':       forms.TextInput(attrs={'class': 'form-control'}),
            'type_doc':    forms.Select(attrs={'class': 'form-select'}),
            'etage':       forms.Select(attrs={'class': 'form-select'}),
            'fichier':     forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'version':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'v1.0'}),
            'date_doc':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, patrimoine=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patrimoine:
            self.fields['etage'].queryset = Etage.objects.filter(patrimoine=patrimoine)
            self.fields['etage'].empty_label = '— Bâtiment entier —'
        self.fields['etage'].required = False
