"""
Service de conversion IFC → JSON enrichi.
Extrait : géométrie, étages, pièces (surfaces exactes), revêtements,
          équipements/ouvertures avec nomenclature, dimensions, vitrage, puissance.
"""

import json, os, traceback, decimal
from django.core.files.base import ContentFile


# ── Mapping type IFC → catégorie ─────────────────────────────────────────────
IFC_TYPE_CATEGORIE = {
    'IfcDoor':                           'ouverture',
    'IfcWindow':                         'ouverture',
    'IfcCurtainWall':                    'ouverture',
    'IfcSanitaryTerminal':               'sanitaire',
    'IfcFlowTerminal':                   'sanitaire',
    'IfcFurnishingElement':              'mobilier',
    'IfcFurniture':                      'mobilier',
    'IfcFlowSegment':                    'mep',
    'IfcFlowFitting':                    'mep',
    'IfcFlowController':                 'mep',
    'IfcEnergyConversionDevice':         'mep',
    'IfcDistributionControlElement':     'mep',
    'IfcElectricAppliance':              'electrique',
    'IfcLightFixture':                   'electrique',
    'IfcProtectiveDevice':               'electrique',
    'IfcRailing':                        'protection',
    'IfcBuildingElementProxy':           'autre',
}

IFC_COVERING_TYPES = {'IfcCovering', 'IfcWall', 'IfcWallStandardCase'}

# ── Noms de type IFC → nomenclature lisible par défaut ───────────────────────
# ArchiCAD génère souvent des noms comme "DOO-001" → on essaie d'abord ObjectType/Description
IFC_NOMENCLATURE_DEFAULT = {
    'IfcDoor':           'Porte',
    'IfcWindow':         'Fenêtre',
    'IfcCurtainWall':    'Mur-rideau',
    'IfcSanitaryTerminal': 'Appareil sanitaire',
    'IfcFlowTerminal':   'Terminal fluide',
    'IfcLightFixture':   'Luminaire',
    'IfcElectricAppliance': 'Appareil électrique',
    'IfcProtectiveDevice':  'Protection électrique',
    'IfcRailing':        'Garde-corps / Main courante',
    'IfcFurnishingElement': 'Mobilier',
    'IfcFurniture':      'Mobilier',
    'IfcBuildingElementProxy': 'Élément générique',
}

# Mots-clés ArchiCAD dans ObjectType → nomenclature enrichie
NOMENCLATURE_KEYWORDS = {
    # Portes
    'single': 'Porte simple vantail',
    'double': 'Porte double vantaux',
    'swing':  'Porte battante',
    'sliding': 'Porte coulissante',
    'folding': 'Porte pliante',
    'revolving': 'Porte tournante',
    'overhead': 'Porte relevable',
    'garage':  'Porte de garage',
    'interior': 'Porte intérieure',
    'exterior': 'Porte extérieure',
    'fire':    'Porte coupe-feu',
    'entrance': 'Porte d\'entrée',
    'asymmetric': 'Porte double vantaux asymétriques',
    'transom': 'Porte avec imposte',
    'sidelight': 'Porte avec imposte latérale',
    # Fenêtres
    'casement': 'Fenêtre à battant',
    'tilt': 'Fenêtre oscillo-battant',
    'awning': 'Fenêtre à soufflet',
    'fixed': 'Fenêtre fixe',
    'hopper': 'Fenêtre à soufflet (basculante)',
    'jalousie': 'Fenêtre jalousie',
    'bay': 'Fenêtre en baie',
    'bow': 'Fenêtre en arc',
    'skylight': 'Fenêtre de toit / Velux',
    'roof': 'Fenêtre de toit',
    'sill': 'Fenêtre avec allège',
    'allege': 'Fenêtre avec allège',
    # Sanitaires
    'sink': 'Évier',
    'basin': 'Lavabo',
    'washbasin': 'Lavabo',
    'bathtub': 'Baignoire',
    'bath':  'Baignoire',
    'shower': 'Douche',
    'toilet': 'WC / Toilette',
    'wc':    'WC / Toilette',
    'bidet': 'Bidet',
    'urinal': 'Urinoir',
    'evier': 'Évier',
    'baignoire': 'Baignoire',
    'lavabo': 'Lavabo',
    # Éclairage
    'spot':   'Spot encastré',
    'downlight': 'Spot encastré',
    'ceiling': 'Plafonnier',
    'pendant': 'Suspension',
    'wall lamp': 'Applique murale',
    'strip':  'Réglette fluorescente',
    'tube':   'Tube fluorescent',
    'led':    'Luminaire LED',
    # Garde-corps
    'railing': 'Garde-corps',
    'handrail': 'Main courante',
    'balustrade': 'Balustrade',
    'guard': 'Garde-corps',
}


def _build_nomenclature(element, ifc_type):
    """
    Construit une nomenclature lisible depuis les propriétés ArchiCAD de l'élément.
    Priorité : Name > ObjectType > Description > type par défaut.
    """
    # 1. ObjectType souvent le plus descriptif dans ArchiCAD
    obj_type = (getattr(element, 'ObjectType', None) or '').strip()
    description = (getattr(element, 'Description', None) or '').strip()
    name = (getattr(element, 'Name', None) or '').strip()

    # Cherche dans les keywords
    for candidate in [obj_type, description, name]:
        if not candidate:
            continue
        low = candidate.lower()
        for kw, label in NOMENCLATURE_KEYWORDS.items():
            if kw in low:
                # Compléter avec le matériau si présent
                return label
        # Si le nom n'est pas un ID (pas de chiffres dominants), l'utiliser tel quel
        alpha_ratio = sum(c.isalpha() for c in candidate) / max(len(candidate), 1)
        if alpha_ratio > 0.4 and len(candidate) > 3:
            return candidate

    return IFC_NOMENCLATURE_DEFAULT.get(ifc_type, name or ifc_type)


def _extract_dimensions(element, ifc_util):
    """
    Extrait largeur, hauteur, longueur depuis les Psets ArchiCAD.
    Cherche dans les Psets standards et ArchiCAD spécifiques.
    """
    largeur = hauteur = longueur = None
    try:
        psets = ifc_util.get_psets(element)
        for pset_name, pset in psets.items():
            for k, v in pset.items():
                kl = k.lower()
                try:
                    val = float(v)
                    # Convertit m → mm si val < 100 (probablement en mètres)
                    if val and val < 100:
                        val = round(val * 1000, 1)
                    if largeur is None and any(x in kl for x in ('width', 'largeur', 'larg', 'w')):
                        largeur = val
                    if hauteur is None and any(x in kl for x in ('height', 'hauteur', 'haut', 'h')):
                        hauteur = val
                    if longueur is None and any(x in kl for x in ('length', 'longueur', 'long', 'depth', 'profondeur')):
                        longueur = val
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return largeur, hauteur, longueur


def _extract_vitrage(element, ifc_util):
    """Extrait le type de vitrage depuis les Psets."""
    try:
        psets = ifc_util.get_psets(element)
        for pset in psets.values():
            for k, v in pset.items():
                kl = k.lower()
                vl = str(v).lower() if v else ''
                if any(x in kl for x in ('glazing', 'vitrage', 'glass', 'verre')):
                    if 'triple' in vl: return 'Triple vitrage'
                    if 'double' in vl: return 'Double vitrage'
                    if 'simple' in vl or 'single' in vl: return 'Simple vitrage'
                    if v: return str(v)
                # Déduction depuis IsExternal
                if k == 'IsExternal' and v:
                    return 'Double vitrage'  # fenêtre ext → supposer double
    except Exception:
        pass
    return ''


def _extract_puissance(element, ifc_util):
    """Extrait la puissance électrique depuis les Psets."""
    try:
        psets = ifc_util.get_psets(element)
        for pset in psets.values():
            for k, v in pset.items():
                kl = k.lower()
                if any(x in kl for x in ('power', 'puissance', 'watt', 'wattage', 'lamp')):
                    try:
                        w = float(v)
                        return f'{int(w)}W'
                    except (TypeError, ValueError):
                        if v: return str(v)
    except Exception:
        pass
    return ''


def _extract_marque(element, ifc_util):
    """Extrait la marque / fabricant depuis les Psets."""
    try:
        psets = ifc_util.get_psets(element)
        for pset in psets.values():
            for k, v in pset.items():
                kl = k.lower()
                if any(x in kl for x in ('manufacturer', 'brand', 'marque', 'fabricant', 'make')):
                    if v: return str(v)
    except Exception:
        pass
    return ''


def _extract_materiau(element, ifc_util, ifc_model):
    """Extrait le matériau principal."""
    mat = _get_material(element, ifc_model)
    if mat:
        return mat
    try:
        psets = ifc_util.get_psets(element)
        for pset in psets.values():
            for k, v in pset.items():
                kl = k.lower()
                if any(x in kl for x in ('material', 'matériau', 'materiau', 'finish', 'finition')):
                    if v: return str(v)
    except Exception:
        pass
    return ''


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
    except ImportError:
        patrimoine.statut_conversion = 'erreur'
        patrimoine.erreur_conversion = 'ifcopenshell non installé. Lancez : pip install ifcopenshell'
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
            'metadata': {'nom': patrimoine.nom, 'source': os.path.basename(ifc_path)},
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
                patrimoine=patrimoine, nom=storey_nom,
                niveau=idx, ifc_guid=storey_guid,
            )

            etage_data = {
                'id': etage_obj.pk, 'ifc_guid': storey_guid,
                'nom': storey_nom, 'niveau': idx, 'elevation': elevation,
                'pieces': [], 'geometrie': {'meshes': []},
            }

            # ── Espaces / pièces ──────────────────────────────────────────
            espaces = [e for e in ifc_model.by_type('IfcSpace')
                       if _get_storey(e, ifc_model) == storey]
            for espace in espaces:
                surface = _get_surface_exacte(espace, ifc_util)
                if surface:
                    surface_totale_ifc += float(surface)
                piece_obj = Piece.objects.create(
                    etage=etage_obj, nom=espace.Name or 'Pièce',
                    surface=surface, ifc_guid=espace.GlobalId,
                    usage=espace.ObjectType or '',
                )
                etage_data['pieces'].append({
                    'id': piece_obj.pk, 'ifc_guid': espace.GlobalId,
                    'nom': piece_obj.nom,
                    'surface': float(surface) if surface else None,
                    'usage': piece_obj.usage,
                })

            # ── Éléments de l'étage ───────────────────────────────────────
            elements = _get_elements_of_storey(ifc_model, storey)
            for element in elements:
                ifc_type = element.is_a()

                # Revêtements
                if ifc_type in IFC_COVERING_TYPES:
                    surf = _get_area_from_quantities(element, ifc_util)
                    mat  = _get_material(element, ifc_model)
                    RevetementMur.objects.create(
                        patrimoine=patrimoine, etage=etage_obj,
                        nom=element.Name or ifc_type, materiau=mat,
                        surface=surf, ifc_guid=element.GlobalId, type_ifc=ifc_type,
                    )

                # Équipements / ouvertures / sanitaires enrichis
                categorie = IFC_TYPE_CATEGORIE.get(ifc_type)
                if categorie:
                    nomenclature             = _build_nomenclature(element, ifc_type)
                    largeur, hauteur, longueur = _extract_dimensions(element, ifc_util)
                    vitrage                  = _extract_vitrage(element, ifc_util) if ifc_type in ('IfcWindow', 'IfcCurtainWall') else ''
                    puissance                = _extract_puissance(element, ifc_util) if categorie == 'electrique' else ''
                    marque                   = _extract_marque(element, ifc_util)
                    materiau                 = _extract_materiau(element, ifc_util, ifc_model)

                    EquipementOuverture.objects.create(
                        patrimoine=patrimoine, etage=etage_obj,
                        nom=element.Name or ifc_type,
                        nomenclature=nomenclature,
                        type_element=categorie,
                        type_ifc=ifc_type,
                        ifc_guid=element.GlobalId,
                        description=element.Description or '',
                        largeur=largeur,
                        hauteur=hauteur,
                        longueur=longueur,
                        vitrage=vitrage,
                        puissance=puissance,
                        marque=marque,
                        materiau=materiau,
                    )

                # Géométrie 3D
                try:
                    shape   = ifcopenshell.geom.create_shape(settings, element)
                    geo     = shape.geometry
                    etage_data['geometrie']['meshes'].append({
                        'ifc_guid': element.GlobalId,
                        'type_ifc': ifc_type,
                        'vertices': list(geo.verts),
                        'indices':  list(geo.faces),
                    })
                except Exception:
                    pass

            result['etages'].append(etage_data)

        # ── Surface totale ────────────────────────────────────────────────
        if surface_totale_ifc > 0:
            patrimoine.surface_totale = decimal.Decimal(str(round(surface_totale_ifc, 2)))

        # ── Sérialise JSON ────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_surface_exacte(espace, ifc_util):
    try:
        psets = ifc_util.get_psets(espace, qtos_only=True)
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
    TYPES_VOULUS = {
        # Ouvertures
        'IfcDoor', 'IfcWindow', 'IfcCurtainWall',
        # Structure
        'IfcWall', 'IfcWallStandardCase', 'IfcSlab',
        'IfcColumn', 'IfcBeam', 'IfcRoof', 'IfcFooting',
        'IfcPile', 'IfcMember',
        # Circulation
        'IfcStair', 'IfcStairFlight', 'IfcRamp', 'IfcRampFlight',
        # Finitions
        'IfcCovering',
        # Sanitaires
        'IfcSanitaryTerminal', 'IfcFlowTerminal',
        # MEP
        'IfcFlowSegment', 'IfcFlowFitting', 'IfcFlowController',
        'IfcEnergyConversionDevice', 'IfcDistributionControlElement',
        # Électrique / Éclairage
        'IfcElectricAppliance', 'IfcLightFixture', 'IfcProtectiveDevice',
        # Mobilier
        'IfcFurnishingElement', 'IfcFurniture',
        # Protection / Garde-corps
        'IfcRailing',
        # Générique
        'IfcBuildingElementProxy',
    }
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure == storey:
            for el in rel.RelatedElements:
                if el.is_a() in TYPES_VOULUS:
                    elements.append(el)
    return elements
