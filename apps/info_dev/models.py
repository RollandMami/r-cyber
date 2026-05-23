from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


# ─── Upload helpers ────────────────────────────────────────────────────────────

def projet_livrable_path(instance, filename):
    return f'info_dev/projets/{instance.projet.pk}/livrables/{filename}'

def projet_doc_path(instance, filename):
    return f'info_dev/projets/{instance.projet.pk}/docs/{filename}'

def devis_path(instance, filename):
    return f'info_dev/devis/{instance.pk}/{filename}'

def facture_path(instance, filename):
    return f'info_dev/factures/{instance.pk}/{filename}'


# ─────────────────────────────────────────────────────────────────────────────
#  CLIENT  (partagé avec les autres apps via référence souple)
# ─────────────────────────────────────────────────────────────────────────────

class Client(models.Model):
    """
    Client Info-Dev — peut être lié à un client construction/BE
    via client_ref (référence textuelle) ou rester indépendant.
    """
    nom         = models.CharField(max_length=200)
    email       = models.EmailField(blank=True)
    telephone   = models.CharField(max_length=30, blank=True)
    adresse     = models.TextField(blank=True)
    entreprise  = models.CharField(max_length=200, blank=True)
    # Lien souple vers une référence externe (ex. construction:client_nom)
    client_ref  = models.CharField(max_length=100, blank=True,
                                   help_text='Référence client partagée (ex. construction)')
    note        = models.TextField(blank=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Client'
        verbose_name_plural = 'Clients'
        ordering            = ['nom']

    def __str__(self):
        return f'{self.nom}' + (f' ({self.entreprise})' if self.entreprise else '')


# ─────────────────────────────────────────────────────────────────────────────
#  PROJET  (pivot central info-dev)
# ─────────────────────────────────────────────────────────────────────────────

class Projet(models.Model):

    TYPE = [
        ('script',      'Script Python / Bash / C'),
        ('web',         'Site web / Application web'),
        ('logiciel',    'Logiciel desktop'),
        ('api',         'API / Intégration'),
        ('maintenance', 'Maintenance & Support'),
    ]

    STATUT = [
        ('prospect',    'Prospection'),
        ('en_cours',    'En cours'),
        ('recette',     'Recette / Tests'),
        ('livre',       'Livré'),
        ('maintenance', 'En maintenance'),
        ('archive',     'Archivé'),
    ]

    PRIORITE = [
        ('haute',   'Haute'),
        ('normale', 'Normale'),
        ('basse',   'Basse'),
    ]

    reference       = models.CharField(max_length=30, unique=True, blank=True)
    titre           = models.CharField(max_length=255)
    type_projet     = models.CharField(max_length=20, choices=TYPE, default='web')
    statut          = models.CharField(max_length=20, choices=STATUT, default='prospect')
    priorite        = models.CharField(max_length=10, choices=PRIORITE, default='normale')

    client          = models.ForeignKey(Client, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='projets')

    description     = models.TextField(blank=True)
    cahier_charges  = models.TextField(blank=True, help_text='Besoins fonctionnels du client')
    stack_technique = models.CharField(max_length=300, blank=True,
                                       help_text='ex. Python 3.12, Django 5, PostgreSQL, React…')

    # Repository / URL
    repo_url        = models.URLField(blank=True, help_text='GitHub / GitLab / URL du projet')
    url_prod        = models.URLField(blank=True, help_text='URL de production')
    url_recette     = models.URLField(blank=True, help_text='URL de recette / staging')

    # Planning
    date_debut      = models.DateField(default=timezone.now)
    date_fin_prevue = models.DateField(null=True, blank=True)
    date_livraison  = models.DateField(null=True, blank=True)

    # Budget
    budget_ht       = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)

    responsable     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='infdev_projets_responsable')
    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                         related_name='infdev_projets_crees')
    cree_le         = models.DateTimeField(auto_now_add=True)
    modifie_le      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Projet Info-Dev'
        verbose_name_plural = 'Projets Info-Dev'
        ordering            = ['-cree_le']

    def __str__(self):
        return f'[{self.reference}] {self.titre}'

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            last  = Projet.objects.filter(reference__startswith=f'DEV-{annee}-').count()
            self.reference = f'DEV-{annee}-{last + 1:03d}'
        super().save(*args, **kwargs)

    @property
    def avancement(self):
        taches = self.taches.all()
        if not taches.exists():
            return 0
        terminees = taches.filter(statut='termine').count()
        return int(terminees / taches.count() * 100)

    @property
    def nb_bugs_ouverts(self):
        return self.bugs.filter(statut__in=['ouvert', 'en_cours']).count()

    @property
    def est_en_retard(self):
        if self.date_fin_prevue and self.statut in ('en_cours', 'recette', 'prospect'):
            return self.date_fin_prevue < timezone.now().date()
        return False

    @property
    def nb_jours_restants(self):
        if self.date_fin_prevue:
            return (self.date_fin_prevue - timezone.now().date()).days
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  TÂCHE (gestion de projet)
# ─────────────────────────────────────────────────────────────────────────────

class Tache(models.Model):

    STATUT = [
        ('todo',      'À faire'),
        ('en_cours',  'En cours'),
        ('review',    'En révision'),
        ('termine',   'Terminée'),
        ('annulee',   'Annulée'),
    ]

    PRIORITE = [
        ('critique', 'Critique'),
        ('haute',    'Haute'),
        ('normale',  'Normale'),
        ('basse',    'Basse'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='taches')
    titre       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    statut      = models.CharField(max_length=15, choices=STATUT, default='todo')
    priorite    = models.CharField(max_length=10, choices=PRIORITE, default='normale')
    assignee    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='infdev_taches')
    date_debut  = models.DateField(null=True, blank=True)
    date_fin    = models.DateField(null=True, blank=True)
    ordre       = models.PositiveIntegerField(default=0)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'cree_le']
        verbose_name        = 'Tâche'
        verbose_name_plural = 'Tâches'

    def __str__(self):
        return f'{self.titre} ({self.projet.reference})'

    @property
    def est_en_retard(self):
        return (self.date_fin and
                self.statut not in ('termine', 'annulee') and
                self.date_fin < timezone.now().date())


# ─────────────────────────────────────────────────────────────────────────────
#  BUG / DEMANDE CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class Bug(models.Model):

    TYPE = [
        ('bug',      'Bug'),
        ('feature',  'Nouvelle fonctionnalité'),
        ('perf',     'Performance'),
        ('secu',     'Sécurité'),
        ('question', 'Question / Support'),
    ]

    STATUT = [
        ('ouvert',    'Ouvert'),
        ('en_cours',  'En cours'),
        ('resolu',    'Résolu'),
        ('ferme',     'Fermé / Non reproductible'),
        ('reporte',   'Reporté'),
    ]

    SEVERITE = [
        ('critique', 'Critique'),
        ('haute',    'Haute'),
        ('normale',  'Normale'),
        ('basse',    'Basse'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='bugs')
    titre       = models.CharField(max_length=255)
    type_bug    = models.CharField(max_length=15, choices=TYPE, default='bug')
    statut      = models.CharField(max_length=15, choices=STATUT, default='ouvert')
    severite    = models.CharField(max_length=10, choices=SEVERITE, default='normale')

    description = models.TextField(help_text='Description détaillée du problème')
    etapes_repro= models.TextField(blank=True, help_text='Étapes pour reproduire')
    environnement = models.CharField(max_length=200, blank=True,
                                      help_text='OS, navigateur, version…')
    solution    = models.TextField(blank=True, help_text='Solution apportée')

    rapporte_par= models.CharField(max_length=100, blank=True,
                                    help_text='Nom du client ou utilisateur')
    assigne_a   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='infdev_bugs')
    tache_liee  = models.ForeignKey(Tache, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='bugs')

    date_ouvert = models.DateField(default=timezone.now)
    date_resolu = models.DateField(null=True, blank=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_ouvert', 'severite']
        verbose_name        = 'Bug / Demande'
        verbose_name_plural = 'Bugs / Demandes'

    def __str__(self):
        return f'[{self.get_type_bug_display()}] {self.titre}'


# ─────────────────────────────────────────────────────────────────────────────
#  LIVRABLE (code, fichiers, déploiement)
# ─────────────────────────────────────────────────────────────────────────────

class Livrable(models.Model):

    TYPE = [
        ('code_source', 'Code source / Archive'),
        ('executable',  'Exécutable / Build'),
        ('script',      'Script'),
        ('config',      'Fichier de configuration'),
        ('doc_tech',    'Documentation technique'),
        ('manuel',      'Manuel utilisateur'),
        ('autre',       'Autre'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='livrables')
    type_livrable = models.CharField(max_length=20, choices=TYPE, default='code_source')
    titre       = models.CharField(max_length=255)
    version     = models.CharField(max_length=30, default='v1.0.0')
    fichier     = models.FileField(upload_to=projet_livrable_path, null=True, blank=True)
    url_externe = models.URLField(blank=True, help_text='Lien release GitHub, CDN…')
    description = models.TextField(blank=True)
    changelog   = models.TextField(blank=True, help_text='Notes de version')
    livre_au_client = models.BooleanField(default=False)
    date_livraison  = models.DateField(default=timezone.now)
    produit_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_livraison', 'type_livrable']
        verbose_name        = 'Livrable'
        verbose_name_plural = 'Livrables'

    def __str__(self):
        return f'{self.titre} {self.version}'

    def extension(self):
        if self.fichier:
            _, ext = os.path.splitext(self.fichier.name)
            return ext.lower().lstrip('.')
        return ''


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTATION TECHNIQUE
# ─────────────────────────────────────────────────────────────────────────────

class Documentation(models.Model):

    CATEGORIE = [
        ('installation', 'Guide d\'installation'),
        ('api',          'Documentation API'),
        ('architecture', 'Architecture système'),
        ('utilisation',  'Manuel d\'utilisation'),
        ('maintenance',  'Guide de maintenance'),
        ('autre',        'Autre'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='docs')
    categorie   = models.CharField(max_length=20, choices=CATEGORIE, default='autre')
    titre       = models.CharField(max_length=255)
    contenu     = models.TextField(help_text='Contenu Markdown ou texte brut')
    version     = models.CharField(max_length=20, default='v1.0')
    fichier     = models.FileField(upload_to=projet_doc_path, null=True, blank=True)
    publie      = models.BooleanField(default=False, help_text='Visible par le client')
    redige_par  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)
    modifie_le  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['categorie', '-modifie_le']
        verbose_name        = 'Documentation'
        verbose_name_plural = 'Documentations'

    def __str__(self):
        return f'{self.get_categorie_display()} — {self.titre}'


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS INFO-DEV
# ─────────────────────────────────────────────────────────────────────────────

class Devis(models.Model):

    STATUT = [
        ('brouillon', 'Brouillon'),
        ('envoye',    'Envoyé'),
        ('accepte',   'Accepté'),
        ('refuse',    'Refusé'),
        ('expire',    'Expiré'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='devis')
    numero          = models.CharField(max_length=30, unique=True, blank=True)
    statut          = models.CharField(max_length=15, choices=STATUT, default='brouillon')

    emetteur_nom    = models.CharField(max_length=200, default='R-CYBER Info-Dev')
    emetteur_adresse= models.TextField(blank=True)
    emetteur_tel    = models.CharField(max_length=30, blank=True)
    emetteur_email  = models.EmailField(blank=True)
    emetteur_nif    = models.CharField(max_length=50, blank=True)

    client_nom      = models.CharField(max_length=200)
    client_adresse  = models.TextField(blank=True)

    date_devis      = models.DateField(default=timezone.now)
    date_validite   = models.DateField(null=True, blank=True)

    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_tva     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    objet           = models.CharField(max_length=300, blank=True)
    conditions      = models.TextField(blank=True)
    note            = models.TextField(blank=True)

    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='info_dev_devis_crees')
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
            last  = Devis.objects.filter(numero__startswith=f'DEVI-{annee}-').count()
            self.numero = f'DEVI-{annee}-{last + 1:03d}'
        self.montant_tva = self.montant_ht * self.tva_pct / 100
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)


class LigneDevis(models.Model):
    devis           = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='lignes')
    designation     = models.CharField(max_length=255)
    unite           = models.CharField(max_length=30, blank=True, default='forfait')
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
#  FACTURE INFO-DEV
# ─────────────────────────────────────────────────────────────────────────────

class Facture(models.Model):

    TYPE = [
        ('acompte',  'Acompte'),
        ('jalon',    'Facturation par jalon'),
        ('solde',    'Solde / Finale'),
        ('mensuelle','Maintenance mensuelle'),
        ('avoir',    'Avoir'),
    ]

    STATUT = [
        ('brouillon', 'Brouillon'),
        ('envoyee',   'Envoyée'),
        ('payee',     'Payée'),
        ('partielle', 'Paiement partiel'),
        ('retard',    'En retard'),
        ('annulee',   'Annulée'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='factures')
    devis_origine   = models.ForeignKey(Devis, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='factures')
    numero          = models.CharField(max_length=30, unique=True, blank=True)
    type_facture    = models.CharField(max_length=15, choices=TYPE, default='jalon')
    statut          = models.CharField(max_length=15, choices=STATUT, default='brouillon')

    emetteur_nom    = models.CharField(max_length=200, default='R-CYBER Info-Dev')
    emetteur_adresse= models.TextField(blank=True)
    emetteur_tel    = models.CharField(max_length=30, blank=True)
    emetteur_email  = models.EmailField(blank=True)
    emetteur_nif    = models.CharField(max_length=50, blank=True)

    client_nom      = models.CharField(max_length=200)
    client_adresse  = models.TextField(blank=True)

    date_emission   = models.DateField(default=timezone.now)
    date_echeance   = models.DateField(null=True, blank=True)
    date_paiement   = models.DateField(null=True, blank=True)

    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_tva     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_paye    = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    jalon           = models.CharField(max_length=200, blank=True,
                                        help_text='ex. Livraison phase 1, Recette validée…')
    objet           = models.CharField(max_length=300, blank=True)
    conditions      = models.TextField(blank=True)
    note            = models.TextField(blank=True)

    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='info_dev_factures_creees')
    cree_le         = models.DateTimeField(auto_now_add=True)
    modifie_le      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_emission']
        verbose_name        = 'Facture'
        verbose_name_plural = 'Factures'

    def __str__(self):
        return f'{self.numero} — {self.client_nom}'

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            last  = Facture.objects.filter(numero__startswith=f'FAC-DEV-{annee}-').count()
            self.numero = f'FAC-DEV-{annee}-{last + 1:03d}'
        self.montant_tva = self.montant_ht * self.tva_pct / 100
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)

    @property
    def montant_restant(self):
        return self.montant_ttc - self.montant_paye

    @property
    def est_en_retard(self):
        if self.statut in ('payee', 'annulee'):
            return False
        return self.date_echeance and self.date_echeance < timezone.now().date()


class LigneFacture(models.Model):
    facture         = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='lignes')
    designation     = models.CharField(max_length=255)
    unite           = models.CharField(max_length=30, blank=True, default='forfait')
    quantite        = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    prix_unitaire   = models.DecimalField(max_digits=12, decimal_places=2)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        from django.db.models import Sum
        self.montant_ht = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)
        total = self.facture.lignes.aggregate(t=Sum('montant_ht'))['t'] or 0
        f = Facture.objects.get(pk=self.facture_id)
        Facture.objects.filter(pk=self.facture_id).update(
            montant_ht=total,
            montant_tva=total * f.tva_pct / 100,
            montant_ttc=total + total * f.tva_pct / 100,
        )
