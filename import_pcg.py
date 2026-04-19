import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app_compta.models import CompteComptable

def charger_pcg_initial():
    comptes = [
        ('101000', 'Capital', '1'),
        ('218300', 'Matériel informatique', '2'),
        ('401000', 'Fournisseurs', '4'),
        ('411000', 'Clients', '4'),
        ('512000', 'Banque', '5'),
        ('606100', 'Eau, gaz, électricité', '6'),
        ('613200', 'Loyers', '6'),
        ('626000', 'Frais postaux et télécoms', '6'),
        ('707000', 'Ventes de marchandises', '7'),
    ]
    
    for num, lib, classe in comptes:
        CompteComptable.objects.get_or_create(
            numero=num, 
            defaults={'libelle': lib, 'classe': classe}
        )
    print("✅ Plan comptable de base importé !")

if __name__ == "__main__":
    charger_pcg_initial()
