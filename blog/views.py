from django.shortcuts import render
from rest_framework.decorators import api_view
from django.db import models
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from django.db.models import Sum, Q
from django.utils.dateparse import parse_datetime
from .models import Deal, Role, Services, Payment
from .serializers import DealSerializer
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
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from .models import Service, Deal
from .serializers import ServiceSerializer, DealSerializer

from .models import Personal, Deal, Shift
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
            # Находим сотрудника по username (если имена совпадают с пользователями Django)
            personal = Personal.objects.filter(name=user.username).first()

            if not personal:
                return Response({"error": "Сотрудник не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Обновляем все сделки сотрудника
            Deal.objects.filter(personal=personal).update(ais=False)

            # Находим активную смену, где он либо админ, либо бармен
            active_shift = Shift.objects.filter(
                is_active=True
            ).filter(
                models.Q(admin=personal) | models.Q(barman=personal)
            ).first()

            if active_shift:
                active_shift.is_active = False
                active_shift.end_time = timezone.now()
                active_shift.save()

            return Response({
                "message": "Выход выполнен успешно. Сделки обновлены, активная смена закрыта.",
                "shift_closed": bool(active_shift),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ShiftView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        shifts = Shift.objects.all()
        serializer = ShiftSerializer(shifts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)





class DealHistoryView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Получить все сделки без фильтра',
        description='Возвращает пустой ответ или все сделки без фильтрации (просто страницу без всего).',
        responses={
            200: OpenApiResponse(description='Пустой ответ'),
            401: OpenApiResponse(description='Неавторизован'),
        }
    )
    def get(self, request):
        # Возвращаем пустой ответ для GET, как указано ("страницу без всего")
        return Response({}, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Фильтровать сделки по датам и рассчитывать аггрегаты',
        description='Принимает даты "от" и "до", фильтрует сделки по date_time, возвращает их и аггрегаты: доход с услуг, с товаров, по видам оплаты, заработок ролей.',
        parameters=[
            OpenApiParameter(name='from_date', type=str, required=True, description='Дата от (формат: YYYY-MM-DDTHH:MM:SS+03:00)'),
            OpenApiParameter(name='to_date', type=str, required=True, description='Дата до (формат: YYYY-MM-DDTHH:MM:SS+03:00)'),
        ],
        request=None,  # POST без тела, параметры в query или form, но используем POST с JSON
        responses={
            200: OpenApiResponse(
                description='Фильтрованные сделки и аггрегаты',
                examples=[
                    OpenApiExample(
                        'Пример ответа',
                        value={
                            'deals': [
                                {'id': 1, 'maney': 1000, 'services': {'name': 'услуга'}, 'payment': {'name': 'карта'}, 'personal': {'role': {'name': 'Бармен', 'maney': 10}}},
                            ],
                            'aggregates': {
                                'income_services': 5000,
                                'income_goods': 3000,
                                'payments': {'карта': 4000, 'наличные': 4000},
                                'roles_earnings': {'Бармен': 500, 'Официант': 300},
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description='Неверные даты'),
            401: OpenApiResponse(description='Неавторизован'),
        }
    )
    def post(self, request):
        from_date_str = request.data.get('from_date')
        to_date_str = request.data.get('to_date')
        if not from_date_str or not to_date_str:
            return Response({'error': 'Требуются from_date и to_date'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from_date = parse_datetime(from_date_str)
            to_date = parse_datetime(to_date_str)
            if not from_date or not to_date:
                raise ValueError
        except ValueError:
            return Response({'error': 'Неверный формат дат'}, status=status.HTTP_400_BAD_REQUEST)

        # Фильтруем сделки по датам
        deals = Deal.objects.filter(date_time__range=(from_date, to_date))
        serializer = DealSerializer(deals, many=True)

        # Рассчитываем аггрегаты
        aggregates = self.calculate_aggregates(deals)

        response_data = {
            'deals': serializer.data,
            'aggregates': aggregates
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def calculate_aggregates(self, deals):
        # Доход с услуг (services.name == 'услуга')
        income_services = deals.filter(services__name='услуга').aggregate(total=Sum('maney'))['total'] or 0

        # Доход с товаров (services.name == 'товар')
        income_goods = deals.filter(services__name='товар').aggregate(total=Sum('maney'))['total'] or 0

        # По видам оплаты (группировка по payment.name, sum maney)
        payments = {}
        for payment in Payment.objects.all():
            payments[payment.name] = deals.filter(payment=payment).aggregate(total=Sum('maney'))['total'] or 0

        # Заработок ролей
        roles_earnings = {}
        for role in Role.objects.all():
            # Сотрудники с этой ролью
            personals = Personal.objects.filter(role=role)
            role_deals = deals.filter(personal__in=personals)

            earnings = 0
            if role.params_one:
                earnings += income_services * (role.maney / 100)
            if role.params_two:
                earnings += income_goods * (role.maney / 100)
            roles_earnings[role.name] = earnings

        return {
            'income_services': income_services,
            'income_goods': income_goods,
            'payments': payments,
            'roles_earnings': roles_earnings,
        }


class ProductServiceAnalysisView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        service_ids = request.data.get('service_ids', [])
        from_date_str = request.data.get('from_date')
        to_date_str = request.data.get('to_date')

        if not service_ids or not from_date_str or not to_date_str:
            return Response({'error': 'Требуются service_ids, from_date и to_date'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from_date = parse_datetime(from_date_str)
            to_date = parse_datetime(to_date_str)
            if not from_date or not to_date:
                raise ValueError
        except ValueError:
            return Response({'error': 'Неверный формат дат'}, status=status.HTTP_400_BAD_REQUEST)

        # Фильтруем сделки по service_ids и датам
        deals = Deal.objects.filter(
            service__id__in=service_ids,
            date_time__range=(from_date, to_date)
        )
        serializer = DealSerializer(deals, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# class IncomeCalculation(APIView):
#     # authentication_classes = [TokenAuthentication]
#     # permission_classes = [IsAuthenticated]

from django.shortcuts import render
from datetime import datetime
from django.db.models import Q
from .models import Deal, Shift
from collections import defaultdict

def calculation_products(request):
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    deals = []
    result = []

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
            end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M")
            deals = Deal.objects.filter(date_time__range=(start_date, end_date)).select_related(
                "personal", "service"
            )
            filter_zp(deals)
        except ValueError as e:
            print(f"Ошибка формата даты: {e}")

    context = {
        "result": result,
        "start": start_str,
        "end": end_str,
    }
    return render(request, "blog/analysis_service.html", context)

from collections import defaultdict
from django.db.models import Q
from .models import Shift

# def filter_zp(start_date, end_date, deals, result):
#     daily_services = defaultdict(list)
#
#     for deal in deals:
#         # --- Определяем активную смену ---
#         shift = (
#             Shift.objects.filter(
#                 Q(start_time__lte=deal.date_time),
#                 Q(end_time__gte=deal.date_time) | Q(end_time__isnull=True)
#             )
#             .order_by('-start_time')
#             .first()
#         )
#
#         role = getattr(deal.personal, 'role', None)
#
#         # --- Собираем инфо по сделке ---
#         info = {
#             'personal': deal.personal.name if deal.personal else '-',
#             'admin': shift.admin.name if shift and shift.admin else '-',
#             'barman': shift.barman.name if shift and shift.barman else '-',
#             'shift_id': shift.id if shift else '-',
#             'date': deal.date_time.date(),
#             'service': deal.service.name if deal.service else '-',
#             'type': deal.services.name.lower() if deal.services else '',
#             'price': deal.maney or 0,
#             'role_obj': role,  # оставим для расчета %
#             'shift': shift,    # добавляем shift для расчета %
#         }
#
#         daily_services[info['date']].append(info)
#         result.append(info)
#
#     # --- Итог по дням ---
#     for day, deals_info in sorted(daily_services.items()):
#         print(f"\n📅 В период {day}:")
#         total_admin = 0
#         total_barman = 0
#
#         for d in deals_info:
#             price = d['price']
#             personal = d['personal']
#             service_type = d['type']
#             shift = d['shift']
#
#             salary = 0
#             role_view = ""
#
#             # Определяем проценты
#             admin_role_percent = shift.admin.role.maney_a if shift and shift.admin and shift.admin.role else 0
#             barman_role_percent = shift.barman.role.maney_a if shift and shift.barman and shift.barman.role else 0
#             personal_percent = d['role_obj'].maney if d['role_obj'] else 0
#
#             # === Расчёт зарплаты ===
#             if service_type == "услуга":
#                 if personal == (shift.admin.name if shift and shift.admin else None):
#                     # Исполнитель и админ — один человек
#                     salary = price * 50 / 100
#                     total_admin += salary
#                     role_view = f"услуга — админ получил {salary:.2f}₽ ({admin_role_percent}%)"
#                 elif personal == (shift.barman.name if shift and shift.barman else None):
#                     # Исполнитель и бармен — один человек
#                     salary = price * 50 / 100
#                     total_barman += salary
#                     role_view = f"услуга — бармен получил {salary:.2f}₽ ({barman_role_percent}%)"
#                 else:
#                     # Другой исполнитель
#                     salary = price * personal_percent / 100
#                     total_admin += salary
#                     role_view = f"услуга — админу {salary:.2f}₽ ({personal_percent}%)"
#
#             elif service_type == "товар":
#                 salary = price * personal_percent / 100
#                 total_barman += salary
#                 role_view = f"товар — бармену {salary:.2f}₽ ({personal_percent}%)"
#
#             print(
#                 f"   • {d['service']} | Цена: {price}₽ | "
#                 f"Исполнитель: {personal} | Админ: {d['admin']} | Бармен: {d['barman']} | "
#                 f"СменаID: {d['shift_id']} | {role_view}"
#             )
#
#         print(f"\n💰 ИТОГО за {day}:")
#         print(f"   Зарплата админа: {round(total_admin, 2)}₽")
#         print(f"   Зарплата бармена: {round(total_barman, 2)}₽")
#         print("-" * 40)

from collections import defaultdict
from django.db.models import Q
from .models import Deal, Shift

from collections import defaultdict
from django.db.models import Q
from .models import Deal, Shift

def filter_zp(deals):
    earnings = defaultdict(lambda: {"earnings": 0, "services": [], "role": "", "name": ""})
    total_revenue = 0

    for deal in deals:
        if not deal.personal:
            continue

        personal = deal.personal
        role = personal.role
        service_type = deal.services.name.lower() if deal.services else ""
        price = deal.maney or 0

        # --- Определяем смену ---
        shift = (
            Shift.objects.filter(
                Q(start_time__lte=deal.date_time),
                Q(end_time__gte=deal.date_time) | Q(end_time__isnull=True)
            ).order_by('-start_time').first()
        )
        admin = shift.admin if shift and shift.admin else None
        barman = shift.barman if shift and shift.barman else None

        def add_earning(user, role_obj, amount, service_name):
            if not user:
                return
            earnings[user.id]["earnings"] += amount
            earnings[user.id]["role"] = role_obj.name if role_obj else "Unknown"
            earnings[user.id]["name"] = user.name
            earnings[user.id]["services"].append({
                "service_name": service_name,
                "amount": round(amount, 2),
                "date": deal.date_time.date().isoformat()
            })

        # --- Логика начисления ---
        if service_type == "товар":
            # Бармен получает maney с продажи товара
            if barman and barman.role:
                salary = price * barman.role.maney / 100
                add_earning(barman, barman.role, salary, deal.service.name if deal.service else "-")
                total_revenue += salary

        elif service_type == "услуга":
            # Исполнитель получает свой процент (maney для танцовщицы/прочего)
            if personal.role:
                if personal not in [admin, barman]:
                    salary_personal = price * personal.role.maney / 100
                    add_earning(personal, personal.role, salary_personal, deal.service.name if deal.service else "-")
                    total_revenue += salary_personal

            # Админ получает всегда maney с любой услуги
            if admin and admin.role:
                salary_admin = price * admin.role.maney / 100
                add_earning(admin, admin.role, salary_admin, deal.service.name if deal.service else "-")
                total_revenue += salary_admin

            # Бармен получает maney_a, если он сам оказал услугу
            if personal == barman and barman and barman.role:
                salary_barman = price * barman.role.maney_a / 100
                add_earning(barman, barman.role, salary_barman, deal.service.name if deal.service else "-")
                total_revenue += salary_barman

            # Админ получает maney_a, если он сам оказал услугу
            if personal == admin and admin and admin.role:
                salary_admin_a = price * admin.role.maney_a / 100
                add_earning(admin, admin.role, salary_admin_a, deal.service.name if deal.service else "-")
                total_revenue += salary_admin_a

    # --- Вывод итогов ---
    print("\n💰 Итоговый доход по ролям:")
    for role_name in ["админ", "бармен", "танцовщица"]:
        print(f"\nИТОГ общий доход {role_name}s:")
        for e in earnings.values():
            if e["role"] == role_name:
                print(f"  {e['name']} - {round(e['earnings'], 2)}₽")

    total_salary = sum([e["earnings"] for e in earnings.values()])
    print(f"\nИТОГ общий доход всех сотрудников: {round(total_salary, 2)}₽")
    print(f"ИТОГ чистый доход (весь доход - расходы на ЗП): {round(total_revenue - total_salary, 2)}₽")

    print(list(earnings.values()))


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from collections import defaultdict
from django.db.models import Q
from datetime import datetime
from .models import Deal, Shift


class SalaryCalculationView(APIView):

    def post(self, request):
        start_str = request.data.get('start')
        end_str = request.data.get('end')

        if not start_str or not end_str:
            return Response({"error": "Параметры start и end обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
            end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            return Response({"error": "Неверный формат даты. Используй ISO: 2025-10-10T00:00"}, status=status.HTTP_400_BAD_REQUEST)

        deals = Deal.objects.filter(date_time__range=(start_date, end_date)).select_related("personal", "service")
        result = self.filter_zp(deals)

        return Response(result, status=status.HTTP_200_OK)

    def filter_zp(self, deals):
        earnings = defaultdict(lambda: {"earnings": 0, "services": [], "role": "", "name": ""})
        total_revenue = 0

        for deal in deals:
            if not deal.personal:
                continue

            personal = deal.personal
            role = personal.role
            service_type = deal.services.name.lower() if deal.services else ""
            price = deal.maney or 0

            # --- Определяем смену ---
            shift = (
                Shift.objects.filter(
                    Q(start_time__lte=deal.date_time),
                    Q(end_time__gte=deal.date_time) | Q(end_time__isnull=True)
                ).order_by('-start_time').first()
            )
            admin = shift.admin if shift and shift.admin else None
            barman = shift.barman if shift and shift.barman else None

            def add_earning(user, role_obj, amount, service_name):
                if not user or amount == 0:
                    return
                earnings[user.id]["earnings"] += amount
                earnings[user.id]["role"] = role_obj.name if role_obj else "Unknown"
                earnings[user.id]["name"] = user.name
                earnings[user.id]["services"].append({
                    "service_name": service_name,
                    "amount": round(amount, 2),
                    "date": deal.date_time.date().isoformat()
                })

            # --- Логика начисления ---
            if service_type == "товар":
                # Бармен получает maney с продажи товара
                if barman and barman.role:
                    salary = price * barman.role.maney / 100
                    add_earning(barman, barman.role, salary, deal.services.name)
                    total_revenue += salary

            elif service_type == "услуга":
                # Исполнитель получает свой процент (maney для танцовщицы/прочего)
                if personal.role and personal not in [admin, barman]:
                    salary_personal = price * personal.role.maney / 100
                    add_earning(personal, personal.role, salary_personal, deal.services.name)
                    total_revenue += salary_personal

                # Админ получает всегда maney с любой услуги
                if admin and admin.role:
                    salary_admin = price * admin.role.maney / 100
                    add_earning(admin, admin.role, salary_admin, deal.services.name)
                    total_revenue += salary_admin

                # Бармен получает maney_a, если он сам оказал услугу
                if personal == barman and barman and barman.role:
                    salary_barman = price * barman.role.maney_a / 100
                    add_earning(barman, barman.role, salary_barman, deal.services.name)
                    total_revenue += salary_barman

                # Админ получает maney_a, если он сам оказал услугу
                if personal == admin and admin and admin.role:
                    salary_admin_a = price * admin.role.maney_a / 100
                    add_earning(admin, admin.role, salary_admin_a, deal.services.name)
                    total_revenue += salary_admin_a

        # --- Итоговый JSON ---
        result = list(earnings.values())

        # --- Подсчет итогов по ролям ---
        roles_summary = defaultdict(float)
        for e in result:
            roles_summary[e["role"]] += e["earnings"]

        total_salary = sum(roles_summary.values())

        summary = {
            "roles_summary": {r: round(v, 2) for r, v in roles_summary.items()},
            "total_salary": round(total_salary, 2),
            "total_revenue": round(total_revenue, 2),
            "clean_profit": round(total_revenue - total_salary, 2),
            "details": result
        }

        return summary
