from django.contrib.auth.models import User
from django.test import Client
from rest_framework import status
from rest_framework.reverse import reverse
from .models import Goods, Basket, Comment, BasketItems
from rest_framework.test import APITestCase


class GoodsTestCase(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.user.basket = Basket.objects.create(user=self.user)  # Add basket for user
        # Create a test Goods instance
        self.test_good = Goods.objects.create(
            name='Test Goods',
            price=100,
            url='test-goods',
            charecterist='Test characteristics',
            delivery=False,
            amount=10,
            image='test-image.jpg',
            seller=self.user,
        )
        #  Create a url to detail view of test_good
        self.detail_url = reverse('details', kwargs={'pk': self.test_good.pk})
        self.comment = Comment.objects.create(user=self.user,
                                              good=self.test_good,
                                              assess=10,
                                              comment='Good product')
        # Create a comment and comment_url for test_user
        self.comment_url = reverse('comment', kwargs={'pk': self.comment.good.pk, 'pk_comment': self.comment.pk})
        # Second example
        self.user1 = User.objects.create_user(username='user1', password='111')
        basket = Basket.objects.create(user=self.user1)
        self.user1.basket = basket  # Add basket for user1
        self.data = {'name': 'Goods1',
                     'price': 1111,
                     'url': 'goods_1',
                     'charecterist': 'GOODS1',
                     'delivery': False,
                     'amount': 22,
                     'image': 'goods1-image.jpg',
                     'seller': self.user1}
        self.good1 = Goods.objects.create(**self.data)
        self.comment1 = Comment.objects.create(user=self.user1,
                                               good=self.good1,
                                               assess=2,
                                               comment='Bad product')
        self.user_basket_url = reverse('basket', kwargs={'pk': self.user.basket.pk})
        self.user1_basket_url = reverse('basket', kwargs={'pk': self.user1.basket.pk})
        # Create basket_item for user
        self.user_basket_items = BasketItems.objects.create(basket=self.user.basket, goods=self.test_good, quantity=2)

    def test_details_good(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Checking if detail_url work properly
        self.assertEqual(response.data['good']['name'], self.test_good.name)
        self.assertEqual(len(response.data['comments']), 1)
        self.assertEqual(Comment.objects.count(), 2)
        # Test post method and add 1 comment
        self.client.post(self.detail_url, data={'serializer1.assess': 6,
                                                'serializer1.comment': 'Normal product',
                                                'serializer2.quantity': 1})
        self.assertEqual(Comment.objects.count(), 3)
        response = self.client.get(self.detail_url)
        # Checking how many comments are for specific good
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(BasketItems.objects.count(), 2)

    def test_update_delete_comments(self):
        self.client.force_login(user=self.user)
        response = self.client.get(self.comment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comment'], 'Good product')
        self.comment_url1 = reverse('comment', kwargs={'pk': self.comment1.good.pk, 'pk_comment': self.comment1.pk})
        # Checking so that user cannot change comments of another user
        self.assertEqual(self.client.put(path=self.comment_url1, data={'comment': "Good", 'assess': 9}).status_code,
                         status.HTTP_403_FORBIDDEN)
        # Test put method
        response = self.client.put(path=self.comment_url, data={'comment': "Very Good product", 'assess': 9})
        self.assertEqual(Comment.objects.count(), 2)
        self.assertEqual(response.data['comment'], 'Very Good product')
        # Test delete
        response = self.client.delete(path=self.comment_url)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_basket(self):
        self.client.force_login(user=self.user)
        # Test user so that he don't have access to another basket
        self.assertEqual(self.client.get(self.user1_basket_url).status_code, status.HTTP_403_FORBIDDEN)
        # Test different actions with basket
        response = self.client.get(self.user_basket_url)
        self.assertEqual(len(response.data['chosen items']), 1)
        response = self.client.put(self.user_basket_url, data={'goods': self.good1.pk,
                                                               'quantity': 3})
        self.assertEqual(len(response.data['chosen items']), 2)
        self.client.delete(self.user_basket_url)
        response = self.client.get(self.user_basket_url)
        self.assertEqual(len(response.data['chosen items']), 0)

    def test_search(self):
        # Testing searching system
        response = self.client.get('/api/?search=t', format='json')
        response_data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_data['results']), 1)
        response = self.client.get('/api/', data={'search': 'o'}, format='json')
        response_data = response.json()
        self.assertEqual(len(response_data['results']), 2)
        response = self.client.get('/api/', data={'search': 'a'}, format='json')
        response_data = response.json()
        self.assertEqual(len(response_data['results']), 0)
