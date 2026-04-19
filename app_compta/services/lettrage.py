from django.db.models import F
from app_compta.models import LigneEcriture

class LettrageService:
    @staticmethod
    def lettrer_comptes_tiers():
        """
        Parcourt les comptes de tiers et lettre les montants identiques.
        """
        # On récupère toutes les lignes non lettrées des comptes clients (411)
        lignes_non_lettrees = LigneEcriture.objects.filter(
            compte__numero__startswith='411',
            lettrage=''
        )

        lettre_index = 65 # Code ASCII pour 'A'
        nb_lettrages = 0

        for ligne in lignes_non_lettrees:
            if ligne.montant_debit > 0:
                # On cherche une ligne de crédit exactement identique pour ce compte
                correspondance = LigneEcriture.objects.filter(
                    compte=ligne.compte,
                    montant_credit=ligne.montant_debit,
                    lettrage=''
                ).first()

                if correspondance:
                    code = chr(lettre_index)
                    ligne.lettrage = code
                    correspondance.lettrage = code
                    
                    ligne.save()
                    correspondance.save()
                    
                    lettre_index += 1
                    nb_lettrages += 1
                    
        return nb_lettrages
