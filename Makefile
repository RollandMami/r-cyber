# Makefile pour le projet Django
# Utilise le venv local pour toutes les commandes.

VENV = env
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
MANAGE = $(PYTHON) manage.py
REQUIREMENTS = requirement.txt

.PHONY: help install migrate run shell test cleanup_media cleanup_media_delete backup push clean

help:
	@echo "Usage: make <target>"
	@echo "Targets:"
	@echo "  install              Installer les dépendances depuis $(REQUIREMENTS)"
	@echo "  migrate              Créer et appliquer les migrations Django"
	@echo "  run                  Lancer le serveur de développement Django"
	@echo "  shell                Ouvrir un shell Django"
	@echo "  test                 Lancer les tests Django"
	@echo "  cleanup_media        Vérifier les fichiers média non utilisés"
	@echo "  cleanup_media_delete Vérifier et supprimer les fichiers média non utilisés"
	@echo "  backup               Générer une sauvegarde locale de db.sqlite3, media et static"
	@echo "  push                 Ajouter, commiter et pousser les changements vers le dépôt git"
	@echo "  clean                Supprimer les fichiers temporaires Python"

install:
	$(PIP) install -r $(REQUIREMENTS)

migrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

run:
	$(MANAGE) runserver

shell:
	$(MANAGE) shell

test:
	$(MANAGE) test

cleanup_media:
	$(MANAGE) cleanup_unused_media --dry-run

cleanup_media_delete:
	$(MANAGE) cleanup_unused_media --delete

backup:
	mkdir -p backups
	@BACKUP_FILE=backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz; \
	 tar -czf "$$BACKUP_FILE" db.sqlite3 media static; \
	 echo "Backup créé: $$BACKUP_FILE"

push:
	@read -p "Entrez votre message de commit: " message; \
	 git add . && \
	 git commit -m "$$message" && \
	 git push

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
