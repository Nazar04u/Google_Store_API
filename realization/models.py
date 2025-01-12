from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils import timezone
from taggit.managers import TaggableManager
from django.contrib.auth.models import User


class Goods(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    url = models.SlugField()
    charecterist = RichTextUploadingField()
    delivery = models.BooleanField(default=False)
    amount = models.IntegerField()
    image = models.ImageField(upload_to='static/img')
    date = models.DateTimeField(default=timezone.now)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    tags = TaggableManager()


class Question(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    text = models.CharField(max_length=10000)
    date = models.DateTimeField(default=timezone.now())

    def admin_names(self):
        return ', '.join([a.name for a in self.items.all()])


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    good = models.ForeignKey(Goods, on_delete=models.CASCADE)
    assess = models.IntegerField()
    comment = models.TextField()
    date = models.DateTimeField(default=timezone.now())

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'from {self.user} in {self.good}'


class Basket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    active = models.BooleanField(default=False)
    items = models.ManyToManyField(Goods, through='BasketItems', null=True)

    def get_cart_total(self):
        return sum([item.item.price for item in self.items.all()])

    def admin_names(self):
        return ', '.join([a.name for a in self.items.all()])

    admin_names.short_description = "Goods"

    def admin_total(self):
        return str(sum([a.price for a in self.items.all()]))

    admin_names.short_description = "Total"


class BasketItems(models.Model):
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, default=None)
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, default=None)
    quantity = models.IntegerField(default=0)


class Search(models.Model):
    q = models.TextField()
