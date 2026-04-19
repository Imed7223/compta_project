"""
Export FEC — Fichier des Écritures Comptables.

Format légal imposé par l'article L.47 A du Livre des Procédures Fiscales.
Obligatoire pour tout contrôle fiscal en France depuis 2014.
Savoir générer un FEC propre = compétence très rare et très valorisée.

Format : CSV pipe-séparé, encodage UTF-8 BOM, 18 colonnes obligatoires.
"""
import csv
import io
import logging
from datetime import date

logger = logging.getLogger(__name__)

COLONNES_FEC = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
    "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib",
    "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
    "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise",
]


def generer_fec(ecritures: list, date_debut: date, date_fin: date) -> str:
    """
    Génère un fichier FEC conforme au format DGFiP.
    Retourne : contenu du fichier (string UTF-8 avec BOM)
    """
    output = io.StringIO()
    output.write('\ufeff')  # BOM UTF-8 requis

    writer = csv.writer(output, delimiter='|', lineterminator='\r\n')
    writer.writerow(COLONNES_FEC)

    nb_lignes = 0
    for ecriture in ecritures:
        for ligne in ecriture.lignes.select_related('compte').all():
            writer.writerow([
                ecriture.journal.code,
                ecriture.journal.libelle,
                ecriture.numero_piece,
                ecriture.date_ecriture.strftime("%Y%m%d"),
                ligne.compte.numero,
                ligne.compte.libelle,
                "",  # CompAuxNum
                "",  # CompAuxLib
                ecriture.numero_piece,
                ecriture.date_ecriture.strftime("%Y%m%d"),
                ligne.libelle or ecriture.libelle,
                str(ligne.montant_debit).replace('.', ',') if ligne.montant_debit else "0,00",
                str(ligne.montant_credit).replace('.', ',') if ligne.montant_credit else "0,00",
                ligne.lettrage or "",
                "",   # DateLet
                ecriture.date_ecriture.strftime("%Y%m%d") if ecriture.valide else "",
                "",   # Montantdevise
                "",   # Idevise
            ])
            nb_lignes += 1

    logger.info(f"FEC généré : {nb_lignes} lignes, période {date_debut} -> {date_fin}")
    return output.getvalue()


def valider_fec(contenu_fec: str) -> dict:
    """Valide un fichier FEC selon les règles DGFiP."""
    erreurs = []
    lignes = contenu_fec.strip().split('\r\n')

    if not lignes:
        return {"valide": False, "erreurs": ["Fichier vide"]}

    entete = lignes[0].split('|')
    if entete != COLONNES_FEC:
        erreurs.append("En-tête FEC incorrect")

    totaux_debit  = 0.0
    totaux_credit = 0.0

    for i, ligne in enumerate(lignes[1:], start=2):
        colonnes = ligne.split('|')
        if len(colonnes) != 18:
            erreurs.append(f"Ligne {i} : {len(colonnes)} colonnes au lieu de 18")
            continue
        try:
            totaux_debit  += float(colonnes[11].replace(',', '.') or '0')
            totaux_credit += float(colonnes[12].replace(',', '.') or '0')
        except ValueError:
            erreurs.append(f"Ligne {i} : montant invalide")

    if abs(totaux_debit - totaux_credit) > 0.01:
        erreurs.append(
            f"Déséquilibre : Débit={totaux_debit:.2f} / Crédit={totaux_credit:.2f}"
        )

    return {
        "valide":       len(erreurs) == 0,
        "nb_lignes":    len(lignes) - 1,
        "total_debit":  round(totaux_debit, 2),
        "total_credit": round(totaux_credit, 2),
        "erreurs":      erreurs,
    }
