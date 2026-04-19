"""
Service de connexion aux APIs bancaires.

Connecteurs implémentés :
  - Qonto      (FinTech FR, API officielle)
  - Bridge API (agrégateur bancaire, accès 300+ banques FR)
  - Simulateur (pour les tests sans credentials)

Utilisation :
    from app.services.api_bancaire import QontoConnector, BridgeConnector

    client = QontoConnector(api_key="xxx", organization_slug="ma-boite")
    transactions = client.get_transactions(date_debut="2024-01-01")
"""
import httpx
import logging
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod
import csv
import os

# On importe les bases si elles sont dans un autre fichier, 
# sinon on utilise celles définies ici.
# from .api_bancaire_base import ConnecteurBancaireBase, TransactionRaw

logger = logging.getLogger(__name__)

@dataclass
class TransactionRaw:
    reference: str
    date_operation: date
    date_valeur: date
    libelle: str
    montant: Decimal
    devise: str = "EUR"
    metadata: dict = field(default_factory=dict)

class ConnecteurBancaireBase(ABC):
    @abstractmethod
    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None
    ) -> list[TransactionRaw]:
        pass

    @abstractmethod
    def test_connexion(self) -> bool:
        pass

# ... (Classes QontoConnector et BridgeConnector inchangées, elles sont correctes) ...

# =============================================================================
# CONNECTEUR CSV — Corrigé pour respecter l'interface
# =============================================================================
class ConnecteurCSV(ConnecteurBancaireBase):
    """
    Lit les transactions à partir d'un fichier CSV réel.
    Respecte l'interface ConnecteurBancaireBase.
    """

    def __init__(self, fichier_path="transactions.csv"):
        self.fichier_path = fichier_path

    def test_connexion(self) -> bool:
        """Pour le CSV, tester la connexion revient à vérifier si le fichier existe."""
        return os.path.exists(self.fichier_path)

    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None
    ) -> list[TransactionRaw]:
        """
        Récupère les transactions et filtre par date si nécessaire.
        """
        transactions = []
        
        if not self.test_connexion():
            logger.warning(f"Fichier {self.fichier_path} non trouvé.")
            return []

        # Conversion des dates de string vers date pour le filtrage
        d_debut = date.fromisoformat(date_debut)
        d_fin = date.fromisoformat(date_fin) if date_fin else date.today()

        with open(self.fichier_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dt_op = datetime.strptime(row['date'], "%Y-%m-%d").date()
                    
                    # Filtrage par période (Optionnel mais recommandé pour respecter l'interface)
                    if not (d_debut <= dt_op <= d_fin):
                        continue

                    tx = TransactionRaw(
                        reference=row['reference'],
                        date_operation=dt_op,
                        date_valeur=dt_op, # Par défaut, date valeur = date op en CSV
                        libelle=row['libelle'],
                        montant=Decimal(row['montant']),
                        metadata={"source": "import_csv"}
                    )
                    transactions.append(tx)
                except (ValueError, KeyError) as e:
                    logger.error(f"Erreur sur la ligne {row}: {e}")
        
        logger.info(f"CSV : {len(transactions)} transactions importées")
        return transactions
