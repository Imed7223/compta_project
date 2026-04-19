# 🚀 ComptaFlow : Système de Comptabilité Automatisé

**ComptaFlow** est une application Django robuste conçue pour automatiser l'intégralité du cycle comptable d'une entreprise : de la synchronisation bancaire à la génération du Bilan et du Fichier des Écritures Comptables (FEC).

---

## 🌟 Fonctionnalités Clés

### 🏦 Automatisation Bancaire & Imputation
* **Synchronisation API** : Importation automatique des transactions (Simulateur intégré & support Qonto).
* **Moteur d'Imputation Intelligent** : Analyse sémantique des libellés bancaires pour affecter automatiquement les comptes du Plan Comptable Général (6xx, 7xx, 4xx).
* **Gestion Automatique de la TVA** : Extraction et ventilation automatique de la TVA (20%) sur les charges et les produits.

### 📊 Pilotage Financier & Reporting
* **Dashboard Dynamique** : Visualisation en temps réel du Solde Banque, du Résultat Net et de la TVA à décaisser.
* **États Financiers** : Génération automatique du Bilan (Actif/Passif) et du Compte de Résultat.
* **Graphiques Analytiques** : Évolution mensuelle des dépenses via Chart.js.

### ⚙️ Expertise Comptable Avancée
* **Lettrage Automatique** : Rapprochement intelligent entre factures et paiements sur les comptes de tiers (411).
* **Export FEC Conforme** : Génération du Fichier des Écritures Comptables (FEC) au format plat 18 colonnes (norme fiscale DGFiP).

### 🔒 Sécurité & Architecture
* **API REST** : Entièrement documentée et manipulable via Django REST Framework.
* **Authentification par Token** : Accès sécurisé aux données sensibles via jetons (Token Authentication).
* **Base de données** : Architecture relationnelle optimisée sous PostgreSQL.

---

## 🛠️ Stack Technique

- **Backend** : Python 3.11, Django 5.x, Django REST Framework
- **Frontend** : HTML5, Tailwind CSS, Bootstrap 5, Chart.js
- **Base de données** : PostgreSQL
- **DevOps** : Git, Environnements virtuels (venv)

---

## 🚀 Installation Rapide

1. **Cloner le projet**
   ```bash
   git clone [https://github.com/votre-compte/compta_project.git](https://github.com/votre-compte/compta_project.git)
   cd compta_project

2. **Installer les dépendances**
 ```bash
pip install -r requirements.txt
Configurer la base de données & Migrer

 ```bash
python manage.py migrate
Lancer la synchronisation initiale

 ```bash
python manage.py sync_banque
Démarrer le serveur

 ```bash
python manage.py runserver
Accédez au dashboard via : http://127.0.0.1:8000/api/dashboard/

3.**📖 Utilisation de l'API**
Endpoint Méthode Description
/api-token-auth/POSTObtenir un Token d'accès sécurisé
/api/ecritures/GETListe toutes les écritures comptables
/api/ecritures/bilan/GETDonnées brutes du bilan (format JSON)
/api/ecritures/exporter_fec/GETTélécharger le FEC officiel (.txt)
/api/dashboard/GETAccès à l'interface visuelle du Dashboard

### 👨‍💻 Auteur

Imed - Expert en développement Backend & Solutions Comptables

GitHub : @votre-pseudo

LinkedIn : [Lien vers votre profil]
