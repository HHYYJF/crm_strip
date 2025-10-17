import time

from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.db import models
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .serializers import ShiftCreateSerializer, LoginSerializer, PersonalSerializer
from .models import Deal, Personal, Services, Service, Payment, Whom, Role, Shift
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime


def get_user_from_cookie(request):
    token_key = request.COOKIES.get('auth_token')
    if not token_key:
        return None

    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return None

def tok(user):
    """
    Создание токена и возврат стандартного ответа с HttpOnly cookie
    """
    if user is not None:
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        # Создаем ответ
        response = Response({
            "user": {
                "id": user.id,
                "username": user.username
            },
            "message": "Успешный вход"
        }, status=status.HTTP_200_OK)
        response.set_cookie(
            key='auth_token',
            value=token.key,
            httponly=True,       # 🚫 JS не может прочитать
            secure=False,        # True в проде (HTTPS)
            samesite='Lax',      # 'None' если фронт и бэк на разных доменах
            max_age=60 * 60 * 24 * 7  # неделя
        )
        return response
    else:
        return Response(
            {"error": "Неверное имя пользователя или пароль"},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    return tok(user)

@api_view(['GET'])
def HistoryAPIView(request):
    deals = Deal.objects.filter(ais=True).values(
        'id',
        'personal__name',
        'service__name',
        'payment__name',
        'whom__name',
        'maney',
        'date_time',
        'ais'
    )

@api_view(['GET'])
def HistoryAPIView(request):

    active_deals = Deal.objects.filter(ais=True).select_related(
        "personal", "services", "service", "payment", "whom"
    )

    data = [
        {
            "id": deal.id,
            "personal": {
                "id": deal.personal.id if deal.personal else None,
                "name": deal.personal.name if deal.personal else None,
                "role": deal.personal.role.name if deal.personal and deal.personal.role else None,
            },
            "services": {
                "id": deal.services.id if deal.services else None,
                "is_tovar": deal.services.is_tovar if deal.services else None,
            },
            "service": deal.service.name if deal.service else None,
            "payment": deal.payment.name if deal.payment else None,
            "whom": deal.whom.name if deal.whom else None,
            "maney": deal.maney,
            "date_time": deal.date_time.strftime("%Y-%m-%d %H:%M:%S"),
            "ais": deal.ais,
        }
        for deal in active_deals
    ]

    return Response({"history": data})
class IndexAPIView(APIView):

    def post(self, request):
        # user = get_user_from_cookie(request)
        # if not user:
        #     return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ShiftCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin_id = serializer.validated_data['administrator_id']
        barman_id = serializer.validated_data['bartender_id']

        admin = Personal.objects.filter(id=admin_id).first()
        barman = Personal.objects.filter(id=barman_id).first()

        if not admin or not barman:
            return Response({"error": "Админ или бармен не найдены"}, status=status.HTTP_400_BAD_REQUEST)

        # Закрываем предыдущую активную смену, если есть
        Shift.objects.filter(is_active=True).update(is_active=False)

        # Создаём новую смену
        shift = Shift.objects.create(admin=admin, barman=barman)

        # Возвращаем ответ в формате GET
        shift_data = {
            "id": shift.id,
            "started_at": shift.start_time.isoformat(),
            "ended_at": shift.end_time.isoformat() if shift.end_time else None,
            "staff": {
                "administrator": {
                    "id": admin.id,
                    "username": admin.name
                },
                "bartender": {
                    "id": barman.id,
                    "username": barman.name
                }
            },
            "status": "active" if shift.is_active else "closed"
        }

        return Response({"shifts": [shift_data]}, status=status.HTTP_201_CREATED)

    def get(self, request):
        # user = get_user_from_cookie(request)
        # if not user:
        #     return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)

        shifts = Shift.objects.all().select_related('admin', 'barman')

        shifts_data = []
        for s in shifts:
            shifts_data.append({
                "id": s.id,
                "started_at": s.start_time.isoformat(),
                "ended_at": s.end_time.isoformat() if s.end_time else None,
                "staff": {
                    "administrator": {
                        "id": s.admin.id if s.admin else None,
                        "username": s.admin.name if s.admin else None
                    },
                    "bartender": {
                        "id": s.barman.id if s.barman else None,
                        "username": s.barman.name if s.barman else None
                    }
                },
                "status": "active" if s.is_active else "closed"
            })

        return Response({"shifts": shifts_data}, status=status.HTTP_200_OK)



class LogoutView(APIView):
    def get(self, request):
        # user = get_user_from_cookie(request)
        # if not user:
        #     return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Все сделки делаем неактивными
            Deal.objects.all().update(ais=False)

            # Закрываем все активные смены, где сотрудник участвует
            active_shifts = Shift.objects.filter(is_active=True)
            for shift in active_shifts:
                shift.is_active = False
                shift.end_time = timezone.now()
                shift.save()

            # # Удаляем токен текущего пользователя
            # Token.objects.filter(user=user).delete()

            return Response({
                "message": "Выход выполнен успешно"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Deal, Payment, Whom, Service, Services, Personal


class DealAPIView(APIView):
    """Создание и получение сделок"""

    def get(self, request):
        # user = get_user_from_cookie(request)
        # if not user:
        #     return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)

        services_qs = Service.objects.select_related('role').all()
        services = []
        for s in services_qs:
            services.append({
                "id": s.id,
                "name": s.name,
                "tovar": s.role.is_tovar if s.role else False
            })

        payments = list(Payment.objects.values("id", "name"))
        whoms = list(Whom.objects.values("id", "name"))
        personals = list(Personal.objects.values("id", "name"))

        return Response({
            "payments": payments,
            "whoms": whoms,
            "services": services,
            "personals": personals
        })

    def post(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        try:
            deal = Deal.objects.create(
                personal_id=data.get("staff_id"),
                services_id=data.get("service_type_id"),
                service_id=data.get("service_id"),
                payment_id=data.get("payment_id"),
                whom_id=data.get("whom_id"),
                maney= data.get("money", 0),
                date_time=timezone.now(),
                ais=True
            )

            deal_data = {
                "id": deal.id,
                "staff": {
                    "id": deal.personal.id if deal.personal else None,
                    "username": deal.personal.name if deal.personal else None
                },
                "service_type": "Продукт" if deal.services and deal.services.is_tovar else "Услуга" if deal.services else None,
                "service": deal.service.name if deal.service else None,
                "payment": deal.payment.name if deal.payment else None,
                "whom": deal.whom.name if deal.whom else None,
                "money": deal.maney,
                "created_at": deal.date_time.isoformat()
            }

            return Response({"deal": deal_data}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def shift_staff(request):
    user = get_user_from_cookie(request)
    if not user:
        return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
    roles = Role.objects.filter(bool_name=True)  # фильтруем только нужные роли
    staff_data = {}

    for role in roles:
        personals = Personal.objects.filter(role=role)
        staff_data[role.name.lower()] = {
            "label": role.name,
            "users": [
                {
                    "id": p.id,
                    "username": p.name
                }
                for p in personals
            ]
        }

    return Response({"staff": staff_data})


class EmployeePerformanceView(APIView):
    """
    GET: возвращает всех сотрудников.
    POST: фильтрует сделки по сотрудникам и дате/времени и возвращает анализ с детализацией.
    """

    def get(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        employees = Personal.objects.all()
        data = [
            {
                'id': e.id,
                'name': e.name,
                'role': e.role.name if e.role else None
            }
            for e in employees
        ]
        return Response({'employees': data})

    def post(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        employee_ids = request.data.get('employees', [])
        start_str = request.data.get('start')
        end_str = request.data.get('end')

        if not employee_ids or not start_str or not end_str:
            return Response({'error': 'Необходимо указать сотрудников и дату начала/конца'},
                            status=status.HTTP_400_BAD_REQUEST)

        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)

        if not start_dt or not end_dt:
            return Response({'error': 'Неверный формат даты'}, status=status.HTTP_400_BAD_REQUEST)

        deals = Deal.objects.filter(
            personal__id__in=employee_ids,
            date_time__range=(start_dt, end_dt)
        ).select_related('personal', 'services', 'service')

        result = {}
        for d in deals:
            emp_name = d.personal.name if d.personal else 'Неизвестный'
            if emp_name not in result:
                result[emp_name] = {
                    'services_count': 0,
                    'tovar_count': 0,
                    'total_amount': 0,
                    'deals': []
                }

            is_tovar = d.services.is_tovar if d.services else False
            is_uslyga = d.services.is_uslyga if d.services else False

            if is_tovar:
                result[emp_name]['tovar_count'] += 1
            if is_uslyga:
                result[emp_name]['services_count'] += 1

            result[emp_name]['total_amount'] += d.maney

            # детализированная запись сделки
            result[emp_name]['deals'].append({
                'date': d.date_time.strftime('%Y-%m-%d %H:%M'),
                'service_type': 'услуга' if is_uslyga else 'товар' if is_tovar else 'неизвестно',
                'service': d.service.name if d.service else None,
                'price': d.maney
            })

        # преобразуем в список
        output = []
        for emp_name, stats in result.items():
            output.append({
                'user': emp_name,
                'services_count': stats['services_count'],
                'tovar_count': stats['tovar_count'],
                'total_amount': stats['total_amount'],
                'deals': stats['deals']
            })

        return Response({'performance': output})

class ProductSalesView(APIView):
    """
    GET: возвращает все товары.
    POST: фильтрует сделки по товарам и дате/времени и возвращает анализ.
    """

    def get(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        products = Service.objects.filter(role__is_tovar=True)
        data = [
            {
                'id': p.id,
                'name': p.name,
            }
            for p in products
        ]
        return Response({'products': data})

    def post(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        """
        Ожидается JSON:
        {
            "products": [1,2,3],  # id товаров
            "start": "2025-10-12T00:00",
            "end": "2025-10-12T23:59"
        }
        """
        product_ids = request.data.get('products', [])
        start_str = request.data.get('start')
        end_str = request.data.get('end')

        if not product_ids or not start_str or not end_str:
            return Response({'error': 'Необходимо указать товары и дату начала/конца'},
                            status=status.HTTP_400_BAD_REQUEST)

        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)

        if not start_dt or not end_dt:
            return Response({'error': 'Неверный формат даты'}, status=status.HTTP_400_BAD_REQUEST)

        deals = Deal.objects.filter(
            service__id__in=product_ids,
            date_time__range=(start_dt, end_dt)
        ).select_related('service')

        result = {}
        for d in deals:
            prod_name = d.service.name if d.service else 'Неизвестный'
            if prod_name not in result:
                result[prod_name] = {'count': 0, 'dates': []}

            result[prod_name]['count'] += 1
            result[prod_name]['dates'].append(d.date_time.strftime('%Y-%m-%d %H:%M'))

        # преобразуем в список для фронтенда
        output = []
        for name, stats in result.items():
            output.append({
                'product': name,
                'sold_count': stats['count'],
                'dates': stats['dates']
            })

        return Response({'sales': output})

"""""""""""""""""""""""""""  история + расчет  """""""""""""""""""""""""""


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from django.db.models import Sum
from .models import Deal

@api_view(['POST'])
def historianalitic(request):
    user = get_user_from_cookie(request)
    if not user:
        return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
    start_str = request.data.get('start')
    end_str = request.data.get('end')

    if not start_str or not end_str:
        return Response({'error': 'Необходимо указать start и end'}, status=status.HTTP_400_BAD_REQUEST)

    # --- безопасная проверка дат ---
    try:
        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)
    except ValueError:
        return Response({
            'error': 'Неверный формат даты. Пример правильного формата: "2025-10-12T00:00"'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not start_dt or not end_dt:
        return Response({
            'error': 'Неверный формат даты. Пример правильного формата: "2025-10-12T00:00"'
        }, status=status.HTTP_400_BAD_REQUEST)

    # --- если end_dt больше текущей даты, ставим текущую ---
    now = datetime.now()
    if end_dt > now:
        end_dt = now

    # --- получаем сделки за период ---
    deals = Deal.objects.filter(date_time__range=[start_dt, end_dt])
    data = get_deals_info(deals)

    # --- расчет доходов ---
    posts, users = calculation(data, start_dt, end_dt)

    # --- аналитика по оплатам ---
    payments_data = (
        deals.values('payment__name')
        .order_by('payment__name')
        .annotate(total=Sum('maney'))
    )

    total_money = deals.aggregate(total=Sum('maney'))['total'] or 0
    services_count = deals.filter(services__is_uslyga=True).count()
    products_count = deals.filter(services__is_tovar=True).count()

    posts.sort(key=lambda x: x['income'], reverse=True)
    users.sort(key=lambda x: x['total_income'], reverse=True)

    result = {
        "payments": [
            {"payment_type": p['payment__name'], "amount": p['total']}
            for p in payments_data
        ],
        "total_money": total_money,
        "services_count": services_count,
        "products_count": products_count,
        "posts": posts,
        "users": users
    }

    return Response(result)




"""""""""""""""""""""""""""  Расчет ЗП  """""""""""""""""""""""""""

from datetime import datetime
from django.db.models import Q
def get_deals_info(deals):
    """
    Преобразует queryset сделок в список словарей с полной информацией.
    """
    data = []

    for d in deals:
        record = {
            'id': d.id,
            'personal': d.personal.name if d.personal else None,
            'service': d.service.name if d.service else None,
            "type_is_tovar": d.services.is_tovar if d.services else False,
            "type_is_uslyga": d.services.is_uslyga if d.services else False,
            'payment': d.payment.name if d.payment else None,
            'whom': d.whom.name if d.whom else None,
            'maney': d.maney,
            'date_time': d.date_time.strftime('%Y-%m-%d %H:%M'),
            'ais': d.ais,
            'shift_admin': None,
            'shift_barman': None,
        }

        # Добавляем проценты и фиксированные выплаты, если есть service
        if d.service:
            record.update({
                'percent_admin': d.service.percent_admin,
                'percent_barmen': d.service.percent_barmen,
                'percent_admin_ysluga': d.service.percent_admin_ysluga,
                'percent_barmen_ysluga': d.service.percent_barmen_ysluga,
                'percent_barmen_tanes': d.service.percent_barmen_tanes,
                'percent_barmen_admin': d.service.percent_barmen_admin,
                'percent_smol': d.service.percent_smol,
            })

        # Ищем смену, в которую попадает дата сделки
        shift = Shift.objects.filter(
            start_time__lte=d.date_time,
            end_time__gte=d.date_time
        ).first()

        if shift:
            record['shift_admin'] = shift.admin.name if shift.admin else None
            record['shift_barman'] = shift.barman.name if shift.barman else None

        data.append(record)

    return data
class DealsInRangeView(APIView):
    def post(self, request):
#         user = get_user_from_cookie(request)
#         if not user:
#             return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        start_str = request.data.get('start')
        end_str = request.data.get('end')

        if not start_str or not end_str:
            return Response({'error': 'Необходимо указать start и end'}, status=status.HTTP_400_BAD_REQUEST)

        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)
        if not start_dt or not end_dt:
            return Response({'error': 'Неверный формат даты'}, status=status.HTTP_400_BAD_REQUEST)

        deals = Deal.objects.filter(date_time__range=(start_dt, end_dt)).select_related(
            'personal', 'service', 'services', 'payment', 'whom'
        )
        data = get_deals_info(deals)
        # вызов функции расчета доходов
        posts,users = calculation(data, start_dt, end_dt)

        return Response({
            'posts': posts,
            'users': users
        })

@csrf_exempt
def deals_in_range(request):
    if request.method == "GET":
        return render(request, "blog/calculation_products.html")

    elif request.method == "POST":
        start_str = request.POST.get('start')
        end_str = request.POST.get('end')

        if not start_str or not end_str:
            return JsonResponse({'error': 'Необходимо указать start и end'}, status=400)

        start_dt = parse_datetime(start_str)
        end_dt = parse_datetime(end_str)

        if not start_dt or not end_dt:
            return JsonResponse({'error': 'Неверный формат даты'}, status=400)

        deals = Deal.objects.filter(date_time__range=(start_dt, end_dt)).select_related(
            'personal', 'service', 'services', 'payment', 'whom'
        )
        data = []
        for d in deals:
            record = {
                'id': d.id,
                'personal': d.personal.name if d.personal else None,
                'service': d.service.name if d.service else None,
                "type_is_tovar": d.services.is_tovar if d.services else False,
                "type_is_uslyga": d.services.is_uslyga if d.services else False,
                'payment': d.payment.name if d.payment else None,
                'whom': d.whom.name if d.whom else None,
                'maney': d.maney,
                'date_time': d.date_time.strftime('%Y-%m-%d %H:%M'),
                'ais': d.ais,
                'shift_admin': None,
                'shift_barman': None,
            }

            # добавляем проценты и фиксированные выплаты, если есть service
            if d.service:
                record.update({
                    'percent_admin': d.service.percent_admin,
                    'percent_barmen': d.service.percent_barmen,
                    'percent_admin_ysluga': d.service.percent_admin_ysluga,
                    'percent_barmen_ysluga': d.service.percent_barmen_ysluga,
                    'percent_barmen_tanes': d.service.percent_barmen_tanes,
                    'percent_barmen_admin': d.service.percent_barmen_admin,
                    'percent_smol': d.service.percent_smol,
                })

            # ищем смену, в которую попадает дата сделки
            shift = Shift.objects.filter(
                start_time__lte=d.date_time,
                end_time__gte=d.date_time
            ).first()

            if shift:
                record['shift_admin'] = shift.admin.name if shift.admin else None
                record['shift_barman'] = shift.barman.name if shift.barman else None

            data.append(record)
        posts,users = calculation(data, start_dt, end_dt)
        print(posts)
        print(users)
        return JsonResponse({"posts":posts,"users":users})



def calculation(data, start_dt, end_dt):
    posts = []
    users = []

    def calculation_income(user, maney):
        for item in posts:
            if item['name'] == user:
                item['income'] += maney
                break
        else:
            posts.append({'name': user, 'income': maney})
    def add_deal(master, date, service_type, service, price, pr_price, percent):
        for user in users:
            if user['name'] == master:
                user['deals'].append({
                    'date': date,
                    'service_type': service_type,
                    'service': service,
                    'price': price,
                    'income': pr_price,
                    'percent': percent
                })
                user['total_income'] += pr_price
                break
        else:
            users.append({
                'name': master,
                'deals': [{
                    'date': date,
                    'service_type': service_type,
                    'service': service,
                    'price': price,
                    'income': pr_price,
                    'percent': percent
                }],
                'total_income': pr_price
            })

    for i in data:
        # --- УСЛУГА ---
        if i['type_is_uslyga']:
            service_type = 'услуга'

            # ✅ Если есть спецпроцент (percent_smol) — он приоритетный
            if i['percent_smol'] > 0:
                percent = i['percent_smol']
                maney = i['maney'] * percent / 100
                add_deal(i['personal'], i['date_time'], service_type, f"{i['service']} (спец %)", i['maney'], maney, percent)
                calculation_income(i['personal'], maney)
                continue  # пропускаем остальную логику

            # ✅ Если исполнитель администратор
            if i['personal'] == i['shift_admin']:
                percent = i['percent_admin_ysluga']
                maney = i['maney'] * percent / 100
                add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (оказана админом)", i['maney'], maney, percent)
                calculation_income(i['shift_admin'], maney)

            # ✅ Если исполнитель бармен
            elif i['personal'] == i['shift_barman']:
                percent = i['percent_barmen_ysluga']
                maney = i['maney'] * percent / 100
                add_deal(i['shift_barman'], i['date_time'], service_type, f"{i['service']} (оказана барменом)", i['maney'], maney, percent)
                calculation_income(i['shift_barman'], maney)

            # ✅ Если кто-то другой (например, танцовщица)
            else:
                percent = i['percent_barmen_tanes']
                maney = i['maney'] * percent / 100
                add_deal(i['personal'], i['date_time'], service_type, i['service'], i['maney'], maney, percent)
                calculation_income(i['personal'], maney)

        # --- ТОВАР ---
        elif i['type_is_tovar']:
            service_type = 'товар'

            # ✅ Доход администратора
            percent_ad = i['percent_admin']
            maney_ad = i['maney'] * percent_ad / 100
            add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (продажа от {i['personal']})", i['maney'], maney_ad, percent_ad)
            calculation_income(i['shift_admin'], maney_ad)

            # ✅ Доход бармена
            percent_bar = i['percent_barmen']
            maney_bar = i['maney'] * percent_bar / 100
            add_deal(i['shift_barman'], i['date_time'], service_type, f"{i['service']} (продажа от {i['personal']})", i['maney'], maney_bar, percent_bar)
            calculation_income(i['shift_barman'], maney_bar)

            # ✅ Фиксированный доход исполнителю, если задан percent_barmen_admin
            if i['percent_barmen_admin'] > 0:
                maney_fix = i['percent_barmen_admin']
                add_deal(i['personal'], i['date_time'], service_type, f"{i['service']} (фикс доход)", i['maney'], maney_fix, 'фиксировано')
                calculation_income(i['personal'], maney_fix)

    # --- ПУСТЫЕ СМЕНЫ ---
    shifts = Shift.objects.filter(
        Q(start_time__lte=end_dt) &
        (Q(end_time__gte=start_dt) | Q(end_time__isnull=True))
    )

    for shift in shifts:
        end_shift = shift.end_time if shift.end_time else datetime.now()
        has_deals = Deal.objects.filter(date_time__range=(shift.start_time, end_shift)).exists()

        if not has_deals:
            # Админ получает фикс за пустую смену
            if shift.admin:
                bonus = shift.admin.role.maney_null
                calculation_income(shift.admin.name, bonus)
                add_deal(shift.admin.name, shift.start_time.strftime('%Y-%m-%d %H:%M'), 'пустая смена', 'Пустая смена', 0, bonus, 'фиксировано')

            # Бармен получает фикс за пустую смену
            if shift.barman:
                bonus = shift.barman.role.maney_null
                calculation_income(shift.barman.name, bonus)
                add_deal(shift.barman.name, shift.start_time.strftime('%Y-%m-%d %H:%M'), 'пустая смена', 'Пустая смена', 0, bonus, 'фиксировано')
    return posts, users