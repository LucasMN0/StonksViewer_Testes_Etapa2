from django.contrib import admin
from .models import Transacao, MetaFinanceira, Lembrete

admin.site.register(Transacao)
admin.site.register(MetaFinanceira)
admin.site.register(Lembrete)
from django.contrib import admin
from .models import Transacao, MetaFinanceira, Lembrete, CustomUser
from django.contrib.auth.admin import UserAdmin

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'first_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
