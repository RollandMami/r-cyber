from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartdocs', '0002_site_ged_elements'),
    ]

    operations = [
        # Nouveaux champs sur EquipementOuverture
        migrations.AddField(
            model_name='equipementouverture',
            name='nomenclature',
            field=models.CharField(max_length=300, blank=True,
                                   help_text='Nom lisible humain (ex: Porte int. bois, Fenêtre oscillo-battant)'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='largeur',
            field=models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       help_text='mm'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='hauteur',
            field=models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       help_text='mm'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='longueur',
            field=models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       help_text='mm — pour sanitaires / mobilier'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='marque',
            field=models.CharField(max_length=150, blank=True),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='vitrage',
            field=models.CharField(max_length=100, blank=True,
                                    help_text='Ex: Simple vitrage, Double vitrage, Triple vitrage'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='puissance',
            field=models.CharField(max_length=50, blank=True,
                                    help_text='Ex: 60W, 2×36W — pour appareils électriques'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='materiau',
            field=models.CharField(max_length=150, blank=True,
                                    help_text='Ex: Bois, PVC, Aluminium, Acier inox'),
        ),
        migrations.AddField(
            model_name='equipementouverture',
            name='reference',
            field=models.CharField(max_length=100, blank=True,
                                    help_text='Référence fabricant / code article'),
        ),
    ]
