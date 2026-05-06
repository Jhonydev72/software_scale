# Create your models here.
from django.db import models

class Process(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Flow(models.Model):
    from_process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='outgoing_flows')
    to_process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='incoming_flows')
    amount = models.FloatField()
    unit = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.from_process} -> {self.to_process}: {self.amount} {self.unit}"

class EmergySource(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='emergy_sources')
    source_name = models.CharField(max_length=200)
    transformity = models.FloatField(help_text="sej por unidade (ex: sej/MJ, sej/kg)")
    amount = models.FloatField()
    unit = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.source_name} @ {self.process.name}: {self.amount} {self.unit} (transformity: {self.transformity} sej/{self.unit})"