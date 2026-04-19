from decimal import Decimal
from django.db.models import Sum
from app_compta.models import CompteComptable, LigneEcriture

class FinanceService:
    @staticmethod
    def obtenir_solde_compte(numero_compte):
        """Calcule le solde d'un compte (Débit - Crédit)"""
        totaux = LigneEcriture.objects.filter(compte__numero__startswith=numero_compte).aggregate(
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit')
        )
        debit = totaux['total_debit'] or Decimal('0.00')
        credit = totaux['total_credit'] or Decimal('0.00')
        return debit - credit

    def generer_bilan(self):
        """Génère un bilan simplifié (Actif / Passif)"""
        # Actif : Immobilisations (2), Stocks (3), Créances (41), Banque (512)
        actif = {
            "Immobilisations": self.obtenir_solde_compte('2'),
            "Stocks": self.obtenir_solde_compte('3'),
            "Créances Clients": self.obtenir_solde_compte('411'),
            "Disponibilités": self.obtenir_solde_compte('512'),
        }
        
        # Passif : Capital (1), Dettes Fournisseurs (401), Dettes Fiscales (44)
        passif = {
            "Capitaux Propres": self.obtenir_solde_compte('1'),
            "Dettes Fournisseurs": abs(self.obtenir_solde_compte('401')),
            "Dettes Fiscales et Sociales": abs(self.obtenir_solde_compte('44')),
        }
        
        return {
            "actif": actif, 
            "total_actif": sum(actif.values()),
            "passif": passif, 
            "total_passif": sum(passif.values())
        }

    def generer_compte_resultat(self):
        """Calcule le Résultat (Produits - Charges)"""
        produits = abs(self.obtenir_solde_compte('7')) # Classe 7 (Créditeur par nature)
        charges = self.obtenir_solde_compte('6')       # Classe 6 (Débiteur par nature)
        
        return {
            "Total Produits (7)": produits,
            "Total Charges (6)": charges,
            "Résultat Net": produits - charges
        }


        def obtenir_synthese_flash():
            # 1. Trésorerie (Solde Banque 512)
            lignes_bq = LigneEcriture.objects.filter(compte__numero='512000')
            cash = (lignes_bq.aggregate(Sum('montant_debit'))['montant_debit__sum'] or 0) - \
                (lignes_bq.aggregate(Sum('montant_credit'))['montant_credit__sum'] or 0)

            # 2. Résultat Net (Produits 7 - Charges 6)
            produits = LigneEcriture.objects.filter(compte__numero__startswith='7').aggregate(Sum('montant_credit'))['montant_credit__sum'] or 0
            charges = LigneEcriture.objects.filter(compte__numero__startswith='6').aggregate(Sum('montant_debit'))['montant_debit__sum'] or 0
            resultat = produits - charges

            # 3. TVA à décaisser (TVA Collectée - TVA Déductible)
            tva_coll = LigneEcriture.objects.filter(compte__numero='445710').aggregate(Sum('montant_credit'))['montant_credit__sum'] or 0
            tva_deduc = LigneEcriture.objects.filter(compte__numero='445660').aggregate(Sum('montant_debit'))['montant_debit__sum'] or 0
            tva_due = tva_coll - tva_deduc

            return {
                "cash": cash,
                "resultat": resultat,
                "tva_due": tva_due,
                "nb_ecritures": LigneEcriture.objects.count()
            }
