# user/forms.py
from django import forms
from .models import Perfil, UserProfile, UserSettings
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django import forms
from django.contrib.auth import authenticate, get_user_model
import re

User = get_user_model()


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _(
            "Usuario o contraseña incorrectos. Por favor, intenta de nuevo."
        ),
        'inactive': _("Esta cuenta está desactivada."),
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    _("El usuario no está registrado."),
                    code='invalid_username',
                )
            else:
                user = authenticate(username=username, password=password)
                if user is None:
                    raise forms.ValidationError(
                        _("La contraseña es incorrecta."),
                        code='invalid_password',
                    )

        return super().clean()


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto_perfil', 'nombre', 'edad', 'genero', 'temas_preferidos', 'personajes_favoritos']
        widgets = {
            'foto_perfil': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'foto_perfil_input'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el nombre del niño/a'
            }),
            'edad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 18,
                'placeholder': 'Edad en años'
            }),
            'genero': forms.Select(attrs={
                'class': 'form-control'
            }),
            'temas_preferidos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ejemplo: amistad, aventura, misterio, fantasía, ciencia ficción'
            }),
            'personajes_favoritos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ejemplo: robots, héroes, dragones, princesas, animales'
            }),
        }
        labels = {
            'foto_perfil': 'Foto de perfil',
            'nombre': 'Nombre',
            'edad': 'Edad',
            'genero': 'Género',
            'temas_preferidos': 'Temas de cuentos preferidos',
            'personajes_favoritos': 'Personajes que te gusten',
        }

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if foto:
            # Validar tamaño del archivo (máximo 5MB)
            if foto.size > 5 * 1024 * 1024:
                raise ValidationError("La imagen no puede ser mayor a 5MB.")

            # Validar tipo de archivo
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if not any(foto.name.lower().endswith(ext) for ext in valid_extensions):
                raise ValidationError("Solo se permiten archivos JPG, JPEG, PNG o GIF.")

        return foto


class RegistroForm(UserCreationForm):
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        help_text="Requerido. 150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente.",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ingresa tu nombre de usuario'}),
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
            'max_length': 'El nombre de usuario no puede tener más de 150 caracteres.'
        }
    )
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Ingresa tu correo electrónico'}),
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Por favor ingresa un correo electrónico válido.'
        }
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Ingresa tu contraseña'}),
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        }
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirma tu contraseña'}),
        error_messages={
            'required': 'Es obligatorio confirmar la contraseña.',
            'password_mismatch': 'Las contraseñas no coinciden.',
            'password_too_similar': 'La contraseña no puede ser demasiado similar al nombre de usuario.'
        }
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Validar que no contenga números
        if any(char.isdigit() for char in username):
            raise ValidationError("El nombre de usuario no debe contener números.")

        # Verificar si ya existe un usuario con ese nombre
        if User.objects.filter(username=username).exists():
            raise ValidationError("Este nombre de usuario ya está en uso.")

        return username

    def clean_email(self):
        """Validar que el email no esté ya registrado"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        """Guardar el usuario con el email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


# NUEVAS FUNCIONALIDADES - FORMULARIOS DE CONFIGURACIONES CON VALIDACIONES
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingrese su nuevo nombre',
            'data-validation': 'username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingrese su nuevo correo',
            'data-validation': 'email'
        })

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Validar que el nuevo nombre no sea igual al actual
        if self.instance and username == self.instance.username:
            raise ValidationError("El nuevo nombre de usuario debe ser diferente al actual.")

        # Verificar si ya existe otro usuario con ese nombre
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este nombre de usuario ya está en uso.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Validar que el nuevo email no sea igual al actual
        if self.instance and email == self.instance.email:
            raise ValidationError("El nuevo correo electrónico debe ser diferente al actual.")

        # Verificar si ya existe otro usuario con ese email
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")

        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'email_notifications', 'dark_mode', 'language']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })


class SettingsUpdateForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['avatar', 'email_notifications', 'dark_mode', 'language']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña actual',
            'data-validation': 'current-password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingrese su nueva contraseña',
            'data-validation': 'new-password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Vuelva a ingresar su nueva contraseña',
            'data-validation': 'confirm-password'
        })

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError("La contraseña actual es incorrecta.")
        return old_password

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')

        # Validaciones de seguridad de contraseña
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")

        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")

        if not re.search(r'[a-z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula.")

        if not re.search(r'\d', password):
            raise ValidationError("La contraseña debe contener al menos un número.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("La contraseña debe contener al menos un carácter especial.")

        # Validar que no sea igual a la contraseña actual
        if self.user.check_password(password):
            raise ValidationError("La nueva contraseña debe ser diferente a la actual.")

        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")

        return password2
