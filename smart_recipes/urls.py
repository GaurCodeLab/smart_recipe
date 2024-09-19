from django.urls import path
from .views import RecipeListCreateView, RecipeDetailView, register_user, login_user, RecipeUpdateView



urlpatterns = [
    path('recipes/', RecipeListCreateView.as_view(), name = 'recipe-list-create'),
    path('recipes/<int:pk>', RecipeDetailView.as_view(), name = 'recipe-detail'),
    path('api/register/', register_user, name='register_user'),
    path('api/login/', login_user, name='login_user'),
    path('recipes.<int:pk>/update/', RecipeUpdateView.as_view(), name ='recipe-update' ),
    
    
]
