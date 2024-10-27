from django.contrib import admin
from .models import Question, Goods, Comment, BasketItems

class CommentAdmin(admin.ModelAdmin):

    list_display = ('user', 'good', 'assess', 'comment')

class QuestionAdmin(admin.ModelAdmin):

    list_display = ('text', 'user')


class GoodsAdmin(admin.ModelAdmin):

    list_display = ('name', 'price', 'seller')

class BasketItemsAdmin(admin.ModelAdmin):

    list_display = ('goods', 'quantity')

class NasketAdmin(admin.ModelAdmin):
    list_display = ('user', 'active', 'admin_names', 'admin_total')

admin.site.register(Question, QuestionAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(BasketItems, BasketItemsAdmin)