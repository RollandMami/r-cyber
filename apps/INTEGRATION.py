# SmartDocs & Viewer — Instructions d'intégration
# ===================================================

# 1. DÉPENDANCES
# --------------
# pip install ifcopenshell Pillow

# 2. SETTINGS.PY — ajouter dans INSTALLED_APPS
# ----------------------------------------------
INSTALLED_APPS = [
    # ... apps existantes ...
    'smartdocs.apps.SmartdocsConfig',
    'viewer.apps.ViewerConfig',
]

# MEDIA (si pas déjà configuré)
import os
MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 3. URLS.PY PRINCIPAL (core/urls.py ou rcyber/urls.py)
# ------------------------------------------------------
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... urls existantes ...
    path('patrimoines/', include('smartdocs.urls')),
    path('viewer/',      include('viewer.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 4. MIGRATIONS
# -------------
# python manage.py makemigrations smartdocs viewer
# python manage.py migrate

# 5. DONNÉES INITIALES — Types de documents
# ------------------------------------------
# Dans le shell Django (python manage.py shell) :
#
# from smartdocs.models import TypeDocument
# types = [
#     ('Plan',          'fa-drafting-compass', 1),
#     ('Photo',         'fa-camera',           2),
#     ('Maquette',      'fa-cube',             3),
#     ('Notice',        'fa-book',             4),
#     ('Devis',         'fa-file-invoice',     5),
#     ('PV',            'fa-file-signature',   6),
#     ('Rapport',       'fa-file-alt',         7),
#     ('Contrat',       'fa-file-contract',    8),
# ]
# for nom, icone, ordre in types:
#     TypeDocument.objects.get_or_create(nom=nom, defaults={'icone': icone, 'ordre': ordre})

# 6. STRUCTURE DES FICHIERS CRÉÉS
# --------------------------------
# smartdocs/
#   models.py      → Patrimoine, Etage, Piece, TypeDocument, Document
#   views.py       → CRUD patrimoines + documents + API arborescence
#   services.py    → Conversion IFC → JSON (ifcopenshell)
#   forms.py       → PatrimoineForm, DocumentForm
#   admin.py       → Interface admin complète
#   urls.py        → Routes
#   templates/smartdocs/
#     patrimoine_list.html
#     patrimoine_detail.html
#     patrimoine_form.html
#     document_form.html
#
# viewer/
#   models.py      → ViewerSession (optionnel)
#   views.py       → viewer() + api_geometrie()
#   urls.py        → Routes
#   templates/viewer/
#     viewer.html  → Interface Three.js + panneau arborescence
#     no_model.html
#   static/viewer/js/
#     viewer.js    → Moteur Three.js (orbite, filtres, raycasting)

# 7. FLUX COMPLET
# ---------------
# Upload IFC → services.convertir_ifc_en_json() → JSON stocké dans media/
# → Viewer charge le JSON → Three.js construit la scène
# → Panneau droit : clic étage → filtrerEtage() → masque les autres étages
# → Clic pièce → filtrerPiece() → isole la pièce par ifc_guid
