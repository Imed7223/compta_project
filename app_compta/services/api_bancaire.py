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

logger = logging.getLogger(__name__)


@dataclass
class TransactionRaw:
    """Structure normalisée indépendante de la source bancaire."""
    reference:       str
    date_operation:  date
    date_valeur:     date
    libelle:         str
    montant:         Decimal          # positif = crédit, négatif = débit
    devise:          str = "EUR"
    metadata:        dict = field(default_factory=dict)


class ConnecteurBancaireBase(ABC):
    """Interface commune à tous les connecteurs bancaires."""

    @abstractmethod
    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None
    ) -> list[TransactionRaw]:
        ...

    @abstractmethod
    def test_connexion(self) -> bool:
        ...


# =============================================================================
# CONNECTEUR QONTO
# API officielle : https://api-doc.qonto.com
# Qonto = banque pro FR très utilisée par les PME et freelances
# =============================================================================
class QontoConnector(ConnecteurBancaireBase):
    BASE_URL = "https://thirdparty.qonto.com/v2"

    def __init__(self, login: str, secret_key: str):
        """
        login      : identifiant Qonto (slug-organisation:id-utilisateur)
        secret_key : clé secrète API Qonto
        """
        self.headers = {
            "Authorization": f"{login}:{secret_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(headers=self.headers, timeout=30)

    def test_connexion(self) -> bool:
        try:
            r = self.client.get(f"{self.BASE_URL}/organizations")
            return r.status_code == 200
        except httpx.RequestError:
            return False

    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None,
        iban: Optional[str] = None
    ) -> list[TransactionRaw]:
        """
        Récupère les transactions Qonto et les normalise.

        date_debut : "2024-01-01"
        date_fin   : "2024-12-31" (défaut = aujourd'hui)
        """
        params = {
            "settled_at_from": f"{date_debut}T00:00:00.000Z",
            "settled_at_to":   f"{date_fin or date.today()}T23:59:59.000Z",
            "per_page": 100,
            "current_page": 1,
        }
        if iban:
            params["iban"] = iban

        transactions = []
        while True:
            try:
                response = self.client.get(
                    f"{self.BASE_URL}/transactions",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Qonto API error {e.response.status_code}: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Qonto connexion error: {e}")
                raise

            for tx in data.get("transactions", []):
                # Qonto : side="debit" = sortie d'argent, "credit" = entrée
                montant = Decimal(str(tx["amount"]))
                if tx["side"] == "debit":
                    montant = -montant

                transactions.append(TransactionRaw(
                    reference=tx["transaction_id"],
                    date_operation=datetime.fromisoformat(
                        tx["settled_at"].replace("Z", "+00:00")
                    ).date(),
                    date_valeur=datetime.fromisoformat(
                        tx["settled_at"].replace("Z", "+00:00")
                    ).date(),
                    libelle=tx.get("label", tx.get("reference", "Sans libellé")),
                    montant=montant,
                    devise=tx.get("currency", "EUR"),
                    metadata={
                        "source": "qonto",
                        "category": tx.get("category"),
                        "vat_amount": tx.get("vat_amount"),
                        "attachment_ids": tx.get("attachment_ids", []),
                    }
                ))

            # Pagination
            meta = data.get("meta", {})
            if params["current_page"] >= meta.get("total_pages", 1):
                break
            params["current_page"] += 1

        logger.info(f"Qonto : {len(transactions)} transactions importées")
        return transactions


# =============================================================================
# CONNECTEUR BRIDGE (agrégateur — accès à 300+ banques FR)
# Docs : https://docs.bridgeapi.io
# =============================================================================
class BridgeConnector(ConnecteurBancaireBase):
    BASE_URL = "https://api.bridgeapi.io/v2"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id     = client_id
        self.client_secret = client_secret
        self._access_token = None
        self.client        = httpx.Client(timeout=30)

    def _authenticate(self) -> str:
        """OAuth2 client_credentials."""
        r = self.client.post(
            f"{self.BASE_URL}/authenticate",
            json={
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "grant_type":    "client_credentials",
            }
        )
        r.raise_for_status()
        self._access_token = r.json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self._access_token}"
        return self._access_token

    def test_connexion(self) -> bool:
        try:
            self._authenticate()
            return True
        except Exception:
            return False

    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None,
        account_id: Optional[int] = None
    ) -> list[TransactionRaw]:
        if not self._access_token:
            self._authenticate()

        params = {
            "since": date_debut,
            "until": date_fin or str(date.today()),
            "limit": 500,
        }
        if account_id:
            params["account_id"] = account_id

        r = self.client.get(f"{self.BASE_URL}/transactions", params=params)
        r.raise_for_status()

        transactions = []
        for tx in r.json().get("resources", []):
            transactions.append(TransactionRaw(
                reference=str(tx["id"]),
                date_operation=date.fromisoformat(tx["date"]),
                date_valeur=date.fromisoformat(tx.get("value_date", tx["date"])),
                libelle=tx.get("description", ""),
                montant=Decimal(str(tx["amount"])),
                devise=tx.get("currency_code", "EUR"),
                metadata={"source": "bridge", "category_id": tx.get("category_id")},
            ))

        return transactions


# =============================================================================
# SIMULATEUR — pour développer et tester sans credentials réels
# =============================================================================
class SimulateurBancaire(ConnecteurBancaireBase):
    """
    Génère des transactions réalistes pour une PME fictive.
    Parfait pour les démos, les tests, et le développement local.
    """

    DONNEES_FICTIVES = [
        ("VIRT-001", "2024-01-05", "Paiement client SARL DURAND",          +4800.00),
        ("VIRT-002", "2024-01-08", "Loyer bureau janvier",                  -1200.00),
        ("VIRT-003", "2024-01-10", "Fournisseur IMPRIMERIE MARTIN",          -350.00),
        ("VIRT-004", "2024-01-15", "Virement client SAS INNOVATION",        +2400.00),
        ("VIRT-005", "2024-01-18", "EDF PRO — facture énergie",              -180.00),
        ("VIRT-006", "2024-01-20", "Abonnement Sage 100",                    -129.00),
        ("VIRT-007", "2024-01-22", "Paiement prestataire freelance",        -1500.00),
        ("VIRT-008", "2024-01-25", "Virement client MAIRIE DE PARIS",       +8500.00),
        ("VIRT-009", "2024-01-28", "Charges sociales URSSAF",              -2100.00),
        ("VIRT-010", "2024-01-31", "Remboursement note de frais",            -245.00),
        ("VIRT-011", "2024-02-02", "Paiement client SARL TECHNO",           +3200.00),
        ("VIRT-012", "2024-02-05", "Orange Pro — téléphonie",                 -89.00),
        ("VIRT-013", "2024-02-10", "Achat matériel informatique",            -780.00),
        ("VIRT-014", "2024-02-14", "Virement client BTP CONSTRUCTIONS",     +5600.00),
        ("VIRT-015", "2024-02-28", "Loyer bureau février",                  -1200.00),
    ]

    def test_connexion(self) -> bool:
        return True

    def get_transactions(
        self,
        date_debut: str,
        date_fin: Optional[str] = None
    ) -> list[TransactionRaw]:
        debut = date.fromisoformat(date_debut)
        fin   = date.fromisoformat(date_fin) if date_fin else date.today()

        transactions = []
        for ref, d, libelle, montant in self.DONNEES_FICTIVES:
            d_parsed = date.fromisoformat(d)
            if debut <= d_parsed <= fin:
                transactions.append(TransactionRaw(
                    reference=ref,
                    date_operation=d_parsed,
                    date_valeur=d_parsed,
                    libelle=libelle,
                    montant=Decimal(str(montant)),
                    devise="EUR",
                    metadata={"source": "simulateur"},
                ))

        logger.info(f"Simulateur : {len(transactions)} transactions générées")
        return transactions
