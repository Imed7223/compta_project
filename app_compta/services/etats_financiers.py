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
        disponibilites = round(self.obtenir_solde_compte('512'), 2)
        creances = round(self.obtenir_solde_compte('411'), 2)
        immo = round(self.obtenir_solde_compte('2'), 2)

        fournisseurs = round(abs(self.obtenir_solde_compte('401')), 2)
        tva_due = round(abs(self.obtenir_solde_compte('445710')) - abs(self.obtenir_solde_compte('445660')), 2)

        return {
            'actif': {
                'Immobilisations': immo,
                'Créances Clients': creances,
                'Disponibilités': disponibilites,
            },
            'passif': {
                'Dettes Fournisseurs': fournisseurs,
                'Dettes Fiscales et Sociales': tva_due,
                'Capitaux Propres': Decimal('0.00'),
            },
            'total_actif': round(immo + creances + disponibilites, 2),
            'total_passif': round(fournisseurs + tva_due, 2)
        }

def generer_compte_resultat(self):
    res_7 = round(LigneEcriture.objects.filter(
        compte__numero__startswith='7'
    ).aggregate(total=Sum('montant_credit'))['total'] or Decimal('0.00'), 2)
    
    res_6 = round(LigneEcriture.objects.filter(
        compte__numero__startswith='6'
    ).aggregate(total=Sum('montant_debit'))['total'] or Decimal('0.00'), 2)

    return {
        'Total Produits (7)': res_7,
        'Total Charges (6)': res_6,
        'Résultat Net': round(res_7 - res_6, 2)
    }
