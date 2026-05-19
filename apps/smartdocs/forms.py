from django import forms
from .models import Patrimoine, Document, Etage, DocumentGED, GED_ARBORESCENCE


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
                'placeholder': 'Calculé automatiquement depuis IFC si vide'
            }),
            'photo':       forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'fichier_ifc': forms.FileInput(attrs={'class': 'form-control', 'accept': '.ifc'}),
        }
        help_texts = {
            'surface_totale': ('Laissez vide si vous uploadez un fichier IFC — '
                               'la surface sera calculée automatiquement à partir '
                               'des surfaces exactes de chaque espace (IfcSpace).'),
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
            'version':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex. v1.0'}),
            'date_doc':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, patrimoine=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patrimoine:
            self.fields['etage'].queryset = Etage.objects.filter(patrimoine=patrimoine)
            self.fields['etage'].empty_label = "— Bâtiment entier —"
        self.fields['etage'].required = False


# Choix pour le formulaire GED
def _get_dossier_choices():
    choices = []
    for corps_key, corps_data in GED_ARBORESCENCE.items():
        group_choices = [
            (f'{corps_key}__{k}', v)
            for k, v in corps_data['sous_dossiers'].items()
        ]
        choices.append((corps_data['label'], group_choices))
    return choices


class DocumentGEDForm(forms.ModelForm):
    class Meta:
        model  = DocumentGED
        fields = ['titre', 'fichier', 'description', 'version', 'date_doc']
        widgets = {
            'titre':       forms.TextInput(attrs={'class': 'form-control'}),
            'fichier':     forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'version':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex. v1.0'}),
            'date_doc':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
