from datetime import date
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from .services.pdf_export import PDFExportService

# Imports de vos modèles
from .models import EcritureComptable, TransactionBancaire, LigneEcriture, CompteComptable

# Imports de vos sérialiseurs
from .serializers import EcritureComptableSerializer, TransactionBancaireSerializer

# Imports de vos services métier
from .services.export_fec import generer_fec
from .services.etats_financiers import FinanceService
from .services.lettrage import LettrageService


class EcritureViewSet(viewsets.ModelViewSet):
    """
    Gestion des écritures comptables, export FEC et états financiers.
    """
    queryset = EcritureComptable.objects.all()
    serializer_class = EcritureComptableSerializer

    @action(detail=False, methods=['get'])
    def exporter_fec(self, request):
        ecritures = EcritureComptable.objects.all()
        # Export pour l'année 2024 selon votre configuration initiale
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
        
        # 2. Données du Résultat
        res_data = service_finance.generer_compte_resultat()
        resultat = {
            'total_produits': res_data.get('Total Produits (7)', 0),
            'total_charges': res_data.get('Total Charges (6)', 0),
            'resultat_net': res_data.get('Résultat Net', 0),
        }
        
        # 3. Calcul de la Synthèse (Identique au Dashboard)
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
        
        # 4. Génération du PDF avec les 3 arguments
        pdf_buffer = PDFExportService.generer_rapport_financier(bilan, resultat, synthese)
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Rapport_Financier_2026.pdf"'
        return response


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionBancaire.objects.all()
    serializer_class = TransactionBancaireSerializer


# --- VUE DU DASHBOARD (HTML) ---
@login_required
def dashboard_view(request):
    finance_service = FinanceService()
    
    # 1. Lancer le lettrage automatique
    LettrageService.lettrer_comptes_tiers()
    
    # 2. Récupérer les données brutes
    bilan_data = finance_service.generer_bilan()
    resultat_data = finance_service.generer_compte_resultat()
    
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
            'total_produits': resultat_data.get('Total Produits (7)', 0),
            'total_charges': resultat_data.get('Total Charges (6)', 0),
            'resultat_net': resultat_data.get('Résultat Net', 0),
        },
        'tva_estimee': round(tva_estimee, 2),
        'creances_attente': round(creances_attente, 2),
        'graph_data': list(depenses_mensuelles),
        'repartition_charges': list(repartition_charges),
    }

    return render(request, 'app_compta/dashboard.html', context)
