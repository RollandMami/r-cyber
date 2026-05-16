"""
Service de conversion IFC → JSON.
Dépendance : ifcopenshell  (pip install ifcopenshell)

Le JSON produit a la structure suivante :
{
  "metadata": { "nom": "...", "source": "fichier.ifc" },
  "etages": [
    {
      "ifc_guid": "...",
      "nom": "...",
      "niveau": 0,
      "pieces": [
        { "ifc_guid": "...", "nom": "...", "surface": 12.5, "usage": "Bureau" }
      ],
      "geometrie": {
        "meshes": [
          {
            "ifc_guid": "...",
            "type_ifc": "IfcWall",
            "vertices": [...],   // flat Float32Array → liste Python
            "indices":  [...]
          }
        ]
      }
    }
  ]
}
"""

import json
import os
import tempfile
import traceback

from django.core.files.base import ContentFile


def convertir_ifc_en_json(patrimoine):
    """
    Lit le fichier IFC du patrimoine, extrait la géométrie et l'arborescence,
    écrit le résultat dans patrimoine.fichier_json et met à jour le statut.
    Crée ou met à jour aussi les objets Etage / Piece en base.
    """
    from apps.smartdocs.models import Etage, Piece

    patrimoine.statut_conversion  = 'en_cours'
    patrimoine.erreur_conversion  = ''
    patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])

    try:
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.element as ifc_util
    except ImportError:
        patrimoine.statut_conversion = 'erreur'
        patrimoine.erreur_conversion = (
            'ifcopenshell non installé. '
            'Lancez : pip install ifcopenshell'
        )
        patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])
        return

    try:
        # ── 1. Ouvre le fichier IFC ──────────────────────────────────
        ifc_path = patrimoine.fichier_ifc.path
        ifc_model = ifcopenshell.open(ifc_path)

        # ── 2. Paramètres de tesselation ────────────────────────────
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, False)

        # ── 3. Récupère les étages (IfcBuildingStorey) ───────────────
        storeys = ifc_model.by_type('IfcBuildingStorey')
        storeys_sorted = sorted(storeys, key=lambda s: s.Elevation or 0)

        result = {
            'metadata': {
                'nom':    patrimoine.nom,
                'source': os.path.basename(ifc_path),
            },
            'etages': []
        }

        # Supprime les étages existants (resync complet)
        patrimoine.etages.all().delete()

        for idx, storey in enumerate(storeys_sorted):
            storey_guid = storey.GlobalId
            storey_nom  = storey.Name or f'Étage {idx}'
            elevation   = storey.Elevation or 0

            # Convertit élévation en numéro de niveau relatif
            niveau = idx  # 0 = RDC par défaut, on affinera si besoin

            # Crée l'étage en base
            etage_obj = Etage.objects.create(
                patrimoine = patrimoine,
                nom        = storey_nom,
                niveau     = niveau,
                ifc_guid   = storey_guid,
            )

            etage_data = {
                'id':       etage_obj.pk,
                'ifc_guid': storey_guid,
                'nom':      storey_nom,
                'niveau':   niveau,
                'elevation': elevation,
                'pieces':   [],
                'geometrie': {'meshes': []},
            }

            # ── 4. Espaces / pièces de cet étage ────────────────────
            espaces = [
                e for e in ifc_model.by_type('IfcSpace')
                if _get_storey(e, ifc_model) == storey
            ]
            for espace in espaces:
                surface = None
                for qset in ifc_util.get_psets(espace).values():
                    for k, v in qset.items():
                        if 'area' in k.lower() or 'surface' in k.lower():
                            try:
                                surface = float(v)
                            except (TypeError, ValueError):
                                pass

                piece_obj = Piece.objects.create(
                    etage    = etage_obj,
                    nom      = espace.Name or 'Pièce',
                    surface  = surface,
                    ifc_guid = espace.GlobalId,
                    usage    = espace.ObjectType or '',
                )
                etage_data['pieces'].append({
                    'id':       piece_obj.pk,
                    'ifc_guid': espace.GlobalId,
                    'nom':      piece_obj.nom,
                    'surface':  surface,
                    'usage':    piece_obj.usage,
                })

            # ── 5. Géométrie des éléments de cet étage ──────────────
            elements = _get_elements_of_storey(ifc_model, storey)
            for element in elements:
                try:
                    shape = ifcopenshell.geom.create_shape(settings, element)
                except Exception:
                    continue

                geo = shape.geometry
                verts   = list(geo.verts)    # [x,y,z, x,y,z, ...]
                indices = list(geo.faces)    # [i0,i1,i2, ...]

                etage_data['geometrie']['meshes'].append({
                    'ifc_guid': element.GlobalId,
                    'type_ifc': element.is_a(),
                    'vertices': verts,
                    'indices':  indices,
                })

            result['etages'].append(etage_data)

        # ── 6. Sérialise et sauvegarde ───────────────────────────────
        json_bytes = json.dumps(result, ensure_ascii=False).encode('utf-8')
        json_name  = os.path.splitext(os.path.basename(ifc_path))[0] + '.json'

        if patrimoine.fichier_json:
            try:
                os.remove(patrimoine.fichier_json.path)
            except FileNotFoundError:
                pass

        patrimoine.fichier_json.save(json_name, ContentFile(json_bytes), save=False)
        patrimoine.statut_conversion = 'ok'
        patrimoine.save(update_fields=['fichier_json', 'statut_conversion', 'erreur_conversion'])

    except Exception as exc:
        patrimoine.statut_conversion = 'erreur'
        patrimoine.erreur_conversion = traceback.format_exc()
        patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])
        raise exc


# ── Helpers internes ─────────────────────────────────────────

def _get_storey(element, ifc_model):
    """Remonte la hiérarchie IFC pour trouver le IfcBuildingStorey parent."""
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if element in rel.RelatedElements:
            if rel.RelatingStructure.is_a('IfcBuildingStorey'):
                return rel.RelatingStructure
    return None


def _get_elements_of_storey(ifc_model, storey):
    """Retourne tous les éléments contenus dans un étage donné."""
    elements = []
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure == storey:
            for el in rel.RelatedElements:
                if el.is_a() in (
                    'IfcWall', 'IfcWallStandardCase', 'IfcSlab',
                    'IfcColumn', 'IfcBeam', 'IfcDoor', 'IfcWindow',
                    'IfcStair', 'IfcRoof', 'IfcCovering',
                ):
                    elements.append(el)
    return elements
