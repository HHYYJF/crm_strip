from django.urls import path

from blog.views import login_view, IndexAPIView, LogoutView, DealAPIView, shift_staff, deals_in_range, DealsInRangeView, \
    EmployeePerformanceView, ProductSalesView, historianalitic

urlpatterns = [
    path('auth/login/', login_view, name='api_login'), # вход
    path('auth/logout /', LogoutView.as_view(), name='logout'),  # выход
    path('shift/', IndexAPIView.as_view(), name='shift'),  # выбор кто на смене
    path('shift/staff/', shift_staff, name='histori'),  # история смен

    path('shift/deal/', DealAPIView.as_view(), name='recording'),  # создание записи
    path('histori_analitic/',historianalitic, name='historianalitic'),  # история + отчет
    path('range/',DealsInRangeView.as_view(), name='range'),  # расчет ЗП + подробная информация
    path('analitic_users/',EmployeePerformanceView.as_view(), name='analitic_users'),  # анализ сотрудников
    path('analitic_tovats/',ProductSalesView.as_view(), name='analitic_tovats'),  # анализ товара
    path('deals_in_range/', deals_in_range, name='deals_in_range'),  # расчет ЗП HTML
]



