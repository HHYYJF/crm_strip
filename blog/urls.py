from django.urls import path

from blog.views import login_view, index, get_services, history, calculation, calculation_chart, \
    calculation_products_view, aggregate_products_api, calculation_user_product_view, aggregate_user_product_api, \
    analysis_api, analysis_view, analysis_product_view, analysis_product_api

urlpatterns = [
    path("", login_view, name="login"),
    path("index/", index, name="index"),
    path("history/", history, name="history"),
    path("calculation/", calculation, name="calculation"),
    path("get_services/", get_services, name="get_services"),
    path("calculation_chart/", calculation_chart, name="calculation_chart"),
    path('calculation/products/', calculation_products_view, name='calculation_products'),
    path('calculation/aggregate/', aggregate_products_api, name='aggregate_products_api'),
    path("calculation/", calculation_user_product_view, name="calculation_user_product"),
    path("calculation/api/", aggregate_user_product_api, name="aggregate_user_product_api"),
    path("analysis/", analysis_view, name="analysis_view"),
    path("analysis/api/", analysis_api, name="analysis_api"),
    path("analysis/product/", analysis_product_view, name="analysis_product_view"),
    path("analysis/product/api/", analysis_product_api, name="analysis_product_api"),

]


