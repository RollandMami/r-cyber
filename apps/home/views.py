from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

# ── Données des services ──────────────────────────────────────
SERVICES = {
    'btp': {
        'slug':      'btp',
        'nom':       'Bureau d\'étude BTP',
        'nom_en':    'Civil Engineering Office',
        'icone':     'fas fa-hard-hat',
        'couleur':   '#1e6fca',
        'hero_desc': 'Études structurelles, plans d\'architecture, métrés, devis estimatifs et suivi de chantier complet.',
        'desc_en':   'Structural studies, architectural plans, quantity surveying, cost estimates and full site supervision.',
        'features':  [
            ('fas fa-drafting-compass', 'Plans d\'architecture', 'Conception et dessin de plans 2D/3D pour tous types de bâtiments.'),
            ('fas fa-calculator',       'Études de structure',   'Calculs structurels, dimensionnement des fondations et ossatures.'),
            ('fas fa-file-invoice',     'Devis & métrés',        'Estimation précise des coûts et quantitatifs des travaux.'),
            ('fas fa-hard-hat',         'Suivi de chantier',     'Supervision des travaux, contrôle qualité et réception des ouvrages.'),
            ('fas fa-map',              'Topographie',           'Levés topographiques, implantation et bornage de terrain.'),
            ('fas fa-certificate',      'Dossiers techniques',   'Constitution des dossiers de permis de construire et réglementaires.'),
        ],
    },
    'construction': {
        'slug':      'construction',
        'nom':       'Construction',
        'nom_en':    'Building & Construction',
        'icone':     'fas fa-building',
        'couleur':   '#f59e0b',
        'hero_desc': 'Réalisation de bâtiments résidentiels et commerciaux, rénovation, maçonnerie et second œuvre.',
        'desc_en':   'Residential and commercial buildings, renovation, masonry and finishing works.',
        'features':  [
            ('fas fa-home',         'Bâtiments résidentiels', 'Villas, appartements, immeubles — clé en main ou par lots.'),
            ('fas fa-store',        'Bâtiments commerciaux',  'Bureaux, entrepôts, commerces et locaux professionnels.'),
            ('fas fa-tools',        'Rénovation',             'Réhabilitation, extension et mise aux normes de l\'existant.'),
            ('fas fa-paint-roller', 'Second œuvre',           'Plâtrerie, carrelage, peinture, menuiserie et finitions.'),
            ('fas fa-water',        'Plomberie & sanitaire',  'Installation et réparation de réseaux eau et assainissement.'),
            ('fas fa-bolt',         'Électricité',            'Installations électriques BT, tableaux et câblage.'),
        ],
    },
    'info-dev': {
        'slug':      'info-dev',
        'nom':       'Info-Dev Web/Python',
        'nom_en':    'Web & Python Development',
        'icone':     'fas fa-code',
        'couleur':   '#00c8ff',
        'hero_desc': 'Développement web sur mesure, applications Django/Python, APIs, automatisation et maintenance.',
        'desc_en':   'Custom web development, Django/Python apps, REST APIs, automation and ongoing maintenance.',
        'features':  [
            ('fas fa-globe',        'Sites web',        'Sites vitrines, portfolios et landing pages responsive et modernes.'),
            ('fas fa-cogs',         'Applications web', 'Applications Django full-stack sur mesure pour votre métier.'),
            ('fas fa-plug',         'APIs REST',        'Conception et développement d\'APIs robustes et documentées.'),
            ('fas fa-robot',        'Automatisation',   'Scripts Python pour automatiser vos tâches répétitives.'),
            ('fas fa-database',     'Bases de données', 'Conception et optimisation de bases de données relationnelles.'),
            ('fas fa-mobile-alt',   'Apps mobiles',     'Applications Android (WebView + PWA) compatibles offline.'),
        ],
    },
    'cybercafe': {
        'slug':      'cybercafe',
        'nom':       'Cybercafé',
        'nom_en':    'Internet Café',
        'icone':     'fas fa-wifi',
        'couleur':   '#22c55e',
        'hero_desc': 'Accès internet haut débit, impression, scan, photocopie et services bureautiques pour tous.',
        'desc_en':   'High-speed internet access, printing, scanning, photocopying and office services for everyone.',
        'features':  [
            ('fas fa-wifi',          'Internet haut débit', 'Connexion fibre rapide et stable pour navigation, streaming et travail.'),
            ('fas fa-print',         'Impression',          'Impression couleur et noir/blanc, formats A4 à A0.'),
            ('fas fa-scanner-image', 'Scan & Photocopie',   'Numérisation de documents et photocopies en quelques minutes.'),
            ('fas fa-file-word',     'Bureautique',         'Suite Office complète disponible — Word, Excel, PowerPoint.'),
            ('fas fa-video',         'Visioconférence',     'Cabines calmes pour vos appels vidéo professionnels.'),
            ('fas fa-headset',       'Assistance',          'Personnel disponible pour vous guider et vous aider.'),
        ],
    },
    'gaming': {
        'slug':      'gaming',
        'nom':       'Gaming',
        'nom_en':    'Gaming Center',
        'icone':     'fas fa-gamepad',
        'couleur':   '#a855f7',
        'hero_desc': 'Salle gaming équipée de PCs haute performance, tournois eSport, abonnements et location à l\'heure.',
        'desc_en':   'High-performance gaming PCs, eSport tournaments, subscriptions and hourly rentals.',
        'features':  [
            ('fas fa-desktop',      'PCs gaming',       'Stations équipées de GPU dernière génération, moniteurs 144Hz.'),
            ('fas fa-headphones',   'Audio premium',    'Casques gaming haute fidélité pour une immersion totale.'),
            ('fas fa-trophy',       'Tournois eSport',  'Organisation de tournois locaux et qualifications régionales.'),
            ('fas fa-id-card',      'Abonnements',      'Forfaits horaires, journaliers et mensuels adaptés à tous.'),
            ('fas fa-gamepad',      'Jeux multijoueur', 'Large bibliothèque de jeux PC, consoles et jeux en réseau local.'),
            ('fas fa-users',        'Espace social',    'Zone lounge, rafraîchissements et ambiance conviviale.'),
        ],
    },
    'studio': {
        'slug':      'studio',
        'nom':       'Studio Son',
        'nom_en':    'Recording Studio',
        'icone':     'fas fa-microphone',
        'couleur':   '#f43660',
        'hero_desc': 'Enregistrement audio, mixage, mastering, production musicale et podcast dans un studio professionnel.',
        'desc_en':   'Audio recording, mixing, mastering, music production and podcasting in a professional studio.',
        'features':  [
            ('fas fa-microphone',   'Enregistrement',   'Cabine insonorisée, micros pro et préamplis haut de gamme.'),
            ('fas fa-sliders-h',    'Mixage',           'Mix multicanal, traitement de la dynamique et des effets.'),
            ('fas fa-compact-disc', 'Mastering',        'Finalisation audio pour distribution streaming et physique.'),
            ('fas fa-music',        'Production',       'Création de beat, arrangement et production musicale complète.'),
            ('fas fa-podcast',      'Podcast',          'Enregistrement et montage de podcasts professionnels.'),
            ('fas fa-film',         'Post-prod vidéo',  'Synchronisation et mixage audio pour contenus vidéo.'),
        ],
    },
    'multiservice': {
        'slug':      'multiservice',
        'nom':       'Multi-Service',
        'nom_en':    'Multi-Service Center',
        'icone':     'fas fa-th-large',
        'couleur':   '#06b6d4',
        'hero_desc': 'Transfert d\'argent, paiement de factures, recharge téléphonique, secrétariat et services divers.',
        'desc_en':   'Money transfer, bill payment, phone top-up, secretarial and various services.',
        'features':  [
            ('fas fa-money-bill-wave', 'Transfert argent',    'Envoi et réception d\'argent local et international.'),
            ('fas fa-file-invoice-dollar', 'Paiement factures', 'Eau, électricité, téléphone — paiement rapide et sécurisé.'),
            ('fas fa-sim-card',        'Recharge téléphone',  'Recharges Orange, Airtel, Telma et cartes prépayées.'),
            ('fas fa-file-alt',        'Secrétariat',         'Saisie, rédaction, mise en page et impression de documents.'),
            ('fas fa-copy',            'Reprographie',        'Photocopie, reliure, plastification et façonnage.'),
            ('fas fa-id-card',         'Services admin',      'Aide aux démarches administratives et formulaires officiels.'),
        ],
    },
}


def index(request):
    return render(request, 'home/index.html')


def services(request):
    return render(request, 'home/services.html', {'services': SERVICES})


def service_detail(request, slug):
    service = SERVICES.get(slug)
    if not service:
        from django.http import Http404
        raise Http404(f'Service « {slug} » introuvable')
    return render(request, 'home/service_detail.html', {'service': service, 'services': SERVICES})


def about(request):
    atout = ["Autodidacte & rigoureux",
            "Fort esprit collaboratif",
            "Vision terrain + code",
            "Permis A & B",
            "Blender 3D",
            "Profil rare BTP × Dev",
            ]
    return render(request, 'home/about.html', {'atouts' : atout})


def contact(request):
    from django.contrib import messages
    if request.method == 'POST':
        nom     = request.POST.get('nom', '').strip()
        email   = request.POST.get('email', '').strip()
        sujet   = request.POST.get('sujet', '').strip()
        message = request.POST.get('message', '').strip()
        if nom and email and message:
            # TODO: envoyer email réel avec send_mail()
            messages.success(request, f'Merci {nom} ! Votre message a bien été envoyé. Nous vous répondrons sous 24h.')
        else:
            messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
    return render(request, 'home/contact.html')


def projects(request):
    return render(request, 'home/projects.html')
