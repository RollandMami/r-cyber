from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def dashboard(request):
    """Hub central — agrège les stats de toutes les apps."""
    context = {}

    # ── Stats Construction (si app installée) ──────────────────────────────
    try:
        from apps.construction.models import Projet, Facture, TacheGantt
        from django.db.models import Sum

        context['btp'] = {
            'projets_total':   Projet.objects.count(),
            'projets_en_cours':Projet.objects.filter(statut='en_cours').count(),
            'projets_termines':Projet.objects.filter(statut='termine').count(),
            'ca_facture':      Facture.objects.filter(
                statut__in=['envoyee','payee']
            ).aggregate(t=Sum('montant_ttc'))['t'] or 0,
            'ca_paye':         Facture.objects.filter(
                statut='payee'
            ).aggregate(t=Sum('montant_ttc'))['t'] or 0,
            'factures_retard': Facture.objects.filter(statut='retard').count(),
            'taches_retard':   TacheGantt.objects.filter(
                date_fin__lt=timezone.now().date(),
                statut__in=['a_faire','en_cours']
            ).count(),
            'projets_recents': Projet.objects.prefetch_related('photos','taches')
                                             .order_by('-cree_le')[:5],
            'factures_recentes': Facture.objects.select_related('projet')
                                               .order_by('-date_emission')[:5],
        }
    except Exception:
        context['btp'] = None

    # ── Stats SmartDocs (si app installée) ────────────────────────────────
    try:
        from apps.smartdocs.models import Patrimoine, Document
        context['smartdocs'] = {
            'patrimoines': Patrimoine.objects.count(),
            'documents':   Document.objects.count(),
        }
    except Exception:
        context['smartdocs'] = None

    return render(request, 'dashboard/dashboard.html', context)
