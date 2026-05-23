from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def dashboard(request):
    """Hub central — agrège les stats de toutes les apps."""
    context = {}
    
    # ── Stats Info-Dev ────────────────────────────────────────────────────────
    try:
        from apps.info_dev.models import Projet as ProjetDev, Bug, Facture as FactureDev
        context['infodev'] = {
            'projets_total':   ProjetDev.objects.count(),
            'projets_encours': ProjetDev.objects.filter(statut='en_cours').count(),
            'projets_livres':  ProjetDev.objects.filter(statut='livre').count(),
            'bugs_ouverts':    Bug.objects.filter(statut__in=['ouvert','en_cours']).count(),
            'ca_facture':      FactureDev.objects.filter(
                statut__in=['envoyee','payee']
            ).aggregate(t=Sum('montant_ttc'))['t'] or 0,
            'projets_recents': ProjetDev.objects.select_related('client')
                                                .order_by('-cree_le')[:5],
            'bugs_recents':    Bug.objects.select_related('projet')
                                          .filter(statut__in=['ouvert','en_cours'])
                                          .order_by('-date_ouvert')[:4],
        }
    except Exception:
        context['infodev'] = None

    # ── Stats Bureau d'Étude ──────────────────────────────────────────────
    try:
        from apps.bureau_etude.models import Mission, Devis
        context['be'] = {
            'missions_total':   Mission.objects.count(),
            'missions_en_cours':Mission.objects.filter(statut='en_cours').count(),
            'missions_rendues': Mission.objects.filter(statut__in=['rendu','valide']).count(),
            'ca_devis':         Devis.objects.filter(statut='accepte').aggregate(t=Sum('montant_ttc'))['t'] or 0,
            'en_retard':        sum(1 for m in Mission.objects.filter(statut__in=['en_cours','prospection']) if m.est_en_retard),
            'missions_recentes':Mission.objects.select_related('responsable').order_by('-cree_le')[:5],
            'devis_recents':    Devis.objects.select_related('mission').order_by('-date_devis')[:4],
        }
    except Exception:
        context['be'] = None

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
            'projets_recents': list(Projet.objects.prefetch_related('photos','taches')
                                             .order_by('-cree_le')[:5]),
            'factures_recentes': list(Facture.objects.select_related('projet')
                                               .order_by('-date_emission')[:5]),
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
