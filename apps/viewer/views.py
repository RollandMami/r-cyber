from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404

from apps.smartdocs.models import Patrimoine, Etage


@login_required
def viewer(request, patrimoine_pk):
    """Vue principale du viewer 3D."""
    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)

    if not patrimoine.has_viewer():
        return render(request, 'viewer/no_model.html', {'patrimoine': patrimoine})

    etages = patrimoine.etages.prefetch_related('pieces').all()

    return render(request, 'viewer/viewer.html', {
        'patrimoine': patrimoine,
        'etages':     etages,
        'json_url':   patrimoine.fichier_json.url,
    })


@login_required
def api_geometrie(request, patrimoine_pk):
    """
    Sert le JSON de géométrie au Three.js.
    Peut filtrer par étage via ?etage=<pk>
    """
    import json

    patrimoine = get_object_or_404(Patrimoine, pk=patrimoine_pk)
    if not patrimoine.fichier_json:
        raise Http404('Pas de modèle 3D converti pour ce patrimoine.')

    etage_pk = request.GET.get('etage')

    with patrimoine.fichier_json.open('r') as f:
        data = json.load(f)

    # Filtre par étage si demandé
    if etage_pk:
        try:
            etage_obj = Etage.objects.get(pk=etage_pk, patrimoine=patrimoine)
            data['etages'] = [
                e for e in data.get('etages', [])
                if str(e.get('id')) == etage_pk or e.get('ifc_guid') == etage_obj.ifc_guid
            ]
        except Etage.DoesNotExist:
            pass

    return JsonResponse(data)
