"""
Migration manuelle — ajoute le champ service_tag au modèle Projet.

Copie ce fichier dans :
apps/construction/migrations/00XX_add_service_tag.py
(remplace 00XX par le prochain numéro de migration)

Puis lance : python manage.py migrate
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    # Remplace '0001_initial' par la dernière migration de l'app construction
    dependencies = [
        ('construction', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projet',
            name='service_tag',
            field=models.CharField(
                max_length=30,
                blank=True,
                default='construction',
                choices=[
                    ('btp',          'Bureau d\'étude BTP'),
                    ('construction', 'Construction'),
                    ('info-dev',     'Info-Dev Web/Python'),
                    ('cybercafe',    'Cybercafé'),
                    ('gaming',       'Gaming'),
                    ('studio',       'Studio Son'),
                    ('multiservice', 'Multi-Service'),
                ],
                verbose_name='Service associé',
                help_text='Slug du service auquel ce projet est rattaché pour l\'affichage vitrine.',
            ),
        ),
    ]
