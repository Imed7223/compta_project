import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app_compta.models import Journal

# Création des journaux de base
Journal.objects.get_or_create(code="BQ", libelle="Banque", type="BQ")
Journal.objects.get_or_create(code="VTE", libelle="Ventes", type="VTE")
Journal.objects.get_or_create(code="ACH", libelle="Achats", type="ACH")
Journal.objects.get_or_create(code="DIV", libelle="Divers", type="DIV")

print("Journaux créés avec succès !")
