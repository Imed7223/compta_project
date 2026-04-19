from django.contrib import admin
from .models import CompteComptable, Journal, EcritureComptable, LigneEcriture, TransactionBancaire

# Enregistrement simple de vos modèles
admin.site.register(CompteComptable)
admin.site.register(Journal)
admin.site.register(TransactionBancaire)

# Configuration un peu plus avancée pour les écritures (vue imbriquée)
class LigneEcritureInline(admin.TabularInline):
    model = LigneEcriture
    extra = 2 # Affiche 2 lignes vides par défaut

@admin.register(EcritureComptable)
class EcritureAdmin(admin.ModelAdmin):
    list_display = ('date_ecriture', 'journal', 'numero_piece', 'libelle', 'valide')
    inlines = [LigneEcritureInline]
    search_fields = ('numero_piece', 'libelle')
