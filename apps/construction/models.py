from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
import os


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def projet_photo_path(instance, filename):
    return f'construction/projets/{instance.projet.pk}/photos/{filename}'

def projet_doc_client_path(instance, filename):
    return f'construction/projets/{instance.projet.pk}/client/{filename}'

def projet_doc_chantier_path(instance, filename):
    return f'construction/projets/{instance.projet.pk}/chantier/{filename}'

def bon_commande_path(instance, filename):
    return f'construction/projets/{instance.projet.pk}/commandes/{filename}'

def rapport_path(instance, filename):
    return f'construction/projets/{instance.projet.pk}/rapports/{filename}'


# ─────────────────────────────────────────────────────────────────────────────
#  PROJET  (entité centrale)
# ─────────────────────────────────────────────────────────────────────────────

class Projet(models.Model):
    """Projet de construction — pivot de tout le module."""

    STATUT = [
        ('prospection',  'Prospection'),
        ('etude',        'En étude'),
        ('en_cours',     'En cours'),
        ('reception',    'Réception travaux'),
        ('termine',      'Terminé'),
        ('suspendu',     'Suspendu'),
    ]

    TYPE_PROJET = [
        ('batiment',     'Bâtiment neuf'),
        ('renovation',   'Rénovation'),
        ('amenagement',  'Aménagement'),
        ('vrd',          'VRD / Génie civil'),
        ('autre',        'Autre'),
    ]

    # ── Identité ──────────────────────────────────────────────
    reference       = models.CharField(max_length=30, unique=True, blank=True,
                                       help_text='Générée auto si vide — ex. PROJ-2026-001')
    titre           = models.CharField(max_length=200)
    type_projet     = models.CharField(max_length=20, choices=TYPE_PROJET, default='batiment')
    statut          = models.CharField(max_length=20, choices=STATUT, default='etude')

    # ── Client ────────────────────────────────────────────────
    client_nom      = models.CharField(max_length=200)
    client_contact  = models.CharField(max_length=100, blank=True)
    client_email    = models.EmailField(blank=True)
    client_tel      = models.CharField(max_length=30, blank=True)
    client_adresse  = models.TextField(blank=True)

    # ── Localisation chantier ──────────────────────────────────
    adresse_chantier = models.TextField(blank=True)

    # ── Vitrine ───────────────────────────────────────────────
    description_courte  = models.CharField(max_length=300, blank=True,
                                           help_text='Résumé affiché en vitrine')
    cahier_des_charges  = models.TextField(blank=True,
                                           help_text='Ce que le client attendait')
    visible_vitrine     = models.BooleanField(default=False,
                                              help_text='Afficher sur la page publique')

    # ── Dates ─────────────────────────────────────────────────
    date_debut          = models.DateField(null=True, blank=True)
    date_fin_prevue     = models.DateField(null=True, blank=True)
    date_fin_reelle     = models.DateField(null=True, blank=True)

    # ── Budget global ─────────────────────────────────────────
    budget_estime       = models.DecimalField(max_digits=14, decimal_places=2,
                                              null=True, blank=True)
    budget_contractuel  = models.DecimalField(max_digits=14, decimal_places=2,
                                              null=True, blank=True)

    # ── Méta ──────────────────────────────────────────────────
    cree_par    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='projets_crees')
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='projets_geres')
    cree_le     = models.DateTimeField(auto_now_add=True)
    modifie_le  = models.DateTimeField(auto_now=True)
    service_tag = models.CharField( blank=True, null=True)
    class Meta:
        verbose_name        = 'Projet'
        verbose_name_plural = 'Projets'
        ordering            = ['-cree_le']

    def __str__(self):
        return f'[{self.reference}] {self.titre}'

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            last = Projet.objects.filter(reference__startswith=f'PROJ-{annee}-').count()
            self.reference = f'PROJ-{annee}-{last + 1:03d}'
        super().save(*args, **kwargs)

    # ── Propriétés calculées ──────────────────────────────────
    @property
    def avancement_global(self):
        taches = self.taches.all()
        if not taches.exists():
            return 0
        return int(taches.aggregate(m=models.Avg('avancement'))['m'] or 0)

    @property
    def total_facture(self):
        return self.factures.filter(statut__in=['envoyee', 'payee']).aggregate(
            t=Sum('montant_ttc'))['t'] or 0

    @property
    def total_depenses(self):
        return self.lignes_budget.aggregate(t=Sum('montant_reel'))['t'] or 0

    @property
    def photo_principale(self):
        return self.photos.filter(principale=True).first() or self.photos.first()

    @property
    def nb_jours_restants(self):
        if self.date_fin_prevue:
            delta = self.date_fin_prevue - timezone.now().date()
            return delta.days
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTOS VITRINE
# ─────────────────────────────────────────────────────────────────────────────

class PhotoProjet(models.Model):
    """Jusqu'à 5 photos par projet pour la vitrine."""

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='photos')
    image       = models.ImageField(upload_to=projet_photo_path)
    legende     = models.CharField(max_length=200, blank=True)
    principale  = models.BooleanField(default=False,
                                      help_text='Photo de couverture affichée en vitrine')
    ordre       = models.PositiveSmallIntegerField(default=0)
    ajoutee_le  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Photo'
        verbose_name_plural = 'Photos'
        ordering            = ['ordre', 'ajoutee_le']

    def __str__(self):
        return f'Photo {self.ordre} — {self.projet.titre}'

    def save(self, *args, **kwargs):
        # Si marquée principale, démarquer les autres
        if self.principale:
            PhotoProjet.objects.filter(projet=self.projet).update(principale=False)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS CLIENT (données brutes)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentClient(models.Model):
    """Fichiers entrants du client : cahiers des charges, plans, briefs…"""

    TYPE = [
        ('cdc',     'Cahier des charges'),
        ('plan',    'Plan / Esquisse'),
        ('photo',   'Photo de référence'),
        ('contrat', 'Contrat / Devis signé'),
        ('autre',   'Autre'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='docs_client')
    type_doc    = models.CharField(max_length=20, choices=TYPE, default='cdc')
    titre       = models.CharField(max_length=255)
    fichier     = models.FileField(upload_to=projet_doc_client_path)
    description = models.TextField(blank=True)
    version     = models.CharField(max_length=20, blank=True)
    date_reception = models.DateField(default=timezone.now)
    recu_par    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Document client'
        verbose_name_plural = 'Documents clients'
        ordering            = ['-date_reception']

    def __str__(self):
        return f'{self.get_type_doc_display()} — {self.titre}'

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
        return ext.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS CHANTIER (production)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentChantier(models.Model):
    """Livrables produits : plans d'exécution, notes de calcul, DOE…"""

    TYPE = [
        ('plan_exe',   'Plan d\'exécution'),
        ('note_calc',  'Note de calcul'),
        ('doe',        'DOE / Dossier des ouvrages exécutés'),
        ('pv',         'PV / Procès-verbal'),
        ('metrage',    'Métré / Devis quantitatif'),
        ('planning',   'Planning'),
        ('securite',   'Plan de sécurité'),
        ('reception',  'Fiche de réception'),
        ('autre',      'Autre'),
    ]

    PHASE = [
        ('etude',    'Phase étude'),
        ('exe',      'Phase exécution'),
        ('reception','Réception'),
        ('garantie', 'Garantie'),
    ]

    projet      = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='docs_chantier')
    type_doc    = models.CharField(max_length=20, choices=TYPE, default='plan_exe')
    phase       = models.CharField(max_length=20, choices=PHASE, default='exe')
    titre       = models.CharField(max_length=255)
    fichier     = models.FileField(upload_to=projet_doc_chantier_path)
    description = models.TextField(blank=True)
    version     = models.CharField(max_length=20, blank=True, default='v1.0')
    indice      = models.CharField(max_length=10, blank=True, help_text='ex. A, B, C…')
    date_doc    = models.DateField(default=timezone.now)
    produit_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    valide      = models.BooleanField(default=False)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Document chantier'
        verbose_name_plural = 'Documents chantier'
        ordering            = ['-date_doc', 'type_doc']

    def __str__(self):
        return f'{self.get_type_doc_display()} {self.version} — {self.titre}'

    def extension(self):
        _, ext = os.path.splitext(self.fichier.name)
        return ext.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  PLANNING — TÂCHES (Gantt)
# ─────────────────────────────────────────────────────────────────────────────

class TacheGantt(models.Model):
    """Tâche du planning Gantt."""

    STATUT = [
        ('a_faire',    'À faire'),
        ('en_cours',   'En cours'),
        ('termine',    'Terminée'),
        ('bloquee',    'Bloquée'),
        ('annulee',    'Annulée'),
    ]

    PRIORITE = [
        ('haute',   'Haute'),
        ('normale', 'Normale'),
        ('basse',   'Basse'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='taches')
    parent          = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                        related_name='sous_taches')
    dependances     = models.ManyToManyField('self', symmetrical=False, blank=True,
                                             related_name='bloquantes')

    titre           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    statut          = models.CharField(max_length=20, choices=STATUT, default='a_faire')
    priorite        = models.CharField(max_length=10, choices=PRIORITE, default='normale')
    avancement      = models.PositiveSmallIntegerField(default=0,
                                                       help_text='Pourcentage 0-100')

    date_debut      = models.DateField()
    date_fin        = models.DateField()
    assignee_a      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='taches_assignees')
    couleur         = models.CharField(max_length=7, default='#2196f3',
                                       help_text='Couleur hex pour le Gantt')
    ordre           = models.PositiveIntegerField(default=0)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Tâche'
        verbose_name_plural = 'Tâches'
        ordering            = ['ordre', 'date_debut']

    def __str__(self):
        return self.titre

    @property
    def duree_jours(self):
        return (self.date_fin - self.date_debut).days + 1

    @property
    def est_en_retard(self):
        if self.statut in ('termine', 'annulee'):
            return False
        return self.date_fin < timezone.now().date()


# ─────────────────────────────────────────────────────────────────────────────
#  BUDGET
# ─────────────────────────────────────────────────────────────────────────────

class LigneBudget(models.Model):
    """Ligne de budget : prévu vs réel par poste."""

    CATEGORIE = [
        ('main_oeuvre',  'Main d\'œuvre'),
        ('materiaux',    'Matériaux'),
        ('equipement',   'Équipement / Location'),
        ('sous_traitant','Sous-traitance'),
        ('etude',        'Études / Bureau'),
        ('divers',       'Divers / Imprévus'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='lignes_budget')
    tache           = models.ForeignKey(TacheGantt, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='lignes_budget')
    categorie       = models.CharField(max_length=20, choices=CATEGORIE)
    designation     = models.CharField(max_length=255)
    unite           = models.CharField(max_length=30, blank=True, help_text='m², ml, u, forfait…')
    quantite        = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    prix_unitaire   = models.DecimalField(max_digits=12, decimal_places=2)
    montant_prevu   = models.DecimalField(max_digits=14, decimal_places=2)
    montant_reel    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    note            = models.TextField(blank=True)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Ligne budget'
        verbose_name_plural = 'Lignes budget'
        ordering            = ['categorie', 'designation']

    def __str__(self):
        return f'{self.get_categorie_display()} — {self.designation}'

    def save(self, *args, **kwargs):
        self.montant_prevu = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)

    @property
    def ecart(self):
        return self.montant_reel - self.montant_prevu


# ─────────────────────────────────────────────────────────────────────────────
#  BON DE COMMANDE
# ─────────────────────────────────────────────────────────────────────────────

class BonCommande(models.Model):
    """Bon de commande émis vers un fournisseur ou sous-traitant."""

    STATUT = [
        ('brouillon',  'Brouillon'),
        ('envoye',     'Envoyé'),
        ('valide',     'Validé / Accepté'),
        ('livre',      'Livré'),
        ('annule',     'Annulé'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='bons_commande')
    numero          = models.CharField(max_length=30, unique=True, blank=True)
    statut          = models.CharField(max_length=20, choices=STATUT, default='brouillon')

    fournisseur_nom = models.CharField(max_length=200)
    fournisseur_contact = models.CharField(max_length=100, blank=True)
    fournisseur_tel = models.CharField(max_length=30, blank=True)

    date_commande   = models.DateField(default=timezone.now)
    date_livraison  = models.DateField(null=True, blank=True)
    lieu_livraison  = models.CharField(max_length=200, blank=True)

    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    note            = models.TextField(blank=True)
    fichier_pdf     = models.FileField(upload_to=bon_commande_path, null=True, blank=True)
    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Bon de commande'
        verbose_name_plural = 'Bons de commande'
        ordering            = ['-date_commande']

    def __str__(self):
        return f'{self.numero} — {self.fournisseur_nom}'

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            last = BonCommande.objects.filter(numero__startswith=f'BC-{annee}-').count()
            self.numero = f'BC-{annee}-{last + 1:04d}'
        self.montant_ttc = self.montant_ht * (1 + self.tva_pct / 100)
        super().save(*args, **kwargs)


class LigneBonCommande(models.Model):
    """Ligne de détail d'un bon de commande."""

    bon         = models.ForeignKey(BonCommande, on_delete=models.CASCADE, related_name='lignes')
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=30, blank=True)
    quantite    = models.DecimalField(max_digits=10, decimal_places=3)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    montant_ht  = models.DecimalField(max_digits=14, decimal_places=2, editable=False, default=0)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        self.montant_ht = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)
        # Recalcule le total du bon
        total = self.bon.lignes.aggregate(t=Sum('montant_ht'))['t'] or 0
        BonCommande.objects.filter(pk=self.bon_id).update(
            montant_ht=total,
            montant_ttc=total * (1 + self.bon.tva_pct / 100)
        )


# ─────────────────────────────────────────────────────────────────────────────
#  RAPPORT D'ACTIVITÉ
# ─────────────────────────────────────────────────────────────────────────────

class RapportActivite(models.Model):
    """Rapport périodique : hebdo, mensuel ou par tâche accomplie."""

    PERIODE = [
        ('journalier', 'Journalier'),
        ('hebdo',      'Hebdomadaire'),
        ('mensuel',    'Mensuel'),
        ('tache',      'Fin de tâche'),
        ('situation',  'Situation de travaux'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='rapports')
    type_rapport    = models.CharField(max_length=20, choices=PERIODE, default='hebdo')
    titre           = models.CharField(max_length=255)
    periode_debut   = models.DateField()
    periode_fin     = models.DateField()

    # Tâches concernées
    taches_concernees = models.ManyToManyField(TacheGantt, blank=True,
                                                related_name='rapports')

    # Contenu
    travaux_realises    = models.TextField(help_text='Travaux effectués pendant la période')
    observations        = models.TextField(blank=True, help_text='Problèmes, risques, remarques')
    travaux_prevus      = models.TextField(blank=True, help_text='Prochaine période')

    # Avancement global constaté
    avancement_constate = models.PositiveSmallIntegerField(default=0)

    # Main d'œuvre
    nb_ouvriers         = models.PositiveSmallIntegerField(default=0)
    nb_journees         = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    # Pièce jointe
    fichier             = models.FileField(upload_to=rapport_path, null=True, blank=True)

    # Facturation forfaitaire par tâche
    montant_a_facturer  = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                               help_text='Montant à facturer sur ce rapport')
    facture_liee        = models.ForeignKey('Facture', on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='rapports_lies')

    redige_par  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le     = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name        = 'Rapport d\'activité'
        verbose_name_plural = 'Rapports d\'activité'
        ordering            = ['-periode_fin']

    def __str__(self):
        return f'{self.get_type_rapport_display()} — {self.titre}'


# ─────────────────────────────────────────────────────────────────────────────
#  FACTURATION
# ─────────────────────────────────────────────────────────────────────────────

class Facture(models.Model):
    """Facture émise au client — peut être une situation de travaux."""

    STATUT = [
        ('brouillon', 'Brouillon'),
        ('envoyee',   'Envoyée'),
        ('payee',     'Payée'),
        ('partielle', 'Paiement partiel'),
        ('retard',    'En retard'),
        ('annulee',   'Annulée'),
    ]

    TYPE = [
        ('acompte',    'Acompte / Appel de fonds'),
        ('situation',  'Situation de travaux'),
        ('solde',      'Facture de solde'),
        ('avoir',      'Avoir'),
    ]

    projet          = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='factures')
    numero          = models.CharField(max_length=30, unique=True, blank=True,
                                       help_text='Généré auto — FAC-2026-001')
    type_facture    = models.CharField(max_length=20, choices=TYPE, default='situation')
    statut          = models.CharField(max_length=20, choices=STATUT, default='brouillon')

    # Émetteur (votre société)
    emetteur_nom    = models.CharField(max_length=200, default='R-CYBER BTP')
    emetteur_adresse= models.TextField(blank=True)
    emetteur_tel    = models.CharField(max_length=30, blank=True)
    emetteur_email  = models.EmailField(blank=True)
    emetteur_nif    = models.CharField(max_length=50, blank=True, help_text='NIF / STAT')

    # Destinataire (client)
    client_nom      = models.CharField(max_length=200)
    client_adresse  = models.TextField(blank=True)

    # Dates
    date_emission   = models.DateField(default=timezone.now)
    date_echeance   = models.DateField(null=True, blank=True)
    date_paiement   = models.DateField(null=True, blank=True)

    # Montants
    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_tva     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_paye    = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Situation de travaux
    pct_avancement  = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                          help_text='% avancement pour cette situation')
    montant_precedent = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                            help_text='Cumul déjà facturé')

    objet           = models.CharField(max_length=300, blank=True)
    conditions_paiement = models.TextField(blank=True)
    note            = models.TextField(blank=True)

    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le         = models.DateTimeField(auto_now_add=True)
    modifie_le      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Facture'
        verbose_name_plural = 'Factures'
        ordering            = ['-date_emission']

    def __str__(self):
        return f'{self.numero} — {self.client_nom} — {self.montant_ttc} Ar'

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            last = Facture.objects.filter(numero__startswith=f'FAC-{annee}-').count()
            self.numero = f'FAC-{annee}-{last + 1:03d}'
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
    """Ligne de détail d'une facture."""

    facture         = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='lignes')
    designation     = models.CharField(max_length=255)
    unite           = models.CharField(max_length=30, blank=True)
    quantite        = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    prix_unitaire   = models.DecimalField(max_digits=12, decimal_places=2)
    montant_ht      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tache           = models.ForeignKey(TacheGantt, on_delete=models.SET_NULL,
                                         null=True, blank=True)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        self.montant_ht = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)
        # Recalcule le total de la facture
        total = self.facture.lignes.aggregate(t=Sum('montant_ht'))['t'] or 0
        f = Facture.objects.get(pk=self.facture_id)
        f.montant_ht = total
        f.montant_tva = total * f.tva_pct / 100
        f.montant_ttc = total + f.montant_tva
        Facture.objects.filter(pk=self.facture_id).update(
            montant_ht=f.montant_ht,
            montant_tva=f.montant_tva,
            montant_ttc=f.montant_ttc,
        )
