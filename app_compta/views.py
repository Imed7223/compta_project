from datetime import datetime, date
from decimal import Decimal
import csv
import io

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

# Imports de vos modèles
from .models import EcritureComptable, TransactionBancaire, LigneEcriture, CompteComptable, Journal
from .serializers import EcritureComptableSerializer, TransactionBancaireSerializer

# Imports de vos services métier
from .services.export_fec import generer_fec
from .services.etats_financiers import FinanceService
from .services.lettrage import LettrageService
from .services.pdf_export import PDFExportService
from .services.imputation import MoteurImputation
from .forms import CsvImportForm


class EcritureViewSet(viewsets.ModelViewSet):
    """
    Gestion des écritures comptables, export FEC et états financiers.
    """
    queryset = EcritureComptable.objects.all()
    serializer_class = EcritureComptableSerializer

    @action(detail=False, methods=['get'])
    def exporter_fec(self, request):
        """Génère le fichier FEC conforme DGFiP."""
        ecritures = EcritureComptable.objects.all()
        # Export pour l'année 2024
        contenu_fec = generer_fec(ecritures, date(2024, 1, 1), date(2024, 12, 31))
        response = HttpResponse(contenu_fec, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="fec_export.txt"'
        return response

    @action(detail=False, methods=['get'])
    def bilan(self, request):
        service = FinanceService()
        return Response(service.generer_bilan())

    @action(detail=False, methods=['get'])
    def resultat(self, request):
        service = FinanceService()
        return Response(service.generer_compte_resultat())

    @action(detail=False, methods=['get'])
    def telecharger_pdf(self, request):
        """
        Génère le rapport PDF incluant la synthèse, le bilan et le résultat.
        """
        service_finance = FinanceService()
        
        # 1. Données du Bilan
        bilan = service_finance.generer_bilan()
        
        # 2. Données du Résultat (Harmonisation des clés)
        res_data = service_finance.generer_compte_resultat()
        resultat = {
            'total_produits': res_data.get('total_produits', res_data.get('Total Produits (7)', 0)),
            'total_charges': res_data.get('total_charges', res_data.get('Total Charges (6)', 0)),
            'resultat_net': res_data.get('resultat_net', res_data.get('Résultat Net', 0)),
        }
        
        # 3. Calcul de la Synthèse
        solde_banque = service_finance.obtenir_solde_compte('512000')
        tva_collectee = service_finance.obtenir_solde_compte('445710')
        tva_deductible = service_finance.obtenir_solde_compte('445660')
        tva_estimee = abs(tva_collectee) - abs(tva_deductible)
        
        creances_attente = LigneEcriture.objects.filter(
            compte__numero__startswith='411',
            lettrage=''
        ).aggregate(total=Sum('montant_debit'))['total'] or 0

        synthese = {
            'solde_banque': round(abs(solde_banque), 2),
            'tva_estimee': round(tva_estimee, 2),
            'creances_attente': round(creances_attente, 2),
        }
        
        # 4. Génération du PDF
        pdf_buffer = PDFExportService.generer_rapport_financier(bilan, resultat, synthese)
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Rapport_Financier_2026.pdf"'
        return response


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionBancaire.objects.all()
    serializer_class = TransactionBancaireSerializer


# --- VUE DU DASHBOARD (HTML) ---
#@login_required
def dashboard_view(request):
    finance_service = FinanceService()
    
    # 1. Lancer le lettrage automatique
    LettrageService.lettrer_comptes_tiers()
    
    # 2. Récupérer les données financières
    bilan_data = finance_service.generer_bilan()
    res_data = finance_service.generer_compte_resultat()
    
    # 3. Calcul du solde banque
    solde_banque = finance_service.obtenir_solde_compte('512000')

    # 4. Calcul de la TVA
    tva_collectee = finance_service.obtenir_solde_compte('445710')
    tva_deductible = finance_service.obtenir_solde_compte('445660')
    tva_estimee = abs(tva_collectee) - abs(tva_deductible)

    # 5. Créances clients non lettrées
    creances_attente = LigneEcriture.objects.filter(
        compte__numero__startswith='411',
        lettrage=''
    ).aggregate(total=Sum('montant_debit'))['total'] or 0

    # 6. Graphique : Évolution des dépenses (Classe 6)
    depenses_mensuelles = LigneEcriture.objects.filter(compte__numero__startswith='6') \
                            .annotate(mois=ExtractMonth('ecriture__date_ecriture')) \
                            .values('mois') \
                            .annotate(total=Sum('montant_debit')) \
                            .order_by('mois')

    # 7. Graphique : Top 5 des charges (Répartition)
    repartition_charges = LigneEcriture.objects.filter(compte__numero__startswith='6') \
                            .values('compte__libelle') \
                            .annotate(total=Sum('montant_debit')) \
                            .order_by('-total')[:5]

    context = {
        'bilan': bilan_data,
        'solde_banque': round(abs(solde_banque), 2),
        'resultat': {
            'total_produits': res_data.get('total_produits', res_data.get('Total Produits (7)', 0)),
            'total_charges': res_data.get('total_charges', res_data.get('Total Charges (6)', 0)),
            'resultat_net': res_data.get('resultat_net', res_data.get('Résultat Net', 0)),
        },
        'tva_estimee': round(tva_estimee, 2),
        'creances_attente': round(creances_attente, 2),
        'graph_data': list(depenses_mensuelles),
        'repartition_charges': list(repartition_charges),
    }

    return render(request, 'app_compta/dashboard.html', context)


LIBELLES_COMPTES = {
    '707000': 'Ventes de prestations',
    '606100': 'Eau, gaz, électricité',
    '606300': 'Fournitures entretien',
    '613200': 'Loyers',
    '616000': 'Assurances',
    '622600': 'Honoraires',
    '626000': 'Télécoms et cloud',
    '627000': 'Services bancaires',
    '630000': 'Impôts et taxes',
    '645000': 'Charges sociales',
    '421000': 'Personnel rémunérations',
    '218300': 'Matériel informatique',
    '512000': 'Banque',
    '445660': 'TVA déductible',
    '445710': 'TVA collectée',
    '471000': "Compte d'attente",
}


def import_csv_view(request):
    if request.method == "POST":
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                next(reader)

                from .services.imputation import MoteurImputation, COMPTE_BANQUE
                from .services.api_bancaire import TransactionRaw
                from decimal import Decimal as D

                moteur = MoteurImputation()
                journal_bq, _ = Journal.objects.get_or_create(
                    code="BQ",
                    defaults={'libelle': 'Journal de Banque', 'type': 'BQ'}
                )
                count = 0

                for row in reader:
                    if len(row) < 4:
                        continue
                    ref, date_str, libelle, montant = row[0], row[1], row[2], row[3]
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    montant_decimal = D(montant)

                    if TransactionBancaire.objects.filter(reference_externe=ref).exists():
                        continue

                    tx_raw = TransactionRaw(
                        reference=ref,
                        date_operation=date_obj,
                        date_valeur=date_obj,
                        libelle=libelle,
                        montant=montant_decimal,
                    )

                    resultat = moteur.generer_ecriture(tx_raw)

                    if resultat:
                        taux_tva = D('0.20')
                        tva_active = resultat.get('tva_applicable', False)

                        ecriture = EcritureComptable.objects.create(
                            journal=journal_bq,
                            date_ecriture=date_obj,
                            numero_piece=ref,
                            libelle=libelle,
                            valide=True,
                            source='import_csv_web',
                        )

                        for l in resultat['lignes']:
                            montant_ttc = l['montant_debit'] if l['montant_debit'] > 0 else l['montant_credit']
                            
                            compte_obj, _ = CompteComptable.objects.get_or_create(
                                numero=l['compte_numero'],
                                defaults={
                                    'libelle': LIBELLES_COMPTES.get(l['compte_numero'], 'Compte Auto'),
                                    'classe': l['compte_numero'][0]
                                }
                            )
                            if compte_obj.libelle == 'Compte Auto':
                                compte_obj.libelle = LIBELLES_COMPTES.get(l['compte_numero'], 'Compte Auto')
                                compte_obj.save()

                            if tva_active and l['compte_numero'].startswith(('6', '7')):
                                montant_ht = (montant_ttc / (D('1') + taux_tva)).quantize(D('0.01'))
                                montant_tva = montant_ttc - montant_ht

                                LigneEcriture.objects.create(
                                    ecriture=ecriture,
                                    compte=compte_obj,
                                    libelle=f"{l['libelle']} (HT)",
                                    montant_debit=montant_ht if l['montant_debit'] > 0 else 0,
                                    montant_credit=montant_ht if l['montant_credit'] > 0 else 0,
                                )
                                compte_tva_num = "445660" if l['montant_debit'] > 0 else "445710"
                                compte_tva, _ = CompteComptable.objects.get_or_create(
                                    numero=compte_tva_num,
                                    defaults={'libelle': LIBELLES_COMPTES.get(compte_tva_num), 'classe': '4'}
                                )
                                LigneEcriture.objects.create(
                                    ecriture=ecriture,
                                    compte=compte_tva,
                                    libelle=f"TVA sur {l['libelle']}",
                                    montant_debit=montant_tva if l['montant_debit'] > 0 else 0,
                                    montant_credit=montant_tva if l['montant_credit'] > 0 else 0,
                                )
                            else:
                                LigneEcriture.objects.create(
                                    ecriture=ecriture,
                                    compte=compte_obj,
                                    libelle=l['libelle'],
                                    montant_debit=l['montant_debit'],
                                    montant_credit=l['montant_credit'],
                                )

                        TransactionBancaire.objects.create(
                            reference_externe=ref,
                            date_operation=date_obj,
                            date_valeur=date_obj,
                            libelle_banque=libelle,
                            montant=montant_decimal,
                            statut='imputee',
                            ecriture_generee=ecriture,
                        )
                        count += 1

                messages.success(request, f"Succès ! {count} nouvelles transactions importées et imputées.")
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f"Erreur lors de la lecture du fichier : {e}")

    else:
        form = CsvImportForm()

    return render(request, 'app_compta/import_csv.html', {'form': form})


def reset_donnees_view(request):
    if request.method == "POST":
        LigneEcriture.objects.all().delete()
        EcritureComptable.objects.all().delete()
        TransactionBancaire.objects.all().delete()
        messages.success(request, "Base réinitialisée. Vous pouvez importer un nouveau CSV.")
        return redirect('import_csv')
    return redirect('import_csv')
