from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from taggit_serializer.serializers import TagListSerializerField
from django.contrib.auth.models import User
from .models import Question, Goods, Comment, Basket, BasketItems, Search
from django.core.validators import MinValueValidator, MaxValueValidator


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(validated_data['username'], password=validated_data['password'], first_name=validated_data['first_name'], last_name=validated_data['last_name'])
        return user

    def update(self, instance, validated_data):
        instance.password = validated_data.get('password', instance.password)
        instance.save()
# User serializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class GoodsSerializer(serializers.ModelSerializer):

    seller = SerializerMethodField()  # Allow to control attributes better and return data which you need
    tags = SerializerMethodField()
    date = serializers.DateTimeField(read_only=True, default=timezone.now())
    class Meta:
        model = Goods
        fields = '__all__'

    def get_seller(self, obj):  # A part of SerializerMethodField() which allow to change an obj
        return obj.seller.username

    def get_tags(self, obj):
        tags = obj.tags.all()

        tag_data = []
        for tag in tags:
            tag_data.append({
                'tag': tag.name,
                'Tag_url': f'http://127.0.0.1:8000/api/tags/{tag.name}/',
            })
        return tag_data

class QuestionSerializer(serializers.ModelSerializer):

    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Question
        fields = '__all__'

    def create(self, validated_data):
        user = self.context['request'].user
        return Question.objects.create(user=user, text=validated_data['text'])


class CommentSerializer(serializers.ModelSerializer):
    user = SerializerMethodField()  # Also You can use this field for ForeignKey objects
    good = SerializerMethodField()
    assess = serializers.IntegerField(validators=[
        MinValueValidator(0),
        MaxValueValidator(10)
    ])
    date = serializers.DateTimeField(read_only=True, default=timezone.now())

    class Meta:
        model = Comment
        fields = '__all__'

    def get_good(self, obj):
        good = obj.good
        good_data = GoodsSerializer(good).data
        return {
            'id': good_data['id'],
            'name': good_data['name']
        }

    def get_user(self, obj):
        user = obj.user
        user_data = UserSerializer(user).data
        return {
            'id': user_data['id'],
            'name': user_data['username']
        }

    def create(self, validated_data):
        user = self.context['request'].user
        good = self.context['good']
        return Comment.objects.create(user=user, good=good, assess=validated_data['assess'], comment=validated_data['comment'])


class ProductNotInBasketSerializer(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        # Access the request object through the context
        request = self.context.get('request', None)

        if request and request.user:
            # Assuming BasketItem is the model representing items in the basket
            basket_items = BasketItems.objects.filter(basket__user=request.user)

            # Get the list of product IDs already in the basket
            product_ids_in_basket = basket_items.values_list('goods', flat=True)

            # Exclude the products already in the basket from the queryset
            queryset = Goods.objects.exclude(id__in=product_ids_in_basket)
            return queryset

        # Return the default queryset if the request or user is not available
        return super().get_queryset()


class BasketItemsSerializer(serializers.ModelSerializer):

    goods = GoodsSerializer(read_only=True)
    basket = serializers.PrimaryKeyRelatedField(read_only=True)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = BasketItems
        fields = '__all__'

    def create(self, validated_data):
        user = self.context['request'].user
        goods = self.context['good']
        basket = Basket.objects.get(user=user)
        quantity = validated_data['quantity']
        basket_item = BasketItems.objects.create(goods=goods, basket=basket, quantity=quantity)
        return basket_item

    def get_fields(self):
        fields = super().get_fields()
        if self.context.get('basket_view'):
            fields['goods'].read_only = True  # Make goods field read-only
        return fields


class BasketSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = BasketItemsSerializer(many=True)

    class Meta:
        model = Basket
        fields = '__all__'


class Basket_CommentSerializer(serializers.Serializer):

    serializer1 = CommentSerializer()
    serializer2 = BasketItemsSerializer()

    def to_representation(self, instance):
        data_a = self.fields['serializer1'].to_representation(instance)
        data_b = self.fields['serializer2'].to_representation(instance)
        return {**data_a, **data_b}


class Filtered_byTags(serializers.ModelSerializer):

    class Meta:
        model = Goods
        fields = '__all__'


class AddInBasket_ItemsSerializer(serializers.ModelSerializer):

    goods = ProductNotInBasketSerializer(queryset=Goods.objects.all())
    basket = serializers.PrimaryKeyRelatedField(read_only=True)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = BasketItems
        fields = '__all__'

    def create(self, validated_data):
        user = self.context['request'].user
        goods = validated_data['goods']
        basket = Basket.objects.get(user=user)
        quantity = validated_data['quantity']
        return BasketItems.objects.create(goods=goods, basket=basket, quantity=quantity)


class SearchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Search
        fields = '__all__'
