from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Avg, Count, Q
from django.forms import modelformset_factory
from django.utils import timezone
import json

from .models import (
    Projet, PhotoProjet, DocumentClient, DocumentChantier,
    TacheGantt, LigneBudget, BonCommande, LigneBonCommande,
    RapportActivite, Facture, LigneFacture,
)
from .forms import (
    ProjetForm, PhotoProjetForm, DocumentClientForm, DocumentChantierForm,
    TacheGanttForm, LigneBudgetForm, BonCommandeForm, LigneBonCommandeForm,
    RapportActiviteForm, FactureForm, LigneFactureForm,
)


# ─────────────────────────────────────────────────────────────────────────────
#  VITRINE (publique)
# ─────────────────────────────────────────────────────────────────────────────

def vitrine(request):
    """Page publique — projets visibles."""
    projets = Projet.objects.filter(visible_vitrine=True).prefetch_related('photos')
    return render(request, 'construction/vitrine.html', {'projets': projets})


def vitrine_detail(request, pk):
    """Détail public d'un projet."""
    projet = get_object_or_404(Projet, pk=pk, visible_vitrine=True)
    photos = projet.photos.all().order_by('ordre')
    return render(request, 'construction/vitrine_detail.html', {
        'projet': projet,
        'photos': photos,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  DASHBOARD PRODUCTION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Tableau de bord global de l'activité construction."""
    return redirect('dashboard:index')


# ─────────────────────────────────────────────────────────────────────────────
#  PROJETS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def projet_list(request):
    qs = Projet.objects.prefetch_related('photos', 'taches')
    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '')
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(client_nom__icontains=q) | Q(reference__icontains=q))
    return render(request, 'construction/projet_list.html', {
        'projets': qs,
        'statut_filter': statut,
        'q': q,
        'statuts': Projet.STATUT,
    })


@login_required
def projet_create(request):
    form = ProjetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        projet = form.save(commit=False)
        projet.cree_par = request.user
        projet.save()
        messages.success(request, f'Projet « {projet.titre} » créé — {projet.reference}')
        return redirect('construction:projet_detail', pk=projet.pk)
    return render(request, 'construction/projet_form.html', {'form': form, 'action': 'Créer'})


@login_required
def projet_detail(request, pk):
    projet = get_object_or_404(Projet, pk=pk)
    return render(request, 'construction/projet_detail.html', {
        'projet':       projet,
        'photos':       projet.photos.all(),
        'docs_client':  projet.docs_client.all(),
        'docs_chantier':projet.docs_chantier.all(),
        'taches':       projet.taches.filter(parent=None),
        'rapports':     projet.rapports.all()[:5],
        'factures':     projet.factures.all(),
        'bons':         projet.bons_commande.all()[:5],
        'budget_resume': projet.lignes_budget.values('categorie').annotate(
            prevu=Sum('montant_prevu'), reel=Sum('montant_reel')
        ),
    })


@login_required
def projet_edit(request, pk):
    projet = get_object_or_404(Projet, pk=pk)
    form = ProjetForm(request.POST or None, instance=projet)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Projet mis à jour.')
        return redirect('construction:projet_detail', pk=pk)
    return render(request, 'construction/projet_form.html', {
        'form': form, 'projet': projet, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTOS VITRINE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def photo_add(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    if projet.photos.count() >= 5:
        messages.error(request, 'Maximum 5 photos par projet.')
        return redirect('construction:projet_detail', pk=projet_pk)
    form = PhotoProjetForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        photo = form.save(commit=False)
        photo.projet = projet
        photo.save()
        messages.success(request, 'Photo ajoutée.')
        return redirect('construction:projet_detail', pk=projet_pk)
    return render(request, 'construction/photo_form.html', {
        'form': form, 'projet': projet
    })


@login_required
def photo_delete(request, pk):
    photo = get_object_or_404(PhotoProjet, pk=pk)
    projet_pk = photo.projet.pk
    photo.image.delete(save=False)
    photo.delete()
    messages.success(request, 'Photo supprimée.')
    return redirect('construction:projet_detail', pk=projet_pk)


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS CLIENT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def doc_client_add(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = DocumentClientForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        doc = form.save(commit=False)
        doc.projet = projet
        doc.recu_par = request.user
        doc.save()
        messages.success(request, 'Document client ajouté.')
        return redirect('construction:projet_detail', pk=projet_pk)
    return render(request, 'construction/doc_form.html', {
        'form': form, 'projet': projet, 'titre': 'Document client', 'icon': 'inbox'
    })


@login_required
def doc_client_delete(request, pk):
    doc = get_object_or_404(DocumentClient, pk=pk)
    pk_projet = doc.projet.pk
    doc.fichier.delete(save=False)
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('construction:projet_detail', pk=pk_projet)


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS CHANTIER
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def doc_chantier_add(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = DocumentChantierForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        doc = form.save(commit=False)
        doc.projet = projet
        doc.produit_par = request.user
        doc.save()
        messages.success(request, 'Document chantier ajouté.')
        return redirect('construction:projet_detail', pk=projet_pk)
    return render(request, 'construction/doc_form.html', {
        'form': form, 'projet': projet, 'titre': 'Document chantier', 'icon': 'folder-open'
    })


@login_required
def doc_chantier_delete(request, pk):
    doc = get_object_or_404(DocumentChantier, pk=pk)
    pk_projet = doc.projet.pk
    doc.fichier.delete(save=False)
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('construction:projet_detail', pk=pk_projet)


# ─────────────────────────────────────────────────────────────────────────────
#  PLANNING GANTT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def gantt_view(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    taches = projet.taches.select_related('assignee_a', 'parent').prefetch_related('dependances')
    return render(request, 'construction/gantt.html', {
        'projet': projet,
        'taches': taches,
        'taches_json': _taches_to_json(taches),
    })


def _taches_to_json(taches):
    data = []
    for t in taches:
        data.append({
            'id':          t.pk,
            'titre':       t.titre,
            'debut':       t.date_debut.isoformat(),
            'fin':         t.date_fin.isoformat(),
            'avancement':  t.avancement,
            'statut':      t.statut,
            'couleur':     t.couleur,
            'parent':      t.parent_id,
            'assignee':    t.assignee_a.get_full_name() if t.assignee_a else '',
            'retard':      t.est_en_retard,
            'deps':        list(t.dependances.values_list('pk', flat=True)),
        })
    return json.dumps(data, ensure_ascii=False)


@login_required
def tache_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = TacheGanttForm(projet=projet, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tache = form.save(commit=False)
        tache.projet = projet
        tache.save()
        form.save_m2m()
        messages.success(request, f'Tâche « {tache.titre} » ajoutée.')
        return redirect('construction:gantt', projet_pk=projet_pk)
    return render(request, 'construction/tache_form.html', {
        'form': form, 'projet': projet, 'action': 'Créer'
    })


@login_required
def tache_edit(request, pk):
    tache = get_object_or_404(TacheGantt, pk=pk)
    form = TacheGanttForm(projet=tache.projet, data=request.POST or None, instance=tache)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tâche mise à jour.')
        return redirect('construction:gantt', projet_pk=tache.projet_id)
    return render(request, 'construction/tache_form.html', {
        'form': form, 'projet': tache.projet, 'tache': tache, 'action': 'Modifier'
    })


@login_required
def tache_delete(request, pk):
    tache = get_object_or_404(TacheGantt, pk=pk)
    projet_pk = tache.projet_id
    tache.delete()
    messages.success(request, 'Tâche supprimée.')
    return redirect('construction:gantt', projet_pk=projet_pk)


@login_required
def tache_avancement_ajax(request, pk):
    """Mise à jour de l'avancement via AJAX depuis le Gantt."""
    if request.method == 'POST':
        tache = get_object_or_404(TacheGantt, pk=pk)
        data = json.loads(request.body)
        avancement = max(0, min(100, int(data.get('avancement', tache.avancement))))
        tache.avancement = avancement
        if avancement == 100:
            tache.statut = 'termine'
        elif avancement > 0:
            tache.statut = 'en_cours'
        tache.save()
        return JsonResponse({'ok': True, 'avancement': tache.avancement, 'statut': tache.statut})
    return JsonResponse({'ok': False}, status=405)


# ─────────────────────────────────────────────────────────────────────────────
#  BUDGET
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def budget_view(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    lignes = projet.lignes_budget.select_related('tache').order_by('categorie')
    resume = lignes.values('categorie').annotate(
        prevu=Sum('montant_prevu'), reel=Sum('montant_reel')
    )
    total_prevu = lignes.aggregate(t=Sum('montant_prevu'))['t'] or 0
    total_reel  = lignes.aggregate(t=Sum('montant_reel'))['t'] or 0
    return render(request, 'construction/budget.html', {
        'projet': projet, 'lignes': lignes, 'resume': resume,
        'total_prevu': total_prevu, 'total_reel': total_reel,
        'ecart': total_reel - total_prevu,
    })


@login_required
def budget_ligne_add(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = LigneBudgetForm(projet=projet, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ligne = form.save(commit=False)
        ligne.projet = projet
        ligne.save()
        messages.success(request, 'Ligne ajoutée.')
        return redirect('construction:budget', projet_pk=projet_pk)
    return render(request, 'construction/budget_ligne_form.html', {
        'form': form, 'projet': projet
    })


@login_required
def budget_ligne_edit(request, pk):
    ligne = get_object_or_404(LigneBudget, pk=pk)
    form = LigneBudgetForm(projet=ligne.projet, data=request.POST or None, instance=ligne)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Ligne mise à jour.')
        return redirect('construction:budget', projet_pk=ligne.projet_id)
    return render(request, 'construction/budget_ligne_form.html', {
        'form': form, 'projet': ligne.projet, 'ligne': ligne
    })


@login_required
def budget_ligne_delete(request, pk):
    ligne = get_object_or_404(LigneBudget, pk=pk)
    projet_pk = ligne.projet_id
    ligne.delete()
    messages.success(request, 'Ligne supprimée.')
    return redirect('construction:budget', projet_pk=projet_pk)


# ─────────────────────────────────────────────────────────────────────────────
#  BONS DE COMMANDE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def bon_commande_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    bons = projet.bons_commande.prefetch_related('lignes')
    return render(request, 'construction/bon_list.html', {'projet': projet, 'bons': bons})


@login_required
def bon_commande_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = BonCommandeForm(request.POST or None)
    LigneFormSet = modelformset_factory(LigneBonCommande, form=LigneBonCommandeForm,
                                        extra=3, can_delete=True)
    formset = LigneFormSet(request.POST or None, queryset=LigneBonCommande.objects.none())

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        bon = form.save(commit=False)
        bon.projet = projet
        bon.cree_par = request.user
        bon.save()
        for f in formset:
            if f.cleaned_data and not f.cleaned_data.get('DELETE'):
                ligne = f.save(commit=False)
                ligne.bon = bon
                ligne.save()
        messages.success(request, f'Bon {bon.numero} créé.')
        return redirect('construction:bon_detail', pk=bon.pk)

    return render(request, 'construction/bon_form.html', {
        'form': form, 'formset': formset, 'projet': projet, 'action': 'Créer'
    })


@login_required
def bon_commande_detail(request, pk):
    bon = get_object_or_404(BonCommande, pk=pk)
    return render(request, 'construction/bon_detail.html', {'bon': bon})


@login_required
def bon_commande_statut(request, pk):
    """Changer le statut d'un bon via POST simple."""
    bon = get_object_or_404(BonCommande, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(BonCommande.STATUT):
        bon.statut = nouveau
        bon.save()
        messages.success(request, f'Statut mis à jour : {bon.get_statut_display()}')
    return redirect('construction:bon_detail', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
#  RAPPORTS D'ACTIVITÉ
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def rapport_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    rapports = projet.rapports.select_related('redige_par').prefetch_related('taches_concernees')
    return render(request, 'construction/rapport_list.html', {
        'projet': projet, 'rapports': rapports
    })


@login_required
def rapport_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = RapportActiviteForm(projet=projet, data=request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        rapport = form.save(commit=False)
        rapport.projet = projet
        rapport.redige_par = request.user
        rapport.save()
        form.save_m2m()
        messages.success(request, 'Rapport créé.')
        return redirect('construction:rapport_detail', pk=rapport.pk)
    return render(request, 'construction/rapport_form.html', {
        'form': form, 'projet': projet, 'action': 'Créer'
    })


@login_required
def rapport_detail(request, pk):
    rapport = get_object_or_404(RapportActivite, pk=pk)
    return render(request, 'construction/rapport_detail.html', {'rapport': rapport})


@login_required
def rapport_edit(request, pk):
    rapport = get_object_or_404(RapportActivite, pk=pk)
    form = RapportActiviteForm(
        projet=rapport.projet,
        data=request.POST or None,
        files=request.FILES or None,
        instance=rapport
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Rapport mis à jour.')
        return redirect('construction:rapport_detail', pk=pk)
    return render(request, 'construction/rapport_form.html', {
        'form': form, 'projet': rapport.projet, 'rapport': rapport, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  FACTURATION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def facture_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    factures = projet.factures.prefetch_related('lignes')
    total_facture = factures.filter(statut__in=['envoyee','payee']).aggregate(t=Sum('montant_ttc'))['t'] or 0
    total_paye    = factures.filter(statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    return render(request, 'construction/facture_list.html', {
        'projet': projet, 'factures': factures,
        'total_facture': total_facture, 'total_paye': total_paye,
        'total_restant': total_facture - total_paye,
    })


@login_required
def facture_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    initial = {
        'client_nom':     projet.client_nom,
        'client_adresse': projet.client_adresse,
        'objet':          f'Travaux — {projet.titre}',
    }
    form = FactureForm(request.POST or None, initial=initial)
    LigneFormSet = modelformset_factory(LigneFacture, form=LigneFactureForm,
                                        extra=3, can_delete=True)
    formset = LigneFormSet(request.POST or None, queryset=LigneFacture.objects.none(),
                           form_kwargs={'projet': projet})

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        facture = form.save(commit=False)
        facture.projet = projet
        facture.cree_par = request.user
        facture.save()
        for f in formset:
            if f.cleaned_data and not f.cleaned_data.get('DELETE'):
                ligne = f.save(commit=False)
                ligne.facture = facture
                ligne.save()
        messages.success(request, f'Facture {facture.numero} créée.')
        return redirect('construction:facture_detail', pk=facture.pk)

    return render(request, 'construction/facture_form.html', {
        'form': form, 'formset': formset, 'projet': projet, 'action': 'Créer'
    })


@login_required
def facture_detail(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    return render(request, 'construction/facture_detail.html', {'facture': facture})


@login_required
def facture_edit(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    form = FactureForm(request.POST or None, instance=facture)
    LigneFormSet = modelformset_factory(LigneFacture, form=LigneFactureForm,
                                        extra=2, can_delete=True)
    formset = LigneFormSet(
        request.POST or None,
        queryset=facture.lignes.all(),
        form_kwargs={'projet': facture.projet}
    )
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, 'Facture mise à jour.')
        return redirect('construction:facture_detail', pk=pk)
    return render(request, 'construction/facture_form.html', {
        'form': form, 'formset': formset, 'projet': facture.projet,
        'facture': facture, 'action': 'Modifier'
    })


@login_required
def facture_statut(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(Facture.STATUT):
        facture.statut = nouveau
        if nouveau == 'payee':
            facture.date_paiement = timezone.now().date()
            facture.montant_paye = facture.montant_ttc
        facture.save()
        messages.success(request, f'Statut : {facture.get_statut_display()}')
    return redirect('construction:facture_detail', pk=pk)


@login_required
def facture_print(request, pk):
    """Vue d'impression — page blanche sans navbar."""
    facture = get_object_or_404(Facture, pk=pk)
    return render(request, 'construction/facture_print.html', {'facture': facture})
