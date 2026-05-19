# Migration manuelle — ajoute Site, DocumentGED, RevetementMur, EquipementOuverture
# et le FK site sur Patrimoine

import django.db.models.deletion
import apps.smartdocs.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartdocs', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Site ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200)),
                ('adresse', models.CharField(blank=True, max_length=300)),
                ('description', models.TextField(blank=True)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='sites/photos/')),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('modifie_le', models.DateTimeField(auto_now=True)),
                ('cree_par', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                               related_name='sites', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Site', 'verbose_name_plural': 'Sites', 'ordering': ['-cree_le']},
        ),

        # ── FK site sur Patrimoine ─────────────────────────────────────────────
        migrations.AddField(
            model_name='patrimoine',
            name='site',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                     related_name='batiments', to='smartdocs.site'),
        ),

        # ── RevetementMur ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='RevetementMur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200)),
                ('materiau', models.CharField(blank=True, max_length=200)),
                ('surface', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('ifc_guid', models.CharField(blank=True, max_length=100)),
                ('type_ifc', models.CharField(blank=True, max_length=100)),
                ('patrimoine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='revetements', to='smartdocs.patrimoine')),
                ('etage', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                             related_name='revetements', to='smartdocs.etage')),
            ],
            options={'verbose_name': 'Revêtement mur', 'ordering': ['etage__niveau', 'nom']},
        ),

        # ── EquipementOuverture ────────────────────────────────────────────────
        migrations.CreateModel(
            name='EquipementOuverture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200)),
                ('type_element', models.CharField(choices=[
                    ('ouverture', 'Ouverture (porte / fenêtre)'),
                    ('sanitaire', 'Sanitaire'),
                    ('equipement', 'Équipement'),
                    ('mep', 'MEP / Technique'),
                    ('mobilier', 'Mobilier'),
                    ('autre', 'Autre'),
                ], default='autre', max_length=20)),
                ('type_ifc', models.CharField(blank=True, max_length=100)),
                ('quantite', models.PositiveIntegerField(default=1)),
                ('ifc_guid', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('patrimoine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='equipements', to='smartdocs.patrimoine')),
                ('etage', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                             related_name='equipements', to='smartdocs.etage')),
            ],
            options={'verbose_name': 'Équipement / Ouverture', 'ordering': ['etage__niveau', 'type_element', 'nom']},
        ),

        # ── DocumentGED ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name='DocumentGED',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('corps', models.CharField(choices=[('CEA', 'CEA'), ('CET', 'CET')], max_length=10)),
                ('dossier', models.CharField(help_text='Clé du sous-dossier (ex: plans_niveau)', max_length=100)),
                ('titre', models.CharField(max_length=255)),
                ('fichier', models.FileField(upload_to=apps.smartdocs.models.ged_upload_path)),
                ('description', models.TextField(blank=True)),
                ('version', models.CharField(blank=True, max_length=20)),
                ('date_doc', models.DateField(blank=True, null=True)),
                ('uploade_le', models.DateTimeField(auto_now_add=True)),
                ('patrimoine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='documents_ged', to='smartdocs.patrimoine')),
                ('uploade_par', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                   to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Document GED', 'verbose_name_plural': 'Documents GED',
                     'ordering': ['corps', 'dossier', '-uploade_le']},
        ),
    ]
