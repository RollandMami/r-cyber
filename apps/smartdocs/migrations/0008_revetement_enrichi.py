from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartdocs', '0007_alter_revetementmur_nature_alter_revetementmur_piece'),
    ]

    operations = [
        # piece et nature sont déjà présents via 0007 — on n'y touche plus.
        # On ajoute uniquement type_revetement et on met à jour les meta.
        migrations.AddField(
            model_name='revetementmur',
            name='type_revetement',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('mur',     'Mur'),
                    ('sol',     'Sol'),
                    ('plafond', 'Plafond'),
                    ('autre',   'Autre'),
                ],
                default='mur',
            ),
        ),
        migrations.AlterModelOptions(
            name='revetementmur',
            options={
                'verbose_name':        'Revêtement',
                'verbose_name_plural': 'Revêtements',
                'ordering': ['etage__niveau', 'type_revetement', 'nom'],
            },
        ),
    ]
