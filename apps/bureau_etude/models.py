from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


# ─── helpers upload ───────────────────────────────────────────────────────────

def mission_doc_path(instance, filename):
    return f'bureau_etude/missions/{instance.mission.pk}/docs/{filename}'

def mission_plan_path(instance, filename):
    return f'bureau_etude/missions/{instance.mission.pk}/plans/{filename}'

def devis_path(instance, filename):
    return f'bureau_etude/missions/{instance.mission.pk}/devis/{filename}'

def rapport_etude_path(instance, filename):
    return f'bureau_etude/missions/{instance.mission.pk}/rapports/{filename}'


# ─────────────────────────────────────────────────────────────────────────────
#  MISSION  (pivot central)
# ─────────────────────────────────────────────────────────────────────────────

class Mission(models.Model):
    """Mission d'étude — entité centrale du bureau d'étude."""

    STATUT = [
        ('prospection', 'Prospection'),
        ('en_cours',    'En cours'),
        ('rendu',       'Rendu client'),
        ('valide',      'Validé'),
        ('archive',     'Archivé'),
    ]

    TYPE = [
        ('etude_sol',      'Étude de sol'),
        ('structure',      'Calcul de structure'),
        ('thermique',      'Étude thermique'),
        ('hydraulique',    'Étude hydraulique'),
        ('topographie',    'Topographie / Levé'),
        ('voirie',         'Voirie & Réseaux'),
        ('architecture',   'Conception architecturale'),
        ('permis',         'Dossier de permis'),
        ('diagnostic',     'Diagnostic technique'),
        ('autre',          'Autre étude'),
    ]

    reference       = models.CharField(max_length=30, unique=True, blank=True)
    titre           = models.CharField(max_length=255)
    type_mission    = models.CharField(max_length=30, choices=TYPE, default='structure')
    statut          = models.CharField(max_length=20, choices=STATUT, default='prospection')

    # Client
    client_nom      = models.CharField(max_length=200)
    client_tel      = models.CharField(max_length=30, blank=True)
    client_email    = models.EmailField(blank=True)
    client_adresse  = models.TextField(blank=True)

    # Localisation
    adresse_site    = models.TextField(blank=True)

    # Contenu
    description     = models.TextField(blank=True, help_text='Objet de la mission')
    objectifs       = models.TextField(blank=True, help_text='Objectifs techniques attendus')

    # Dates
    date_commande   = models.DateField(default=timezone.now)
    date_rendu      = models.DateField(null=True, blank=True, help_text='Date de rendu prévue')
    date_rendu_reel = models.DateField(null=True, blank=True)

    # Honoraires
    honoraires_ht   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    honoraires_ttc  = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, editable=False)

    # Équipe
    responsable     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='missions_responsable')
    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                         related_name='missions_creees')
    cree_le         = models.DateTimeField(auto_now_add=True)
    modifie_le      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Mission'
        verbose_name_plural = 'Missions'
        ordering            = ['-cree_le']

    def __str__(self):
        return f'[{self.reference}] {self.titre}'

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            last  = Mission.objects.filter(reference__startswith=f'BE-{annee}-').count()
            self.reference = f'BE-{annee}-{last + 1:03d}'
        if self.honoraires_ht:
            self.honoraires_ttc = self.honoraires_ht * (1 + self.tva_pct / 100)
        super().save(*args, **kwargs)

    @property
    def nb_jours_restants(self):
        if self.date_rendu and self.statut not in ('rendu', 'valide', 'archive'):
            return (self.date_rendu - timezone.now().date()).days
        return None

    @property
    def est_en_retard(self):
        if self.date_rendu and self.statut in ('en_cours', 'prospection'):
            return self.date_rendu < timezone.now().date()
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS D'ENTRÉE (données brutes client)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentEntree(models.Model):
    """Pièces fournies par le client : plans existants, relevés, photos…"""

    TYPE = [
        ('plan_existant', 'Plan existant'),
        ('releve',        'Relevé de terrain'),
        ('photo',         'Photos'),
        ('rapport_prec',  'Rapport précédent'),
        ('contrat',       'Contrat / Commande'),
        ('autre',         'Autre'),
    ]

    mission     = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='docs_entree')
    type_doc    = models.CharField(max_length=25, choices=TYPE, default='autre')
    titre       = models.CharField(max_length=255)
    fichier     = models.FileField(upload_to=mission_doc_path)
    description = models.TextField(blank=True)
    date_reception = models.DateField(default=timezone.now)
    recu_par    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_reception']
        verbose_name        = 'Document d\'entrée'
        verbose_name_plural = 'Documents d\'entrée'

    def __str__(self):
        return f'{self.get_type_doc_display()} — {self.titre}'

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
        return ext.lower().lstrip('.')


# ─────────────────────────────────────────────────────────────────────────────
#  PLANS & LIVRABLES (production)
# ─────────────────────────────────────────────────────────────────────────────

class PlanLivrable(models.Model):
    """Plans, notes de calcul, rapports produits par le bureau."""

    TYPE = [
        ('plan_arch',   'Plan d\'architecture'),
        ('plan_struct', 'Plan de structure'),
        ('note_calc',   'Note de calcul'),
        ('rapport',     'Rapport d\'étude'),
        ('metrage',     'Métré / Quantitatif'),
        ('dossier_pc',  'Dossier permis de construire'),
        ('plan_exe',    'Plan d\'exécution'),
        ('autre',       'Autre livrable'),
    ]

    PHASE = [
        ('esquisse',    'Esquisse'),
        ('avp',         'Avant-Projet (AVP)'),
        ('pro',         'Projet (PRO)'),
        ('exe',         'Exécution (EXE)'),
        ('doe',         'DOE / Dossier final'),
    ]

    mission     = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='livrables')
    type_doc    = models.CharField(max_length=25, choices=TYPE, default='rapport')
    phase       = models.CharField(max_length=15, choices=PHASE, default='pro')
    titre       = models.CharField(max_length=255)
    fichier     = models.FileField(upload_to=mission_plan_path)
    description = models.TextField(blank=True)
    version     = models.CharField(max_length=20, default='v1.0')
    indice      = models.CharField(max_length=10, blank=True)
    date_doc    = models.DateField(default=timezone.now)
    valide      = models.BooleanField(default=False)
    produit_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_doc', 'type_doc']
        verbose_name        = 'Livrable'
        verbose_name_plural = 'Livrables'

    def __str__(self):
        return f'{self.get_type_doc_display()} {self.version} — {self.titre}'

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
        return ext.lower().lstrip('.')


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS / OFFRE D'HONORAIRES
# ─────────────────────────────────────────────────────────────────────────────

class Devis(models.Model):
    """Offre d'honoraires émise au client."""

    STATUT = [
        ('brouillon', 'Brouillon'),
        ('envoye',    'Envoyé'),
        ('accepte',   'Accepté'),
        ('refuse',    'Refusé'),
        ('expire',    'Expiré'),
    ]

    mission         = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='devis')
    numero          = models.CharField(max_length=30, unique=True, blank=True)
    statut          = models.CharField(max_length=15, choices=STATUT, default='brouillon')

    # Émetteur
    emetteur_nom    = models.CharField(max_length=200, default='R-CYBER Bureau d\'Étude')
    emetteur_adresse= models.TextField(blank=True)
    emetteur_tel    = models.CharField(max_length=30, blank=True)
    emetteur_email  = models.EmailField(blank=True)
    emetteur_nif    = models.CharField(max_length=50, blank=True)

    # Client
    client_nom      = models.CharField(max_length=200)
    client_adresse  = models.TextField(blank=True)

    # Dates
    date_devis      = models.DateField(default=timezone.now)
    date_validite   = models.DateField(null=True, blank=True)

    # Montants
    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_tva     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    objet           = models.CharField(max_length=300, blank=True)
    conditions      = models.TextField(blank=True)
    note            = models.TextField(blank=True)
    fichier_pdf     = models.FileField(upload_to=devis_path, null=True, blank=True)

    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_devis']
        verbose_name        = 'Devis'
        verbose_name_plural = 'Devis'

    def __str__(self):
        return f'{self.numero} — {self.client_nom}'

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            last  = Devis.objects.filter(numero__startswith=f'DEV-{annee}-').count()
            self.numero = f'DEV-{annee}-{last + 1:03d}'
        self.montant_tva = self.montant_ht * self.tva_pct / 100
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)


class LigneDevis(models.Model):
    """Ligne de détail d'un devis."""
    devis           = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='lignes')
    designation     = models.CharField(max_length=255)
    unite           = models.CharField(max_length=30, blank=True)
    quantite        = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    prix_unitaire   = models.DecimalField(max_digits=12, decimal_places=2)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        from django.db.models import Sum
        self.montant_ht = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)
        total = self.devis.lignes.aggregate(t=Sum('montant_ht'))['t'] or 0
        d = Devis.objects.get(pk=self.devis_id)
        Devis.objects.filter(pk=self.devis_id).update(
            montant_ht=total,
            montant_tva=total * d.tva_pct / 100,
            montant_ttc=total + total * d.tva_pct / 100,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  NOTE DE CALCUL
# ─────────────────────────────────────────────────────────────────────────────

class NoteCalcul(models.Model):
    """Note de calcul structuré avec hypothèses, résultats et conclusion."""

    DOMAINE = [
        ('beton_arme',  'Béton armé'),
        ('charpente',   'Charpente bois / métal'),
        ('fondation',   'Fondations'),
        ('thermique',   'Thermique'),
        ('hydraulique', 'Hydraulique'),
        ('geotechnique','Géotechnique'),
        ('autre',       'Autre'),
    ]

    mission         = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='notes_calcul')
    domaine         = models.CharField(max_length=20, choices=DOMAINE, default='beton_arme')
    titre           = models.CharField(max_length=255)
    version         = models.CharField(max_length=20, default='v1.0')

    hypotheses      = models.TextField(blank=True, help_text='Hypothèses de calcul')
    methodologie    = models.TextField(blank=True, help_text='Méthode / normes utilisées')
    resultats       = models.TextField(blank=True, help_text='Résultats et dimensionnements')
    conclusion      = models.TextField(blank=True)

    norme_ref       = models.CharField(max_length=200, blank=True, help_text='ex. Eurocode 2, BAEL 91…')
    logiciel        = models.CharField(max_length=100, blank=True, help_text='ex. Robot, RDM6, Excel…')

    valide          = models.BooleanField(default=False)
    valide_par      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='notes_validees')
    date_validation = models.DateField(null=True, blank=True)

    fichier         = models.FileField(upload_to=rapport_etude_path, null=True, blank=True)

    redige_par      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                         related_name='notes_redigees')
    cree_le         = models.DateTimeField(auto_now_add=True)
    modifie_le      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-cree_le']
        verbose_name        = 'Note de calcul'
        verbose_name_plural = 'Notes de calcul'

    def __str__(self):
        return f'{self.get_domaine_display()} {self.version} — {self.titre}'


# ─────────────────────────────────────────────────────────────────────────────
#  RÉUNION / COMPTE-RENDU
# ─────────────────────────────────────────────────────────────────────────────

class Reunion(models.Model):
    """Compte-rendu de réunion lié à une mission."""

    TYPE = [
        ('lancement',   'Réunion de lancement'),
        ('avancement',  'Point d\'avancement'),
        ('validation',  'Réunion de validation'),
        ('coordination','Coordination'),
        ('autre',       'Autre'),
    ]

    mission         = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='reunions')
    type_reunion    = models.CharField(max_length=20, choices=TYPE, default='avancement')
    titre           = models.CharField(max_length=255)
    date_reunion    = models.DateField()
    lieu            = models.CharField(max_length=200, blank=True)

    participants    = models.TextField(blank=True, help_text='Liste des participants (un par ligne)')
    ordre_du_jour   = models.TextField(blank=True)
    compte_rendu    = models.TextField(blank=True)
    actions         = models.TextField(blank=True, help_text='Actions à mener (responsable / délai)')

    fichier         = models.FileField(upload_to=rapport_etude_path, null=True, blank=True)
    redige_par      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_reunion']
        verbose_name        = 'Réunion'
        verbose_name_plural = 'Réunions'

    def __str__(self):
        return f'{self.get_type_reunion_display()} — {self.titre} ({self.date_reunion})'
