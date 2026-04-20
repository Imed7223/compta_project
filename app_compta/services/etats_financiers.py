from django.db.models import Sum
from decimal import Decimal
from app_compta.models import LigneEcriture, CompteComptable

class FinanceService:
    def obtenir_solde_compte(self, prefixe_compte):
        """
        Calcule le solde net (Débit - Crédit) pour tous les comptes 
        commençant par le préfixe donné (ex: '512').
        """
        resultat = LigneEcriture.objects.filter(
            compte__numero__startswith=prefixe_compte
        ).aggregate(
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit')
        )

        debit = resultat.get('total_debit') or Decimal('0.00')
        credit = resultat.get('total_credit') or Decimal('0.00')
        
        return debit - credit

    def generer_bilan(self):
        """Calcule les masses de l'Actif et du Passif."""
        # Actif : Solde Débiteur (Banque + Immo + Créances)
        disponibilites = round(self.obtenir_solde_compte('512'), 2)
        creances = round(self.obtenir_solde_compte('411'), 2)
        immo = round(self.obtenir_solde_compte('2'), 2)

        # Passif : Solde Créditeur (Dettes Fournisseurs + TVA due)
        # Note : On multiplie par -1 car les dettes sont au crédit (négatif ici)
        fournisseurs = round(abs(self.obtenir_solde_compte('401')), 2)
        tva_due = round(abs(self.obtenir_solde_compte('445710')) - abs(self.obtenir_solde_compte('445660')), 2)

        return {
            'actif': {
                'Immobilisations': immo,
                'Créances Clients': creances,
                'Disponibilités': disponibilites,
                #'Stocks': self.obtenir_solde_compte('601'),  # Achats matières premières
            },
            'passif': {
                'Dettes Fournisseurs': fournisseurs,
                'Dettes Fiscales et Sociales': round(tva_due, 2),
                'Capitaux Propres': Decimal('0.00'),
            },
            'total_actif': round(immo + creances + disponibilites, 2),
            'total_passif': round(fournisseurs + tva_due, 2)
        }

    def generer_compte_resultat(self):
        """Calcule les Produits (7) et les Charges (6)."""
        # Produits : On prend le Crédit (Ventes)
        res_7 = LigneEcriture.objects.filter(
            compte__numero__startswith='7'
        ).aggregate(total=Sum('montant_credit'))['total'] or Decimal('0.00')
        
        # Charges : On prend le Débit (Frais)
        res_6 = LigneEcriture.objects.filter(
            compte__numero__startswith='6'
        ).aggregate(total=Sum('montant_debit'))['total'] or Decimal('0.00')

        return {
            'Total Produits (7)': res_7,
            'Total Charges (6)': res_6,
            'Résultat Net': (res_7 - res_6, 2)
        }
