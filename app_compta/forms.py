from django import forms

class CsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Sélectionnez le relevé bancaire (CSV)",
        help_text="Format supporté : .csv uniquement"
    )
