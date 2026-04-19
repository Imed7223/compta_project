from django.contrib import admin
from .models import CompteComptable, Journal, EcritureComptable, LigneEcriture, TransactionBancaire

# Enregistrement simple de vos modèles
admin.site.register(CompteComptable)
admin.site.register(Journal)
admin.site.register(TransactionBancaire)


class LigneEcritureInline(admin.TabularInline):
    model = LigneEcriture
    extra = 2
    # Optionnel : permet de voir le solde en temps réel dans l'édition
    fields = ('compte', 'libelle', 'montant_debit', 'montant_credit')

@admin.register(EcritureComptable)
class EcritureAdmin(admin.ModelAdmin):
    # Correction ici : on s'assure que 'est_equilibree' est bien dans list_display
    list_display = ('date_ecriture', 'journal', 'numero_piece', 'libelle', 'valide', 'est_equilibree')
    list_filter = ('journal', 'date_ecriture', 'valide')
    search_fields = ('libelle', 'numero_piece')
    inlines = [LigneEcritureInline]

    # La méthode corrigée
    def est_equilibree(self, obj):
        # On appelle la méthode du modèle
        equilibre, total_d, total_c = obj.verifier_equilibre()
        return equilibre
    
    # Paramètres d'affichage pour l'admin Django
    est_equilibree.boolean = True  # Affiche une icône check/cross
    est_equilibree.short_description = "Équilibrée"

    def save_related(self, request, form, formsets, change):
        """Vérification après l'enregistrement des lignes (Inlines)"""
        super().save_related(request, form, formsets, change)
        
        # On récupère l'instance mise à jour
        obj = form.instance
        equilibre, total_d, total_c = obj.verifier_equilibre()
        
        if not equilibre:
            from django.contrib import messages
            messages.warning(
                request, 
                f"Attention : l'écriture '{obj.libelle}' est déséquilibrée ! "
                f"(Débit: {total_d} € | Crédit: {total_c} €)"
            )


@admin.register(LigneEcriture)
class LigneEcritureAdmin(admin.ModelAdmin):
    list_display = ('ecriture', 'compte', 'montant_debit', 'montant_credit', 'lettrage') # <-- Ajoutez 'lettrage' ici
