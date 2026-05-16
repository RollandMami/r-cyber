# 📦 Guide de déploiement complet — R-CYBER Patrimoine
## Serveur Ubuntu · Nginx · Gunicorn · No-IP DDNS

---

## 🗺️ Vue d'ensemble

```
Internet
   │
   ▼
rcyber.ddns.net (No-IP DDNS)
   │  pointe vers ton IP publique (mise à jour par noip2)
   ▼
Box / Routeur  →  Port 80 redirigé vers le serveur
   │
   ▼
Nginx (port 80)
   │  sert /static/ et /media/ directement
   │  proxy le reste vers Gunicorn
   ▼
Gunicorn (127.0.0.1:8000)
   │
   ▼
Django (r-cyber/)
```

---

## ✅ Prérequis vérifiés

- [x] Git clone du dépôt déjà effectué sur le serveur
- [ ] Python 3.10+ installé
- [ ] Nginx installé
- [ ] No-IP DDNS créé (rcyber.ddns.net)
- [ ] noip2 client à installer et configurer

---

## ÉTAPE 1 — Créer l'utilisateur système

Travailler sous un utilisateur dédié (pas root) est obligatoire.

```bash
# Crée l'utilisateur rcyber
sudo adduser rcyber

# Ajoute-le au groupe www-data (pour Nginx)
sudo usermod -aG www-data rcyber
```

---

## ÉTAPE 2 — Organiser le projet

Le projet cloné doit se trouver dans `/home/rcyber/r-cyber/`.

```bash
# Si cloné ailleurs, déplace-le :
sudo mv /chemin/vers/r-cyber /home/rcyber/r-cyber

# Donne les droits à l'utilisateur rcyber
sudo chown -R rcyber:rcyber /home/rcyber/r-cyber
```

---

## ÉTAPE 3 — Environnement virtuel Python

```bash
# Passe sur l'utilisateur rcyber
sudo -u rcyber bash

# Va dans le projet
cd /home/rcyber/r-cyber

# Crée le virtualenv
python3 -m venv venv

# Active-le
source venv/bin/activate

# Installe les dépendances
pip install --upgrade pip
pip install django gunicorn whitenoise pillow

# Installe ifcopenshell (pour la conversion IFC → JSON)
pip install ifcopenshell

# Si tu as un requirements.txt :
# pip install -r requirements.txt
```

---

## ÉTAPE 4 — Fichier .env (variables d'environnement)

```bash
# Toujours dans /home/rcyber/r-cyber/
cp .env.example .env
nano .env
```

Génère une SECRET_KEY unique :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Colle la valeur dans le .env :

```env
SECRET_KEY=ta-cle-generee-ici
DEBUG=False
ALLOWED_HOSTS=rcyber.ddns.net,127.0.0.1
```

### Adapter settings.py pour lire le .env

Installe python-decouple :

```bash
pip install python-decouple
```

En haut de `core/settings.py`, ajoute :

```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG       = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')
```

---

## ÉTAPE 5 — Collecte des fichiers statiques

Django doit regrouper tous les fichiers CSS/JS/images dans un seul dossier
que Nginx servira directement.

```bash
# Dans settings.py, vérifie que STATIC_ROOT est défini :
# STATIC_ROOT = BASE_DIR / 'staticfiles'

python manage.py collectstatic --noinput
```

Les fichiers iront dans `/home/rcyber/r-cyber/staticfiles/`.

---

## ÉTAPE 6 — Migrations et superutilisateur

```bash
python manage.py makemigrations
python manage.py migrate

# Crée le compte admin
python manage.py createsuperuser
```

---

## ÉTAPE 7 — Tester Gunicorn manuellement

Avant de configurer le service systemd, teste que Gunicorn fonctionne :

```bash
cd /home/rcyber/r-cyber
source venv/bin/activate

gunicorn --bind 127.0.0.1:8000 core.wsgi:application
```

Si tu vois `Listening at: http://127.0.0.1:8000` → tout va bien.
Arrête avec `Ctrl+C`.

---

## ÉTAPE 8 — Service systemd Gunicorn

### 8.1 Créer le dossier de logs

```bash
sudo mkdir -p /var/log/gunicorn
sudo chown rcyber:rcyber /var/log/gunicorn
```

### 8.2 Copier le fichier service

```bash
sudo cp r-cyber.service /etc/systemd/system/r-cyber.service
```

### 8.3 Activer et démarrer

```bash
# Recharge systemd
sudo systemctl daemon-reload

# Active le service au démarrage du serveur
sudo systemctl enable r-cyber

# Démarre maintenant
sudo systemctl start r-cyber

# Vérifie le statut
sudo systemctl status r-cyber
```

Tu dois voir `Active: active (running)`.

### 8.4 Commandes utiles

```bash
# Voir les logs en temps réel
sudo journalctl -u r-cyber -f

# Redémarrer après un changement de code
sudo systemctl restart r-cyber

# Arrêter
sudo systemctl stop r-cyber
```

---

## ÉTAPE 9 — Configuration Nginx

### 9.1 Copier le fichier de configuration

```bash
sudo cp rcyber.ddns.net /etc/nginx/sites-available/rcyber.ddns.net
```

### 9.2 Activer le site

```bash
# Crée le lien symbolique dans sites-enabled
sudo ln -s /etc/nginx/sites-available/rcyber.ddns.net \
           /etc/nginx/sites-enabled/rcyber.ddns.net

# Supprime le site par défaut si présent (évite les conflits)
sudo rm -f /etc/nginx/sites-enabled/default
```

### 9.3 Tester la configuration Nginx

```bash
sudo nginx -t
```

Tu dois voir :
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 9.4 Recharger Nginx

```bash
sudo systemctl reload nginx
# ou redémarrer complètement :
sudo systemctl restart nginx
```

---

## ÉTAPE 10 — No-IP DDNS + noip2

### 10.1 Créer le compte No-IP (si pas encore fait)

1. Va sur [https://www.noip.com](https://www.noip.com)
2. Crée un compte gratuit
3. Dans "My Hostnames" → crée `rcyber.ddns.net`
4. Sélectionne "DNS Host (A)" → laisse l'IP se remplir automatiquement

### 10.2 Installer le client noip2 sur le serveur

```bash
# Installe les dépendances de compilation
sudo apt update
sudo apt install build-essential -y

# Télécharge le client officiel No-IP
cd /tmp
wget https://dmej8g5cpdyqd.cloudfront.net/downloads/noip-duc_3.3.0.tar.gz

# Décompresse
tar xf noip-duc_3.3.0.tar.gz
cd noip-duc_3.3.0/

# Compile et installe
make
sudo make install
# ou si binaire disponible :
# sudo apt install noip2
```

### 10.3 Configurer noip2

```bash
sudo noip2 -C
```

Le client te posera ces questions :
- **Email** : ton email No-IP
- **Mot de passe** : ton mot de passe No-IP
- **Hostname à mettre à jour** : `rcyber.ddns.net`
- **Intervalle de mise à jour** : `30` (minutes)

### 10.4 Créer un service systemd pour noip2

```bash
sudo nano /etc/systemd/system/noip2.service
```

Colle ce contenu :

```ini
[Unit]
Description=No-IP Dynamic DNS Update Client
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/noip2
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable noip2
sudo systemctl start noip2
sudo systemctl status noip2
```

### 10.5 Vérifier que le DDNS fonctionne

```bash
# Depuis le serveur, vérifie l'IP publique actuelle
curl ifconfig.me

# Vérifie que le domaine pointe vers cette IP
nslookup rcyber.ddns.net
# ou
dig rcyber.ddns.net +short
```

Les deux IPs doivent être identiques.

---

## ÉTAPE 11 — Redirection port sur le routeur/box

⚠️ **Étape critique** — Nginx écoute sur le port 80 du serveur,
mais le routeur doit faire passer les requêtes venant d'internet.

1. Connecte-toi à l'interface de ta box (souvent `192.168.1.1`)
2. Va dans **NAT / Redirection de ports**
3. Ajoute une règle :
   - **Port externe** : `80`
   - **IP interne** : IP locale de ton serveur (ex. `192.168.1.X`)
   - **Port interne** : `80`
   - **Protocole** : TCP

Pour connaître l'IP locale du serveur :
```bash
ip a | grep "inet " | grep -v 127
```

---

## ÉTAPE 12 — Test final

```bash
# Depuis n'importe quel appareil extérieur au réseau local :
curl -I http://rcyber.ddns.net

# Tu dois voir :
# HTTP/1.1 200 OK
# Server: nginx/...
```

Ou ouvre `http://rcyber.ddns.net` dans un navigateur → tu dois voir la liste des patrimoines.

---

## ÉTAPE 13 — HTTPS avec Let's Encrypt (recommandé)

Une fois le HTTP fonctionnel, sécurise avec un certificat SSL gratuit :

```bash
sudo apt install certbot python3-certbot-nginx -y

sudo certbot --nginx -d rcyber.ddns.net
```

Certbot modifie automatiquement le fichier Nginx pour passer en HTTPS
et configure le renouvellement automatique.

```bash
# Test du renouvellement automatique
sudo certbot renew --dry-run
```

---

## 🔄 Workflow de mise à jour du code

Quand tu fais des modifications et push sur git :

```bash
# Sur le serveur
cd /home/rcyber/r-cyber

# Récupère les dernières modifications
git pull origin main

# Active le venv
source venv/bin/activate

# Applique les migrations si nécessaire
python manage.py migrate

# Recollecte les statiques si CSS/JS modifiés
python manage.py collectstatic --noinput

# Redémarre Gunicorn
sudo systemctl restart r-cyber
```

---

## 🛠️ Dépannage rapide

| Problème | Commande de diagnostic |
|---|---|
| Site inaccessible | `sudo systemctl status r-cyber` |
| Erreur Nginx | `sudo nginx -t` puis `sudo journalctl -u nginx -n 50` |
| Logs Gunicorn | `sudo journalctl -u r-cyber -n 100` |
| DDNS ne se met pas à jour | `sudo systemctl status noip2` |
| 502 Bad Gateway | Gunicorn ne tourne pas → `sudo systemctl restart r-cyber` |
| 404 sur /static/ | `python manage.py collectstatic` non exécuté |
| Permission denied media | `sudo chown -R rcyber:www-data /home/rcyber/r-cyber/media` |

---

## 📁 Structure finale du serveur

```
/home/rcyber/r-cyber/          ← Projet Django (git clone)
    venv/                      ← Environnement virtuel Python
    .env                       ← Variables secrets (jamais dans git)
    staticfiles/               ← collectstatic output
    media/                     ← Uploads utilisateurs (IFC, PDF…)
    manage.py
    core/
    smartdocs/
    viewer/

/etc/systemd/system/
    r-cyber.service            ← Service Gunicorn
    noip2.service              ← Service DDNS

/etc/nginx/
    sites-available/rcyber.ddns.net   ← Config Nginx
    sites-enabled/rcyber.ddns.net     ← Lien symbolique actif

/var/log/
    nginx/rcyber_access.log
    nginx/rcyber_error.log
    gunicorn/rcyber_access.log
    gunicorn/rcyber_error.log
```
