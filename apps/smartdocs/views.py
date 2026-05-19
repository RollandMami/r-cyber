import json
import os

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum

from .models import (
    Patrimoine, Etage, Document, TypeDocument,
    DocumentGED, GED_ARBORESCENCE, Site,
    RevetementMur, EquipementOuverture, Piece,
)
from .forms import PatrimoineForm, DocumentForm, DocumentGEDForm
from .services import convertir_ifc_en_json


# ─── PATRIMOINES LIST ─────────────────────────────────────────────────────────

@login_required
def patrimoine_list(request):
    q = request.GET.get('q', '').strip()
    patrimoines = Patrimoine.objects.prefetch_related('etages', 'documents').all()
    if q:
        patrimoines = patrimoines.filter(
            Q(nom__icontains=q) | Q(adresse__icontains=q) | Q(description__icontains=q)
        )
    return render(request, 'smartdocs/patrimoine_list.html', {
        'patrimoines': patrimoines,
        'q': q,
    })


# ─── PATRIMOINE DETAIL ────────────────────────────────────────────────────────

@login_required
def patrimoine_detail(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    etages     = patrimoine.etages.prefetch_related('pieces', 'documents', 'revetements', 'equipements').all()
    types_docs = TypeDocument.objects.all()

    # Onglet 1 — résumé IFC
    surface_ifc    = patrimoine.surface_ifc()
    nb_etages      = patrimoine.nombre_etages()
    revetements    = RevetementMur.objects.filter(patrimoine=patrimoine).select_related('etage')
    equipements    = EquipementOuverture.objects.filter(patrimoine=patrimoine).select_related('etage')
    sanitaires     = equipements.filter(type_element='sanitaire')
    ouvertures     = equipements.filter(type_element='ouverture')
    mep            = equipements.filter(type_element__in=['mep', 'equipement'])
    mobilier       = equipements.filter(type_element='mobilier')

    # Onglet 2 — GED
    docs_ged = DocumentGED.objects.filter(patrimoine=patrimoine).select_related('uploade_par')
    # Construit l'arbo avec docs
    ged_arbo = _build_ged_arbo(docs_ged, request.user.is_staff)

    # Onglet 3 — Plan du site (étages pour filtre)
    etages_plan = list(etages)

    # Onglet 4 — Composition site
    site = patrimoine.site
    site_batiments = site.batiments.all() if site else []

    return render(request, 'smartdocs/patrimoine_detail.html', {
        'patrimoine':    patrimoine,
        'etages':        etages,
        'types_docs':    types_docs,
        'surface_ifc':   surface_ifc,
        'nb_etages':     nb_etages,
        'revetements':   revetements,
        'sanitaires':    sanitaires,
        'ouvertures':    ouvertures,
        'mep':           mep,
        'mobilier':      mobilier,
        'ged_arbo':      ged_arbo,
        'ged_arborescence': GED_ARBORESCENCE,
        'etages_plan':   etages_plan,
        'site':          site,
        'site_batiments': site_batiments,
        'total_docs':    patrimoine.total_documents(),
    })


def _build_ged_arbo(docs_ged, is_admin):
    """
    Construit un dict imbriqué CEA/CET → dossier → [docs]
    Pour user simple : on n'inclut que les dossiers non vides.
    """
    arbo = {}
    for corps_key, corps_data in GED_ARBORESCENCE.items():
        dossiers = {}
        for dossier_key, dossier_label in corps_data['sous_dossiers'].items():
            docs = [d for d in docs_ged
                    if d.corps == corps_key and d.dossier == dossier_key]
            if is_admin or docs:   # admin voit tout, user voit seulement si docs
                dossiers[dossier_key] = {
                    'label': dossier_label,
                    'docs':  docs,
                    'count': len(docs),
                }
        if is_admin or dossiers:
            arbo[corps_key] = {
                'label':    corps_data['label'],
                'icone':    corps_data['icone'],
                'dossiers': dossiers,
            }
    return arbo


# ─── PATRIMOINE CRUD ──────────────────────────────────────────────────────────

@login_required
def patrimoine_create(request):
    if request.method == 'POST':
        form = PatrimoineForm(request.POST, request.FILES)
        if form.is_valid():
            patrimoine = form.save(commit=False)
            patrimoine.cree_par = request.user
            # Surface : laisser vide → sera calculée depuis IFC
            patrimoine.save()
            if patrimoine.fichier_ifc:
                convertir_ifc_en_json(patrimoine)
            messages.success(request, f'Patrimoine « {patrimoine.nom} » créé avec succès.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)
    else:
        form = PatrimoineForm()
    return render(request, 'smartdocs/patrimoine_form.html', {'form': form, 'action': 'Créer'})


@login_required
def patrimoine_edit(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    if request.method == 'POST':
        form = PatrimoineForm(request.POST, request.FILES, instance=patrimoine)
        if form.is_valid():
            patrimoine = form.save()
            if 'fichier_ifc' in request.FILES:
                convertir_ifc_en_json(patrimoine)
            messages.success(request, 'Patrimoine mis à jour.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)
    else:
        form = PatrimoineForm(instance=patrimoine)
    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'patrimoine': patrimoine, 'action': 'Modifier'
    })


@login_required
@require_POST
def patrimoine_delete(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    nom = patrimoine.nom
    patrimoine.delete()
    messages.success(request, f'Patrimoine « {nom} » supprimé.')
    return redirect('smartdocs:patrimoine_list')


# ─── DOCUMENTS (ancien système) ───────────────────────────────────────────────

@login_required
def document_upload(request, patrimoine_pk):
    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, patrimoine=patrimoine)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.patrimoine  = patrimoine
            doc.uploade_par = request.user
            doc.save()
            messages.success(request, f'Document « {doc.titre} » ajouté.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)
    else:
        form = DocumentForm(patrimoine=patrimoine)
    return render(request, 'smartdocs/document_form.html', {'form': form, 'patrimoine': patrimoine})


@login_required
def document_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not doc.fichier:
        raise Http404
    return FileResponse(doc.fichier.open('rb'), as_attachment=True,
                        filename=os.path.basename(doc.fichier.name))


@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    patrimoine = doc.patrimoine
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)


# ─── GED ─────────────────────────────────────────────────────────────────────

@login_required
def ged_upload(request, patrimoine_pk):
    """Upload d'un document GED — admin seulement."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission refusée'}, status=403)

    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)

    if request.method == 'POST':
        corps   = request.POST.get('corps', '').upper()
        dossier = request.POST.get('dossier', '')
        titre   = request.POST.get('titre', '').strip()
        fichier = request.FILES.get('fichier')
        version = request.POST.get('version', '')
        date_doc = request.POST.get('date_doc') or None

        if not all([corps, dossier, titre, fichier]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Corps, dossier, titre et fichier sont requis.'}, status=400)
            messages.error(request, 'Corps, dossier, titre et fichier sont requis.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)

        doc = DocumentGED(
            patrimoine=patrimoine,
            corps=corps,
            dossier=dossier,
            titre=titre,
            fichier=fichier,
            version=version,
            date_doc=date_doc,
            uploade_par=request.user,
        )
        doc.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success':    True,
                'id':         doc.pk,
                'titre':      doc.titre,
                'corps':      doc.corps,
                'dossier':    doc.dossier,
                'dossier_label': doc.nom_dossier_affichage(),
                'extension':  doc.extension(),
                'taille':     doc.taille_fichier(),
                'url_download': f'/patrimoines/ged/{doc.pk}/telecharger/',
            })
        messages.success(request, f'Document « {doc.titre} » ajouté dans la GED.')
        return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)

    return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)


@login_required
def ged_download(request, pk):
    doc = get_object_or_404(DocumentGED, pk=pk)
    if not doc.fichier:
        raise Http404
    return FileResponse(doc.fichier.open('rb'), as_attachment=True,
                        filename=os.path.basename(doc.fichier.name))


@login_required
@require_POST
def ged_delete(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    doc = get_object_or_404(DocumentGED, pk=pk)
    patrimoine_pk = doc.patrimoine.pk
    doc.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Document GED supprimé.')
    return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)


# ─── SITE / COMPOSITION ──────────────────────────────────────────────────────

@login_required
def site_ajouter_batiment(request, patrimoine_pk):
    """Associe un bâtiment existant à un site, ou en crée un nouveau."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission refusée'}, status=403)

    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'create_site')

        if action == 'create_site':
            site_nom = request.POST.get('site_nom', '').strip()
            if site_nom:
                site = Site.objects.create(nom=site_nom, cree_par=request.user)
                patrimoine.site = site
                patrimoine.save(update_fields=['site'])
                messages.success(request, f'Site « {site_nom} » créé et associé.')

        elif action == 'assign_site':
            site_pk = request.POST.get('site_pk')
            try:
                site = Site.objects.get(pk=site_pk)
                patrimoine.site = site
                patrimoine.save(update_fields=['site'])
                messages.success(request, f'Bâtiment associé au site « {site.nom} ».')
            except Site.DoesNotExist:
                messages.error(request, 'Site introuvable.')

        elif action == 'add_batiment':
            bat_pk = request.POST.get('batiment_pk')
            site   = patrimoine.site
            if site and bat_pk:
                try:
                    autre = Patrimoine.objects.get(pk=bat_pk)
                    autre.site = site
                    autre.save(update_fields=['site'])
                    messages.success(request, f'« {autre.nom} » ajouté au site.')
                except Patrimoine.DoesNotExist:
                    messages.error(request, 'Bâtiment introuvable.')

        elif action == 'remove_batiment':
            bat_pk = request.POST.get('batiment_pk')
            try:
                autre = Patrimoine.objects.get(pk=bat_pk)
                if autre.pk == patrimoine_pk:
                    autre.site = None
                    autre.save(update_fields=['site'])
                    messages.success(request, 'Bâtiment retiré du site.')
                else:
                    autre.site = None
                    autre.save(update_fields=['site'])
                    messages.success(request, f'« {autre.nom} » retiré du site.')
            except Patrimoine.DoesNotExist:
                messages.error(request, 'Bâtiment introuvable.')

    return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)


# ─── API — Viewer ─────────────────────────────────────────────────────────────

@login_required
def api_patrimoine_arborescence(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    data = {
        'id':     patrimoine.pk,
        'nom':    patrimoine.nom,
        'etages': []
    }
    for etage in patrimoine.etages.prefetch_related('pieces').all():
        data['etages'].append({
            'id':       etage.pk,
            'nom':      etage.nom,
            'niveau':   etage.niveau,
            'ifc_guid': etage.ifc_guid,
            'pieces': [
                {
                    'id':       p.pk,
                    'nom':      p.nom,
                    'surface':  float(p.surface) if p.surface else None,
                    'ifc_guid': p.ifc_guid,
                    'usage':    p.usage,
                }
                for p in etage.pieces.all()
            ]
        })
    return JsonResponse(data)


@login_required
def api_tous_patrimoines(request):
    """Retourne les patrimoines sans site pour la sélection dans composition."""
    pats = Patrimoine.objects.filter(site__isnull=True).values('id', 'nom', 'adresse')
    return JsonResponse({'patrimoines': list(pats)})
