import json, os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum

from .models import (
    Patrimoine, Etage, Document, TypeDocument,
    DocumentGED, GED_ARBORESCENCE, Site,
    RevetementMur, EquipementOuverture, Piece,
)
from .forms import PatrimoineForm, DocumentForm
from .services import convertir_ifc_en_json


# ═══════════════════════════════════════════════════════════
#  SITES
# ═══════════════════════════════════════════════════════════

@login_required
def site_list(request):
    q = request.GET.get('q', '').strip()
    sites = Site.objects.prefetch_related('batiments').all()
    if q:
        sites = sites.filter(
            Q(nom__icontains=q) | Q(adresse__icontains=q) |
            Q(batiments__nom__icontains=q)
        ).distinct()
    return render(request, 'smartdocs/site_list.html', {'sites': sites, 'q': q})


@login_required
def site_detail(request, pk):
    site = get_object_or_404(Site, pk=pk)
    batiments = site.batiments.prefetch_related('etages').all()
    total_surface = batiments.aggregate(t=Sum('surface_totale'))['t']
    total_docs    = sum(b.total_documents() for b in batiments)
    nb_3d         = sum(1 for b in batiments if b.has_viewer())
    return render(request, 'smartdocs/site_detail.html', {
        'site':          site,
        'batiments':     batiments,
        'total_surface': total_surface,
        'total_docs':    total_docs,
        'nb_3d':         nb_3d,
    })


@login_required
def site_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    if request.method == 'POST':
        nom      = request.POST.get('nom', '').strip()
        adresse  = request.POST.get('adresse', '').strip()
        description = request.POST.get('description', '').strip()
        photo    = request.FILES.get('photo')
        if not nom:
            messages.error(request, 'Le nom du site est requis.')
        else:
            site = Site(nom=nom, adresse=adresse, description=description, cree_par=request.user)
            if photo:
                site.photo = photo
            site.save()
            messages.success(request, f'Site « {nom} » créé avec succès.')
            return redirect('smartdocs:site_detail', pk=site.pk)
    from .forms import SiteForm
    form = SiteForm()
    return render(request, 'smartdocs/site_form.html', {'form': form, 'action': 'Créer'})


@login_required
def site_edit(request, pk):
    if not request.user.is_staff:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    site = get_object_or_404(Site, pk=pk)
    if request.method == 'POST':
        site.nom         = request.POST.get('nom', site.nom).strip()
        site.adresse     = request.POST.get('adresse', '').strip()
        site.description = request.POST.get('description', '').strip()
        if request.FILES.get('photo'):
            site.photo = request.FILES['photo']
        site.save()
        messages.success(request, 'Site mis à jour.')
        return redirect('smartdocs:site_detail', pk=site.pk)
    from .forms import SiteForm
    form = SiteForm(instance=site)
    return render(request, 'smartdocs/site_form.html', {'form': form, 'action': 'Modifier'})


@login_required
@require_POST
def site_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    site = get_object_or_404(Site, pk=pk)
    nom = site.nom
    site.delete()
    messages.success(request, f'Site « {nom} » supprimé.')
    return redirect('smartdocs:site_list')


# ═══════════════════════════════════════════════════════════
#  PATRIMOINES (BÂTIMENTS)
# ═══════════════════════════════════════════════════════════

@login_required
def patrimoine_list(request):
    """Redirige vers la liste des sites (nouveau point d'entrée)."""
    return redirect('smartdocs:site_list')


@login_required
def patrimoine_detail(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    etages     = patrimoine.etages.prefetch_related('pieces', 'documents', 'revetements', 'equipements').all()
    types_docs = TypeDocument.objects.all()

    surface_ifc = patrimoine.surface_ifc()
    nb_etages   = patrimoine.nombre_etages()
    revetements = RevetementMur.objects.filter(patrimoine=patrimoine).select_related('etage')
    equipements = EquipementOuverture.objects.filter(patrimoine=patrimoine).select_related('etage')
    sanitaires  = equipements.filter(type_element='sanitaire')
    ouvertures  = equipements.filter(type_element='ouverture')
    mep         = equipements.filter(type_element__in=['mep', 'equipement'])
    mobilier    = equipements.filter(type_element='mobilier')

    docs_ged = DocumentGED.objects.filter(patrimoine=patrimoine).select_related('uploade_par')
    ged_arbo = _build_ged_arbo(docs_ged, request.user.is_staff)

    site           = patrimoine.site
    site_batiments = site.batiments.all() if site else []

    return render(request, 'smartdocs/patrimoine_detail.html', {
        'patrimoine':       patrimoine,
        'etages':           etages,
        'types_docs':       types_docs,
        'surface_ifc':      surface_ifc,
        'nb_etages':        nb_etages,
        'revetements':      revetements,
        'sanitaires':       sanitaires,
        'ouvertures':       ouvertures,
        'mep':              mep,
        'mobilier':         mobilier,
        'ged_arbo':         ged_arbo,
        'ged_arborescence': GED_ARBORESCENCE,
        'etages_plan':      list(etages),
        'site':             site,
        'site_batiments':   site_batiments,
        'total_docs':       patrimoine.total_documents(),
    })


def _build_ged_arbo(docs_ged, is_admin):
    arbo = {}
    for corps_key, corps_data in GED_ARBORESCENCE.items():
        dossiers = {}
        for dossier_key, dossier_label in corps_data['sous_dossiers'].items():
            docs = [d for d in docs_ged if d.corps == corps_key and d.dossier == dossier_key]
            if is_admin or docs:
                dossiers[dossier_key] = {'label': dossier_label, 'docs': docs, 'count': len(docs)}
        if is_admin or dossiers:
            arbo[corps_key] = {'label': corps_data['label'], 'icone': corps_data['icone'], 'dossiers': dossiers}
    return arbo


@login_required
def patrimoine_create(request):
    """Création sans site pré-sélectionné."""
    if not request.user.is_staff:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    sites = Site.objects.all()
    if request.method == 'POST':
        return _handle_patrimoine_save(request, None, None)
    form = PatrimoineForm()
    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'sites': sites, 'action': 'Créer',
    })


@login_required
def patrimoine_create_in_site(request, site_pk):
    """Création d'un bâtiment directement dans un site."""
    if not request.user.is_staff:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    site  = get_object_or_404(Site, pk=site_pk)
    sites = Site.objects.all()
    if request.method == 'POST':
        return _handle_patrimoine_save(request, None, site)
    form = PatrimoineForm()
    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'sites': sites, 'site': site, 'action': 'Créer',
    })


@login_required
def patrimoine_edit(request, pk):
    if not request.user.is_staff:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    sites = Site.objects.all()
    if request.method == 'POST':
        return _handle_patrimoine_save(request, patrimoine, None)
    form = PatrimoineForm(instance=patrimoine)
    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'sites': sites, 'site': patrimoine.site,
        'patrimoine': patrimoine, 'action': 'Modifier',
    })


def _handle_patrimoine_save(request, patrimoine, default_site):
    """Traitement commun création / modification."""
    sites = Site.objects.all()
    is_create = patrimoine is None
    form = PatrimoineForm(request.POST, request.FILES, instance=patrimoine)
    if form.is_valid():
        bat = form.save(commit=False)
        if is_create:
            bat.cree_par = request.user
        # Site sélectionné
        site_pk = request.POST.get('site')
        if site_pk:
            try:
                bat.site = Site.objects.get(pk=site_pk)
            except Site.DoesNotExist:
                bat.site = default_site
        elif default_site and is_create:
            bat.site = default_site
        bat.save()
        if 'fichier_ifc' in request.FILES:
            convertir_ifc_en_json(bat)
        messages.success(request, f'Bâtiment « {bat.nom} » {"créé" if is_create else "mis à jour"} avec succès.')
        if bat.site:
            return redirect('smartdocs:site_detail', pk=bat.site.pk)
        return redirect('smartdocs:patrimoine_detail', pk=bat.pk)

    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'sites': sites,
        'site': default_site or (patrimoine.site if patrimoine else None),
        'patrimoine': patrimoine, 'action': 'Créer' if is_create else 'Modifier',
    })


@login_required
@require_POST
def patrimoine_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission refusée.')
        return redirect('smartdocs:site_list')
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    site_pk = patrimoine.site.pk if patrimoine.site else None
    nom = patrimoine.nom
    patrimoine.delete()
    messages.success(request, f'Bâtiment « {nom} » supprimé.')
    if site_pk:
        return redirect('smartdocs:site_detail', pk=site_pk)
    return redirect('smartdocs:site_list')


# ═══════════════════════════════════════════════════════════
#  DOCUMENTS
# ═══════════════════════════════════════════════════════════

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
    patrimoine_pk = doc.patrimoine.pk
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)


# ═══════════════════════════════════════════════════════════
#  GED
# ═══════════════════════════════════════════════════════════

@login_required
def ged_upload(request, patrimoine_pk):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)
    if request.method == 'POST':
        corps   = request.POST.get('corps', '').upper()
        dossier = request.POST.get('dossier', '')
        titre   = request.POST.get('titre', '').strip()
        fichier = request.FILES.get('fichier')
        if not all([corps, dossier, titre, fichier]):
            err = {'error': 'Corps, dossier, titre et fichier sont requis.'}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(err, status=400)
            messages.error(request, err['error'])
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)
        doc = DocumentGED(
            patrimoine=patrimoine, corps=corps, dossier=dossier,
            titre=titre, fichier=fichier,
            version=request.POST.get('version', ''),
            date_doc=request.POST.get('date_doc') or None,
            uploade_par=request.user,
        )
        doc.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'id': doc.pk, 'titre': doc.titre,
                                  'corps': doc.corps, 'dossier': doc.dossier,
                                  'dossier_label': doc.nom_dossier_affichage(),
                                  'extension': doc.extension(),
                                  'url_download': f'/patrimoines/ged/{doc.pk}/telecharger/'})
        messages.success(request, f'Document « {doc.titre} » ajouté.')
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


# ═══════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════

@login_required
def api_patrimoines_sans_site(request):
    pats = Patrimoine.objects.filter(site__isnull=True).values('id', 'nom', 'adresse')
    return JsonResponse({'patrimoines': list(pats)})


@login_required
def api_tous_patrimoines(request):
    pats = Patrimoine.objects.filter(site__isnull=True).values('id', 'nom', 'adresse')
    return JsonResponse({'patrimoines': list(pats)})
