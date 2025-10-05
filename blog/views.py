from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shift, Personal, Role
from .serializers import ShiftCreateSerializer, PersonalSerializer,LoginSerializer
from .serializers import DealSerializer, PersonalSerializer,ShiftCreateSerializer,LoginSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import Shift
from .serializers import ShiftSerializer
from .models import Deal, Personal, Services, Service, Payment, Whom, Role, Shift
from .serializers import (DealSerializer, PersonalSerializer, ServicesSerializer,
                          ServiceSerializer, PaymentSerializer, WhomSerializer,
                          RoleSerializer, ShiftSerializer)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Deal, Personal
from .serializers import DealSerializer
from django.db.models import Q




@api_view(['POST'])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    user = authenticate(username=username, password=password)

    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
            }
        })
    else:
        return Response(
            {"error": "Неверное имя пользователя или пароль"},
            status=status.HTTP_401_UNAUTHORIZED
        )

class IndexAPIView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def post(self, request):


        serializer = ShiftCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin_id = serializer.validated_data['admin_id']
        barman_id = serializer.validated_data['barman_id']

        admin = Personal.objects.filter(id=admin_id).first()
        barman = Personal.objects.filter(id=barman_id).first()

        if not admin or not barman:
            return Response({"error": "Админ или бармен не найдены"}, status=status.HTTP_400_BAD_REQUEST)

        # Закрываем предыдущую активную смену, если есть
        Shift.objects.filter(is_active=True).update(is_active=False)

        # Создаём новую смену
        shift = Shift.objects.create(admin=admin, barman=barman)

        return Response({
            "id": shift.id,
            "admin": admin.name,
            "barman": barman.name,
            "start_time": shift.start_time,
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        # if not request.user.is_authenticated:
        #     return Response({"error": "Неавторизованный доступ"}, status=status.HTTP_401_UNAUTHORIZED)

        admin_role = Role.objects.filter(name__iexact="админ").first()
        barman_role = Role.objects.filter(name__iexact="бармен").first()

        admins = Personal.objects.filter(role=admin_role)
        barmans = Personal.objects.filter(role=barman_role)

        admin_data = PersonalSerializer(admins, many=True).data
        barman_data = PersonalSerializer(barmans, many=True).data

        return Response({
            "admins": admin_data,
            "barmans": barman_data
        })


class DealView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch all Deal records where ais=True
        deals = Deal.objects.filter(ais=True)
        deal_serializer = DealSerializer(deals, many=True)

        # Fetch all records for other models
        roles = Role.objects.all()
        personals = Personal.objects.all()
        services = Services.objects.all()
        service_items = Service.objects.all()
        payments = Payment.objects.all()
        whoms = Whom.objects.all()


        # Serialize all models
        role_serializer = RoleSerializer(roles, many=True)
        personal_serializer = PersonalSerializer(personals, many=True)
        services_serializer = ServicesSerializer(services, many=True)
        service_serializer = ServiceSerializer(service_items, many=True)
        payment_serializer = PaymentSerializer(payments, many=True)
        whom_serializer = WhomSerializer(whoms, many=True)

        response_data = {
            'deals': deal_serializer.data,
            'roles': role_serializer.data,
            'personals': personal_serializer.data,
            'services': services_serializer.data,
            'service_items': service_serializer.data,
            'payments': payment_serializer.data,
            'whoms': whom_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DealSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            all_deals = Deal.objects.all()
            all_serializer = DealSerializer(all_deals, many=True)
            return Response(all_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceListView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        services_id = request.query_params.get('services_id')
        if services_id:
            services = Service.objects.filter(service_id=services_id)
        else:
            services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response({
            'status': 'success',
            'services': serializer.data,
            'count': services.count()
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            personal = Personal.objects.filter(name=user.username).first()
            if personal:
                Deal.objects.filter(personal=personal).update(ais=False)
            return Response({"message": "Logged out successfully, ais set to False for related deals."},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ShiftView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        shifts = Shift.objects.all()
        serializer = ShiftSerializer(shifts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)