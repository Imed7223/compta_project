from rest_framework import serializers
from .models import CompteComptable, Journal, EcritureComptable, LigneEcriture, TransactionBancaire

class CompteComptableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompteComptable
        fields = '__all__'

class LigneEcritureSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneEcriture
        fields = ['id', 'compte', 'libelle', 'montant_debit', 'montant_credit', 'lettrage']

class EcritureComptableSerializer(serializers.ModelSerializer):
    lignes = LigneEcritureSerializer(many=True, read_only=True)
    
    class Meta:
        model = EcritureComptable
        fields = ['id', 'journal', 'date_ecriture', 'numero_piece', 'libelle', 'valide', 'lignes']

class TransactionBancaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionBancaire
        fields = '__all__'
