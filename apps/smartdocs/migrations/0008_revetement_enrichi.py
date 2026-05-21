from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('smartdocs', '0003_equipement_details'),
    ]

    operations = [
        # Renomme le modèle (on garde la table, on ajoute des champs)
        migrations.AddField(
            model_name='revetementmur',
            name='piece',
            field=models.ForeignKey(
                'smartdocs.Piece', on_delete=django.db.models.deletion.SET_NULL,
                null=True, blank=True, related_name='revetements',
                help_text='Pièce / zone concernée'
            ),
        ),
        migrations.AddField(
            model_name='revetementmur',
            name='type_revetement',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('mur',      'Mur'),
                    ('sol',      'Sol'),
                    ('plafond',  'Plafond'),
                    ('autre',    'Autre'),
                ],
                default='mur',
            ),
        ),
        migrations.AddField(
            model_name='revetementmur',
            name='nature',
            field=models.CharField(
                max_length=150, blank=True,
                help_text='Ex: Carrelage, Parquet, Enduit, Peinture, Faux-plafond…'
            ),
        ),
        migrations.AlterModelOptions(
            name='revetementmur',
            options={
                'verbose_name': 'Revêtement',
                'verbose_name_plural': 'Revêtements',
                'ordering': ['etage__niveau', 'type_revetement', 'nom'],
            },
        ),
    ]
