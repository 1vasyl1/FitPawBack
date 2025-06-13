from django.db import models


class Trainer(models.Model):
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class Lessons(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lessons',
    )
    class Meta:
        ordering = ('date','start_time',)

    def __str__(self):
        return f"{self.subject} - {self.date} {self.start_time} - {self.end_time}"