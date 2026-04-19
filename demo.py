"""
Démonstration complète du projet — tourne sans Django ni base de données.

Lance avec : python demo.py

Ce script simule un flux complet :
  1. Import de transactions depuis l'API bancaire (simulateur)
  2. Imputation automatique (moteur de règles)
  3. Génération du rapport
  4. Export FEC simplifié

C'est ce que tu montres à un recruteur ou un client freelance.
"""
import sys
from decimal import Decimal
from datetime import date
import json

# ---------------------------------------------------------------------------
# Simulateur inline (pas besoin d'installer quoi que ce soit)
# ---------------------------------------------------------------------------
TRANSACTIONS_DEMO = [
    ("VRT-001", "2024-01-05", "Paiement client SARL DURAND",            +4800.00),
    ("VRT-002", "2024-01-08", "Loyer bureau janvier",                   -1200.00),
    ("VRT-003", "2024-01-10", "Fournisseur IMPRIMERIE MARTIN",           -350.00),
    ("VRT-004", "2024-01-15", "Virement client SAS INNOVATION",         +2400.00),
    ("VRT-005", "2024-01-18", "EDF PRO — facture énergie",               -180.00),
    ("VRT-006", "2024-01-20", "Abonnement Sage 100",                     -129.00),
    ("VRT-007", "2024-01-22", "Paiement prestataire freelance",         -1500.00),
    ("VRT-008", "2024-01-25", "Virement client MAIRIE DE PARIS",        +8500.00),
    ("VRT-009", "2024-01-28", "Charges sociales URSSAF",               -2100.00),
    ("VRT-010", "2024-01-31", "Remboursement note de frais",             -245.00),
    ("VRT-011", "2024-02-14", "Achat matériel informatique",             -780.00),
    ("VRT-012", "2024-02-20", "Abonnement AWS Cloud",                    -320.00),
    ("VRT-013", "2024-02-28", "Inconnu - virement reçu XKCD42",        +1000.00),  # Sans règle
]

COMPTE_BANQUE = "512000"

REGLES = [
    {"mots_cles": ["client", "virement", "mairie", "sarl", "sas"],
     "sens": "credit", "compte": "411000", "label": "Clients"},
    {"mots_cles": ["loyer", "bail"],
     "sens": "debit",  "compte": "613200", "label": "Loyers"},
    {"mots_cles": ["urssaf", "charges sociales"],
     "sens": "debit",  "compte": "645000", "label": "Charges sociales"},
    {"mots_cles": ["fournisseur", "imprimerie", "prestataire", "freelance"],
     "sens": "debit",  "compte": "401000", "label": "Fournisseurs"},
    {"mots_cles": ["sage", "abonnement", "aws", "microsoft", "ovh"],
     "sens": "debit",  "compte": "626000", "label": "Abonnements"},
    {"mots_cles": ["edf", "gaz", "énergie", "energie"],
     "sens": "debit",  "compte": "606100", "label": "Énergie"},
    {"mots_cles": ["matériel", "informatique", "ordinateur"],
     "sens": "debit",  "compte": "218300", "label": "Matériel info"},
    {"mots_cles": ["note de frais", "remboursement", "frais"],
     "sens": "debit",  "compte": "625000", "label": "Frais"},
]


def identifier_regle(libelle: str, montant: float) -> dict | None:
    sens = "credit" if montant > 0 else "debit"
    lib  = libelle.lower()
    for regle in REGLES:
        if regle["sens"] != sens:
            continue
        for mot in regle["mots_cles"]:
            if mot in lib:
                return regle
    return None


def imputer(ref, d, libelle, montant) -> dict | None:
    regle = identifier_regle(libelle, montant)
    if not regle:
        return None

    mt = abs(Decimal(str(montant)))

    if montant > 0:  # Entrée : D Banque / C Clients
        lignes = [
            (COMPTE_BANQUE,      "Banque",          mt,   Decimal(0)),
            (regle["compte"],    regle["label"],    Decimal(0), mt),
        ]
    else:            # Sortie : D Charge / C Banque
        lignes = [
            (regle["compte"],    regle["label"],    mt,   Decimal(0)),
            (COMPTE_BANQUE,      "Banque",          Decimal(0), mt),
        ]

    return {
        "ref":    ref,
        "date":   d,
        "libelle": libelle,
        "compte_contrepartie": regle["compte"],
        "categorie": regle["label"],
        "lignes": lignes,
        "equilibre": sum(l[2] for l in lignes) == sum(l[3] for l in lignes),
    }


def run():
    SEP  = "─" * 68
    SEP2 = "═" * 68

    print(f"\n{SEP2}")
    print("  COMPTA API — Démonstration d'imputation automatique")
    print(f"{SEP2}\n")

    # ── 1. Import des transactions ───────────────────────────────────────────
    print(f"{'ÉTAPE 1':─<68}")
    print(f"  Import de {len(TRANSACTIONS_DEMO)} transactions bancaires\n")

    for ref, d, lib, mt in TRANSACTIONS_DEMO:
        sens = f"+{mt:.2f}€" if mt > 0 else f"{mt:.2f}€"
        print(f"  {'✓':2} {d}  {sens:>12}  {lib[:45]}")

    # ── 2. Imputation automatique ────────────────────────────────────────────
    print(f"\n{'ÉTAPE 2':─<68}")
    print("  Imputation automatique par moteur de règles\n")

    imputees     = []
    non_imputees = []

    for ref, d, lib, mt in TRANSACTIONS_DEMO:
        ecriture = imputer(ref, d, lib, mt)
        if ecriture:
            imputees.append(ecriture)
        else:
            non_imputees.append((ref, d, lib, mt))

    for e in imputees:
        signe = "+" if any(l[2] > 0 and l[0] == COMPTE_BANQUE for l in e["lignes"]) else "-"
        print(f"  ✅ {e['ref']:10} → {e['compte_contrepartie']} {e['categorie']}")
        for l in e["lignes"]:
            d_str = f"D {l[2]:.2f}€" if l[2] else f"          C {l[3]:.2f}€"
            print(f"           {l[0]}  {d_str}")
        print()

    for ref, d, lib, mt in non_imputees:
        print(f"  ⚠️  {ref:10} → AUCUNE RÈGLE — imputation manuelle requise")
        print(f"           Libellé : {lib}\n")

    # ── 3. Rapport ───────────────────────────────────────────────────────────
    print(f"\n{'ÉTAPE 3':─<68}")
    print("  Rapport de traitement\n")

    total    = len(TRANSACTIONS_DEMO)
    nb_imp   = len(imputees)
    taux     = nb_imp / total * 100

    total_recettes = sum(
        abs(Decimal(str(mt))) for _, _, _, mt in TRANSACTIONS_DEMO if mt > 0
    )
    total_depenses = sum(
        abs(Decimal(str(mt))) for _, _, _, mt in TRANSACTIONS_DEMO if mt < 0
    )
    solde = total_recettes - total_depenses

    print(f"  Transactions importées   : {total}")
    print(f"  Imputées automatiquement : {nb_imp}  ({taux:.0f}%)")
    print(f"  À traiter manuellement   : {len(non_imputees)}")
    print()
    print(f"  Total recettes           : +{total_recettes:>10.2f} €")
    print(f"  Total dépenses           :  {total_depenses:>10.2f} €")
    print(f"  Solde net                : {'+'if solde>=0 else ''}{solde:>10.2f} €")

    # ── 4. Export FEC (simplifié) ────────────────────────────────────────────
    print(f"\n{'ÉTAPE 4':─<68}")
    print("  Aperçu export FEC (Fichier des Écritures Comptables)\n")

    print("  JournalCode|EcritureNum|EcritureDate|CompteNum|CompteLib|Debit|Credit")
    print("  " + "·" * 66)
    for e in imputees[:4]:
        for l in e["lignes"]:
            print(f"  BQ|{e['ref']}|{e['date']}|{l[0]}|{l[1][:20]:<20}|"
                  f"{l[2]:.2f}|{l[3]:.2f}")
    print("  [...]")

    print(f"\n{SEP2}")
    print("  Projet complet sur GitHub → Django REST API + Connecteurs Qonto/Bridge")
    print(f"  Stack : Python · Django · PostgreSQL · Redis · Docker")
    print(f"{SEP2}\n")


if __name__ == "__main__":
    run()
