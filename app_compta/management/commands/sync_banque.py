from django.core.management.base import BaseCommand
# On importe le ConnecteurCSV à la place du Simulateur
from app_compta.services.api_bancaire import ConnecteurCSV 
from app_compta.services.imputation import MoteurImputation
from app_compta.models import TransactionBancaire, EcritureComptable, LigneEcriture, Journal, CompteComptable
from decimal import Decimal
import os

class Command(BaseCommand):
    help = 'Importe, impute et enregistre les transactions depuis un fichier CSV'

    def handle(self, *args, **options):
        self.stdout.write("Démarrage de la synchronisation CSV avec calcul de TVA...")

        # 1. Initialisation du connecteur CSV
        # Assurez-vous que le fichier 'transactions.csv' est à la racine du projet
        chemin_csv = "transactions.csv"
        client = ConnecteurCSV(fichier_path=chemin_csv)
        
        # On vérifie si le fichier existe avant de continuer
        if not client.test_connexion():
            self.stdout.write(self.style.ERROR(f"Erreur : Le fichier '{chemin_csv}' est introuvable à la racine du projet."))
            return

        # Récupération des transactions du CSV
        tx_brutes = client.get_transactions(date_debut="2024-01-01")

        if not tx_brutes:
            self.stdout.write(self.style.WARNING("Aucune transaction trouvée dans le fichier (ou hors période)."))
            return

        # 2. Initialisation du moteur
        moteur = MoteurImputation()
        journal_bq, _ = Journal.objects.get_or_create(code="BQ", defaults={'libelle': 'Banque', 'type': 'BQ'})

        for tx in tx_brutes:
            # Éviter les doublons (basé sur la colonne 'reference' du CSV)
            if TransactionBancaire.objects.filter(reference_externe=tx.reference).exists():
                continue

            # 3. Génération de la proposition d'écriture
            resultat = moteur.generer_ecriture(tx)

            if resultat:
                # Création de l'en-tête de l'écriture
                ecriture = EcritureComptable.objects.create(
                    journal=journal_bq,
                    date_ecriture=tx.date_operation,
                    numero_piece=tx.reference,
                    libelle=tx.libelle,
                    valide=True,
                    source='import_csv' # Changé pour la traçabilité
                )

                # 4. Logique de split TVA (20%)
                # On utilise le flag 'tva_applicable' défini dans le moteur d'imputation
                tva_active = resultat.get('tva_applicable', False)
                taux_tva = Decimal('0.20')

                for l in resultat['lignes']:
                    montant_ttc = l['montant_debit'] if l['montant_debit'] > 0 else l['montant_credit']
                    
                    # Split TVA uniquement si la règle le permet ET si c'est une charge(6)/produit(7)
                    if tva_active and l['compte_numero'].startswith(('6', '7')):
                        montant_ht = (montant_ttc / (Decimal('1') + taux_tva)).quantize(Decimal('0.01'))
                        montant_tva = montant_ttc - montant_ht
                        
                        # Création ligne HT
                        LigneEcriture.objects.create(
                            ecriture=ecriture,
                            compte=CompteComptable.objects.get_or_create(
                                numero=l['compte_numero'],
                                defaults={'libelle': 'Compte Auto', 'classe': l['compte_numero'][0]}
                            )[0],
                            libelle=f"{l['libelle']} (HT)",
                            montant_debit=montant_ht if l['montant_debit'] > 0 else 0,
                            montant_credit=montant_ht if l['montant_credit'] > 0 else 0
                        )
                        
                        # Création ligne TVA
                        compte_tva_num = "445660" if l['montant_debit'] > 0 else "445710"
                        compte_tva, _ = CompteComptable.objects.get_or_create(
                            numero=compte_tva_num, 
                            defaults={'libelle': 'TVA sur opérations', 'classe': '4'}
                        )
                        
                        LigneEcriture.objects.create(
                            ecriture=ecriture,
                            compte=compte_tva,
                            libelle=f"TVA sur {l['libelle']}",
                            montant_debit=montant_tva if l['montant_debit'] > 0 else 0,
                            montant_credit=montant_tva if l['montant_credit'] > 0 else 0
                        )
                    else:
                        # Ligne classique (Banque, Tiers, ou Charge sans TVA)
                        LigneEcriture.objects.create(
                            ecriture=ecriture,
                            compte=CompteComptable.objects.get_or_create(
                                numero=l['compte_numero'],
                                defaults={'libelle': 'Compte Auto', 'classe': l['compte_numero'][0]}
                            )[0],
                            libelle=l['libelle'],
                            montant_debit=l['montant_debit'],
                            montant_credit=l['montant_credit']
                        )

                # 5. Enregistrement de la trace bancaire
                TransactionBancaire.objects.create(
                    reference_externe=tx.reference,
                    date_operation=tx.date_operation,
                    date_valeur=tx.date_valeur,
                    libelle_banque=tx.libelle,
                    montant=tx.montant,
                    statut='imputee',
                    ecriture_generee=ecriture
                )
                
                self.stdout.write(self.style.SUCCESS(f"✅ Importé : {tx.libelle} ({tx.montant}€)"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Règle inconnue pour : {tx.libelle}"))
