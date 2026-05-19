"""
Service de conversion IFC → JSON enrichi.
Extrait : géométrie, étages, pièces (surfaces exactes), revêtements, équipements/ouvertures.
"""

import json
import os
import traceback

from django.core.files.base import ContentFile


# Mapping type IFC → catégorie équipement
IFC_TYPE_CATEGORIE = {
    'IfcDoor':     'ouverture',
    'IfcWindow':   'ouverture',
    'IfcSanitaryTerminal': 'sanitaire',
    'IfcFlowTerminal':     'sanitaire',
    'IfcFurnishingElement': 'mobilier',
    'IfcFurniture':         'mobilier',
    'IfcFlowSegment':       'mep',
    'IfcFlowFitting':       'mep',
    'IfcFlowController':    'mep',
    'IfcEnergyConversionDevice': 'mep',
    'IfcDistributionControlElement': 'mep',
    'IfcElectricAppliance': 'equipement',
    'IfcLightFixture':      'equipement',
    'IfcCurtainWall':       'ouverture',
}

IFC_COVERING_TYPES = {'IfcCovering', 'IfcWall', 'IfcWallStandardCase'}


def convertir_ifc_en_json(patrimoine):
    """
    Lit le fichier IFC, extrait géométrie + arborescence,
    peuple Etage/Piece/RevetementMur/EquipementOuverture,
    calcule la surface totale habitable exacte et sauvegarde le JSON.
    """
    from .models import Etage, Piece, RevetementMur, EquipementOuverture

    patrimoine.statut_conversion = 'en_cours'
    patrimoine.erreur_conversion = ''
    patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])

    try:
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.element as ifc_util
        import ifcopenshell.util.shape as ifc_shape
    except ImportError:
        patrimoine.statut_conversion = 'erreur'
        patrimoine.erreur_conversion = (
            'ifcopenshell non installé. Lancez : pip install ifcopenshell'
        )
        patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])
        return

    try:
        ifc_path  = patrimoine.fichier_ifc.path
        ifc_model = ifcopenshell.open(ifc_path)

        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, False)

        storeys = sorted(ifc_model.by_type('IfcBuildingStorey'),
                         key=lambda s: s.Elevation or 0)

        result = {
            'metadata': {
                'nom':    patrimoine.nom,
                'source': os.path.basename(ifc_path),
            },
            'etages': []
        }

        # Resync complet
        patrimoine.etages.all().delete()
        patrimoine.revetements.all().delete()
        patrimoine.equipements.all().delete()

        surface_totale_ifc = 0.0

        for idx, storey in enumerate(storeys):
            storey_guid = storey.GlobalId
            storey_nom  = storey.Name or f'Étage {idx}'
            elevation   = storey.Elevation or 0

            etage_obj = Etage.objects.create(
                patrimoine=patrimoine,
                nom=storey_nom,
                niveau=idx,
                ifc_guid=storey_guid,
            )

            etage_data = {
                'id':        etage_obj.pk,
                'ifc_guid':  storey_guid,
                'nom':       storey_nom,
                'niveau':    idx,
                'elevation': elevation,
                'pieces':    [],
                'geometrie': {'meshes': []},
            }

            # ── Espaces / pièces ─────────────────────────────────────────────
            espaces = [
                e for e in ifc_model.by_type('IfcSpace')
                if _get_storey(e, ifc_model) == storey
            ]
            for espace in espaces:
                # Cherche la surface nette (NetFloorArea ou Qto_SpaceBaseQuantities)
                surface = _get_surface_exacte(espace, ifc_util)
                if surface:
                    surface_totale_ifc += float(surface)

                piece_obj = Piece.objects.create(
                    etage=etage_obj,
                    nom=espace.Name or 'Pièce',
                    surface=surface,
                    ifc_guid=espace.GlobalId,
                    usage=espace.ObjectType or '',
                )
                etage_data['pieces'].append({
                    'id':       piece_obj.pk,
                    'ifc_guid': espace.GlobalId,
                    'nom':      piece_obj.nom,
                    'surface':  float(surface) if surface else None,
                    'usage':    piece_obj.usage,
                })

            # ── Éléments de l'étage ──────────────────────────────────────────
            elements = _get_elements_of_storey(ifc_model, storey)
            for element in elements:
                ifc_type = element.is_a()

                # Revêtements
                if ifc_type in IFC_COVERING_TYPES:
                    surf = _get_area_from_quantities(element, ifc_util)
                    mat  = _get_material(element, ifc_model)
                    RevetementMur.objects.create(
                        patrimoine=patrimoine,
                        etage=etage_obj,
                        nom=element.Name or ifc_type,
                        materiau=mat,
                        surface=surf,
                        ifc_guid=element.GlobalId,
                        type_ifc=ifc_type,
                    )

                # Équipements / ouvertures / sanitaires
                categorie = IFC_TYPE_CATEGORIE.get(ifc_type)
                if categorie:
                    EquipementOuverture.objects.create(
                        patrimoine=patrimoine,
                        etage=etage_obj,
                        nom=element.Name or ifc_type,
                        type_element=categorie,
                        type_ifc=ifc_type,
                        ifc_guid=element.GlobalId,
                        description=element.Description or '',
                    )

                # Géométrie 3D
                try:
                    shape  = ifcopenshell.geom.create_shape(settings, element)
                    geo    = shape.geometry
                    verts  = list(geo.verts)
                    indices = list(geo.faces)
                    etage_data['geometrie']['meshes'].append({
                        'ifc_guid': element.GlobalId,
                        'type_ifc': ifc_type,
                        'vertices': verts,
                        'indices':  indices,
                    })
                except Exception:
                    pass

            result['etages'].append(etage_data)

        # ── Surface totale habitable exacte ───────────────────────────────────
        if surface_totale_ifc > 0:
            import decimal
            patrimoine.surface_totale = decimal.Decimal(str(round(surface_totale_ifc, 2)))

        # ── Sérialise ─────────────────────────────────────────────────────────
        json_bytes = json.dumps(result, ensure_ascii=False).encode('utf-8')
        json_name  = os.path.splitext(os.path.basename(ifc_path))[0] + '.json'

        if patrimoine.fichier_json:
            try:
                os.remove(patrimoine.fichier_json.path)
            except FileNotFoundError:
                pass

        patrimoine.fichier_json.save(json_name, ContentFile(json_bytes), save=False)
        patrimoine.statut_conversion = 'ok'
        patrimoine.save(update_fields=['fichier_json', 'statut_conversion',
                                        'erreur_conversion', 'surface_totale'])

    except Exception as exc:
        patrimoine.statut_conversion = 'erreur'
        patrimoine.erreur_conversion = traceback.format_exc()
        patrimoine.save(update_fields=['statut_conversion', 'erreur_conversion'])
        raise exc


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_surface_exacte(espace, ifc_util):
    """
    Retourne la surface nette exacte d'un IfcSpace.
    Priorité : Qto_SpaceBaseQuantities > BaseQuantities > toute quantité area/surface.
    """
    try:
        psets = ifc_util.get_psets(espace, qtos_only=True)
        # Priorité aux jeux de quantités standards ArchiCAD
        for qset_name in ('Qto_SpaceBaseQuantities', 'BaseQuantities', 'ArchiCAD Properties'):
            if qset_name in psets:
                qset = psets[qset_name]
                for k in ('NetFloorArea', 'GrossFloorArea', 'NetArea', 'GrossArea',
                           'Area', 'NetFloorAreaWithSlab'):
                    if k in qset:
                        try:
                            return float(qset[k])
                        except (TypeError, ValueError):
                            pass
        # Fallback : n'importe quelle quantité avec "area" ou "surface"
        for qset in psets.values():
            for k, v in qset.items():
                if 'area' in k.lower() or 'surface' in k.lower():
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass
    return None


def _get_area_from_quantities(element, ifc_util):
    """Extrait une surface depuis les Qtos d'un élément."""
    try:
        psets = ifc_util.get_psets(element, qtos_only=True)
        for qset in psets.values():
            for k, v in qset.items():
                if 'area' in k.lower() or 'surface' in k.lower():
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass
    return None


def _get_material(element, ifc_model):
    """Tente de récupérer le nom du matériau principal d'un élément."""
    try:
        for assoc in ifc_model.by_type('IfcRelAssociatesMaterial'):
            if element in assoc.RelatedObjects:
                mat = assoc.RelatingMaterial
                if hasattr(mat, 'Name') and mat.Name:
                    return mat.Name
                if mat.is_a('IfcMaterialLayerSetUsage'):
                    layers = mat.ForLayerSet.MaterialLayers
                    names = [l.Material.Name for l in layers if l.Material and l.Material.Name]
                    return ', '.join(names)
    except Exception:
        pass
    return ''


def _get_storey(element, ifc_model):
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if element in rel.RelatedElements:
            if rel.RelatingStructure.is_a('IfcBuildingStorey'):
                return rel.RelatingStructure
    return None


def _get_elements_of_storey(ifc_model, storey):
    elements = []
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure == storey:
            for el in rel.RelatedElements:
                if el.is_a() in (
                    'IfcWall', 'IfcWallStandardCase', 'IfcSlab',
                    'IfcColumn', 'IfcBeam', 'IfcRoof', 'IfcFooting',
                    'IfcPile', 'IfcMember', 'IfcCurtainWall',
                    'IfcDoor', 'IfcWindow',
                    'IfcStair', 'IfcStairFlight', 'IfcRamp', 'IfcRampFlight',
                    'IfcCovering',
                    'IfcSanitaryTerminal', 'IfcFlowTerminal',
                    'IfcFlowSegment', 'IfcFlowFitting', 'IfcFlowController',
                    'IfcEnergyConversionDevice', 'IfcDistributionControlElement',
                    'IfcElectricAppliance', 'IfcLightFixture',
                    'IfcFurnishingElement', 'IfcFurniture',
                    'IfcBuildingElementProxy',
                ):
                    elements.append(el)
    return elements
