from django.db import models
from django.contrib.auth.models import User
import os


def patrimoine_ifc_path(instance, filename):
    return f'patrimoines/{instance.pk}/3d/{filename}'


def document_upload_path(instance, filename):
    if instance.etage:
        return f'patrimoines/{instance.patrimoine.pk}/etages/{instance.etage.pk}/docs/{filename}'
    return f'patrimoines/{instance.patrimoine.pk}/docs/{filename}'


class Patrimoine(models.Model):
    """Bâtiment / actif immobilier principal."""

    nom          = models.CharField(max_length=200)
    adresse      = models.CharField(max_length=300, blank=True)
    description  = models.TextField(blank=True)
    annee_construction = models.PositiveIntegerField(null=True, blank=True)
    surface_totale     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='m²')

    # Fichier IFC source
    fichier_ifc  = models.FileField(upload_to='patrimoines/ifc/', null=True, blank=True)
    # JSON généré automatiquement à partir de l'IFC
    fichier_json = models.FileField(upload_to='patrimoines/json/', null=True, blank=True)
    # Statut de la conversion IFC → JSON
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours',   'Conversion en cours'),
        ('ok',         'Converti'),
        ('erreur',     'Erreur de conversion'),
    ]
    statut_conversion = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    erreur_conversion = models.TextField(blank=True)

    # Photo de couverture
    photo        = models.ImageField(upload_to='patrimoines/photos/', null=True, blank=True)

    cree_par     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='patrimoines')
    cree_le      = models.DateTimeField(auto_now_add=True)
    modifie_le   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Patrimoine'
        verbose_name_plural = 'Patrimoines'
        ordering            = ['-cree_le']

    def __str__(self):
        return self.nom

    def ifc_filename(self):
        return os.path.basename(self.fichier_ifc.name) if self.fichier_ifc else None

    def has_viewer(self):
        return bool(self.fichier_json)


class Etage(models.Model):
    """Étage d'un bâtiment — extrait de l'IFC ou créé manuellement."""

    patrimoine  = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='etages')
    nom         = models.CharField(max_length=100)           # ex. "Rez-de-chaussée", "Étage 1"
    niveau      = models.IntegerField(default=0)             # 0 = RDC, 1 = Étage 1, -1 = Sous-sol
    ifc_guid    = models.CharField(max_length=100, blank=True)  # GUID IFC pour lier à la géométrie

    class Meta:
        verbose_name = 'Étage'
        verbose_name_plural = 'Étages'
        ordering = ['niveau']

    def __str__(self):
        return f'{self.patrimoine.nom} — {self.nom}'


class Piece(models.Model):
    """Pièce / espace au sein d'un étage."""

    etage    = models.ForeignKey(Etage, on_delete=models.CASCADE, related_name='pieces')
    nom      = models.CharField(max_length=150)
    surface  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='m²')
    ifc_guid = models.CharField(max_length=100, blank=True)
    usage    = models.CharField(max_length=100, blank=True)  # Bureau, Couloir, WC…

    class Meta:
        verbose_name = 'Pièce'
        verbose_name_plural = 'Pièces'
        ordering = ['nom']

    def __str__(self):
        return f'{self.etage} — {self.nom}'

    @property
    def patrimoine(self):
        return self.etage.patrimoine


class TypeDocument(models.Model):
    """Catalogue des types de documents (Plan, Photo, Notice, Devis, PV…)."""

    nom   = models.CharField(max_length=100, unique=True)
    icone = models.CharField(max_length=50, default='fa-file', help_text='Classe FontAwesome')
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Type de document'
        verbose_name_plural = 'Types de documents'
        ordering            = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class Document(models.Model):
    """Document lié à un patrimoine et optionnellement à un étage."""

    patrimoine = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='documents')
    etage      = models.ForeignKey(Etage, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents',
                                   help_text='Laisser vide pour un document lié au bâtiment entier')
    type_doc   = models.ForeignKey(TypeDocument, on_delete=models.PROTECT, related_name='documents')

    titre      = models.CharField(max_length=255)
    fichier    = models.FileField(upload_to=document_upload_path)
    description = models.TextField(blank=True)
    version    = models.CharField(max_length=20, blank=True, help_text='ex. v2.1')
    date_doc   = models.DateField(null=True, blank=True, help_text='Date du document')

    uploade_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploade_le  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Document'
        verbose_name_plural = 'Documents'
        ordering            = ['-uploade_le']

    def __str__(self):
        return self.titre

    def extension(self):
        name, ext = os.path.splitext(self.fichier.name)
        return ext.lower()

    def is_pdf(self):
        return self.extension() == '.pdf'

    def is_image(self):
        return self.extension() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']

    def taille_fichier(self):
        try:
            return self.fichier.size
        except Exception:
            return 0
