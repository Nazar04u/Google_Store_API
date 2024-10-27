import json
from urllib.parse import urlencode

import requests
from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from rest_framework import generics, permissions, mixins, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from .models import Goods, Question, Comment, Basket, BasketItems
from .serializer import RegisterSerializer, UserSerializer, QuestionSerializer, GoodsSerializer, CommentSerializer, \
    BasketSerializer, Basket_CommentSerializer, BasketItemsSerializer, AddInBasket_ItemsSerializer, SearchSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import filters
from .filters import CustomSearchFilter
from rest_framework import status
from bs4 import BeautifulSoup


class Pagination(PageNumberPagination):
    page_size = 4
    page_query_param = 'page'
    page_size_query_param = 'page_size'


class RegisterApi(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def get(self, request, *args, **kwargs):
        return Response(data={}, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        basket = Basket.objects.create(user=user, active=True)
        basket_serializer = BasketSerializer(basket, many=False).data
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "message": "User Created Successfully.  Now perform Login to get your token",
            "basket": basket_serializer
        })


class HomeView(generics.ListAPIView):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    queryset = Goods.objects.filter(date__gte=timezone.now() - timezone.timedelta(days=7),
                                    date__lte=timezone.now())
    pagination_class = Pagination
    permission_classes = [AllowAny]
    filter_backends = [CustomSearchFilter]
    search_fields = ['name']

    def get(self, request, *args, **kwargs):
        goods = self.list(request, *args, **kwargs)
        user = self.request.user
        try:
            basket = Basket.objects.get(user=user)
        except (TypeError, Basket.DoesNotExist):
            basket = None
        basket_url = "You are not register"
        if basket:
            basket_url = self.get_basket_url()
            current_url = request.build_absolute_uri().split('/')[0:4]
            current_url = '/'.join(current_url)
            goods.data['basket_url'] = current_url + '/' + basket_url
            return goods
        else:
            goods.data['basket_url'] = basket_url
            return goods

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SearchSerializer
        return GoodsSerializer

    def get_basket_url(self, *args, **kwargs):
        user = self.request.user
        basket = Basket.objects.get(user=user)
        return f'basket/{basket.id}/'


class QuestionView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, *args, **kwargs):
        return Response(data={})


class DetailsView(generics.ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = Basket_CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get(self, request, *args, **kwargs):  # Assuming you have a URL parameter for the MyModel ID
        good = Goods.objects.get(pk=self.kwargs['pk'])
        good_serializer = GoodsSerializer(good)
        comments = Comment.objects.filter(good=good)
        comments_serializer = CommentSerializer(comments, many=True)

        user = self.request.user
        basket = Basket.objects.get(user=user)
        try:
            is_added = BasketItems.objects.get(basket=basket, goods=good)
            self.serializer_class = CommentSerializer
        except BasketItems.DoesNotExist:
            is_added = None
        if is_added:
            data = {
                'good': good_serializer.data,
                'comments': comments_serializer.data,
                'Product': "Is already added to the basket"
            }
        else:
            data = {
                'good': good_serializer.data,
                'comments': comments_serializer.data
            }
        response = Response(data)
        response['Allow'] = 'GET, POST, HEAD, OPTIONS'
        return response

    def create(self, request, *args, **kwargs):
        user = self.request.user
        good = Goods.objects.get(pk=self.kwargs['pk'])
        basket = Basket.objects.get(user=user)
        try:
            is_added = BasketItems.objects.get(basket=basket, goods=good)
        except BasketItems.DoesNotExist:
            is_added = None
        if not is_added:
            serializer_comment = CommentSerializer(data={'user': user, 'good': good,
                                                         'assess': request.data['serializer1.assess'],
                                                         'comment': request.data['serializer1.comment']},
                                                   context={"request": request, 'good': good})
            serializer_basket = BasketItemsSerializer(data={'basket': basket,
                                                            'goods': good,
                                                            'quantity': request.data[
                                                                'serializer2.quantity']},
                                                      context={'request': request, 'good': good, 'basket_view': True})
        else:
            serializer_comment = CommentSerializer(data={'user': user, 'good': good,
                                                         'assess': request.data['assess'],
                                                         'comment': request.data['comment']},
                                                   context={"request": request, 'good': good})
            serializer_basket = None
        saved_comment = None
        saved_basket = None
        if serializer_comment.is_valid():
            saved_comment = self.perform_create_comment(serializer_comment)
            serializer_comment.instance.refresh_from_db()
        if serializer_basket and serializer_basket.is_valid():
            saved_basket = self.perform_create_basket(serializer_basket)
        current_url = request.build_absolute_uri()
        if saved_comment:
            comment_url = reverse('comment', kwargs={'pk': self.kwargs['pk'], 'pk_comment': saved_comment.pk})
            return redirect(comment_url)
        if saved_basket:
            return Response({'message': 'Item is added to your basket'})
        return Response({'message': "Incorrect data"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create_comment(self, serializer):
        saved_comment = serializer.save()
        return saved_comment

    def perform_create_basket(self, serializer):
        saved_basket = serializer.save()
        return saved_basket

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class CommentView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    lookup_url_kwarg = 'pk_comment'
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        comment = Comment.objects.get(pk=self.kwargs['pk_comment'], good=self.kwargs['pk'])
        return comment

    def get_permissions(self):
        if self.request.user != self.get_object().user:
            raise PermissionDenied('You can not change this comment')
        return [IsAuthenticated()]

    def delete(self, request, *args, **kwargs):
        previous_page = request.build_absolute_uri()
        previous_page = previous_page.split('/')
        previous_page = previous_page[:-1]
        previous_page = '/'.join(previous_page)
        self.destroy(request, *args, **kwargs)
        return redirect(previous_page)


class BasketView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddInBasket_ItemsSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        user = self.request.user
        basket = Basket.objects.get(user=user)
        return BasketItems.objects.filter(basket=basket)

    def get(self, request, *args, **kwargs):
        items = self.get_queryset()
        serialized_items = BasketItemsSerializer(data=items, many=True)
        serialized_items.is_valid()
        total = 0
        for item in items:
            total += item.quantity * item.goods.price
        data = {
            'chosen items': serialized_items.data,
            'Total': total
        }
        response = Response(data)
        data = json.dumps(data)
        response.set_cookie('goods_cookies', data, max_age=7200)
        return response

    def delete(self, request, *args, **kwargs):
        self.get_queryset().delete()
        return redirect(request.build_absolute_uri())

    def put(self, request, *args, **kwargs):
        user = self.request.user
        basket = Basket.objects.get(user=user)
        good = request.data['goods']
        quantity = request.data['quantity']
        item_serialized = AddInBasket_ItemsSerializer(data={'basket': basket,
                                                            'goods': good,
                                                            'quantity': quantity},
                                                      context={'request': request})
        if item_serialized.is_valid():
            item_serialized.save()
            return self.get(request)
        return Response({"message": "Error"}, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self):
        basket = Basket.objects.get(pk=self.kwargs['pk'])
        return basket

    def get_permissions(self):
        if self.request.user != self.get_object().user:
            raise PermissionDenied('Incorrect url')
        return [IsAuthenticated()]


class Filtered_byTagsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = GoodsSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get_queryset(self):
        tags = self.kwargs['tags']
        return Goods.objects.filter(tags__name=tags)

    def get(self, request, *args, **kwargs):
        tags = kwargs['tags']
        cached_data = cache.get(tags)
        if cached_data:
            return Response(cached_data)

        default_goods = self.list(request, *args, **kwargs)
        url = self.get_url(tags)
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        div_goods = soup.find_all('div', class_='goods-tile__inner')
        trend_product = []
        count = 0
        for elem in div_goods:
            if elem.find('span', class_=['goods-tile__label', 'promo-label', 'promo-label_type_popularity', 'ng-star'
                                                                                                            '-inserted']) \
                    is not None and count != 10:
                data = {
                    'trend': elem.find('span', class_='goods-tile__label').text,
                    'image': elem.find('img', class_='lazy_img_hover').get('src', 'N/A'),
                    'title': elem.find('span', class_='goods-tile__title').text,
                    'price': elem.find('span', class_='goods-tile__price-value').text,
                    'More details on Rozetka': elem.find('a', class_='goods-tile__heading').get('href', 'N/A')
                }
                count += 1
                trend_product.append(data)
        cache.set(tags, {'top 10 on Rozetka': trend_product, 'Our product': default_goods.data})

        return Response({'top 10 on Rozetka': trend_product, 'Our product': default_goods.data})

    def get_url(self, pk):
        urls = {'Laptops': 'https://rozetka.com.ua/ua/notebooks/c80004/',
                'Earbuds': 'https://rozetka.com.ua/ua/headphones/c80027/21079=2731/',
                'Accesoires': 'https://rozetka.com.ua/ua/naushniki-i-aksessuari/c4660594/',
                'Smartphone': 'https://rozetka.com.ua/ua/mobile-phones/c80003/',
                'Watches': 'https://rozetka.com.ua/ua/nosimie-gadgeti/c4660587/'}
        return urls[pk]
