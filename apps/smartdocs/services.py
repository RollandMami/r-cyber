"""
Service de conversion IFC → JSON enrichi.
- Dimensions converties en cm (pas mm, pas m)
- Vitrage lu depuis valeurs numériques IFC (U-value, glazing count) ET psets textuels
- Revêtements : type (mur/sol/plafond), nature (carrelage/parquet…), pièce associée
"""
import json, os, traceback, decimal
from django.core.files.base import ContentFile

# ── IFC type → catégorie équipement ──────────────────────────────────────────
IFC_TYPE_CATEGORIE = {
    'IfcDoor':                       'ouverture',
    'IfcWindow':                     'ouverture',
    'IfcCurtainWall':                'ouverture',
    'IfcSanitaryTerminal':           'sanitaire',
    'IfcFlowTerminal':               'sanitaire',
    'IfcFurnishingElement':          'mobilier',
    'IfcFurniture':                  'mobilier',
    'IfcFlowSegment':                'mep',
    'IfcFlowFitting':                'mep',
    'IfcFlowController':             'mep',
    'IfcEnergyConversionDevice':     'mep',
    'IfcDistributionControlElement': 'mep',
    'IfcElectricAppliance':          'electrique',
    'IfcLightFixture':               'electrique',
    'IfcProtectiveDevice':           'electrique',
    'IfcRailing':                    'protection',
    'IfcBuildingElementProxy':       'autre',
}

# ── IFC type revêtement → type_revetement + nature ───────────────────────────
IFC_COVERING_MAP = {
    # type_ifc → (type_revetement, nature_default)
    'IfcCovering':          None,   # déterminé par PredefinedType
    'IfcSlab':              ('sol',     'Dalle béton'),
    'IfcWall':              ('mur',     ''),
    'IfcWallStandardCase':  ('mur',     ''),
    'IfcRoof':              ('plafond', 'Toiture'),
    'IfcCeiling':           ('plafond', 'Plafond'),
}

COVERING_PREDEFINED = {
    'FLOORING':   ('sol',     'Revêtement de sol'),
    'CEILING':    ('plafond', 'Faux-plafond'),
    'ROOFING':    ('plafond', 'Toiture'),
    'CLADDING':   ('mur',     'Bardage'),
    'MEMBRANE':   ('sol',     'Membrane'),
    'INSULATION': ('mur',     'Isolation'),
    'SLEEVING':   ('autre',   ''),
    'WRAPPING':   ('autre',   ''),
}

# Mots-clés pour déduire la nature du revêtement depuis le nom/matériau
NATURE_KEYWORDS = {
    'carrelage': 'Carrelage',
    'tile':      'Carrelage',
    'tiling':    'Carrelage',
    'parquet':   'Parquet',
    'wood floor':'Parquet',
    'hardwood':  'Parquet',
    'plancher':  'Plancher bois',
    'carpet':    'Moquette',
    'moquette':  'Moquette',
    'vinyl':     'Revêtement vinyle',
    'pvc':       'Revêtement PVC',
    'epoxy':     'Résine époxy',
    'béton':     'Béton ciré',
    'beton':     'Béton',
    'concrete':  'Béton',
    'marble':    'Marbre',
    'marbre':    'Marbre',
    'granite':   'Granit',
    'enduit':    'Enduit',
    'plaster':   'Enduit / Plâtre',
    'gypsum':    'Plâtre / BA13',
    'placo':     'Plaque de plâtre',
    'peinture':  'Peinture',
    'paint':     'Peinture',
    'wallpaper': 'Papier peint',
    'papier':    'Papier peint',
    'brique':    'Brique apparente',
    'brick':     'Brique',
    'stone':     'Pierre',
    'pierre':    'Pierre',
    'faux-plafond': 'Faux-plafond',
    'faux plafond': 'Faux-plafond',
    'suspended ceiling': 'Faux-plafond suspendu',
    'bardage':   'Bardage',
    'cladding':  'Bardage',
    'terrasse':  'Terrasse',
    'terrace':   'Terrasse',
}

# Nomenclature équipements
IFC_NOMENCLATURE_DEFAULT = {
    'IfcDoor':              'Porte',
    'IfcWindow':            'Fenêtre',
    'IfcCurtainWall':       'Mur-rideau',
    'IfcSanitaryTerminal':  'Appareil sanitaire',
    'IfcFlowTerminal':      'Terminal fluide',
    'IfcLightFixture':      'Luminaire',
    'IfcElectricAppliance': 'Appareil électrique',
    'IfcProtectiveDevice':  'Protection électrique',
    'IfcRailing':           'Garde-corps / Main courante',
    'IfcFurnishingElement':  'Mobilier',
    'IfcFurniture':          'Mobilier',
    'IfcBuildingElementProxy': 'Élément générique',
}

NOMENCLATURE_KEYWORDS = {
    'single':     'Porte simple vantail',
    'double':     'Porte double vantaux',
    'swing':      'Porte battante',
    'sliding':    'Porte coulissante',
    'folding':    'Porte pliante',
    'revolving':  'Porte tournante',
    'overhead':   'Porte relevable',
    'garage':     'Porte de garage',
    'interior':   'Porte intérieure',
    'exterior':   'Porte extérieure',
    'fire':       'Porte coupe-feu',
    'entrance':   "Porte d'entrée",
    'asymmetric': 'Porte double vantaux asymétriques',
    'transom':    'Porte avec imposte',
    'sidelight':  'Porte avec imposte latérale',
    'casement':   'Fenêtre à battant',
    'tilt':       'Fenêtre oscillo-battant',
    'awning':     'Fenêtre à soufflet',
    'fixed':      'Fenêtre fixe',
    'hopper':     'Fenêtre basculante',
    'jalousie':   'Fenêtre jalousie',
    'bay':        'Fenêtre en baie',
    'bow':        'Fenêtre en arc',
    'skylight':   'Fenêtre de toit / Velux',
    'roof':       'Fenêtre de toit',
    'sill':       'Fenêtre avec allège',
    'allege':     'Fenêtre avec allège',
    'sink':       'Évier',
    'basin':      'Lavabo',
    'washbasin':  'Lavabo',
    'bathtub':    'Baignoire',
    'bath':       'Baignoire',
    'shower':     'Douche',
    'toilet':     'WC / Toilette',
    'wc':         'WC / Toilette',
    'bidet':      'Bidet',
    'urinal':     'Urinoir',
    'evier':      'Évier',
    'baignoire':  'Baignoire',
    'lavabo':     'Lavabo',
    'spot':       'Spot encastré',
    'downlight':  'Spot encastré',
    'ceiling':    'Plafonnier',
    'pendant':    'Suspension',
    'wall lamp':  'Applique murale',
    'strip':      'Réglette fluorescente',
    'tube':       'Tube fluorescent',
    'led':        'Luminaire LED',
    'railing':    'Garde-corps',
    'handrail':   'Main courante',
    'balustrade': 'Balustrade',
    'guard':      'Garde-corps',
}


# ─────────────────────────────────────────────────────────────────────────────
#  Fonctions d'extraction
# ─────────────────────────────────────────────────────────────────────────────

def _build_nomenclature(element, ifc_type):
    obj_type    = (getattr(element, 'ObjectType',  None) or '').strip()
    description = (getattr(element, 'Description', None) or '').strip()
    name        = (getattr(element, 'Name',        None) or '').strip()
    for candidate in [obj_type, description, name]:
        if not candidate:
            continue
        low = candidate.lower()
        for kw, label in NOMENCLATURE_KEYWORDS.items():
            if kw in low:
                return label
        alpha_ratio = sum(c.isalpha() for c in candidate) / max(len(candidate), 1)
        if alpha_ratio > 0.4 and len(candidate) > 3:
            return candidate
    return IFC_NOMENCLATURE_DEFAULT.get(ifc_type, name or ifc_type)


def _to_cm(val_m):
    """Convertit une valeur en mètres (unité IFC standard) → centimètres."""
    if val_m is None:
        return None
    v = float(val_m)
    # IFC stocke en mètres. Si la valeur brute > 1000 c'est déjà en mm.
    if v > 1000:
        return round(v / 10, 1)   # mm → cm
    if v > 50:
        return round(v, 1)         # déjà en cm probablement (rare)
    return round(v * 100, 1)       # m → cm


def _extract_dimensions(element, ifc_util):
    """
    Extrait largeur/hauteur/longueur et les retourne en cm.
    Cherche en priorité dans Qto_* puis Pset_*.
    """
    largeur = hauteur = longueur = None
    try:
        psets = ifc_util.get_psets(element)
        for pset_name, pset in psets.items():
            for k, v in pset.items():
                kl = k.lower()
                try:
                    raw = float(v)
                    if raw <= 0:
                        continue
                    cm = _to_cm(raw)
                    if largeur is None and any(x in kl for x in
                            ('width', 'largeur', 'larg', 'overallwidth', 'overall width')):
                        largeur = cm
                    elif hauteur is None and any(x in kl for x in
                            ('height', 'hauteur', 'haut', 'overallheight', 'overall height')):
                        hauteur = cm
                    elif longueur is None and any(x in kl for x in
                            ('length', 'longueur', 'long', 'depth', 'profondeur')):
                        longueur = cm
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return largeur, hauteur, longueur


def _extract_vitrage(element, ifc_util):
    """
    Extrait le type de vitrage.
    Priorité : psets textuels → nombre de vitrages (ThermalTransmittance U-value) → IsExternal.
    """
    try:
        psets = ifc_util.get_psets(element)
        for pset_name, pset in psets.items():
            for k, v in pset.items():
                kl = k.lower()
                vl = str(v).lower() if v else ''

                # Clés textuelles explicites
                if any(x in kl for x in ('glazing', 'vitrage', 'glass', 'verre', 'glazingtype')):
                    if 'triple' in vl:                        return 'Triple vitrage'
                    if 'double' in vl or 'insul' in vl:      return 'Double vitrage'
                    if 'simple' in vl or 'single' in vl:     return 'Simple vitrage'
                    if 'lami' in vl:                          return 'Verre feuilleté'
                    if 'secur' in vl:                         return 'Verre sécurit'
                    if v and str(v).strip():                  return str(v).strip()

                # Nombre de panneaux vitrés (ArchiCAD : GlazingPanels, PanelNumber…)
                if any(x in kl for x in ('panel', 'pane', 'layer', 'count', 'number')) \
                        and 'glaz' in kl:
                    try:
                        n = int(float(v))
                        if n >= 3: return 'Triple vitrage'
                        if n == 2: return 'Double vitrage'
                        if n == 1: return 'Simple vitrage'
                    except (TypeError, ValueError):
                        pass

                # U-value thermique → déduction
                if any(x in kl for x in ('thermaltr', 'u-value', 'uvalue', 'transmittance')):
                    try:
                        u = float(v)
                        if u <= 0.8:   return 'Triple vitrage'
                        if u <= 1.5:   return 'Double vitrage HR'
                        if u <= 2.9:   return 'Double vitrage'
                        return 'Simple vitrage'
                    except (TypeError, ValueError):
                        pass

        # Dernier recours : IsExternal → supposer double vitrage pour fenêtres ext.
        for pset in psets.values():
            if pset.get('IsExternal'):
                return 'Double vitrage'
    except Exception:
        pass
    return ''


def _extract_puissance(element, ifc_util):
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
    try:
        psets = ifc_util.get_psets(element)
        for pset in psets.values():
            for k, v in pset.items():
                kl = k.lower()
                if any(x in kl for x in ('manufacturer', 'brand', 'marque', 'fabricant', 'make')):
                    if v and str(v).strip().lower() not in ('undefined', 'unknown', 'n/a', ''):
                        return str(v).strip()
    except Exception:
        pass
    return ''


def _extract_materiau(element, ifc_util, ifc_model):
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


def _detect_nature(nom, materiau, type_ifc, predefined_type=None):
    """Déduit la nature du revêtement depuis le nom/matériau/type."""
    searchable = (nom + ' ' + materiau + ' ' + (predefined_type or '')).lower()
    for kw, label in NATURE_KEYWORDS.items():
        if kw in searchable:
            return label
    # Depuis le type IFC
    if type_ifc == 'IfcSlab':
        return 'Dalle béton'
    if type_ifc in ('IfcWall', 'IfcWallStandardCase'):
        return ''
    return ''


def _detect_type_revetement(element, type_ifc):
    """Détermine si c'est mur / sol / plafond."""
    predefined = getattr(element, 'PredefinedType', None)
    if predefined and str(predefined) in COVERING_PREDEFINED:
        return COVERING_PREDEFINED[str(predefined)][0], str(predefined)

    if type_ifc in IFC_COVERING_MAP and IFC_COVERING_MAP[type_ifc]:
        return IFC_COVERING_MAP[type_ifc][0], predefined

    # Heuristique sur le nom
    name = (getattr(element, 'Name', '') or '').lower()
    obj  = (getattr(element, 'ObjectType', '') or '').lower()
    combined = name + ' ' + obj
    if any(x in combined for x in ('floor', 'sol', 'slab', 'plancher', 'carrelage')):
        return 'sol', predefined
    if any(x in combined for x in ('ceiling', 'plafond', 'faux', 'roof')):
        return 'plafond', predefined
    return 'mur', predefined


# ─────────────────────────────────────────────────────────────────────────────
#  Conversion principale IFC → JSON
# ─────────────────────────────────────────────────────────────────────────────

def convertir_ifc_en_json(patrimoine):
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
        patrimoine.erreur_conversion = 'ifcopenshell non installé.'
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

        result = {'metadata': {'nom': patrimoine.nom,
                                'source': os.path.basename(ifc_path)},
                  'etages': []}

        patrimoine.etages.all().delete()
        patrimoine.revetements.all().delete()
        patrimoine.equipements.all().delete()

        surface_totale_ifc = 0.0

        for idx, storey in enumerate(storeys):
            etage_obj = Etage.objects.create(
                patrimoine=patrimoine,
                nom=storey.Name or f'Étage {idx}',
                niveau=idx,
                ifc_guid=storey.GlobalId,
            )

            etage_data = {
                'id': etage_obj.pk, 'ifc_guid': storey.GlobalId,
                'nom': etage_obj.nom, 'niveau': idx,
                'elevation': storey.Elevation or 0,
                'pieces': [], 'geometrie': {'meshes': []},
            }

            # ── Pièces / espaces ──────────────────────────────────────────
            espaces = [e for e in ifc_model.by_type('IfcSpace')
                       if _get_storey(e, ifc_model) == storey]
            piece_by_guid = {}
            for espace in espaces:
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
                piece_by_guid[espace.GlobalId] = piece_obj
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

                # Revêtements enrichis
                if ifc_type in IFC_COVERING_MAP or ifc_type == 'IfcCovering':
                    surf = _get_area_from_quantities(element, ifc_util)
                    mat  = _get_material(element, ifc_model)
                    nom  = element.Name or ifc_type
                    type_rev, predefined = _detect_type_revetement(element, ifc_type)
                    nature = _detect_nature(nom, mat,
                                            ifc_type,
                                            str(predefined) if predefined else None)
                    # Pièce associée : cherche dans BoundedBy
                    piece_obj = _find_piece_of_element(element, piece_by_guid, ifc_model)
                    RevetementMur.objects.create(
                        patrimoine=patrimoine,
                        etage=etage_obj,
                        piece=piece_obj,
                        nom=nom,
                        type_revetement=type_rev,
                        nature=nature,
                        materiau=mat,
                        surface=surf,
                        ifc_guid=element.GlobalId,
                        type_ifc=ifc_type,
                    )

                # Équipements enrichis
                categorie = IFC_TYPE_CATEGORIE.get(ifc_type)
                if categorie:
                    nomenclature              = _build_nomenclature(element, ifc_type)
                    largeur, hauteur, longueur = _extract_dimensions(element, ifc_util)
                    vitrage  = _extract_vitrage(element, ifc_util) \
                                if ifc_type in ('IfcWindow', 'IfcCurtainWall') else ''
                    puissance = _extract_puissance(element, ifc_util) \
                                if categorie == 'electrique' else ''
                    marque   = _extract_marque(element, ifc_util)
                    materiau = _extract_materiau(element, ifc_util, ifc_model)

                    EquipementOuverture.objects.create(
                        patrimoine=patrimoine, etage=etage_obj,
                        nom=element.Name or ifc_type,
                        nomenclature=nomenclature,
                        type_element=categorie, type_ifc=ifc_type,
                        ifc_guid=element.GlobalId,
                        description=element.Description or '',
                        largeur=largeur, hauteur=hauteur, longueur=longueur,
                        vitrage=vitrage, puissance=puissance,
                        marque=marque, materiau=materiau,
                    )

                # Géométrie 3D
                try:
                    shape = ifcopenshell.geom.create_shape(settings, element)
                    geo   = shape.geometry
                    etage_data['geometrie']['meshes'].append({
                        'ifc_guid': element.GlobalId,
                        'type_ifc': ifc_type,
                        'vertices': list(geo.verts),
                        'indices':  list(geo.faces),
                    })
                except Exception:
                    pass

            result['etages'].append(etage_data)

        # Surface totale
        if surface_totale_ifc > 0:
            patrimoine.surface_totale = decimal.Decimal(str(round(surface_totale_ifc, 2)))

        # JSON
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

def _find_piece_of_element(element, piece_by_guid, ifc_model):
    """Cherche la pièce qui contient cet élément via IfcRelSpaceBoundary."""
    try:
        for rel in ifc_model.by_type('IfcRelSpaceBoundary'):
            if rel.RelatedBuildingElement == element:
                space = rel.RelatingSpace
                if space and space.GlobalId in piece_by_guid:
                    return piece_by_guid[space.GlobalId]
    except Exception:
        pass
    return None


def _get_surface_exacte(espace, ifc_util):
    try:
        psets = ifc_util.get_psets(espace, qtos_only=True)
        for qset_name in ('Qto_SpaceBaseQuantities', 'BaseQuantities', 'ArchiCAD Properties'):
            if qset_name in psets:
                for k in ('NetFloorArea', 'GrossFloorArea', 'NetArea', 'GrossArea',
                           'Area', 'NetFloorAreaWithSlab'):
                    if k in psets[qset_name]:
                        try:
                            return float(psets[qset_name][k])
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
                    names = [l.Material.Name for l in layers
                             if l.Material and l.Material.Name]
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
    TYPES_VOULUS = {
        'IfcDoor', 'IfcWindow', 'IfcCurtainWall',
        'IfcWall', 'IfcWallStandardCase',
        'IfcSlab', 'IfcRoof',
        'IfcColumn', 'IfcBeam', 'IfcFooting', 'IfcPile', 'IfcMember',
        'IfcStair', 'IfcStairFlight', 'IfcRamp', 'IfcRampFlight',
        'IfcCovering',
        'IfcSanitaryTerminal', 'IfcFlowTerminal',
        'IfcFlowSegment', 'IfcFlowFitting', 'IfcFlowController',
        'IfcEnergyConversionDevice', 'IfcDistributionControlElement',
        'IfcElectricAppliance', 'IfcLightFixture', 'IfcProtectiveDevice',
        'IfcFurnishingElement', 'IfcFurniture',
        'IfcRailing',
        'IfcBuildingElementProxy',
    }
    elements = []
    for rel in ifc_model.by_type('IfcRelContainedInSpatialStructure'):
        if rel.RelatingStructure == storey:
            for el in rel.RelatedElements:
                if el.is_a() in TYPES_VOULUS:
                    elements.append(el)
    return elements
