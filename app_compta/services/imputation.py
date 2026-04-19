"""
Moteur d'imputation automatique des transactions bancaires.
Transforme les flux bancaires en écritures comptables en partie double.
"""
import logging
from decimal import Decimal
from .api_bancaire import TransactionRaw

logger = logging.getLogger(__name__)

# =============================================================================
# RÈGLES D'IMPUTATION (Configurables)
# =============================================================================
REGLES_IMPUTATION = [
    # Recettes clients (Classe 7)
    {
        "mots_cles": ["client", "virement", "paiement", "mairie", "sarl", "sas", "btp"],
        "sens": "credit", 
        "compte_contrepartie": "707000",   # Ventes de marchandises
        "journal": "BQ",
        "categorie": "recette_client",
        "tva_applicable": True,
    },
    # Loyers (Classe 6)
    {
        "mots_cles": ["loyer", "bail", "immobilier"],
        "sens": "debit",
        "compte_contrepartie": "613200", 
        "journal": "BQ",
        "categorie": "loyer",
        "tva_applicable": True,
    },
    # Charges sociales (Classe 6 - Pas de TVA en général)
    {
        "mots_cles": ["urssaf", "cpam", "retraite", "prevoyance", "charges sociales"],
        "sens": "debit",
        "compte_contrepartie": "645000",
        "journal": "BQ",
        "categorie": "charges_sociales",
        "tva_applicable": False,
    },
    # Abonnements SaaS / Telecom (Classe 6)
    {
        "mots_cles": ["sage", "abonnement", "microsoft", "google", "aws", "ovh", "orange", "free"],
        "sens": "debit",
        "compte_contrepartie": "626000",
        "journal": "BQ",
        "categorie": "telecom_saas",
        "tva_applicable": True,
    },
    # Énergie (Classe 6)
    {
        "mots_cles": ["edf", "engie", "gaz", "électricité"],
        "sens": "debit",
        "compte_contrepartie": "606100",
        "journal": "BQ",
        "categorie": "energie",
        "tva_applicable": True,
    },
    # Matériel informatique (Classe 2 - Immobilisation)
    {
        "mots_cles": ["matériel", "informatique", "ordinateur", "serveur"],
        "sens": "debit",
        "compte_contrepartie": "218300",
        "journal": "BQ",
        "categorie": "immobilisation",
        "tva_applicable": True,
    },
]

COMPTE_BANQUE = "512000"

class MoteurImputation:
    def __init__(self, regles: list[dict] = None):
        self.regles = regles or REGLES_IMPUTATION

    def identifier_regle(self, transaction: TransactionRaw) -> dict:
        """Trouve la règle ou retourne le compte d'attente par défaut."""
        libelle_lower = transaction.libelle.lower()
        sens_tx = "credit" if transaction.montant > 0 else "debit"

        for regle in self.regles:
            if regle["sens"] == sens_tx:
                for mot in regle["mots_cles"]:
                    if mot in libelle_lower:
                        return regle

        # Fallback : Compte d'attente si aucune règle ne matche
        return {
            "compte_contrepartie": "471000",
            "journal": "BQ",
            "categorie": "a_preciser",
            "tva_applicable": False,
        }

    def generer_ecriture(self, transaction: TransactionRaw) -> dict:
        """Génère les lignes d'écriture en partie double (TTC)."""
        regle = self.identifier_regle(transaction)
        montant_abs = abs(transaction.montant)
        
        # Définition des lignes (Toujours Banque vs Contrepartie)
        if transaction.montant > 0: # Recette : D 512 / C 7xx
            lignes = [
                {"compte_numero": COMPTE_BANQUE, "montant_debit": montant_abs, "montant_credit": Decimal("0"), "libelle": transaction.libelle},
                {"compte_numero": regle["compte_contrepartie"], "montant_debit": Decimal("0"), "montant_credit": montant_abs, "libelle": transaction.libelle},
            ]
        else: # Dépense : D 6xx / C 512
            lignes = [
                {"compte_numero": regle["compte_contrepartie"], "montant_debit": montant_abs, "montant_credit": Decimal("0"), "libelle": transaction.libelle},
                {"compte_numero": COMPTE_BANQUE, "montant_debit": Decimal("0"), "montant_credit": montant_abs, "libelle": transaction.libelle},
            ]

        return {
            "journal_code": regle["journal"],
            "date_ecriture": transaction.date_operation,
            "numero_piece": transaction.reference,
            "libelle": transaction.libelle,
            "lignes": lignes,
            "tva_applicable": regle.get("tva_applicable", False)
        }
