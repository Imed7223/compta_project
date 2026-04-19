from django.core.management.base import BaseCommand
from app_compta.services.lettrage import LettrageService

class Command(BaseCommand):
    help = 'Déclenche le lettrage automatique des comptes de tiers'

    def handle(self, *args, **options):
        self.stdout.write("Analyse des comptes pour lettrage...")
        
        # Appel du service que nous avons créé précédemment
        lignes_lettrees = LettrageService.lettrer_comptes_tiers()
        
        if lignes_lettrees > 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Succès : {lignes_lettrees} lignes ont été lettrées (marquées avec A, B, C...).")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Info : Aucune nouvelle correspondance trouvée pour le lettrage.")
            )
