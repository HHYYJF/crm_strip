from django.urls import path

from blog.views import login_view, IndexAPIView, DealView, LogoutView, ServiceListView, ShiftView

urlpatterns = [
    path('login/', login_view, name='api_login'),
    path('index/', IndexAPIView.as_view(), name='index'),
    path('deals/', DealView.as_view(), name='deal-list'),
    path('services/', ServiceListView.as_view(), name='get_services'),
    path('shifts/', ShiftView.as_view(), name='shift-list'),
    path('logout/', LogoutView.as_view(), name='logout'),
]


