
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
    
    
    
@method_decorator(cache_page(60*15), name='dispatch')   
class RecipeListCreateView(generics.ListCreateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
   
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []
    
     
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  #Automatically assign the logged-in user
        
    def get(self, request, *args, **kwargs):
        #fetch local recipes from our database
        
        local_recipes = self.get_queryset()
        local_data = RecipeSerializer(local_recipes, many=True).data
       
        
        #fetch external recipes from TheMealDB API
        
        search_query = request.GET.get('query', '')
        
        try:
            response = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?s={search_query}')
            response.raise_for_status()
        #get the list of meals from the API response
            external_data = response.json().get('meals', [])
            
            
            
        except RequestException as e:
            
            print(f"Error fetching external recipes: {e}")    
            external_data = []
        
        #combine the local recipes with external API data
        
        
        combine_recipes = local_data + external_data
        
        return Response(combine_recipes)
        

#Retrieve/Update/Delete a Recipe   
class RecipeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer 
    permission_classes = [IsAuthenticated, IsOwner]       
    
    
class RecipeUpdateView(generics.UpdateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated, IsOwner]    
    
