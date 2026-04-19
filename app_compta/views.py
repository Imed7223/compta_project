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

# Imports de TOUS vos modèles
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
        service_finance = FinanceService()
        bilan = service_finance.generer_bilan()
        
        # On reformate pour le service PDF si nécessaire
        res_data = service_finance.generer_compte_resultat()
        resultat = {
            'total_produits': res_data.get('Total Produits (7)', 0),
            'total_charges': res_data.get('Total Charges (6)', 0),
            'resultat_net': res_data.get('Résultat Net', 0),
        }
        
        pdf_buffer = PDFExportService.generer_rapport_financier(bilan, resultat)
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Rapport_Financier_2026.pdf"'
        return response

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionBancaire.objects.all()
    serializer_class = TransactionBancaireSerializer

# --- VUE DU DASHBOARD (HTML) ---
@login_required # Seuls les utilisateurs connectés peuvent voir le dashboard
def dashboard_view(request):
    finance_service = FinanceService()
    
    # 1. Lancer le lettrage automatique
    LettrageService.lettrer_comptes_tiers()
    
    # 2. Récupérer les données brutes
    bilan_data = finance_service.generer_bilan()
    resultat_data = finance_service.generer_compte_resultat()
    
    # 3. Calcul direct du solde banque (Compte 512)
    # On utilise abs() car le solde bancaire est techniquement débiteur en compta
    solde_banque = finance_service.obtenir_solde_compte('512000')

    # 4. Calcul de la TVA
    tva_collectee = finance_service.obtenir_solde_compte('445710')
    tva_deductible = finance_service.obtenir_solde_compte('445660')
    tva_estimee = abs(tva_collectee) - abs(tva_deductible)

    # 5. Calcul des factures impayées
    creances_attente = LigneEcriture.objects.filter(
        compte__numero__startswith='411',
        lettrage=''
    ).aggregate(total=Sum('montant_debit'))['total'] or 0

    # 6. Contexte envoyé au template
    context = {
        'bilan': bilan_data,
        'solde_banque': round(abs(solde_banque), 2), # <--- CETTE LIGNE MANQUAIT
        'resultat': {
            'total_produits': resultat_data.get('Total Produits (7)', 0),
            'total_charges': resultat_data.get('Total Charges (6)', 0),
            'resultat_net': resultat_data.get('Résultat Net', 0),
        },
        'tva_estimee': round(tva_estimee, 2),
        'creances_attente': round(creances_attente, 2),
        'graph_data': list(LigneEcriture.objects.filter(compte__numero__startswith='6')
                           .annotate(mois=ExtractMonth('ecriture__date_ecriture'))
                           .values('mois')
                           .annotate(total=Sum('montant_debit'))
                           .order_by('mois')),
    }

    return render(request, 'app_compta/dashboard.html', context)
