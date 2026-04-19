from django.core.management.base import BaseCommand
from app_compta.services.api_bancaire import SimulateurBancaire
from app_compta.services.imputation import MoteurImputation
from app_compta.models import TransactionBancaire, EcritureComptable, LigneEcriture, Journal, CompteComptable
from decimal import Decimal

class Command(BaseCommand):
    help = 'Importe, impute et enregistre les transactions en base avec gestion de la TVA'

    def handle(self, *args, **options):
        self.stdout.write("Démarrage de la synchronisation avec calcul de TVA...")

        # 1. Récupération des transactions
        client = SimulateurBancaire()
        tx_brutes = client.get_transactions(date_debut="2024-01-01")

        # 2. Initialisation du moteur
        moteur = MoteurImputation()
        journal_bq, _ = Journal.objects.get_or_create(code="BQ", defaults={'libelle': 'Banque', 'type': 'BQ'})

        for tx in tx_brutes:
            if TransactionBancaire.objects.filter(reference_externe=tx.reference).exists():
                continue

            # 3. Génération de la proposition d'écriture
            resultat = moteur.generer_ecriture(tx)

            if resultat:
                # Création de l'en-tête
                ecriture = EcritureComptable.objects.create(
                    journal=journal_bq,
                    date_ecriture=tx.date_operation,
                    numero_piece=tx.reference,
                    libelle=tx.libelle,
                    valide=True,
                    source='api_bancaire'
                )

                # 4. Logique de split TVA
                taux_tva = Decimal('0.20') # 20% par défaut

                for l in resultat['lignes']:
                    montant_ttc = l['montant_debit'] if l['montant_debit'] > 0 else l['montant_credit']
                    
                    # On applique la TVA uniquement sur les charges (6) ou produits (7)
                    if l['compte_numero'].startswith(('6', '7')):
                        montant_ht = (montant_ttc / (Decimal('1') + taux_tva)).quantize(Decimal('0.01'))
                        montant_tva = montant_ttc - montant_ht
                        
                        # Ligne HT
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
                        
                        # Ligne TVA (445660 pour achat / 445710 pour vente)
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
                        # Ligne classique (Banque ou Tiers)
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

                # 5. Liaison avec la transaction bancaire
                TransactionBancaire.objects.create(
                    reference_externe=tx.reference,
                    date_operation=tx.date_operation,
                    date_valeur=tx.date_valeur,
                    libelle_banque=tx.libelle,
                    montant=tx.montant,
                    statut='imputee',
                    ecriture_generee=ecriture
                )
                
                self.stdout.write(self.style.SUCCESS(f"✅ Importé avec TVA : {tx.libelle}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Règle manquante : {tx.libelle}"))
