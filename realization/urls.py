from django.urls import path, include
from django.views.decorators.cache import cache_page

from .views import RegisterApi, QuestionView, CommentView, DetailsView, BasketView, Filtered_byTagsView
from .views import HomeView
from rest_framework.routers import SimpleRouter


urlpatterns = [
      path('registration/', RegisterApi.as_view(), name='registration'),
      path('ckeditor/', include('ckeditor_uploader.urls')),
      path('api-auth/', include('rest_framework.urls'), name='auth'),
      path('question/', QuestionView.as_view(), name='question'),
      path('details/<int:pk>/', cache_page(60*5)(DetailsView.as_view()), name='details'),
      path('details/<int:pk>/<int:pk_comment>', CommentView.as_view(), name='comment'),
      path('', HomeView.as_view(), name='home'),
      path('basket/<int:pk>/', BasketView.as_view(), name='basket'),
      path('tags/<str:tags>/', Filtered_byTagsView.as_view(), name='filtered_page')
]