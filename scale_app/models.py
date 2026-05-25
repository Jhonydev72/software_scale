# Create your models here.
from django.db import models


class Inventory(models.Model):
    """
    Representa um inventário LCI importado.
    Cada upload cria um novo Inventory ao qual todos os processos,
    fluxos e fontes ficam vinculados.
    """
    name = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f"{self.name} ({self.created_at:%d/%m/%Y %H:%M})"


class Process(models.Model):
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE,
        null=True, blank=True, related_name='processes'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Flow(models.Model):
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE,
        null=True, blank=True, related_name='flows'
    )
    from_process = models.ForeignKey(
        Process, on_delete=models.CASCADE, related_name='outgoing_flows'
    )
    to_process = models.ForeignKey(
        Process, on_delete=models.CASCADE, related_name='incoming_flows'
    )
    amount = models.FloatField()
    unit = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.from_process} -> {self.to_process}: {self.amount} {self.unit}"


class EmergySource(models.Model):
    CATEGORY_CHOICES = [
        ('R', 'Renovável'),
        ('N', 'Não Renovável'),
        ('M', 'Materiais'),
        ('U', 'Não Classificado'),
    ]

    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE,
        null=True, blank=True, related_name='sources'
    )
    process = models.ForeignKey(
        Process, on_delete=models.CASCADE, related_name='emergy_sources'
    )
    source_name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=1, choices=CATEGORY_CHOICES, default='U'
    )
    transformity = models.FloatField(
        help_text="sej por unidade (ex: sej/MJ, sej/kg)"
    )
    amount = models.FloatField()
    unit = models.CharField(max_length=50)

    def __str__(self):
        return (
            f"{self.source_name} @ {self.process.name}: "
            f"{self.amount} {self.unit} "
            f"(transformity: {self.transformity} sej/{self.unit})"
        )