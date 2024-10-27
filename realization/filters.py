from django.db.models import Q
from rest_framework.filters import SearchFilter
from .models import Goods
from django_filters import FilterSet


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)

        queryset = Goods.objects.all()
        name = request.query_params.get('search')
        if not name:
            return Goods.objects.all()
        queryset = Goods.objects.filter(Q(name__icontains=name))
        return queryset


