"""
MOREX Devis BTP — management/commands/load_devis_data.py
Commande Django pour charger les données initiales (matériaux + dosages).
Usage : python manage.py load_devis_data
"""

from django.core.management.base import BaseCommand
from devis_btp.models import Materiau, Dosage


MATERIAUX = [
    # code, designation, unite, prix_fourn, manutention, transport, taux_chute
    ('MAT-01', 'Moellon',         'u',    650,    50,   150,  2),
    ('MAT-02', 'Caillasse',       'm3',  32000,  3000,  5100, 1),
    ('MAT-03', 'Sable',           'm3',  17000,  2500,  3500, 6),
    ('MAT-04', 'Gravillon',       'm3',  52000,  3500,  5500, 5),
    ('MAT-05', 'Eau',             'm3',      0,   500,   900, 3),
    ('MAT-06', 'Pointe',          'Kg',   5200,    50,   350, 2),
    ('MAT-07', 'Fer rond',        'Kg',   5200,   500,  1300, 6),
    ('MAT-08', 'Fil recuit',      'Kg',   4300,    50,   200, 3),
    ('MAT-09', 'Ciment',          'sac',  3200,  2500, 16500, 3),
    ('MAT-10', 'Planche',         'u',    4250,   150,   500, 6),
    ('MAT-11', 'Bois rond',       'u',    3150,   150,   500, 6),
    ('MAT-12', 'Bois carré',      'u',    3650,   150,   500, 6),
    ('MAT-13', 'Brique',          'u',     100,    30,    70, 5),
    ('MAT-14', 'Mortier préparé', 'm3',  25000,  2000,  4000, 5),
    ('MAT-15', 'Acier HA',        'Kg',   5500,   500,  1300, 6),
    ('MAT-16', 'Chaux hydraulique','Kg',  1200,   100,   300, 3),
    ('MAT-17', 'Carrelage',       'm2',  12000,   800,  2000, 8),
    ('MAT-18', 'Colle carrelage', 'sac',  2500,   200,   500, 5),
    ('MAT-19', 'Joint carrelage', 'sac',  1800,   150,   350, 5),
    ('MAT-20', 'Peinture',        'L',    4500,   300,   600, 10),
]

DOSAGES = [
    # code, categorie, dosage_kg, choix_liant, sable_m3, gravillon_m3, eau_l, ciment_kg, chaux_kg, acier_kg
    ('BO-01', 'BETON',  200, 'CPA 250/315',    0.70, 0.40, 170, 200, 0,   0),
    ('BO-02', 'BETON',  250, 'CPA 250/315',    0.65, 0.40, 170, 250, 0,   0),
    ('BO-03', 'BETON',  250, 'CPA',            0.00, 0.00, 170, 250, 0,   0),
    ('BO-04', 'BETON',  300, 'CPA 250/315',    0.70, 0.45, 170, 300, 0,   0),
    ('BO-05', 'BETON',  300, 'CPA 250/315',    0.00, 0.80, 170, 300, 0,   0),
    ('BO-06', 'BETON',  350, 'CPA 250/315',    0.00, 0.85, 170, 350, 0,   0),
    ('BO-07', 'BETON',  400, 'CPA 250/315',    0.00, 0.85, 170, 400, 0,   0),
    ('BO-5S', 'BETON',  350, 'CS 355/500',     0.00, 0.85, 170, 350, 0,   0),
    ('BO-5H', 'BETON',  300, 'CHRI 315/400',   0.00, 0.80, 170, 300, 0,   0),
    ('HR-01', 'BETON',  350, 'Hérrissonage',   0.00, 1.20,   0,   0, 0,   0),
    ('MR-01', 'MORTIER',250, 'CHAUX XEH 30/60',1.00, 0.00, 200,   0, 250, 0),
    ('MR-02', 'MORTIER',300, 'CPA 160/250',    1.00, 0.00, 200, 300, 0,   0),
    ('MR-03', 'MORTIER',350, 'CHAUX XEH 30/60',1.00, 0.00, 200,   0, 350, 0),
    ('MR-04', 'MORTIER',350, 'CPA 160/250',    1.00, 0.00, 200, 350, 0,   0),
    ('MR-05', 'MORTIER',450, 'CPA 250/315',    1.00, 0.00, 200, 450, 0,   0),
    ('MR-06', 'MORTIER',500, 'CPA 250/315',    1.00, 0.00, 200, 500, 0,   0),
    ('MR-07', 'MORTIER',600, 'CPA 250/315',    1.00, 0.00, 200, 600, 0,   0),
    ('MR-08', 'MORTIER',750, 'CPA 250/315',    1.00, 0.00, 200, 750, 0,   0),
    ('MR-09', 'MORTIER',275, 'CPA 160/250',    1.00, 0.00, 200, 275, 0,   0),
    ('MB-01', 'MORTIER',300, 'Maçonnerie brique 22cm', 0.50, 0.00, 200, 300, 0, 0),
    ('MB-02', 'MORTIER',300, 'Maçonnerie brique 15cm', 0.50, 0.00, 200, 300, 0, 0),
    ('MM-01', 'MORTIER',350, 'Hérrissonage moellon',   0.00, 0.00, 150,   0, 0, 0),
]


class Command(BaseCommand):
    help = 'Charge les données initiales MOREX Devis BTP (matériaux + dosages)'

    def handle(self, *args, **options):
        created_mat = 0
        for row in MATERIAUX:
            obj, created = Materiau.objects.get_or_create(
                code=row[0],
                defaults={
                    'designation':        row[1],
                    'unite':              row[2],
                    'prix_fournisseur':   row[3],
                    'frais_manutention':  row[4],
                    'frais_transport':    row[5],
                    'taux_chute':         row[6],
                }
            )
            if created:
                created_mat += 1

        created_dos = 0
        for row in DOSAGES:
            obj, created = Dosage.objects.get_or_create(
                code=row[0],
                defaults={
                    'categorie':    row[1],
                    'dosage_kg':    row[2],
                    'choix_liant':  row[3],
                    'sable_m3':     row[4],
                    'gravillon_m3': row[5],
                    'eau_litres':   row[6],
                    'ciment_kg':    row[7],
                    'chaux_kg':     row[8],
                    'acier_kg':     row[9],
                }
            )
            if created:
                created_dos += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ {created_mat} matériaux créés, {created_dos} dosages créés.'
        ))
        self.stdout.write(
            f'  Total : {Materiau.objects.count()} matériaux, {Dosage.objects.count()} dosages en base.'
        )
