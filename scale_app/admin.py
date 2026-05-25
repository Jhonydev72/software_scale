from django.contrib import admin
from .models import Inventory, Process, Flow, EmergySource


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'inventory', 'description')
    list_filter = ('inventory',)


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_process', 'to_process', 'amount', 'unit', 'inventory')
    list_filter = ('inventory',)


@admin.register(EmergySource)
class EmergySourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_name', 'process', 'category', 'transformity', 'amount', 'unit', 'inventory')
    list_filter = ('inventory', 'category')
    search_fields = ('source_name',)
