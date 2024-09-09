from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser

# recipe models

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self) -> str:
        return self.username

class Recipe(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recipes')
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=3, decimal_places=1)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredient')
    
    def __str__(self) -> str:
        return f"{self.quantity} of {self.name}"
    
    
