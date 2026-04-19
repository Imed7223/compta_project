from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from io import BytesIO

class PDFExportService:
    @staticmethod
    def generer_rapport_financier(bilan, resultat, synthese):
        """
        Génère un rapport PDF complet incluant Synthèse, Bilan et Résultat.
        """
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # --- 1. En-tête ---
        p.setFont("Helvetica-Bold", 22)
        # CORRECTION : Utilisation de HexColor (avec un H majuscule)
        dark_blue = colors.HexColor("#1a1f4e")
        light_blue = colors.HexColor("#2d3a8c")
        
        p.setFillColor(dark_blue)
        p.drawString(2 * cm, height - 2 * cm, "RAPPORT FINANCIER 2026")
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.grey)
        p.drawString(2 * cm, height - 2.6 * cm, "Généré automatiquement par ComptaFlow • Analyse de performance")
        p.line(2 * cm, height - 3 * cm, width - 2 * cm, height - 3 * cm)

        # --- 2. Section I : SYNTHÈSE DE L'ACTIVITÉ ---
        y = height - 4.5 * cm
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(light_blue)
        p.drawString(2 * cm, y, "I. SYNTHÈSE DE L'ACTIVITÉ")
        
        y -= 0.8 * cm
        p.setFont("Helvetica", 11)
        p.setFillColor(colors.black)
        
        indicateurs = [
            ("Trésorerie disponible (Banque)", f"{synthese['solde_banque']:,.2f} €"),
            ("TVA estimée à reverser", f"{synthese['tva_estimee']:,.2f} €"),
            ("Créances clients (Factures non lettrées)", f"{synthese['creances_attente']:,.2f} €"),
        ]

        for label, valeur in indicateurs:
            y -= 0.6 * cm
            p.drawString(2.5 * cm, y, label)
            p.drawRightString(width - 3 * cm, y, valeur)

        # --- 3. Section II : BILAN SIMPLIFIÉ (ACTIF) ---
        y -= 1.5 * cm
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(light_blue)
        p.drawString(2 * cm, y, "II. BILAN SIMPLIFIÉ (ACTIF)")
        
        y -= 0.8 * cm
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.black)
        p.drawString(2.5 * cm, y, "Poste de l'Actif")
        p.drawRightString(width - 3 * cm, y, "Montant (€)")
        
        p.setFont("Helvetica", 11)
        p.line(2.5 * cm, y - 0.2 * cm, width - 3 * cm, y - 0.2 * cm)
        
        for poste, montant in bilan['actif'].items():
            y -= 0.7 * cm
            p.drawString(2.5 * cm, y, str(poste))
            p.drawRightString(width - 3 * cm, y, f"{montant:,.2f}")

        # --- 4. Section III : COMPTE DE RÉSULTAT ---
        y -= 2 * cm
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(light_blue)
        p.drawString(2 * cm, y, "III. COMPTE DE RÉSULTAT")
        
        y -= 1 * cm
        p.setFont("Helvetica", 11)
        p.setFillColor(colors.black)
        p.drawString(2.5 * cm, y, "Total des Produits (Ventes) :")
        p.drawRightString(width - 3 * cm, y, f"{resultat['total_produits']:,.2f}")
        
        y -= 0.7 * cm
        p.drawString(2.5 * cm, y, "Total des Charges :")
        p.drawRightString(width - 3 * cm, y, f"{resultat['total_charges']:,.2f}")
        
        y -= 1.2 * cm
        p.setFont("Helvetica-Bold", 12)
        
        if resultat['resultat_net'] >= 0:
            p.setFillColor(colors.darkgreen)
            label_res = "BÉNÉFICE NET :"
        else:
            p.setFillColor(colors.red)
            label_res = "PERTE NETTE :"
        
        p.drawString(2.5 * cm, y, label_res)
        p.drawRightString(width - 3 * cm, y, f"{resultat['resultat_net']:,.2f} €")

        # --- 5. Bas de page ---
        p.setFont("Helvetica-Oblique", 8)
        p.setFillColor(colors.grey)
        p.drawCentredString(width/2, 1.5 * cm, "ComptaFlow - Logiciel de gestion certifié 2026")

        p.showPage()
        p.save()
        
        buffer.seek(0)
        return buffer
