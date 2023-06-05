from django.db import models

# Create your models here.
class Message(models.Model):
    id = models.BigIntegerField(primary_key=True)
    group_id = models.CharField(max_length=50, null=True)
    group_name = models.CharField(max_length=50, null=True)
    user_id = models.CharField(max_length=50)
    user_name = models.CharField(max_length=50)
    message = models.TextField()
    sent_at = models.DateTimeField()
    unsent_at = models.DateTimeField(null=True)
    
