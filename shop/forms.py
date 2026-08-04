"""Checkout form — validates delivery details properly (not just "not empty")."""
import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Order, Product


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'email', 'phone', 'address', 'city',
                  'postcode', 'state', 'region', 'payment_method']

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'\D', '', phone)          # keep numbers only
        if digits.startswith('60'):                # +60 country code → local 0…
            digits = '0' + digits[2:]
        if not re.fullmatch(r'0\d{8,10}', digits):
            raise forms.ValidationError(
                "Please enter a Malaysian phone number, e.g. 012-345 6789.")
        return phone

    def clean_postcode(self):
        postcode = self.cleaned_data['postcode'].strip()
        if not re.fullmatch(r'\d{5}', postcode):
            raise forms.ValidationError(
                "Malaysian postcode is 5 digits, e.g. 50000.")
        return postcode


class RegisterForm(forms.Form):
    """Customer account signup. The email doubles as the login name."""
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label="Repeat password")

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists — please log in.")
        return email

    def clean_password1(self):
        password = self.cleaned_data['password1']
        validate_password(password)      # same strength rules as the admin
        return password

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "The two passwords do not match.")
        return data


class MultiplePhotoInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePhotoField(forms.ImageField):
    """Validate every file chosen in the quick-add photo picker."""

    allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
    maximum_size = 10 * 1024 * 1024

    def clean(self, data, initial=None):
        if not data:
            raise forms.ValidationError('Add at least one photo.')

        photos = data if isinstance(data, (list, tuple)) else [data]
        cleaned = []
        for photo in photos:
            if photo.content_type not in self.allowed_types:
                raise forms.ValidationError(
                    'Only JPG, PNG, and WebP photos are allowed.')
            if photo.size > self.maximum_size:
                raise forms.ValidationError('Each photo must be 10 MB or smaller.')
            cleaned.append(super().clean(photo, initial))
        return cleaned


class QuickProductForm(forms.ModelForm):
    photos = MultiplePhotoField(
        widget=MultiplePhotoInput(attrs={
            'accept': 'image/jpeg,image/png,image/webp', 'multiple': True,
        }))

    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'compare_at_price', 'description',
                  'sizes', 'stock', 'is_bestseller', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'sizes': forms.TextInput(attrs={'placeholder': 'XS, S, M, L'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'compare_at_price': forms.NumberInput(
                attrs={'step': '0.01', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }
