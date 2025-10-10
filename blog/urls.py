from django.urls import path

from blog.views import login_view, IndexAPIView, DealView, LogoutView, ServiceListView, ShiftView, DealHistoryView, \
    ProductServiceAnalysisView, calculation_products, SalaryCalculationView

urlpatterns = [
    path('login/', login_view, name='api_login'), # вход
    path('index/', IndexAPIView.as_view(), name='index'),  # выбор кто на смене
    path('deals/', DealView.as_view(), name='deal-list'),  #
    path('services/', ServiceListView.as_view(), name='get_services'),
    path('shifts/', ShiftView.as_view(), name='shift-list'),  # информация о сменах
    path('logout/', LogoutView.as_view(), name='logout'),  # выход
    path('deals_history/', DealHistoryView.as_view(), name='deals-history'), # история + анализ
    path('product_service_analysis/', ProductServiceAnalysisView.as_view(), name='product-service-analysis'), # анализ по товару и/или услуге
    # path('income_calculation/', IncomeCalculation.as_view(), name='income-calculation'), # анализ по товару и/или услуге
    path('calculation_products/', calculation_products, name='calculation_products'),  # расчет ЗП
    path("salary/", SalaryCalculationView.as_view(), name="salary-calculation"),  # расчет ЗП
]


