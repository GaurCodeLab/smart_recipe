
import logging
from smart_recipes import permissions
from smart_recipes.permissions import IsOwner
from .models import Recipe
from .serializers import RecipeSerializer
from rest_framework import generics
from .serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
import requests
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from requests.exceptions import RequestException
from django.core.cache import cache
from django.http import HttpResponse
import time
from django.views.decorators.cache import cache_page
from django_redis import get_redis_connection
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.core.cache import cache
import aiohttp
import asyncio
from django.utils.decorators import sync_to_async

# Create your views here.
def test_redis_view(request):
    redis_conn = get_redis_connection("default")
    redis_conn.set("test_key", "hello from django")
    value = redis_conn.get("test_key")
    return HttpResponse(f"Redis returned: {value}")
    
    
#Login user using username and password    
@api_view(['POST'])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh' : str(refresh),
            'access' : str(refresh.access_token),
            
        }, status=status.HTTP_200_OK)
    return Response({'error' : 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)        
    
    
    
#Register new user    
@api_view(['POST'])
def register_user(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message' : 'User created successfully'},
                status=status.HTTP_201_CREATED
            )    
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    
    
    
    
 
class RecipeListCreateView(generics.ListCreateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
   
    def get_permissions(self):
        if self.request.method == 'POST': 
            return [IsAuthenticated()]
        return []
    
     
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  #Automatically assign the logged-in user
        
        #invalidate cache for recipe list when a new recipe is created
        cache.delete('recipe_list_cache')
        
        
    @sync_to_async
    async def fetch_external_recipes(self, search_query):
        url = f'https://www.themealdb.com/api/json/v1/1/search.php?s={search_query}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status ==200:
                    data = await response.json()
                    return data.get('meals', [])
                else:
                    print(f"Error fetching external recipes: {response.status}")
                    return []
           
    async def get(self, request, *args, **kwargs):
        #fetch local recipes from our database
        
        cache_key = 'recipe_list_cache'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        
        local_recipes = self.get_queryset()
        local_data = RecipeSerializer(local_recipes, many=True).data
       
        
        #fetch external recipes from TheMealDB API
        
        search_query = request.GET.get('query', '')
        
        external_data = await self.fetch_external_recipes(search_query)
        
        #combine the local recipes with external API data
        
        
        combine_recipes = local_data + external_data
        
        #cache the combine data
        
        cache.set(cache_key, combine_recipes, 60*15)
        
        return Response(combine_recipes)
        

#Retrieve/Update/Delete a Recipe   
class RecipeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer 
    permission_classes = [IsAuthenticated, IsOwner]       
    
    def get(self, request, *args, **kwargs):
        recipe_id = self.kwargs.get('pk')
        cache_key = f'recipe_{recipe_id}'
        
        #fetching recipe from the cache first
        
        cached_recipe = cache.get(cache_key)
        if cached_recipe:
            return Response(cached_recipe)
        
        #if fetching from cache failed
        
        recipe = self.get_object()
        serializer = self.get_serializer(recipe)
        data = serializer.data
        cache.set(cache_key, data, 60*15)
        return Response(data)
    
    def perform_update(self, serializer):
        updated_recipe =serializer.save()
        
        #Invalidating both list cache and the cache for the specific recipe
        cache.delete('recipe_list_cache')
        cache.delete(f'recipe_{updated_recipe.id}')
        
        logging.info(f'Cache invalidated for recipe_list_cache and recipe_{updated_recipe.id}')
        
        cache.set(f'recipe_{updated_recipe.id}' , serializer.data, 60*15)
        
    def perform_destroy(self, instance):
        recipe_id = instance.id
       
        cache.delete('recipe_list_cache')    
        cache.delete(f'recipe_{recipe_id}')
        instance.delete()
    
class RecipeUpdateView(generics.UpdateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated, IsOwner]    
    
