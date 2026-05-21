from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.forms import modelformset_factory
from django.utils import timezone

from .models import (
    Mission, DocumentEntree, PlanLivrable,
    Devis, LigneDevis, NoteCalcul, Reunion,
)
from .forms import (
    MissionForm, DocumentEntreeForm, PlanLivrableForm,
    DevisForm, LigneDevisForm, NoteCalculForm, ReunionForm,
)


# ─────────────────────────────────────────────────────────────────────────────
#  MISSIONS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mission_list(request):
    qs = Mission.objects.select_related('responsable')
    statut = request.GET.get('statut', '')
    q      = request.GET.get('q', '')
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(
            Q(titre__icontains=q) |
            Q(client_nom__icontains=q) |
            Q(reference__icontains=q)
        )
    stats = {
        'total':       Mission.objects.count(),
        'en_cours':    Mission.objects.filter(statut='en_cours').count(),
        'rendus':      Mission.objects.filter(statut='rendu').count(),
        'ca_total':    Devis.objects.filter(statut='accepte').aggregate(t=Sum('montant_ttc'))['t'] or 0,
        'en_retard':   sum(1 for m in Mission.objects.filter(statut__in=['en_cours','prospection']) if m.est_en_retard),
    }
    return render(request, 'bureau_etude/mission_list.html', {
        'missions':      qs,
        'stats':         stats,
        'statut_filter': statut,
        'q':             q,
        'statuts':       Mission.STATUT,
    })


@login_required
def mission_create(request):
    form = MissionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mission = form.save(commit=False)
        mission.cree_par = request.user
        mission.save()
        messages.success(request, f'Mission {mission.reference} créée.')
        return redirect('bureau_etude:mission_detail', pk=mission.pk)
    return render(request, 'bureau_etude/mission_form.html', {'form': form, 'action': 'Créer'})


@login_required
def mission_detail(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    return render(request, 'bureau_etude/mission_detail.html', {
        'mission':    mission,
        'docs':       mission.docs_entree.all(),
        'livrables':  mission.livrables.all(),
        'devis':      mission.devis.all(),
        'notes':      mission.notes_calcul.all(),
        'reunions':   mission.reunions.all()[:5],
    })


@login_required
def mission_edit(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    form = MissionForm(request.POST or None, instance=mission)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Mission mise à jour.')
        return redirect('bureau_etude:mission_detail', pk=pk)
    return render(request, 'bureau_etude/mission_form.html', {
        'form': form, 'mission': mission, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def doc_entree_add(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    form = DocumentEntreeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        doc = form.save(commit=False)
        doc.mission   = mission
        doc.recu_par  = request.user
        doc.save()
        messages.success(request, 'Document ajouté.')
        return redirect('bureau_etude:mission_detail', pk=mission_pk)
    return render(request, 'bureau_etude/doc_form.html', {
        'form': form, 'mission': mission,
        'titre': 'Document d\'entrée', 'icon': 'inbox',
    })


@login_required
def doc_entree_delete(request, pk):
    doc = get_object_or_404(DocumentEntree, pk=pk)
    pk_mission = doc.mission_id
    doc.fichier.delete(save=False)
    doc.delete()
    messages.success(request, 'Document supprimé.')
    return redirect('bureau_etude:mission_detail', pk=pk_mission)


# ─────────────────────────────────────────────────────────────────────────────
#  LIVRABLES (plans, rapports, notes)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def livrable_add(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    form = PlanLivrableForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        livrable = form.save(commit=False)
        livrable.mission     = mission
        livrable.produit_par = request.user
        livrable.save()
        messages.success(request, 'Livrable ajouté.')
        return redirect('bureau_etude:mission_detail', pk=mission_pk)
    return render(request, 'bureau_etude/doc_form.html', {
        'form': form, 'mission': mission,
        'titre': 'Livrable / Plan', 'icon': 'drafting-compass',
    })


@login_required
def livrable_delete(request, pk):
    livrable = get_object_or_404(PlanLivrable, pk=pk)
    pk_mission = livrable.mission_id
    livrable.fichier.delete(save=False)
    livrable.delete()
    messages.success(request, 'Livrable supprimé.')
    return redirect('bureau_etude:mission_detail', pk=pk_mission)


# ─────────────────────────────────────────────────────────────────────────────
#  LIVRABLES — liste complète par mission
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def livrable_list(request, mission_pk):
    mission   = get_object_or_404(Mission, pk=mission_pk)
    livrables = mission.livrables.all()
    phase     = request.GET.get('phase', '')
    if phase:
        livrables = livrables.filter(phase=phase)
    return render(request, 'bureau_etude/livrable_list.html', {
        'mission':   mission,
        'livrables': livrables,
        'phase':     phase,
        'phases':    PlanLivrable.PHASE,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def devis_list(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    return render(request, 'bureau_etude/devis_list.html', {
        'mission': mission,
        'devis':   mission.devis.prefetch_related('lignes'),
    })


@login_required
def devis_create(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    initial = {
        'client_nom':     mission.client_nom,
        'client_adresse': mission.client_adresse,
        'objet':          f'Mission d\'étude — {mission.titre}',
    }
    form = DevisForm(request.POST or None, initial=initial)
    LigneFormSet = modelformset_factory(LigneDevis, form=LigneDevisForm,
                                        extra=3, can_delete=True)
    formset = LigneFormSet(request.POST or None,
                           queryset=LigneDevis.objects.none())
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        devis = form.save(commit=False)
        devis.mission  = mission
        devis.cree_par = request.user
        devis.save()
        for f in formset:
            if f.cleaned_data and not f.cleaned_data.get('DELETE'):
                ligne = f.save(commit=False)
                ligne.devis = devis
                ligne.save()
        messages.success(request, f'Devis {devis.numero} créé.')
        return redirect('bureau_etude:devis_detail', pk=devis.pk)
    return render(request, 'bureau_etude/devis_form.html', {
        'form': form, 'formset': formset,
        'mission': mission, 'action': 'Créer',
    })


@login_required
def devis_detail(request, pk):
    devis = get_object_or_404(Devis, pk=pk)
    return render(request, 'bureau_etude/devis_detail.html', {'devis': devis})


@login_required
def devis_statut(request, pk):
    devis = get_object_or_404(Devis, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(Devis.STATUT):
        devis.statut = nouveau
        devis.save()
        # Si accepté, mettre à jour les honoraires de la mission
        if nouveau == 'accepte':
            devis.mission.honoraires_ht  = devis.montant_ht
            devis.mission.honoraires_ttc = devis.montant_ttc
            devis.mission.save()
        messages.success(request, f'Statut : {devis.get_statut_display()}')
    return redirect('bureau_etude:devis_detail', pk=pk)


@login_required
def devis_print(request, pk):
    devis = get_object_or_404(Devis, pk=pk)
    return render(request, 'bureau_etude/devis_print.html', {'devis': devis})


# ─────────────────────────────────────────────────────────────────────────────
#  NOTES DE CALCUL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def note_list(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    return render(request, 'bureau_etude/note_list.html', {
        'mission': mission,
        'notes':   mission.notes_calcul.all(),
    })


@login_required
def note_create(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    form = NoteCalculForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        note = form.save(commit=False)
        note.mission    = mission
        note.redige_par = request.user
        if note.valide:
            note.valide_par = request.user
        note.save()
        messages.success(request, 'Note de calcul créée.')
        return redirect('bureau_etude:note_detail', pk=note.pk)
    return render(request, 'bureau_etude/note_form.html', {
        'form': form, 'mission': mission, 'action': 'Créer'
    })


@login_required
def note_detail(request, pk):
    note = get_object_or_404(NoteCalcul, pk=pk)
    return render(request, 'bureau_etude/note_detail.html', {'note': note})


@login_required
def note_edit(request, pk):
    note = get_object_or_404(NoteCalcul, pk=pk)
    form = NoteCalculForm(request.POST or None, request.FILES or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        saved = form.save(commit=False)
        if saved.valide and not saved.valide_par:
            saved.valide_par      = request.user
            saved.date_validation = timezone.now().date()
        saved.save()
        messages.success(request, 'Note mise à jour.')
        return redirect('bureau_etude:note_detail', pk=pk)
    return render(request, 'bureau_etude/note_form.html', {
        'form': form, 'mission': note.mission, 'note': note, 'action': 'Modifier'
    })


# ─────────────────────────────────────────────────────────────────────────────
#  RÉUNIONS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def reunion_list(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    return render(request, 'bureau_etude/reunion_list.html', {
        'mission':  mission,
        'reunions': mission.reunions.all(),
    })


@login_required
def reunion_create(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    form = ReunionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        reunion = form.save(commit=False)
        reunion.mission    = mission
        reunion.redige_par = request.user
        reunion.save()
        messages.success(request, 'Réunion enregistrée.')
        return redirect('bureau_etude:reunion_detail', pk=reunion.pk)
    return render(request, 'bureau_etude/reunion_form.html', {
        'form': form, 'mission': mission, 'action': 'Créer'
    })


@login_required
def reunion_detail(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    return render(request, 'bureau_etude/reunion_detail.html', {'reunion': reunion})


@login_required
def reunion_edit(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    form = ReunionForm(request.POST or None, request.FILES or None, instance=reunion)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Réunion mise à jour.')
        return redirect('bureau_etude:reunion_detail', pk=pk)
    return render(request, 'bureau_etude/reunion_form.html', {
        'form': form, 'mission': reunion.mission, 'reunion': reunion, 'action': 'Modifier'
    })
