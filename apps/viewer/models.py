from django.db import models
from apps.smartdocs.models import Patrimoine


class ViewerSession(models.Model):
    """
    Optionnel — permet de sauvegarder la position caméra et les filtres actifs
    d'une session viewer pour un patrimoine donné.
    """
    patrimoine   = models.ForeignKey(Patrimoine, on_delete=models.CASCADE, related_name='sessions_viewer')
    etage_actif  = models.IntegerField(null=True, blank=True, help_text='pk de l\'étage filtré, null = tout afficher')
    camera_state = models.JSONField(default=dict, blank=True, help_text='Position/orientation caméra Three.js')
    cree_le      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Session viewer'
        verbose_name_plural = 'Sessions viewer'
        ordering            = ['-cree_le']

    def __str__(self):
        return f'Session viewer — {self.patrimoine.nom}'
