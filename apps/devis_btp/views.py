"""
MOREX Devis BTP — views.py
Toutes les vues du module devis BTP indépendant.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Q
from django.utils import timezone

from .models import (
    Materiau, Dosage, Devis, LigneAvantMetre, RecapAvantMetre,
    EquipePHMO, TacheForfaitMO, FraisChantier, LigneDEPS,
    BonCommandeMateriaux, LigneBonCommande, LigneNomenclature,
)
from .utils import (
    calculer_nomenclature, calculer_deps,
    calcul_recap_financier, nombre_en_lettres, fmt_ar,
)
from .forms import (
    DevisForm, MateriauForm, DosageForm,
    LigneAvantMetreForm, RecapAvantMetreForm,
    EquipePHMOForm, TacheForfaitMOForm, FraisChantierForm,
)


# ─────────────────────────────────────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    devis_list = Devis.objects.filter(cree_par=request.user).order_by('-date_devis')[:10]
    total_mat  = Materiau.objects.filter(actif=True).count()
    total_dos  = Dosage.objects.filter(actif=True).count()
    ctx = {
        'devis_list': devis_list,
        'total_mat':  total_mat,
        'total_dos':  total_dos,
        'page': 'dashboard',
    }
    return render(request, 'devis_btp/dashboard.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
#  DEVIS — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def devis_list(request):
    qs = Devis.objects.filter(cree_par=request.user).order_by('-date_devis')
    q  = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(client_nom__icontains=q) | Q(titre__icontains=q) | Q(reference__icontains=q))
    return render(request, 'devis_btp/devis_list.html', {'devis_list': qs, 'q': q})


@login_required
def devis_create(request):
    """
    Crée un nouveau devis.
    Paramètres GET optionnels :
      - source      : 'bureau_etude' | 'construction' | 'direct'
      - mission_id  : PK de la Mission liée
      - projet_id   : PK du Projet lié
      - client      : nom du client pré-rempli
    """
    initial = {
        'source':       request.GET.get('source', 'direct'),
        'client_nom':   request.GET.get('client', ''),
        'mission_id_ref': request.GET.get('mission_id', ''),
        'projet_id_ref':  request.GET.get('projet_id', ''),
    }
    form = DevisForm(request.POST or None, initial=initial)
    if form.is_valid():
        devis = form.save(commit=False)
        devis.cree_par = request.user
        devis.save()
        messages.success(request, f'Devis {devis.reference} créé.')
        return redirect('devis_btp:avantmetre', pk=devis.pk)
    return render(request, 'devis_btp/devis_form.html', {'form': form, 'title': 'Nouveau devis'})


@login_required
def devis_edit(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    form  = DevisForm(request.POST or None, instance=devis)
    if form.is_valid():
        form.save()
        messages.success(request, 'Devis mis à jour.')
        return redirect('devis_btp:devis_detail', pk=devis.pk)
    return render(request, 'devis_btp/devis_form.html', {
        'form': form, 'devis': devis, 'title': f'Modifier {devis.reference}'
    })


@login_required
def devis_delete(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    if request.method == 'POST':
        ref = devis.reference
        devis.delete()
        messages.success(request, f'Devis {ref} supprimé.')
        return redirect('devis_btp:devis_list')
    return render(request, 'devis_btp/confirm_delete.html', {'obj': devis})


@login_required
def devis_detail(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    return render(request, 'devis_btp/devis_detail.html', {'devis': devis})


# ─────────────────────────────────────────────────────────────────────────────
#  BASE MATÉRIAUX
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def materiaux_list(request):
    qs = Materiau.objects.all().order_by('code')
    return render(request, 'devis_btp/materiaux_list.html', {'materiaux': qs})


@login_required
def materiau_create(request):
    form = MateriauForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Matériau ajouté.')
        return redirect('devis_btp:materiaux_list')
    return render(request, 'devis_btp/materiau_form.html', {'form': form, 'title': 'Nouveau matériau'})


@login_required
def materiau_edit(request, pk):
    mat  = get_object_or_404(Materiau, pk=pk)
    form = MateriauForm(request.POST or None, instance=mat)
    if form.is_valid():
        form.save()
        messages.success(request, 'Matériau mis à jour.')
        return redirect('devis_btp:materiaux_list')
    return render(request, 'devis_btp/materiau_form.html', {
        'form': form, 'mat': mat, 'title': f'Modifier {mat.designation}'
    })


@login_required
def materiau_delete(request, pk):
    mat = get_object_or_404(Materiau, pk=pk)
    if request.method == 'POST':
        mat.delete()
        messages.success(request, 'Matériau supprimé.')
        return redirect('devis_btp:materiaux_list')
    return render(request, 'devis_btp/confirm_delete.html', {'obj': mat})


# ─────────────────────────────────────────────────────────────────────────────
#  BASE DOSAGES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dosages_list(request):
    qs = Dosage.objects.all().order_by('categorie', 'dosage_kg')
    return render(request, 'devis_btp/dosages_list.html', {'dosages': qs})


@login_required
def dosage_create(request):
    form = DosageForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Dosage ajouté.')
        return redirect('devis_btp:dosages_list')
    return render(request, 'devis_btp/dosage_form.html', {'form': form, 'title': 'Nouveau dosage'})


@login_required
def dosage_edit(request, pk):
    dos  = get_object_or_404(Dosage, pk=pk)
    form = DosageForm(request.POST or None, instance=dos)
    if form.is_valid():
        form.save()
        messages.success(request, 'Dosage mis à jour.')
        return redirect('devis_btp:dosages_list')
    return render(request, 'devis_btp/dosage_form.html', {
        'form': form, 'dos': dos, 'title': f'Modifier {dos.code}'
    })


@login_required
def dosage_delete(request, pk):
    dos = get_object_or_404(Dosage, pk=pk)
    if request.method == 'POST':
        dos.delete()
        return redirect('devis_btp:dosages_list')
    return render(request, 'devis_btp/confirm_delete.html', {'obj': dos})


# ─────────────────────────────────────────────────────────────────────────────
#  AVANT-MÉTRÉ
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def avantmetre(request, pk):
    devis  = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    lignes = devis.avant_metre.order_by('ordre', 'pk')
    recap  = devis.recap_am.order_by('ordre', 'numero')
    form   = LigneAvantMetreForm(request.POST or None, initial={'devis': devis})

    if request.method == 'POST' and form.is_valid():
        ligne = form.save(commit=False)
        ligne.devis = devis
        ligne.ordre = devis.avant_metre.count()
        ligne.save()
        # Mettre à jour le récap
        _update_recap(devis)
        messages.success(request, 'Ligne ajoutée.')
        return redirect('devis_btp:avantmetre', pk=pk)

    return render(request, 'devis_btp/avantmetre.html', {
        'devis': devis, 'lignes': lignes, 'recap': recap, 'form': form,
    })


@login_required
def avantmetre_edit_ligne(request, pk, ligne_pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    ligne = get_object_or_404(LigneAvantMetre, pk=ligne_pk, devis=devis)
    form  = LigneAvantMetreForm(request.POST or None, instance=ligne)
    if form.is_valid():
        form.save()
        _update_recap(devis)
        return redirect('devis_btp:avantmetre', pk=pk)
    return render(request, 'devis_btp/avantmetre_ligne_form.html', {
        'devis': devis, 'form': form, 'ligne': ligne
    })


@login_required
def avantmetre_delete_ligne(request, pk, ligne_pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    ligne = get_object_or_404(LigneAvantMetre, pk=ligne_pk, devis=devis)
    if request.method == 'POST':
        ligne.delete()
        _update_recap(devis)
        return redirect('devis_btp:avantmetre', pk=pk)
    return render(request, 'devis_btp/confirm_delete.html', {'obj': ligne})


def _update_recap(devis):
    """Recalcule le RecapAvantMetre depuis les lignes."""
    from django.db.models import Sum as DSum
    # Grouper par designation+unite
    groups = {}
    for ligne in devis.avant_metre.order_by('ordre', 'pk'):
        key = (ligne.ouvrage_num or '', ligne.designation, ligne.unite)
        if key not in groups:
            groups[key] = {
                'numero': ligne.ouvrage_num or '',
                'designation': ligne.designation,
                'unite': ligne.unite,
                'qam': 0,
                'ordre': len(groups),
            }
        groups[key]['qam'] += float(ligne.qam)

    # Mettre à jour ou créer les RecapAvantMetre
    existing = {r.designation: r for r in devis.recap_am.all()}
    for (num, desig, unite), data in groups.items():
        if desig in existing:
            r = existing[desig]
            r.numero = data['numero']
            r.unite  = data['unite']
            r.qam    = round(data['qam'], 4)
            r.ordre  = data['ordre']
            r.save()
        else:
            RecapAvantMetre.objects.create(
                devis=devis,
                numero=data['numero'],
                designation=desig,
                unite=unite,
                qam=round(data['qam'], 4),
                ordre=data['ordre'],
            )
    # Supprimer les recap obsolètes
    for desig, r in existing.items():
        if desig not in {k[1] for k in groups.keys()}:
            r.delete()


# ─────────────────────────────────────────────────────────────────────────────
#  NOMENCLATURE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def nomenclature(request, pk):
    devis  = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    recap  = devis.recap_am.select_related('dosage').order_by('ordre')
    dosages = Dosage.objects.filter(actif=True).order_by('categorie', 'dosage_kg')
    materiaux = Materiau.objects.filter(actif=True).order_by('code')

    if request.method == 'POST':
        # Mise à jour des dosages associés
        for r in recap:
            dos_id = request.POST.get(f'dosage_{r.pk}', '')
            if dos_id:
                try:
                    r.dosage = Dosage.objects.get(pk=dos_id)
                except Dosage.DoesNotExist:
                    r.dosage = None
            else:
                r.dosage = None
            r.save()
        # Recalcul
        calculer_nomenclature(devis)
        messages.success(request, 'Nomenclature calculée.')
        return redirect('devis_btp:nomenclature', pk=pk)

    # Récupérer nomenclature calculée
    nom_data = {}
    for ligne in devis.nomenclature.select_related('recap_am', 'materiau').all():
        key = ligne.recap_am.designation
        if key not in nom_data:
            nom_data[key] = {}
        nom_data[key][ligne.materiau.code] = {
            'nette': float(ligne.quantite_nette),
            'chute': float(ligne.quantite_chute),
        }

    return render(request, 'devis_btp/nomenclature.html', {
        'devis': devis, 'recap': recap,
        'dosages': dosages, 'materiaux': materiaux,
        'nom_data': json.dumps(nom_data),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  PHMO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def phmo(request, pk):
    devis  = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    equipes = devis.equipes_phmo.order_by('ordre')
    forfaits = devis.taches_forfait.order_by('ordre')

    if request.method == 'POST':
        mode = request.POST.get('mode_mo', 'horaire')
        devis.mode_mo = mode
        devis.save(update_fields=['mode_mo'])
        messages.success(request, 'Mode MO mis à jour.')
        return redirect('devis_btp:phmo', pk=pk)

    ctx = {
        'devis': devis,
        'equipes': equipes,
        'forfaits': forfaits,
        'equipe_form': EquipePHMOForm(),
        'forfait_form': TacheForfaitMOForm(),
        'total_equipes': sum(e.cout_total for e in equipes),
        'total_forfaits': float(forfaits.aggregate(t=Sum('montant_mo'))['t'] or 0),
    }
    return render(request, 'devis_btp/phmo.html', ctx)


@login_required
def phmo_add_equipe(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    form  = EquipePHMOForm(request.POST)
    if form.is_valid():
        eq = form.save(commit=False)
        eq.devis = devis
        eq.save()
        messages.success(request, 'Équipe ajoutée.')
    return redirect('devis_btp:phmo', pk=pk)


@login_required
def phmo_delete_equipe(request, pk, equipe_pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    eq    = get_object_or_404(EquipePHMO, pk=equipe_pk, devis=devis)
    if request.method == 'POST':
        eq.delete()
    return redirect('devis_btp:phmo', pk=pk)


@login_required
def phmo_add_forfait(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    form  = TacheForfaitMOForm(request.POST)
    if form.is_valid():
        t = form.save(commit=False)
        t.devis = devis
        t.save()
        messages.success(request, 'Tâche forfait ajoutée.')
    return redirect('devis_btp:phmo', pk=pk)


@login_required
def phmo_delete_forfait(request, pk, forfait_pk):
    devis   = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    forfait = get_object_or_404(TacheForfaitMO, pk=forfait_pk, devis=devis)
    if request.method == 'POST':
        forfait.delete()
    return redirect('devis_btp:phmo', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
#  FRAIS DE CHANTIER
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def frais_chantier(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    frais = devis.frais_chantier.order_by('categorie', 'ordre')
    totaux = {}
    for cat, label in FraisChantier.CATEGORIE:
        totaux[cat] = float(frais.filter(categorie=cat).aggregate(t=Sum('montant'))['t'] or 0)
    total_global = sum(totaux.values())

    if request.method == 'POST':
        form = FraisChantierForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.devis = devis
            f.save()
            messages.success(request, 'Frais ajouté.')
            return redirect('devis_btp:frais_chantier', pk=pk)
    else:
        form = FraisChantierForm()

    return render(request, 'devis_btp/frais_chantier.html', {
        'devis': devis, 'frais': frais,
        'totaux': totaux, 'total_global': total_global,
        'form': form, 'categories': FraisChantier.CATEGORIE,
    })


@login_required
def frais_delete(request, pk, frais_pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    frais = get_object_or_404(FraisChantier, pk=frais_pk, devis=devis)
    if request.method == 'POST':
        frais.delete()
    return redirect('devis_btp:frais_chantier', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
#  PRIX UNITAIRES MATÉRIAUX (A2)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def prix_unitaires(request, pk):
    devis    = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    recap    = devis.recap_am.select_related('dosage').order_by('ordre')
    materiaux = Materiau.objects.filter(actif=True).order_by('code')

    lignes_pu = []
    for r in recap:
        pu_mat = r.montant_materiaux_unitaire
        cols   = []
        if r.dosage:
            dos = r.dosage
            from .utils import get_materiaux_map
            mat_map_prices = {}
            for mat in materiaux:
                desig = mat.designation.lower()
                if 'sable' in desig:
                    cols.append({'mat': mat, 'qty': float(dos.sable_m3), 'montant': float(dos.sable_m3) * float(mat.prix_rendu_chantier)})
                elif 'gravillon' in desig or 'gravier' in desig:
                    cols.append({'mat': mat, 'qty': float(dos.gravillon_m3), 'montant': float(dos.gravillon_m3) * float(mat.prix_rendu_chantier)})
                elif 'eau' in desig:
                    cols.append({'mat': mat, 'qty': float(dos.eau_litres), 'montant': float(dos.eau_litres) * float(mat.prix_rendu_chantier)})
                elif 'ciment' in desig:
                    cols.append({'mat': mat, 'qty': float(dos.ciment_kg), 'montant': float(dos.ciment_kg) * float(mat.prix_rendu_chantier)})
                elif 'chaux' in desig:
                    cols.append({'mat': mat, 'qty': float(dos.chaux_kg), 'montant': float(dos.chaux_kg) * float(mat.prix_rendu_chantier)})
                else:
                    cols.append({'mat': mat, 'qty': 0, 'montant': 0})
        lignes_pu.append({
            'recap': r,
            'cols': cols,
            'pu_mat': pu_mat,
            'montant_total': float(r.qam) * pu_mat if float(r.qam) else 0,
        })

    return render(request, 'devis_btp/prix_unitaires.html', {
        'devis': devis,
        'lignes_pu': lignes_pu,
        'materiaux': materiaux,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  DÉBOURSÉ SEC (DEPS)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def debourse_sec(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)

    if request.method == 'POST':
        # Recalcul complet
        calculer_nomenclature(devis)
        calculer_deps(devis)
        messages.success(request, 'Déboursé sec calculé et mis à jour.')
        return redirect('devis_btp:debourse_sec', pk=pk)

    lignes = devis.lignes_deps.order_by('ordre')
    totaux = lignes.aggregate(
        mat=Sum('montant_materiaux'),
        mo=Sum('montant_mo'),
        frais=Sum('montant_frais'),
        total=Sum('montant_total'),
    )
    frais_global = float(devis.frais_chantier.aggregate(t=Sum('montant'))['t'] or 0)

    return render(request, 'devis_btp/debourse_sec.html', {
        'devis': devis,
        'lignes': lignes,
        'totaux': totaux,
        'frais_global': frais_global,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  RÉCAPITULATIF & DOCUMENT LIVRABLE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def recap_final(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)

    if request.method == 'POST':
        # Mise à jour du coefficient K
        devis.taux_aleas   = request.POST.get('taux_aleas', devis.taux_aleas)
        devis.taux_benefice = request.POST.get('taux_benefice', devis.taux_benefice)
        devis.taux_tva     = request.POST.get('taux_tva', devis.taux_tva)
        devis.statut       = 'finalise'
        devis.save()
        # Recalcul des totaux
        calculer_deps(devis)
        messages.success(request, 'Récapitulatif finalisé.')
        return redirect('devis_btp:recap_final', pk=pk)

    recap_fin  = calcul_recap_financier(devis)
    en_lettres = nombre_en_lettres(int(round(recap_fin['montant_ttc'])))
    lignes_deps = devis.lignes_deps.order_by('ordre')
    frais       = devis.frais_chantier.order_by('categorie', 'ordre')

    return render(request, 'devis_btp/recap_final.html', {
        'devis':      devis,
        'recap_fin':  recap_fin,
        'en_lettres': en_lettres,
        'lignes_deps': lignes_deps,
        'frais':      frais,
        'fmt_ar':     fmt_ar,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  VERSION IMPRIMABLE (print-friendly)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def devis_print(request, pk):
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    recap_fin  = calcul_recap_financier(devis)
    en_lettres = nombre_en_lettres(int(round(recap_fin['montant_ttc'])))
    lignes_deps = devis.lignes_deps.order_by('ordre')
    frais       = devis.frais_chantier.order_by('categorie', 'ordre')
    materiaux   = Materiau.objects.filter(actif=True).order_by('code')

    return render(request, 'devis_btp/devis_print.html', {
        'devis':      devis,
        'recap_fin':  recap_fin,
        'en_lettres': en_lettres,
        'lignes_deps': lignes_deps,
        'frais':      frais,
        'materiaux':  materiaux,
        'print_mode': True,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  API JSON (pour l'interface React/AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_materiaux(request):
    data = [
        {
            'id': m.pk, 'code': m.code, 'designation': m.designation,
            'unite': m.unite,
            'prix_fournisseur': float(m.prix_fournisseur),
            'frais_manutention': float(m.frais_manutention),
            'frais_transport': float(m.frais_transport),
            'taux_chute': float(m.taux_chute),
            'prix_rendu_chantier': m.prix_rendu_chantier,
        }
        for m in Materiau.objects.filter(actif=True).order_by('code')
    ]
    return JsonResponse({'materiaux': data})


@login_required
@require_GET
def api_dosages(request):
    data = [
        {
            'id': d.pk, 'code': d.code, 'categorie': d.categorie,
            'dosage_kg': d.dosage_kg, 'choix_liant': d.choix_liant,
            'sable_m3': float(d.sable_m3), 'gravillon_m3': float(d.gravillon_m3),
            'eau_litres': float(d.eau_litres), 'ciment_kg': float(d.ciment_kg),
            'chaux_kg': float(d.chaux_kg), 'acier_kg': float(d.acier_kg),
        }
        for d in Dosage.objects.filter(actif=True).order_by('categorie', 'dosage_kg')
    ]
    return JsonResponse({'dosages': data})


@login_required
def api_devis_state(request, pk):
    """Retourne l'état complet d'un devis pour l'interface React."""
    devis = get_object_or_404(Devis, pk=pk, cree_par=request.user)
    recap_fin = calcul_recap_financier(devis)

    return JsonResponse({
        'devis': {
            'id': devis.pk,
            'reference': devis.reference,
            'titre': devis.titre,
            'client_nom': devis.client_nom,
            'statut': devis.statut,
            'mode_mo': devis.mode_mo,
            'taux_aleas': float(devis.taux_aleas),
            'taux_benefice': float(devis.taux_benefice),
            'taux_tva': float(devis.taux_tva),
            'coefficient_k': devis.coefficient_k,
        },
        'recap_financier': recap_fin,
        'montant_en_lettres': nombre_en_lettres(int(round(recap_fin['montant_ttc']))),
    })
