"""
MOREX Devis BTP — models.py
Module indépendant de devis complet pour projets de construction.
Chaîne : Matériaux → Dosages → Avant-métré → Nomenclature → PHMO → Frais → DEPS → Récapitulatif
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
import os


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def devis_pdf_path(instance, filename):
    return f'devis_btp/{instance.pk}/pdf/{filename}'


# ─────────────────────────────────────────────────────────────────────────────
#  BASE DE DONNÉES MATÉRIAUX
# ─────────────────────────────────────────────────────────────────────────────

class Materiau(models.Model):
    """
    Prix unitaire d'un matériau rendu chantier.
    Prix rendu chantier = (prix_fournisseur + manutention + transport) × (1 + taux_chute/100)
    """
    code            = models.CharField(max_length=20, unique=True)
    designation     = models.CharField(max_length=200)
    unite           = models.CharField(max_length=20, help_text='u, m3, m2, kg, sac, ml…')

    prix_fournisseur = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                           help_text='Prix ex-usine ou catalogue fournisseur')
    frais_manutention = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    frais_transport   = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taux_chute        = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                            help_text='Taux de chute et perte en %')

    actif  = models.BooleanField(default=True)
    note   = models.TextField(blank=True)
    cree_le    = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Matériau'
        verbose_name_plural = 'Matériaux'
        ordering            = ['code']

    def __str__(self):
        return f'[{self.code}] {self.designation} ({self.unite})'

    @property
    def prix_rendu_chantier(self):
        """Prix unitaire total rendu chantier, chute incluse."""
        base = float(self.prix_fournisseur) + float(self.frais_manutention) + float(self.frais_transport)
        return round(base * (1 + float(self.taux_chute) / 100), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  BASE DE DONNÉES DOSAGES (Bétons & Mortiers)
# ─────────────────────────────────────────────────────────────────────────────

class Dosage(models.Model):
    """
    Composition unitaire d'un béton ou mortier (pour 1 m³).
    Permet de calculer automatiquement les quantités de matériaux
    en fonction du volume d'ouvrage.
    """
    CATEGORIE = [
        ('BETON',   'Béton'),
        ('MORTIER', 'Mortier'),
        ('ENDUIT',  'Enduit'),
        ('AUTRE',   'Autre'),
    ]

    code        = models.CharField(max_length=20, unique=True, help_text='ex. BO-01, MR-04')
    categorie   = models.CharField(max_length=10, choices=CATEGORIE, default='BETON')
    dosage_kg   = models.IntegerField(default=300, help_text='Dosage en kg de liant par m³')
    choix_liant = models.CharField(max_length=100, blank=True, help_text='ex. CPA 250/315, CHRI 315/400')
    description = models.CharField(max_length=200, blank=True)

    # Quantités pour 1 m³ de béton/mortier
    sable_m3    = models.DecimalField(max_digits=6, decimal_places=3, default=0, help_text='m³ de sable')
    gravillon_m3= models.DecimalField(max_digits=6, decimal_places=3, default=0, help_text='m³ de gravillon')
    eau_litres  = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Litres d\'eau')
    ciment_kg   = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='kg de ciment')
    chaux_kg    = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='kg de chaux (si mortier chaux)')
    acier_kg    = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='kg d\'acier HA (béton armé)')
    fil_recuit_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='kg de fil recuit')

    actif       = models.BooleanField(default=True)
    cree_le     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Dosage'
        verbose_name_plural = 'Dosages'
        ordering            = ['categorie', 'dosage_kg']

    def __str__(self):
        return f'[{self.code}] {self.get_categorie_display()} {self.dosage_kg}kg — {self.choix_liant}'


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS (entité centrale)
# ─────────────────────────────────────────────────────────────────────────────

class Devis(models.Model):
    """
    Devis BTP complet — entité pivot reliant toutes les étapes du calcul.
    Peut être lié à une Mission (bureau d'étude) ou un Projet (construction).
    """
    STATUT = [
        ('brouillon',  'Brouillon'),
        ('en_cours',   'En cours'),
        ('finalise',   'Finalisé'),
        ('envoye',     'Envoyé au client'),
        ('accepte',    'Accepté'),
        ('refuse',     'Refusé'),
        ('archive',    'Archivé'),
    ]

    SOURCE = [
        ('direct',       'Direct'),
        ('bureau_etude', 'Bureau d\'étude'),
        ('construction', 'Construction'),
    ]

    MODE_MO = [
        ('horaire',  'Base horaire (PHMO)'),
        ('forfait',  'Forfaitaire par tâche'),
    ]

    # ── Identité ────────────────────────────────────────────
    reference       = models.CharField(max_length=30, unique=True, blank=True)
    titre           = models.CharField(max_length=255, help_text='Objet du devis')
    statut          = models.CharField(max_length=15, choices=STATUT, default='brouillon')
    source          = models.CharField(max_length=20, choices=SOURCE, default='direct')

    # ── Liens optionnels vers les autres modules ─────────────
    # Ces champs sont des IntegerField null pour éviter les imports circulaires.
    # Dans vos vues, résolvez-les avec get_object_or_404(Mission, pk=mission_id) etc.
    mission_id_ref  = models.IntegerField(null=True, blank=True,
                                           help_text='PK de la Mission liée (bureau_etude)')
    projet_id_ref   = models.IntegerField(null=True, blank=True,
                                           help_text='PK du Projet lié (construction)')

    # ── Client ───────────────────────────────────────────────
    client_nom      = models.CharField(max_length=200)
    client_adresse  = models.TextField(blank=True)
    client_tel      = models.CharField(max_length=30, blank=True)
    client_email    = models.EmailField(blank=True)
    maitre_ouvrage  = models.CharField(max_length=200, blank=True)

    # ── Chantier ─────────────────────────────────────────────
    adresse_chantier = models.TextField(blank=True)
    duree_chantier_mois = models.DecimalField(max_digits=5, decimal_places=1, default=6)

    # ── Mode de calcul main d'œuvre ──────────────────────────
    mode_mo         = models.CharField(max_length=10, choices=MODE_MO, default='horaire')

    # ── Coefficient K ────────────────────────────────────────
    taux_aleas      = models.DecimalField(max_digits=5, decimal_places=2, default=5,
                                          help_text='% d\'aléas et imprévus')
    taux_benefice   = models.DecimalField(max_digits=5, decimal_places=2, default=10,
                                          help_text='% de bénéfices')
    taux_tva        = models.DecimalField(max_digits=5, decimal_places=2, default=20,
                                          help_text='% TVA')

    # ── Montants calculés (mis à jour par save_totaux()) ─────
    montant_debourse_sec  = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    montant_ht            = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    montant_tva           = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    montant_ttc           = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    # ── Émetteur ─────────────────────────────────────────────
    emetteur_nom    = models.CharField(max_length=200, default='MOREX BTP')
    emetteur_adresse = models.TextField(blank=True)
    emetteur_tel    = models.CharField(max_length=30, blank=True)
    emetteur_email  = models.EmailField(blank=True)
    emetteur_nif    = models.CharField(max_length=50, blank=True, help_text='NIF / STAT')

    # ── Texte libre ──────────────────────────────────────────
    conditions      = models.TextField(blank=True, help_text='Conditions générales')
    notes           = models.TextField(blank=True)

    # ── Dates ────────────────────────────────────────────────
    date_devis      = models.DateField(default=timezone.now)
    date_validite   = models.DateField(null=True, blank=True)

    # ── PDF généré ───────────────────────────────────────────
    fichier_pdf     = models.FileField(upload_to=devis_pdf_path, null=True, blank=True)

    # ── Méta ─────────────────────────────────────────────────
    cree_par   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='devis_btp_crees')
    cree_le    = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Devis BTP'
        verbose_name_plural = 'Devis BTP'
        ordering            = ['-date_devis']

    def __str__(self):
        return f'[{self.reference}] {self.titre} — {self.client_nom}'

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            last  = Devis.objects.filter(reference__startswith=f'DV-{annee}-').count()
            self.reference = f'DV-{annee}-{last + 1:03d}'
        super().save(*args, **kwargs)

    @property
    def coefficient_k(self):
        """K = (1 + aleas) × (1 + benefice) × (1 + tva)"""
        return (
            (1 + float(self.taux_aleas) / 100) *
            (1 + float(self.taux_benefice) / 100) *
            (1 + float(self.taux_tva) / 100)
        )

    def save_totaux(self):
        """Recalcule et sauvegarde tous les montants du devis."""
        # Matériaux
        mat = sum(
            ligne.montant_materiaux
            for ligne in self.lignes_deps.all()
        )
        # Main d'œuvre
        if self.mode_mo == 'forfait':
            mo = float(
                self.taches_forfait.aggregate(t=Sum('montant_mo'))['t'] or 0
            )
        else:
            mo = sum(
                float(eq.taux_horaire) * float(eq.heures_total)
                for eq in self.equipes_phmo.all()
            )
        # Frais de chantier
        frais = float(
            self.frais_chantier.aggregate(t=Sum('montant'))['t'] or 0
        )

        ds = mat + mo + frais
        ht = ds * (1 + float(self.taux_aleas) / 100) * (1 + float(self.taux_benefice) / 100)
        tva_amt = ht * float(self.taux_tva) / 100
        ttc = ht + tva_amt

        Devis.objects.filter(pk=self.pk).update(
            montant_debourse_sec=round(ds, 2),
            montant_ht=round(ht, 2),
            montant_tva=round(tva_amt, 2),
            montant_ttc=round(ttc, 2),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  AVANT-MÉTRÉ
# ─────────────────────────────────────────────────────────────────────────────

class LigneAvantMetre(models.Model):
    """
    Ligne de calcul de l'avant-métré (surfaces, volumes, longueurs).
    Quantité partielle = NPS × L × l × H (selon unité)
    Quantité définitive (QAM) = somme des partiels ± déductions
    """
    UNITE = [
        ('m3', 'm³'), ('m2', 'm²'), ('ml', 'ml'),
        ('u',  'u'),  ('kg', 'kg'), ('sac', 'sac'),
        ('t',  'tonne'),
    ]

    SIGNE = [
        ('ajouter',  'À ajouter'),
        ('deduire',  'À déduire'),
    ]

    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='avant_metre')
    ouvrage_num = models.CharField(max_length=10, blank=True, help_text='ex. 101, 201')
    designation = models.CharField(max_length=255)
    repere      = models.CharField(max_length=30, blank=True, help_text='ex. s1, v1, sbp1')
    unite       = models.CharField(max_length=5, choices=UNITE, default='m3')
    signe       = models.CharField(max_length=10, choices=SIGNE, default='ajouter')

    # Dimensions
    nps         = models.DecimalField(max_digits=6, decimal_places=2, default=1,
                                       help_text='Nombre de pièces semblables')
    longueur    = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text='L (m)')
    largeur     = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text='l (m)')
    hauteur     = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text='H (m)')

    # Résultats (calculés)
    aux         = models.DecimalField(max_digits=12, decimal_places=4, default=0,
                                       editable=False, help_text='Résultat auxiliaire')
    partiel     = models.DecimalField(max_digits=12, decimal_places=4, default=0,
                                       editable=False, help_text='NPS × calcul')
    qam         = models.DecimalField(max_digits=14, decimal_places=4, default=0,
                                       editable=False, help_text='Quantité avant-métré définitive')

    ordre       = models.PositiveIntegerField(default=0)
    note        = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Ligne avant-métré'
        verbose_name_plural = 'Lignes avant-métré'
        ordering            = ['ordre', 'pk']

    def __str__(self):
        return f'{self.ouvrage_num} — {self.designation} [{self.unite}]'

    def save(self, *args, **kwargs):
        L = float(self.longueur)
        l = float(self.largeur)
        H = float(self.hauteur)
        N = float(self.nps)

        if self.unite == 'm3':
            self.aux     = round(L * l * H, 4) if (L and l and H) else round(L * l, 4)
            self.partiel = round(N * float(self.aux), 4)
        elif self.unite == 'm2':
            self.aux     = round(L * (l or H), 4)
            self.partiel = round(N * float(self.aux), 4)
        elif self.unite == 'ml':
            self.aux     = round(L, 4)
            self.partiel = round(N * L, 4)
        else:
            self.aux     = round(L, 4)
            self.partiel = round(N * L, 4)

        self.qam = -float(self.partiel) if self.signe == 'deduire' else float(self.partiel)
        super().save(*args, **kwargs)


class RecapAvantMetre(models.Model):
    """
    Ligne récapitulative de l'avant-métré, regroupée par ouvrage (QAM total).
    Générée automatiquement depuis les LigneAvantMetre.
    """
    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='recap_am')
    numero      = models.CharField(max_length=10, blank=True)
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=5, default='m3')
    qam         = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    dosage      = models.ForeignKey(Dosage, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text='Dosage associé pour le calcul des matériaux')
    ordre       = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Récap avant-métré'
        verbose_name_plural = 'Récap avant-métrés'
        ordering            = ['ordre', 'numero']
        unique_together     = [('devis', 'designation')]

    def __str__(self):
        return f'{self.numero} — {self.designation} : {self.qam} {self.unite}'

    @property
    def montant_materiaux_unitaire(self):
        """Coût matériaux pour 1 unité de cet ouvrage, basé sur le dosage."""
        if not self.dosage:
            return 0
        dos = self.dosage
        from .utils import get_materiaux_map
        mat_map = get_materiaux_map()
        total = 0
        total += float(dos.sable_m3)    * mat_map.get('sable', 0)
        total += float(dos.gravillon_m3)* mat_map.get('gravillon', 0)
        total += float(dos.eau_litres)  * mat_map.get('eau', 0)
        total += float(dos.ciment_kg)   * mat_map.get('ciment', 0)
        total += float(dos.chaux_kg)    * mat_map.get('chaux', 0)
        total += float(dos.acier_kg)    * mat_map.get('acier_ha', 0)
        total += float(dos.fil_recuit_kg) * mat_map.get('fil_recuit', 0)
        return round(total, 2)

    @property
    def montant_materiaux_total(self):
        return round(float(self.qam) * self.montant_materiaux_unitaire, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  NOMENCLATURE DES MATÉRIAUX (calculée)
# ─────────────────────────────────────────────────────────────────────────────

class LigneNomenclature(models.Model):
    """
    Ligne de la nomenclature : quantité d'un matériau donné
    pour un ouvrage donné (QAM × dosage).
    """
    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='nomenclature')
    recap_am    = models.ForeignKey(RecapAvantMetre, on_delete=models.CASCADE,
                                     related_name='nomenclature_lignes')
    materiau    = models.ForeignKey(Materiau, on_delete=models.CASCADE)
    quantite_nette = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    quantite_chute = models.DecimalField(max_digits=14, decimal_places=4, default=0,
                                          help_text='Quantité avec chute et perte')

    class Meta:
        verbose_name        = 'Ligne nomenclature'
        verbose_name_plural = 'Lignes nomenclature'
        unique_together     = [('devis', 'recap_am', 'materiau')]

    def __str__(self):
        return f'{self.recap_am.designation} × {self.materiau.code} = {self.quantite_chute}'


# ─────────────────────────────────────────────────────────────────────────────
#  PHMO — PRIX HORAIRE MAIN D'ŒUVRE
# ─────────────────────────────────────────────────────────────────────────────

class EquipePHMO(models.Model):
    """
    Équipe ou catégorie de main d'œuvre avec calcul du taux horaire.
    Taux horaire = salaire_chargé / (nb_jours_mois × heures_par_jour)
    """
    CATEGORIE = [
        ('P',  'P — Personnel de production'),
        ('H',  'H — Personnel hautement qualifié'),
        ('M',  'M — Maîtrise'),
        ('O',  'O — Ouvrier'),
        ('E',  'E — Employé'),
        ('C',  'C — Cadre'),
    ]

    devis           = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='equipes_phmo')
    designation     = models.CharField(max_length=200)
    categorie       = models.CharField(max_length=2, choices=CATEGORIE, default='O')

    salaire_base    = models.DecimalField(max_digits=12, decimal_places=2,
                                           help_text='Salaire de base mensuel brut (Ar)')
    taux_charges    = models.DecimalField(max_digits=5, decimal_places=2, default=22,
                                           help_text='Taux charges sociales patronales (%)')
    nb_jours_mois   = models.DecimalField(max_digits=4, decimal_places=1, default=26)
    heures_par_jour = models.DecimalField(max_digits=4, decimal_places=1, default=8)

    # Utilisé si mode_mo = 'horaire' : nombre d'heures total sur le chantier
    heures_total    = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text='Heures totales prévues sur le chantier')
    ordre           = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Équipe PHMO'
        verbose_name_plural = 'Équipes PHMO'
        ordering            = ['ordre', 'categorie']

    def __str__(self):
        return f'{self.get_categorie_display()} — {self.designation}'

    @property
    def salaire_charge(self):
        return float(self.salaire_base) * (1 + float(self.taux_charges) / 100)

    @property
    def heures_mois(self):
        return float(self.nb_jours_mois) * float(self.heures_par_jour)

    @property
    def taux_horaire(self):
        return round(self.salaire_charge / self.heures_mois, 2) if self.heures_mois > 0 else 0

    @property
    def cout_total(self):
        return round(self.taux_horaire * float(self.heures_total), 2)


class TacheForfaitMO(models.Model):
    """
    Tâche avec main d'œuvre forfaitaire (quand mode_mo = 'forfait').
    Le montant MO est saisi directement sans calcul horaire.
    """
    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='taches_forfait')
    numero      = models.CharField(max_length=10, blank=True)
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=20, default='fft')
    quantite    = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    pu_mo       = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                       help_text='Prix unitaire MO forfaitaire (Ar)')
    montant_mo  = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                       editable=False)
    ordre       = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Tâche forfait MO'
        verbose_name_plural = 'Tâches forfait MO'
        ordering            = ['ordre', 'pk']

    def __str__(self):
        return f'{self.designation} — {self.montant_mo} Ar'

    def save(self, *args, **kwargs):
        self.montant_mo = round(float(self.quantite) * float(self.pu_mo), 2)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  FRAIS DE CHANTIER
# ─────────────────────────────────────────────────────────────────────────────

class FraisChantier(models.Model):
    """
    Poste de frais de chantier : état-major, MO non productive, fonctionnement.
    """
    CATEGORIE = [
        ('etat_major',           'Coûts état-major du chantier'),
        ('mo_non_productive',    'Main d\'œuvre non productive'),
        ('fonctionnement',       'Dépenses de fonctionnement'),
    ]

    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='frais_chantier')
    categorie   = models.CharField(max_length=25, choices=CATEGORIE, default='fonctionnement')
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=30, default='mois')
    quantite    = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant     = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                       editable=False)
    ordre       = models.PositiveIntegerField(default=0)
    note        = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Frais de chantier'
        verbose_name_plural = 'Frais de chantier'
        ordering            = ['categorie', 'ordre']

    def __str__(self):
        return f'{self.get_categorie_display()} — {self.designation}'

    def save(self, *args, **kwargs):
        self.montant = round(float(self.quantite) * float(self.prix_unitaire), 2)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  DÉBOURSÉ SEC (DEPS) — tableau final par ouvrage
# ─────────────────────────────────────────────────────────────────────────────

class LigneDEPS(models.Model):
    """
    Ligne du tableau de déboursé sec.
    Synthèse par ouvrage : matériaux + main d'œuvre + frais ventilés.
    """
    devis       = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='lignes_deps')
    recap_am    = models.ForeignKey(RecapAvantMetre, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='lignes_deps')
    numero      = models.CharField(max_length=10, blank=True)
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=10, default='m3')
    qam         = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    pu_materiaux  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pu_mo         = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pu_frais      = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    montant_materiaux = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                             editable=False)
    montant_mo        = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                             editable=False)
    montant_frais     = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                             editable=False)
    montant_total     = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                             editable=False)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Ligne DEPS'
        verbose_name_plural = 'Lignes DEPS'
        ordering            = ['ordre', 'numero']

    def __str__(self):
        return f'{self.numero} — {self.designation} : {self.montant_total} Ar'

    def save(self, *args, **kwargs):
        q = float(self.qam)
        self.montant_materiaux = round(q * float(self.pu_materiaux), 2)
        self.montant_mo        = round(q * float(self.pu_mo), 2)
        self.montant_frais     = round(q * float(self.pu_frais), 2)
        self.montant_total     = round(
            float(self.montant_materiaux) + float(self.montant_mo) + float(self.montant_frais), 2
        )
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  BON DE COMMANDE MATÉRIAUX
# ─────────────────────────────────────────────────────────────────────────────

class BonCommandeMateriaux(models.Model):
    """
    Bon de commande matériaux généré depuis la nomenclature.
    """
    STATUT = [
        ('brouillon', 'Brouillon'),
        ('envoye',    'Envoyé'),
        ('valide',    'Validé'),
        ('livre',     'Livré'),
        ('annule',    'Annulé'),
    ]

    devis           = models.ForeignKey(Devis, on_delete=models.CASCADE,
                                         related_name='bons_commande')
    numero          = models.CharField(max_length=30, unique=True, blank=True)
    statut          = models.CharField(max_length=15, choices=STATUT, default='brouillon')
    fournisseur_nom = models.CharField(max_length=200)
    fournisseur_tel = models.CharField(max_length=30, blank=True)
    date_commande   = models.DateField(default=timezone.now)
    date_livraison_prevue = models.DateField(null=True, blank=True)
    lieu_livraison  = models.CharField(max_length=200, blank=True)
    montant_ht      = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    montant_ttc     = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    tva_pct         = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    note            = models.TextField(blank=True)
    cree_par        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cree_le         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Bon de commande matériaux'
        verbose_name_plural = 'Bons de commande matériaux'
        ordering            = ['-date_commande']

    def __str__(self):
        return f'{self.numero} — {self.fournisseur_nom}'

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            last  = BonCommandeMateriaux.objects.filter(
                numero__startswith=f'BCM-{annee}-').count()
            self.numero = f'BCM-{annee}-{last + 1:04d}'
        self.montant_ttc = round(
            float(self.montant_ht) * (1 + float(self.tva_pct) / 100), 2)
        super().save(*args, **kwargs)


class LigneBonCommande(models.Model):
    """Ligne de détail d'un bon de commande matériaux."""
    bon         = models.ForeignKey(BonCommandeMateriaux, on_delete=models.CASCADE,
                                     related_name='lignes')
    materiau    = models.ForeignKey(Materiau, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.CharField(max_length=255)
    unite       = models.CharField(max_length=20)
    quantite    = models.DecimalField(max_digits=10, decimal_places=3)
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=2)
    montant_ht  = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        self.montant_ht = round(float(self.quantite) * float(self.prix_unitaire), 2)
        super().save(*args, **kwargs)
        total = self.bon.lignes.aggregate(t=Sum('montant_ht'))['t'] or 0
        BonCommandeMateriaux.objects.filter(pk=self.bon_id).update(
            montant_ht=total,
            montant_ttc=round(float(total) * (1 + float(self.bon.tva_pct) / 100), 2)
        )
