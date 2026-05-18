from django.db import models


class AppVersion(models.Model):
    """
    Gère les versions de l'application Android.
    Le serveur expose /api/version/ qui retourne la dernière version.
    """
    version         = models.CharField(max_length=20, unique=True)   # ex. "1.2.0"
    version_code    = models.PositiveIntegerField(unique=True)        # entier croissant ex. 10200
    apk_file        = models.FileField(upload_to='releases/', null=True, blank=True)
    apk_url_externe = models.URLField(blank=True, help_text='URL externe si APK hébergé ailleurs')
    changelog       = models.TextField(blank=True, help_text='Notes de version (HTML ou texte)')
    est_active      = models.BooleanField(default=True, help_text='Seule la version active est retournée par l\'API')
    publiee_le      = models.DateTimeField(auto_now_add=True)
    obligatoire     = models.BooleanField(default=False, help_text='Si True, force la mise à jour')

    class Meta:
        verbose_name        = 'Version application'
        verbose_name_plural = 'Versions application'
        ordering            = ['-version_code']

    def __str__(self):
        return f'v{self.version} (code {self.version_code})'

    def get_apk_url(self):
        if self.apk_url_externe:
            return self.apk_url_externe
        if self.apk_file:
            return self.apk_file.url
        return None