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
