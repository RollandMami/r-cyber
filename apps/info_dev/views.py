from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import (
    Client, Projet, Tache, Bug, Livrable,
    Documentation, Devis, LigneDevis, Facture, LigneFacture,
)
from .forms import (
    ClientForm, ProjetForm, TacheForm, BugForm, LivrableForm,
    DocumentationForm, DevisForm, LigneDevisForm, FactureForm, LigneFactureForm,
)


# ─────────────────────────────────────────────────────────────────────────────
#  CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def client_list(request):
    clients = Client.objects.annotate(nb_projets=Count('projets')).order_by('nom')
    return render(request, 'info_dev/client_list.html', {'clients': clients})


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Client créé.')
        return redirect('info_dev:client_list')
    return render(request, 'info_dev/client_form.html', {'form': form, 'action': 'Créer'})


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Client mis à jour.')
        return redirect('info_dev:client_list')
    return render(request, 'info_dev/client_form.html', {
        'form': form, 'client': client, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  PROJETS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def projet_list(request):
    qs     = Projet.objects.select_related('client', 'responsable')
    statut = request.GET.get('statut', '')
    type_p = request.GET.get('type', '')
    q      = request.GET.get('q', '')
    if statut:
        qs = qs.filter(statut=statut)
    if type_p:
        qs = qs.filter(type_projet=type_p)
    if q:
        qs = qs.filter(
            Q(titre__icontains=q) |
            Q(reference__icontains=q) |
            Q(client__nom__icontains=q)
        )
    stats = {
        'total':      Projet.objects.count(),
        'en_cours':   Projet.objects.filter(statut='en_cours').count(),
        'livres':     Projet.objects.filter(statut='livre').count(),
        'ca_facture': Facture.objects.filter(
            statut__in=['envoyee', 'payee']
        ).aggregate(t=Sum('montant_ttc'))['t'] or 0,
        'bugs_ouverts': Bug.objects.filter(statut__in=['ouvert', 'en_cours']).count(),
    }
    return render(request, 'info_dev/projet_list.html', {
        'projets': qs, 'stats': stats,
        'statut_filter': statut, 'type_filter': type_p, 'q': q,
        'statuts': Projet.STATUT, 'types': Projet.TYPE,
    })


@login_required
def projet_create(request):
    form = ProjetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        projet = form.save(commit=False)
        projet.cree_par = request.user
        projet.save()
        messages.success(request, f'Projet {projet.reference} créé.')
        return redirect('info_dev:projet_detail', pk=projet.pk)
    return render(request, 'info_dev/projet_form.html', {'form': form, 'action': 'Créer'})


@login_required
def projet_detail(request, pk):
    projet = get_object_or_404(Projet, pk=pk)
    return render(request, 'info_dev/projet_detail.html', {
        'projet':    projet,
        'taches':    projet.taches.all(),
        'bugs':      projet.bugs.order_by('-date_ouvert')[:8],
        'livrables': projet.livrables.all()[:6],
        'docs':      projet.docs.all()[:5],
        'devis':     projet.devis.all(),
        'factures':  projet.factures.all(),
    })


@login_required
def projet_edit(request, pk):
    projet = get_object_or_404(Projet, pk=pk)
    form = ProjetForm(request.POST or None, instance=projet)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Projet mis à jour.')
        return redirect('info_dev:projet_detail', pk=pk)
    return render(request, 'info_dev/projet_form.html', {
        'form': form, 'projet': projet, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  TÂCHES (kanban + AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def tache_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    taches = projet.taches.select_related('assignee')
    return render(request, 'info_dev/tache_list.html', {
        'projet': projet, 'taches': taches,
        'cols': [
            ('todo',     'À faire',     '#64748b'),
            ('en_cours', 'En cours',    '#6366f1'),
            ('review',   'En révision', '#f59e0b'),
            ('termine',  'Terminées',   '#22c55e'),
        ],
    })


@login_required
def tache_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = TacheForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tache = form.save(commit=False)
        tache.projet = projet
        tache.save()
        messages.success(request, 'Tâche ajoutée.')
        return redirect('info_dev:tache_list', projet_pk=projet_pk)
    return render(request, 'info_dev/tache_form.html', {
        'form': form, 'projet': projet, 'action': 'Créer'
    })


@login_required
def tache_edit(request, pk):
    tache = get_object_or_404(Tache, pk=pk)
    form = TacheForm(request.POST or None, instance=tache)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tâche mise à jour.')
        return redirect('info_dev:tache_list', projet_pk=tache.projet_id)
    return render(request, 'info_dev/tache_form.html', {
        'form': form, 'projet': tache.projet, 'tache': tache, 'action': 'Modifier'
    })


@login_required
def tache_statut_ajax(request, pk):
    """Mise à jour du statut via drag & drop Kanban."""
    if request.method == 'POST':
        tache = get_object_or_404(Tache, pk=pk)
        data = json.loads(request.body)
        nouveau = data.get('statut')
        if nouveau in dict(Tache.STATUT):
            tache.statut = nouveau
            tache.save()
            return JsonResponse({'ok': True, 'statut': tache.statut})
    return JsonResponse({'ok': False}, status=400)


@login_required
def tache_delete(request, pk):
    tache = get_object_or_404(Tache, pk=pk)
    projet_pk = tache.projet_id
    tache.delete()
    messages.success(request, 'Tâche supprimée.')
    return redirect('info_dev:tache_list', projet_pk=projet_pk)


# ─────────────────────────────────────────────────────────────────────────────
#  BUGS / DEMANDES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def bug_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    bugs   = projet.bugs.select_related('assigne_a')
    statut = request.GET.get('statut', '')
    if statut:
        bugs = bugs.filter(statut=statut)
    return render(request, 'info_dev/bug_list.html', {
        'projet': projet, 'bugs': bugs,
        'statut_filter': statut, 'statuts': Bug.STATUT,
    })


@login_required
def bug_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = BugForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bug = form.save(commit=False)
        bug.projet = projet
        bug.save()
        messages.success(request, 'Bug / demande enregistré.')
        return redirect('info_dev:bug_list', projet_pk=projet_pk)
    return render(request, 'info_dev/bug_form.html', {
        'form': form, 'projet': projet, 'action': 'Créer'
    })


@login_required
def bug_detail(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    return render(request, 'info_dev/bug_detail.html', {'bug': bug})


@login_required
def bug_edit(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    form = BugForm(request.POST or None, instance=bug)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Mis à jour.')
        return redirect('info_dev:bug_detail', pk=pk)
    return render(request, 'info_dev/bug_form.html', {
        'form': form, 'projet': bug.projet, 'bug': bug, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  LIVRABLES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def livrable_list(request, projet_pk):
    projet    = get_object_or_404(Projet, pk=projet_pk)
    livrables = projet.livrables.all()
    return render(request, 'info_dev/livrable_list.html', {
        'projet': projet, 'livrables': livrables
    })


@login_required
def livrable_add(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = LivrableForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        l = form.save(commit=False)
        l.projet      = projet
        l.produit_par = request.user
        l.save()
        messages.success(request, 'Livrable ajouté.')
        return redirect('info_dev:livrable_list', projet_pk=projet_pk)
    return render(request, 'info_dev/livrable_form.html', {
        'form': form, 'projet': projet, 'action': 'Ajouter'
    })


@login_required
def livrable_delete(request, pk):
    l = get_object_or_404(Livrable, pk=pk)
    pk_p = l.projet_id
    if l.fichier:
        l.fichier.delete(save=False)
    l.delete()
    messages.success(request, 'Livrable supprimé.')
    return redirect('info_dev:livrable_list', projet_pk=pk_p)


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTATION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def doc_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    docs   = projet.docs.all()
    return render(request, 'info_dev/doc_list.html', {
        'projet': projet, 'docs': docs
    })


@login_required
def doc_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    form = DocumentationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        doc = form.save(commit=False)
        doc.projet     = projet
        doc.redige_par = request.user
        doc.save()
        messages.success(request, 'Documentation créée.')
        return redirect('info_dev:doc_detail', pk=doc.pk)
    return render(request, 'info_dev/doc_form.html', {
        'form': form, 'projet': projet, 'action': 'Créer'
    })


@login_required
def doc_detail(request, pk):
    doc = get_object_or_404(Documentation, pk=pk)
    return render(request, 'info_dev/doc_detail.html', {'doc': doc})


@login_required
def doc_edit(request, pk):
    doc = get_object_or_404(Documentation, pk=pk)
    form = DocumentationForm(request.POST or None, request.FILES or None, instance=doc)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Documentation mise à jour.')
        return redirect('info_dev:doc_detail', pk=pk)
    return render(request, 'info_dev/doc_form.html', {
        'form': form, 'projet': doc.projet, 'doc': doc, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def devis_list(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    return render(request, 'info_dev/devis_list.html', {
        'projet': projet, 'devis': projet.devis.prefetch_related('lignes')
    })


@login_required
def devis_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    initial = {
        'client_nom':     projet.client.nom if projet.client else '',
        'client_adresse': projet.client.adresse if projet.client else '',
        'objet':          f'Développement — {projet.titre}',
    }
    form = DevisForm(request.POST or None, initial=initial)
    LigneFS = modelformset_factory(LigneDevis, form=LigneDevisForm, extra=3, can_delete=True)
    formset = LigneFS(request.POST or None, queryset=LigneDevis.objects.none())
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        devis = form.save(commit=False)
        devis.projet   = projet
        devis.cree_par = request.user
        devis.save()
        for f in formset:
            if f.cleaned_data and not f.cleaned_data.get('DELETE'):
                ligne = f.save(commit=False)
                ligne.devis = devis
                ligne.save()
        messages.success(request, f'Devis {devis.numero} créé.')
        return redirect('info_dev:devis_detail', pk=devis.pk)
    return render(request, 'info_dev/devis_form.html', {
        'form': form, 'formset': formset, 'projet': projet, 'action': 'Créer'
    })


@login_required
def devis_detail(request, pk):
    devis = get_object_or_404(Devis, pk=pk)
    return render(request, 'info_dev/devis_detail.html', {'devis': devis})


@login_required
def devis_statut(request, pk):
    devis = get_object_or_404(Devis, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(Devis.STATUT):
        devis.statut = nouveau
        devis.save()
        messages.success(request, f'Statut : {devis.get_statut_display()}')
    return redirect('info_dev:devis_detail', pk=pk)


@login_required
def devis_print(request, pk):
    return render(request, 'info_dev/devis_print.html', {
        'devis': get_object_or_404(Devis, pk=pk)
    })


# ─────────────────────────────────────────────────────────────────────────────
#  FACTURATION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def facture_list(request, projet_pk):
    projet   = get_object_or_404(Projet, pk=projet_pk)
    factures = projet.factures.prefetch_related('lignes')
    total_f  = factures.filter(statut__in=['envoyee','payee']).aggregate(t=Sum('montant_ttc'))['t'] or 0
    total_p  = factures.filter(statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    return render(request, 'info_dev/facture_list.html', {
        'projet': projet, 'factures': factures,
        'total_facture': total_f, 'total_paye': total_p,
        'total_restant': total_f - total_p,
    })


@login_required
def facture_create(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk)
    initial = {
        'client_nom':     projet.client.nom if projet.client else '',
        'client_adresse': projet.client.adresse if projet.client else '',
        'objet':          f'Développement — {projet.titre}',
    }
    form = FactureForm(request.POST or None, initial=initial)
    LigneFS = modelformset_factory(LigneFacture, form=LigneFactureForm, extra=3, can_delete=True)
    formset = LigneFS(request.POST or None, queryset=LigneFacture.objects.none())
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        facture = form.save(commit=False)
        facture.projet   = projet
        facture.cree_par = request.user
        facture.save()
        for f in formset:
            if f.cleaned_data and not f.cleaned_data.get('DELETE'):
                ligne = f.save(commit=False)
                ligne.facture = facture
                ligne.save()
        messages.success(request, f'Facture {facture.numero} créée.')
        return redirect('info_dev:facture_detail', pk=facture.pk)
    return render(request, 'info_dev/facture_form.html', {
        'form': form, 'formset': formset, 'projet': projet, 'action': 'Créer'
    })


@login_required
def facture_detail(request, pk):
    return render(request, 'info_dev/facture_detail.html', {
        'facture': get_object_or_404(Facture, pk=pk)
    })


@login_required
def facture_statut(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(Facture.STATUT):
        facture.statut = nouveau
        if nouveau == 'payee':
            facture.date_paiement = timezone.now().date()
            facture.montant_paye  = facture.montant_ttc
        facture.save()
        messages.success(request, f'Statut : {facture.get_statut_display()}')
    return redirect('info_dev:facture_detail', pk=pk)


@login_required
def facture_print(request, pk):
    return render(request, 'info_dev/facture_print.html', {
        'facture': get_object_or_404(Facture, pk=pk)
    })
