from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from io import BytesIO

class PDFExportService:
    @staticmethod
    def generer_rapport_financier(bilan, resultat):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # --- En-tête ---
        p.setFont("Helvetica-Bold", 20)
        p.drawString(2 * cm, height - 2 * cm, "RAPPORT FINANCIER 2026")
        
        p.setFont("Helvetica", 12)
        p.drawString(2 * cm, height - 2.7 * cm, "Généré automatiquement par ComptaFlow")
        p.line(2 * cm, height - 3 * cm, width - 2 * cm, height - 3 * cm)

        # --- Section BILAN (Actif) ---
        y = height - 4.5 * cm
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2 * cm, y, "I. BILAN SIMPLIFIÉ (ACTIF)")
        
        y -= 1 * cm
        p.setFont("Helvetica-Bold", 11)
        p.drawString(2.5 * cm, y, "Poste")
        p.drawRightString(width - 3 * cm, y, "Montant (€)")
        
        p.setFont("Helvetica", 11)
        for poste, montant in bilan['actif'].items():
            y -= 0.7 * cm
            p.drawString(2.5 * cm, y, str(poste))
            p.drawRightString(width - 3 * cm, y, f"{montant:,.2f}")

        # --- Section RÉSULTAT ---
        y -= 2 * cm
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2 * cm, y, "II. COMPTE DE RÉSULTAT")
        
        y -= 1 * cm
        p.setFont("Helvetica", 11)
        p.drawString(2.5 * cm, y, "Total des Produits (Ventes) :")
        p.drawRightString(width - 3 * cm, y, f"{resultat['total_produits']:,.2f}")
        
        y -= 0.7 * cm
        p.drawString(2.5 * cm, y, "Total des Charges :")
        p.drawRightString(width - 3 * cm, y, f"{resultat['total_charges']:,.2f}")
        
        y -= 1 * cm
        p.setFont("Helvetica-Bold", 12)
        if resultat['resultat_net'] >= 0:
            p.setFillColor(colors.green)
            label = "BÉNÉFICE NET :"
        else:
            p.setFillColor(colors.red)
            label = "PERTE NETTE :"
        
        p.drawString(2.5 * cm, y, label)
        p.drawRightString(width - 3 * cm, y, f"{resultat['resultat_net']:,.2f}")

        # --- Bas de page ---
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return buffer
