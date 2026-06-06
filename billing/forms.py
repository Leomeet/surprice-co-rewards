from django import forms
from .models import Product, PointAdjustment, WhatsAppTemplate


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'description', 'price', 'point_value')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class PointAdjustmentForm(forms.Form):
    delta = forms.IntegerField(
        label='Points (negative to deduct)',
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 50 or -20'}),
    )
    reason = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Loyalty bonus'}),
    )


class WhatsAppTemplateForm(forms.ModelForm):
    class Meta:
        model = WhatsAppTemplate
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5}),
        }
