from django.http import JsonResponse
from apps.core_api.models import AppVersion

def api_version(request):
    """
    GET /api/version/
    Retourne la version active de l'application.
    Appelé par le Service Worker au démarrage pour détecter les mises à jour.
    """
    try:
        version = AppVersion.objects.filter(est_active=True).first()
        if not version:
            return JsonResponse({'version': '1.0.0', 'apk_url': None, 'changelog': ''})

        return JsonResponse({
            'version':      version.version,
            'version_code': version.version_code,
            'apk_url':      version.get_apk_url(),
            'changelog':    version.changelog,
            'obligatoire':  version.obligatoire,
        })
    except Exception:
        return JsonResponse({'version': '1.0.0', 'apk_url': None, 'changelog': ''})


def api_offline_sync(request):
    """
    POST /api/sync/
    Reçoit les modifications offline et les applique en base.
    """
    import json
    from django.contrib.auth.decorators import login_required
    from django.views.decorators.csrf import csrf_exempt

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        payload  = json.loads(request.body)
        changes  = payload.get('changes', [])
        results  = []

        for change in changes:
            result = _apply_change(change, request.user)
            results.append(result)

        return JsonResponse({'synced': len([r for r in results if r['ok']]), 'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _apply_change(change, user):
    """Applique une modification offline selon son type."""
    from apps.smartdocs.models import Patrimoine, Document

    try:
        change_type = change.get('type')
        data        = change.get('data', {})

        if change_type == 'patrimoine_create':
            p = Patrimoine.objects.create(
                nom        = data.get('nom', 'Sans titre'),
                adresse    = data.get('adresse', ''),
                cree_par   = user if user.is_authenticated else None,
            )
            return {'ok': True, 'type': change_type, 'id': p.pk}

        if change_type == 'patrimoine_update':
            pk = data.get('id')
            Patrimoine.objects.filter(pk=pk).update(
                nom     = data.get('nom'),
                adresse = data.get('adresse', ''),
            )
            return {'ok': True, 'type': change_type, 'id': pk}

        return {'ok': False, 'type': change_type, 'error': 'Type inconnu'}

    except Exception as e:
        return {'ok': False, 'type': change.get('type'), 'error': str(e)}