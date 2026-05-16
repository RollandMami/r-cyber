from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
import os

from .models import Patrimoine, Etage, Document, TypeDocument
from .forms import PatrimoineForm, DocumentForm
from .services import convertir_ifc_en_json


# ─────────────────────────────────────────
#  PATRIMOINES
# ─────────────────────────────────────────

#@login_required
def patrimoine_list(request):
    patrimoines = Patrimoine.objects.prefetch_related('etages', 'documents').all()
    return render(request, 'smartdocs/patrimoine_list.html', {'patrimoines': patrimoines})


#@login_required
def patrimoine_detail(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    etages     = patrimoine.etages.prefetch_related('pieces', 'documents').all()
    types_docs = TypeDocument.objects.all()

    # Documents globaux (sans étage)
    docs_batiment = patrimoine.documents.filter(etage__isnull=True).select_related('type_doc')

    return render(request, 'smartdocs/patrimoine_detail.html', {
        'patrimoine':   patrimoine,
        'etages':       etages,
        'types_docs':   types_docs,
        'docs_batiment': docs_batiment,
    })


#@login_required
def patrimoine_create(request):
    if request.method == 'POST':
        form = PatrimoineForm(request.POST, request.FILES)
        if form.is_valid():
            patrimoine          = form.save(commit=False)
            if request.user.is_authenticated:
                patrimoine.cree_par = request.user
            patrimoine.save()

            # Lance la conversion IFC si un fichier a été uploadé
            if patrimoine.fichier_ifc:
                convertir_ifc_en_json(patrimoine)

            messages.success(request, f'Patrimoine « {patrimoine.nom} » créé avec succès.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)
    else:
        form = PatrimoineForm()

    return render(request, 'smartdocs/patrimoine_form.html', {'form': form, 'action': 'Créer'})


#@login_required
def patrimoine_edit(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    if request.method == 'POST':
        form = PatrimoineForm(request.POST, request.FILES, instance=patrimoine)
        if form.is_valid():
            patrimoine = form.save()

            # Reconvertit si un nouveau fichier IFC a été uploadé
            if 'fichier_ifc' in request.FILES:
                convertir_ifc_en_json(patrimoine)

            messages.success(request, 'Patrimoine mis à jour.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)
    else:
        form = PatrimoineForm(instance=patrimoine)

    return render(request, 'smartdocs/patrimoine_form.html', {
        'form': form, 'patrimoine': patrimoine, 'action': 'Modifier'
    })


#@login_required
@require_POST
def patrimoine_delete(request, pk):
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    nom = patrimoine.nom
    patrimoine.delete()
    messages.success(request, f'Patrimoine « {nom} » supprimé.')
    return redirect('smartdocs:patrimoine_list')


# ─────────────────────────────────────────
#  DOCUMENTS
# ─────────────────────────────────────────

#@login_required
def document_upload(request, patrimoine_pk):
    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, patrimoine=patrimoine)
        if form.is_valid():
            doc              = form.save(commit=False)
            doc.patrimoine   = patrimoine
            doc.uploade_par  = request.user
            doc.save()
            messages.success(request, f'Document « {doc.titre} » ajouté.')
            return redirect('smartdocs:patrimoine_detail', pk=patrimoine_pk)
    else:
        form = DocumentForm(patrimoine=patrimoine)

    return render(request, 'smartdocs/document_form.html', {
        'form': form, 'patrimoine': patrimoine
    })


#@login_required
def document_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not doc.fichier:
        raise Http404
    response = FileResponse(doc.fichier.open('rb'), as_attachment=True, filename=os.path.basename(doc.fichier.name))
    return response


#@login_required
@require_POST
def document_delete(request, pk):
    doc        = get_object_or_404(Document, pk=pk)
    patrimoine = doc.patrimoine
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('smartdocs:patrimoine_detail', pk=patrimoine.pk)


# ─────────────────────────────────────────
#  API — pour le Viewer
# ─────────────────────────────────────────

#@login_required
def api_patrimoine_arborescence(request, pk):
    """Retourne l'arborescence étages/pièces en JSON pour le panneau de navigation du viewer."""
    patrimoine = get_object_or_404(Patrimoine, pk=pk)
    data = {
        'id':   patrimoine.pk,
        'nom':  patrimoine.nom,
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
