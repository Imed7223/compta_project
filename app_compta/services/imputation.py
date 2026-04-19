"""
Moteur d'imputation automatique des transactions bancaires.
Transforme les flux bancaires en écritures comptables en partie double.
"""
import logging
from decimal import Decimal
from .api_bancaire import TransactionRaw
from app_compta.models import EcritureComptable, LigneEcriture, CompteComptable, Journal

logger = logging.getLogger(__name__)

# =============================================================================
# RÈGLES D'IMPUTATION (Configurables)
# =============================================================================

# Configuration du compte de banque par défaut
COMPTE_BANQUE = "512000"

REGLES_IMPUTATION = [
    # --- PRODUITS (CLASSE 7) ---
    {
        "mots_cles": ["vente", "client", "virement", "paiement", "facture", "sarl", "sas"],
        "sens": "credit",
        "compte_contrepartie": "707000",  # Ventes de marchandises / Prestations
        "categorie": "chiffre_affaires",
        "tva_applicable": True,
    },
    
    # --- CHARGES EXTERNES (CLASSE 60/61/62) ---
    {
        "mots_cles": ["edf", "engie", "total", "gaz", "electricite", "eau"],
        "sens": "debit",
        "compte_contrepartie": "606100",  # Fournitures non stockables (Énergie)
        "categorie": "energie",
        "tva_applicable": True,
    },
    {
        "mots_cles": ["amazon", "fnac", "bureau", "fourniture", "papier", "encre"],
        "sens": "debit",
        "compte_contrepartie": "606300",  # Fournitures d'entretien et de petit équipement
        "categorie": "achats_divers",
        "tva_applicable": True,
    },
    {
        "mots_cles": ["loyer", "immobilier", "sci", "bail", "quittance"],
        "sens": "debit",
        "compte_contrepartie": "613200",  # Locations immobilières
        "categorie": "loyer",
        "tva_applicable": True,
    },
    {
        "mots_cles": ["assurance", "axa", "allianz", "maaf", "macif", "generali"],
        "sens": "debit",
        "compte_contrepartie": "616000",  # Primes d'assurances (Souvent sans TVA)
        "categorie": "assurance",
        "tva_applicable": False,
    },
    {
        "mots_cles": ["avocat", "comptable", "expert", "honoraire", "conseil", "juridique"],
        "sens": "debit",
        "compte_contrepartie": "622600",  # Honoraires
        "categorie": "honoraires",
        "tva_applicable": True,
    },
    {
        "mots_cles": ["orange", "sfr", "bouygues", "free", "telecom", "internet", "cloud", "aws", "google", "microsoft"],
        "sens": "debit",
        "compte_contrepartie": "626000",  # Frais postaux et télécommunications
        "categorie": "telecom_it",
        "tva_applicable": True,
    },
    {
        "mots_cles": ["frais", "commission", "agios", "tenue de compte", "banque"],
        "sens": "debit",
        "compte_contrepartie": "627000",  # Services bancaires
        "categorie": "frais_bancaires",
        "tva_applicable": False, # La plupart des frais bancaires sont exonérés
    },

    # --- IMPÔTS ET TAXES (CLASSE 63) ---
    {
        "mots_cles": ["impot", "tresor public", "cfe", "is", "taxe"],
        "sens": "debit",
        "compte_contrepartie": "630000",  # Impôts et taxes
        "categorie": "impots",
        "tva_applicable": False,
    },

    # --- CHARGES DE PERSONNEL (CLASSE 64) ---
    {
        "mots_cles": ["salaire", "remuneration", "virement salaire"],
        "sens": "debit",
        "compte_contrepartie": "421000",  # Personnel - Rémunérations dues (On passe par un compte tiers)
        "categorie": "salaires",
        "tva_applicable": False,
    },
    {
        "mots_cles": ["urssaf", "cotisation", "retraite", "prevoyance", "malakoff", "agirc"],
        "sens": "debit",
        "compte_contrepartie": "645000",  # Charges de sécurité sociale
        "categorie": "social",
        "tva_applicable": False,
    },

    # --- IMMOBILISATIONS (CLASSE 2) ---
    {
        "mots_cles": ["apple", "macbook", "dell", "ordinateur", "serveur", "iphone"],
        "sens": "debit",
        "compte_contrepartie": "218300",  # Matériel de bureau et informatique
        "categorie": "immo_it",
        "tva_applicable": True,
    },
]

class MoteurImputation:
    def __init__(self, regles: list[dict] = None):
        self.regles = regles or REGLES_IMPUTATION

    def imputer(self, transaction):
        regle = self.identifier_regle(transaction)
        montant_abs = abs(transaction.montant)
        
        # 1. Récupérer ou créer l'objet Journal "Achats/Ventes/Banque"
        # On utilise "BQ" pour Banque
        journal_obj, _ = Journal.objects.get_or_create(
            code="BQ", 
            defaults={'libelle': 'Journal de Banque'}
        )

        # 2. Créer l'entête de l'écriture en passant l'OBJET journal
        ecriture = EcritureComptable.objects.create(
            journal=journal_obj,  # <-- On passe l'objet, pas le texte
            date_ecriture=transaction.date_operation,
            libelle=transaction.libelle_banque,
            numero_piece=transaction.reference_externe
        )

        # 3. Créer les lignes (Partie Double)
        # Compte de contrepartie (Charge ou Produit)
        compte_cp = CompteComptable.objects.get_or_create(numero=regle["compte_contrepartie"])[0]
        # Compte de banque
        compte_bq = CompteComptable.objects.get_or_create(numero=COMPTE_BANQUE)[0]

        if transaction.montant > 0: # Entrée d'argent (Vente)
            # Débit Banque / Crédit Produit
            LigneEcriture.objects.create(ecriture=ecriture, compte=compte_bq, montant_debit=montant_abs, libelle=transaction.libelle_banque)
            LigneEcriture.objects.create(ecriture=ecriture, compte=compte_cp, montant_credit=montant_abs, libelle=transaction.libelle_banque)
        else: # Sortie d'argent (Achat)
            # Débit Charge / Crédit Banque
            LigneEcriture.objects.create(ecriture=ecriture, compte=compte_cp, montant_debit=montant_abs, libelle=transaction.libelle_banque)
            LigneEcriture.objects.create(ecriture=ecriture, compte=compte_bq, montant_credit=montant_abs, libelle=transaction.libelle_banque)

        # 4. Mettre à jour le statut de la transaction
        transaction.statut = 'valide'
        transaction.ecriture_generee = ecriture
        transaction.save()
        
        return ecriture
    def identifier_regle(self, transaction) -> dict:
        """Recherche une règle basée sur le libellé de la transaction."""
        # Compatibilité TransactionRaw (libelle) et TransactionBancaire (libelle_banque)
        libelle_raw = getattr(transaction, 'libelle', None) or getattr(transaction, 'libelle_banque', '')
        libelle_lower = libelle_raw.lower()
        sens_tx = "credit" if transaction.montant > 0 else "debit"

        for regle in self.regles:
            if regle["sens"] == sens_tx:
                for mot in regle["mots_cles"]:
                    if mot in libelle_lower:
                        return regle

        return {
            "compte_contrepartie": "471000",
            "categorie": "a_preciser",
            "tva_applicable": False,
        }

    def generer_ecriture(self, transaction) -> dict | None:
        """
        Retourne un dict décrivant les lignes à créer, sans toucher à la base.
        """
        regle = self.identifier_regle(transaction)
        montant_abs = abs(transaction.montant)
        libelle = getattr(transaction, 'libelle', None) or getattr(transaction, 'libelle_banque', '')

        if transaction.montant > 0:
            lignes = [
                {
                    'compte_numero': COMPTE_BANQUE,
                    'libelle': libelle,
                    'montant_debit': montant_abs,
                    'montant_credit': Decimal('0'),
                },
                {
                    'compte_numero': regle['compte_contrepartie'],
                    'libelle': libelle,
                    'montant_debit': Decimal('0'),
                    'montant_credit': montant_abs,
                },
            ]
        else:
            lignes = [
                {
                    'compte_numero': regle['compte_contrepartie'],
                    'libelle': libelle,
                    'montant_debit': montant_abs,
                    'montant_credit': Decimal('0'),
                },
                {
                    'compte_numero': COMPTE_BANQUE,
                    'libelle': libelle,
                    'montant_debit': Decimal('0'),
                    'montant_credit': montant_abs,
                },
            ]

        return {
            'lignes': lignes,
            'tva_applicable': regle.get('tva_applicable', False),
        }
