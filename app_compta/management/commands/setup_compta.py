from django.core.management.base import BaseCommand
from app_compta.models import CompteComptable, Journal
from app_compta.services.imputation import REGLES_IMPUTATION, COMPTE_BANQUE

class Command(BaseCommand):
    help = 'Initialise le plan comptable et les journaux basés sur les règles d imputation'

    def handle(self, *args, **options):
        self.stdout.write("Initialisation du référentiel comptable...")

        # 1. Création du Journal de Banque (BQ)
        journal_bq, created = Journal.objects.get_or_create(
            code="BQ",
            defaults={'libelle': 'Journal de Banque', 'type': 'BQ'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Journal BQ créé."))

        # 2. Création du compte de Banque par défaut (512000)
        CompteComptable.objects.get_or_create(
            numero=COMPTE_BANQUE,
            defaults={'libelle': 'Banque BNP Paribas', 'classe': '5'}
        )

        # 3. Création des comptes avec vrais libellés
        comptes_avec_libelles = {
            '707000': 'Ventes de prestations',
            '606100': 'Eau, gaz, électricité',
            '606300': 'Fournitures entretien',
            '613200': 'Loyers',
            '616000': 'Assurances',
            '622600': 'Honoraires',
            '626000': 'Télécoms et cloud',
            '627000': 'Services bancaires',
            '630000': 'Impôts et taxes',
            '645000': 'Charges sociales',
            '421000': 'Personnel rémunérations',
            '218300': 'Matériel informatique',
        }

        for regle in REGLES_IMPUTATION:
            num = regle['compte_contrepartie']
            libelle = comptes_avec_libelles.get(num, regle['categorie'].replace('_', ' ').capitalize())
            classe = num[0]
            compte, created = CompteComptable.objects.get_or_create(
                numero=num,
                defaults={'libelle': libelle, 'classe': classe}
            )
            if not created:
                # Mettre à jour le libelle si c'est encore générique
                if compte.libelle in ['Compte Auto', regle['categorie']]:
                    compte.libelle = libelle
                    compte.save()
            if created:
                self.stdout.write(f"➕ Compte créé : {num} - {libelle}")

        # 4. Ajout des comptes techniques obligatoires
        comptes_obligatoires = [
            ("445660", "TVA déductible", "4"),
            ("445710", "TVA collectée", "4"),
            ("471000", "Compte d'attente", "4"),
            ("101000", "Capital social", "1"),
        ]
        
        for num, lib, cl in comptes_obligatoires:
            CompteComptable.objects.get_or_create(
                numero=num,
                defaults={'libelle': lib, 'classe': cl}
            )

        self.stdout.write(self.style.SUCCESS("🚀 Configuration terminée. Votre plan comptable est prêt !"))
