"""
Modèles comptables — cœur du projet.
Respecte la structure du Plan Comptable Général (PCG) français.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class CompteComptable(models.Model):
    """
    Plan Comptable Général — classes 1 à 7.
    Ex: 411000 = Clients, 401000 = Fournisseurs, 512000 = Banque
    """
    CLASSES = [
        ('1', 'Comptes de capitaux'),
        ('2', 'Comptes d\'immobilisations'),
        ('3', 'Comptes de stocks'),
        ('4', 'Comptes de tiers'),
        ('5', 'Comptes financiers'),
        ('6', 'Comptes de charges'),
        ('7', 'Comptes de produits'),
    ]

    numero      = models.CharField(max_length=10, unique=True)
    libelle     = models.CharField(max_length=200)
    classe      = models.CharField(max_length=1, choices=CLASSES)
    actif       = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['numero']
        verbose_name = 'Compte comptable'

    def __str__(self):
        return f"{self.numero} — {self.libelle}"

    @property
    def solde(self):
        """Calcule le solde débit - crédit de toutes les écritures."""
        from django.db.models import Sum
        lignes = self.lignes_ecriture.aggregate(
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit')
        )
        debit  = lignes['total_debit']  or Decimal('0')
        credit = lignes['total_credit'] or Decimal('0')
        return debit - credit


class Journal(models.Model):
    """Journaux comptables : ACH (achats), VTE (ventes), BQ (banque), OD (opérations diverses)"""
    TYPES = [
        ('ACH', 'Achats'),
        ('VTE', 'Ventes'),
        ('BQ',  'Banque'),
        ('CAI', 'Caisse'),
        ('OD',  'Opérations diverses'),
        ('AN',  'A nouveaux'),
    ]

    code    = models.CharField(max_length=5, unique=True)
    libelle = models.CharField(max_length=100)
    type    = models.CharField(max_length=5, choices=TYPES)

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class EcritureComptable(models.Model):
    """
    En-tête d'une écriture comptable (pièce).
    Une écriture = plusieurs lignes dont la somme débit = somme crédit.
    """
    journal         = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name='ecritures')
    date_ecriture   = models.DateField()
    numero_piece    = models.CharField(max_length=50)
    libelle         = models.CharField(max_length=200)
    date_import     = models.DateTimeField(auto_now_add=True)
    source          = models.CharField(max_length=50, default='manuel',
                                       help_text="manuel | api_bancaire | import_fec | qonto | pennylane")
    valide          = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_ecriture', '-id']
        unique_together = ['journal', 'numero_piece']

    def __str__(self):
        return f"{self.journal.code} / {self.numero_piece} — {self.libelle}"

    @property
    def est_equilibree(self):
        """Vérifie que débit = crédit (règle fondamentale de la comptabilité)."""
        from django.db.models import Sum
        totaux = self.lignes.aggregate(
            debit=Sum('montant_debit'),
            credit=Sum('montant_credit')
        )
        return (totaux['debit'] or 0) == (totaux['credit'] or 0)


class LigneEcriture(models.Model):
    """
    Ligne d'une écriture comptable.
    Règle : montant_debit XOR montant_credit (jamais les deux à la fois).
    """
    ecriture        = models.ForeignKey(EcritureComptable, on_delete=models.CASCADE, related_name='lignes')
    compte          = models.ForeignKey(CompteComptable, on_delete=models.PROTECT, related_name='lignes_ecriture')
    libelle         = models.CharField(max_length=200)
    montant_debit   = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    montant_credit  = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    date_echeance   = models.DateField(null=True, blank=True)
    lettrage        = models.CharField(max_length=10, blank=True,
                                       help_text="Code de lettrage pour rapprochement tiers")

    class Meta:
        ordering = ['id']

    def __str__(self):
        sens = f"D {self.montant_debit}" if self.montant_debit else f"C {self.montant_credit}"
        return f"{self.compte.numero} | {sens}"


class TransactionBancaire(models.Model):
    """
    Transaction importée depuis une API bancaire (Qonto, Bridge, etc.)
    Avant lettrage/imputation comptable.
    """
    STATUTS = [
        ('brut',    'Importée — non traitée'),
        ('imputee', 'Imputée comptablement'),
        ('ignoree', 'Ignorée'),
    ]

    reference_externe   = models.CharField(max_length=100, unique=True)
    date_operation      = models.DateField()
    date_valeur         = models.DateField()
    libelle_banque      = models.CharField(max_length=300)
    montant             = models.DecimalField(max_digits=15, decimal_places=2)
    devise              = models.CharField(max_length=3, default='EUR')
    statut              = models.CharField(max_length=10, choices=STATUTS, default='brut')
    ecriture_generee    = models.OneToOneField(
        EcritureComptable, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='transaction_source'
    )
    metadata            = models.JSONField(default=dict, blank=True)
    imported_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_operation']

    def __str__(self):
        sens = "+" if self.montant > 0 else ""
        return f"{self.date_operation} | {sens}{self.montant}€ — {self.libelle_banque[:50]}"
