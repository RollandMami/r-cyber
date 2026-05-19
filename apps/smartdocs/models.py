from django.db import models
from django.contrib.auth.models import User
import os


# ─── Helpers upload ───────────────────────────────────────────────────────────

def patrimoine_ifc_path(instance, filename):
    return f'patrimoines/{instance.pk}/3d/{filename}'


def document_upload_path(instance, filename):
    if instance.etage:
        return f'patrimoines/{instance.patrimoine.pk}/etages/{instance.etage.pk}/docs/{filename}'
    return f'patrimoines/{instance.patrimoine.pk}/docs/{filename}'


def ged_upload_path(instance, filename):
    return f'patrimoines/{instance.patrimoine.pk}/ged/{instance.corps}/{instance.dossier}/{filename}'


# ─── Arborescence GED CEA / CET ──────────────────────────────────────────────

GED_ARBORESCENCE = {
    'CEA': {
        'label': "Corps d'État Architectural",
        'icone': 'fa-drafting-compass',
        'sous_dossiers': {
            'plans_niveau':           'Plans de niveau',
            'plans_facade':           'Plans de façade',
            'plans_coupe':            'Plans de coupe',
            'plans_masse':            'Plan de masse',
            'plans_fondations':       'Plans de fondations',
            'plans_charpente':        'Plans de charpente / toiture',
            'plans_menuiseries':      'Plans menuiseries (portes / fenêtres)',
            'plans_carrelage':        'Plans carrelage / revêtements',
            'plans_faux_plafond':     'Plans faux-plafonds',
            'details_architecturaux': 'Détails architecturaux',
            'notes_calcul_archi':     'Notes de calcul architecturales',
            'permis_construire':      'Permis de construire',
            'rapports_expertise':     "Rapports d'expertise",
            'photos_chantier':        'Photos de chantier',
        }
    },
    'CET': {
        'label': "Corps d'État Technique",
        'icone': 'fa-tools',
        'sous_dossiers': {
            'plans_electricite':        "Plans d'électricité",
            'plans_eclairage':          "Plans d'éclairage",
            'plans_courants_faibles':   'Plans courants faibles (VDI / sécurité)',
            'plans_plomberie':          'Plans de plomberie',
            'plans_sanitaires':         'Plans sanitaires',
            'plans_cvca':               'Plans CVCA (Chauffage / Ventilation / Climatisation)',
            'plans_ventilation':        'Plans ventilation / désenfumage',
            'plans_sprinkler':          'Plans sprinkler / extinction incendie',
            'plans_gaz':                'Plans de gaz',
            'schemas_unifilaires':      'Schémas unifilaires électriques',
            'fiches_techniques':        'Fiches techniques équipements',
            'notices_installation':     "Notices d'installation",
            'pv_reception':             'PV de réception / levée de réserves',
            'contrats_maintenance':     'Contrats de maintenance',
            'rapports_controle':        'Rapports de contrôle (VERITAS / APAVE…)',
            'plans_reseaux_exterieurs': 'Plans réseaux extérieurs (VRD)',
        }
    }
}


# ─── Site ─────────────────────────────────────────────────────────────────────

class Site(models.Model):
    """Site / domaine regroupant plusieurs bâtiments."""
    nom         = models.CharField(max_length=200)
    adresse     = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    photo       = models.ImageField(upload_to='sites/photos/', null=True, blank=True)
    cree_par    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sites')
    cree_le     = models.DateTimeField(auto_now_add=True)
    modifie_le  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Site'
        verbose_name_plural = 'Sites'
        ordering            = ['-cree_le']

    def __str__(self):
        return self.nom


# ─── Patrimoine ───────────────────────────────────────────────────────────────

class Patrimoine(models.Model):
    """Bâtiment / actif immobilier principal."""

    site         = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='batiments')
    nom          = models.CharField(max_length=200)
    adresse      = models.CharField(max_length=300, blank=True)
    description  = models.TextField(blank=True)
    annee_construction = models.PositiveIntegerField(null=True, blank=True)
    surface_totale     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              help_text='m² — calculé automatiquement depuis IFC')

    fichier_ifc  = models.FileField(upload_to='patrimoines/ifc/', null=True, blank=True)
    fichier_json = models.FileField(upload_to='patrimoines/json/', null=True, blank=True)

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours',   'Conversion en cours'),
        ('ok',         'Converti'),
        ('erreur',     'Erreur de conversion'),
    ]
    statut_conversion = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    erreur_conversion = models.TextField(blank=True)

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

    def surface_ifc(self):
        """Somme exacte des surfaces IFC (IfcSpace)."""
        from django.db.models import Sum
        result = Piece.objects.filter(etage__patrimoine=self).aggregate(total=Sum('surface'))
        return result['total']

    def nombre_etages(self):
        return self.etages.count()

    def total_documents(self):
        return self.documents.count() + self.documents_ged.count()


# ─── Étage ────────────────────────────────────────────────────────────────────

class Etage(models.Model):
    patrimoine  = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='etages')
    nom         = models.CharField(max_length=100)
    niveau      = models.IntegerField(default=0)
    ifc_guid    = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Étage'
        verbose_name_plural = 'Étages'
        ordering = ['niveau']

    def __str__(self):
        return f'{self.patrimoine.nom} — {self.nom}'


# ─── Pièce ────────────────────────────────────────────────────────────────────

class Piece(models.Model):
    etage    = models.ForeignKey(Etage, on_delete=models.CASCADE, related_name='pieces')
    nom      = models.CharField(max_length=150)
    surface  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='m²')
    ifc_guid = models.CharField(max_length=100, blank=True)
    usage    = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Pièce'
        verbose_name_plural = 'Pièces'
        ordering = ['nom']

    def __str__(self):
        return f'{self.etage} — {self.nom}'

    @property
    def patrimoine(self):
        return self.etage.patrimoine


# ─── Éléments IFC enrichis ────────────────────────────────────────────────────

class RevetementMur(models.Model):
    """Revêtement de mur / surface extrait de l'IFC."""
    patrimoine  = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='revetements')
    etage       = models.ForeignKey(Etage, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='revetements')
    nom         = models.CharField(max_length=200)
    materiau    = models.CharField(max_length=200, blank=True)
    surface     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ifc_guid    = models.CharField(max_length=100, blank=True)
    type_ifc    = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Revêtement mur'
        ordering = ['etage__niveau', 'nom']


class EquipementOuverture(models.Model):
    TYPE_CHOICES = [
        ('ouverture',  'Ouverture (porte / fenêtre)'),
        ('sanitaire',  'Sanitaire'),
        ('equipement', 'Équipement'),
        ('mep',        'MEP / Technique'),
        ('mobilier',   'Mobilier'),
        ('autre',      'Autre'),
    ]
    patrimoine   = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='equipements')
    etage        = models.ForeignKey(Etage, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='equipements')
    nom          = models.CharField(max_length=200)
    type_element = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    type_ifc     = models.CharField(max_length=100, blank=True)
    quantite     = models.PositiveIntegerField(default=1)
    ifc_guid     = models.CharField(max_length=100, blank=True)
    description  = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Équipement / Ouverture'
        ordering = ['etage__niveau', 'type_element', 'nom']


# ─── Type de document ─────────────────────────────────────────────────────────

class TypeDocument(models.Model):
    nom   = models.CharField(max_length=100, unique=True)
    icone = models.CharField(max_length=50, default='fa-file')
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Type de document'
        verbose_name_plural = 'Types de documents'
        ordering            = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class Document(models.Model):
    """Document lié à un patrimoine (ancien système, conservé pour compatibilité)."""
    patrimoine = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='documents')
    etage      = models.ForeignKey(Etage, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='documents',
                                    help_text='Laisser vide pour un document global')
    type_doc   = models.ForeignKey(TypeDocument, on_delete=models.PROTECT, related_name='documents')

    titre      = models.CharField(max_length=255)
    fichier    = models.FileField(upload_to=document_upload_path)
    description = models.TextField(blank=True)
    version    = models.CharField(max_length=20, blank=True)
    date_doc   = models.DateField(null=True, blank=True)

    uploade_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploade_le  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Document'
        verbose_name_plural = 'Documents'
        ordering            = ['-uploade_le']

    def __str__(self):
        return self.titre

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
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


# ─── GED ─────────────────────────────────────────────────────────────────────

class DocumentGED(models.Model):
    """Document dans la GED structurée CEA / CET."""
    patrimoine = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='documents_ged')
    corps      = models.CharField(max_length=10, choices=[('CEA', 'CEA'), ('CET', 'CET')])
    dossier    = models.CharField(max_length=100, help_text='Clé du sous-dossier (ex: plans_niveau)')

    titre      = models.CharField(max_length=255)
    fichier    = models.FileField(upload_to=ged_upload_path)
    description = models.TextField(blank=True)
    version    = models.CharField(max_length=20, blank=True)
    date_doc   = models.DateField(null=True, blank=True)

    uploade_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploade_le  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Document GED'
        verbose_name_plural = 'Documents GED'
        ordering            = ['corps', 'dossier', '-uploade_le']

    def __str__(self):
        return f'[{self.corps}/{self.dossier}] {self.titre}'

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
        return ext.lower()

    def is_pdf(self):
        return self.extension() == '.pdf'

    def is_image(self):
        return self.extension() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']

    def nom_dossier_affichage(self):
        corps_data = GED_ARBORESCENCE.get(self.corps, {})
        return corps_data.get('sous_dossiers', {}).get(self.dossier, self.dossier)

    def taille_fichier(self):
        try:
            return self.fichier.size
        except Exception:
            return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
