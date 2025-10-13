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

posts = []
users = []
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
            "bartenders": barman_data
        })

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

class DealAPIView(APIView):
    """Создание и получение сделок"""

    def get(self, request):
        # 1️⃣ Активные сделки
        active_deals = Deal.objects.filter(ais=True).select_related(
            "personal", "services", "service", "payment", "whom"
        )

        deals_data = [
            {
                "id": d.id,
                "personal": d.personal.name if d.personal else None,
                "personal_id": d.personal.id if d.personal else None,
                "service_type": "товар" if d.services and d.services.is_tovar else "услуга" if d.services else None,
                "service": d.service.name if d.service else None,
                "service_id": d.service.id if d.service else None,
                "payment": d.payment.name if d.payment else None,
                "payment_id": d.payment.id if d.payment else None,
                "whom": d.whom.name if d.whom else None,
                "whom_id": d.whom.id if d.whom else None,
                "maney": d.maney,
                "date_time": d.date_time.strftime("%Y-%m-%d %H:%M"),
            }
            for d in active_deals
        ]

        personals = list(Personal.objects.values("id", "name"))
        services_types = list(Services.objects.values("id", "is_tovar", "is_uslyga"))
        services = list(Service.objects.values("id", "name"))
        payments = list(Payment.objects.values("id", "name"))
        whoms = list(Whom.objects.values("id", "name"))

        return Response({
            "deals": deals_data,
            "meta": {
                "personals": personals,
                "services_types": services_types,
                "services": services,
                "payments": payments,
                "whoms": whoms,
            }
        })

    def post(self, request):
        """Создание новой сделки"""
        data = request.data
        try:
            deal = Deal.objects.create(
                personal_id=data.get("personal_id"),
                services_id=data.get("services_id"),
                service_id=data.get("service_id"),
                payment_id=data.get("payment_id"),
                whom_id=data.get("whom_id"),
                maney=data.get("maney", 0),
                date_time=timezone.now(),
                ais=True
            )

            return Response({
                "message": "Сделка успешно создана",
                "deal_id": deal.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def histori(request):
    """История всех смен (активных и закрытых)"""
    shifts = Shift.objects.select_related("admin", "barman").order_by("-start_time")

    data = []
    for s in shifts:
        data.append({
            "id": s.id,
            "admin": s.admin.name if s.admin else None,
            "barman": s.barman.name if s.barman else None,
            "start_time": s.start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": s.end_time.strftime("%Y-%m-%d %H:%M") if s.end_time else None,
            "is_active": s.is_active
        })

    return Response({"history": data})


class EmployeePerformanceView(APIView):
    """
    GET: возвращает всех сотрудников.
    POST: фильтрует сделки по сотрудникам и дате/времени и возвращает анализ с детализацией.
    """

    def get(self, request):
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
        """
        Ожидается JSON:
        {
            "employees": [1,2],  # id сотрудников
            "start": "2025-10-12T00:00",
            "end": "2025-10-12T23:59"
        }
        """
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
        # возвращаем все товары (Service с is_tovar=True)
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



"""""""""""""""""""""""""""  Расчет ЗП  """""""""""""""""""""""""""

from datetime import datetime
from django.db.models import Q
class DealsInRangeView(APIView):

    def post(self, request):
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

            shift = Shift.objects.filter(
                start_time__lte=d.date_time,
                end_time__gte=d.date_time
            ).first()

            if shift:
                record['shift_admin'] = shift.admin.name if shift.admin else None
                record['shift_barman'] = shift.barman.name if shift.barman else None

            data.append(record)

        # вызов функции расчета доходов
        calculation(data, start_dt, end_dt)

        return Response({
            'posts': posts,
            'users': users
        })
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
        calculation(data, start_dt, end_dt)
        print(posts)
        print(users)
        return JsonResponse({'deals': data})
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
def calculation(data, start_dt, end_dt):
    for i in data:
        if i['type_is_uslyga']:  # Если сделка — услуга
            service_type = 'услуга'
            # if i['personal'] == i['shift_admin']:  # Услуга оказана администратором
            #     percent = i['percent_admin_ysluga']
            #     maney = i['maney'] * percent / 100
            #     user = i['shift_admin']
            #     add_deal(user, i['date_time'], service_type, i['service'], i['maney'], maney, percent)
            #     calculation_income(user, maney)
            # elif i['personal'] == i['shift_barman']:  # Услуга оказана барменом
            #     # Доход бармена
            #     percent = i['percent_barmen_ysluga']
            #     maney = i['maney'] * percent / 100
            #     user = i['shift_barman']
            #     add_deal(user, i['date_time'], service_type, f"{i['service']} (оказана барменом)", i['maney'], maney,
            #              percent)
            #     calculation_income(user, maney)
            #     # Доход администратора
            #     percent_ad = i['percent_admin']
            #     maney_ad = i['maney'] * percent_ad / 100
            #     add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (от {i['personal']})",
            #              i['maney'], maney_ad, percent_ad)
            #     calculation_income(i['shift_admin'], maney_ad)
            # else:  # Услуга оказана другим сотрудником
            #     # Доход администратора
            #     percent_ad = i['percent_admin']
            #     maney_ad = i['maney'] * percent_ad / 100
            #     add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (от {i['personal']})",
            #              i['maney'], maney_ad, percent_ad)
            #     calculation_income(i['shift_admin'], maney_ad)
            #     # Доход исполнителя
            #     percent_p = i['percent_barmen_tanes']
            #     maney_p = i['maney'] * percent_p / 100
            #     add_deal(i['personal'], i['date_time'], service_type, i['service'], i['maney'], maney_p, percent_p)
            #     calculation_income(i['personal'], maney_p)
            if i['personal'] == i['shift_admin']:  # Услуга оказана администратором
                percent = i['percent_smol'] if i['percent_smol'] > 0 else i[
                    'percent_admin_ysluga']  # Use percent_smol if non-zero
                maney = i['maney'] * percent / 100
                user = i['shift_admin']
                add_deal(user, i['date_time'], service_type, i['service'], i['maney'], maney, percent)
                calculation_income(user, maney)
            elif i['personal'] == i['shift_barman']:  # Услуга оказана барменом
                # Доход бармена
                percent = i['percent_smol'] if i['percent_smol'] > 0 else i[
                    'percent_barmen_ysluga']  # Use percent_smol if non-zero
                maney = i['maney'] * percent / 100
                user = i['shift_barman']
                add_deal(user, i['date_time'], service_type, f"{i['service']} (оказана барменом)", i['maney'], maney,
                         percent)
                calculation_income(user, maney)
                # Доход администратора
                percent_ad = i['percent_admin']
                maney_ad = i['maney'] * percent_ad / 100
                add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (от {i['personal']})",
                         i['maney'], maney_ad, percent_ad)
                calculation_income(i['shift_admin'], maney_ad)
            else:  # Услуга оказана другим сотрудником
                # Доход администратора
                percent_ad = i['percent_admin']
                maney_ad = i['maney'] * percent_ad / 100
                add_deal(i['shift_admin'], i['date_time'], service_type, f"{i['service']} (от {i['personal']})",
                         i['maney'], maney_ad, percent_ad)
                calculation_income(i['shift_admin'], maney_ad)
                # Доход исполнителя
                percent_p = i['percent_smol'] if i['percent_smol'] > 0 else i[
                    'percent_barmen_tanes']  # Use percent_smol if non-zero
                maney_p = i['maney'] * percent_p / 100
                add_deal(i['personal'], i['date_time'], service_type, i['service'], i['maney'], maney_p, percent_p)
                calculation_income(i['personal'], maney_p)
        elif i['type_is_tovar']:  # Если сделка — товар
            service_type = 'товар'
            # Доход бармена
            percent_bar = i['percent_barmen']
            maney_bar = i['maney'] * percent_bar / 100
            add_deal(i['shift_barman'], i['date_time'], service_type, f"{i['service']} (от {i['personal']})",
                     i['maney'], maney_bar, percent_bar)
            calculation_income(i['shift_barman'], maney_bar)
            # Фиксированный доход для исполнителя, если есть
            if i['percent_barmen_admin'] > 0:
                maney_fix = i['percent_barmen_admin']
                add_deal(i['personal'], i['date_time'], service_type, f"{i['service']} (фиксированный доход)",
                         i['maney'], maney_fix, 'фиксировано')
                calculation_income(i['personal'], maney_fix)
# Добавлено: Обработка пустых смен
    shifts = Shift.objects.filter(
        Q(start_time__lte=end_dt) &
        (Q(end_time__gte=start_dt) | Q(end_time__isnull=True))
    )
    for shift in shifts:
        end_shift = shift.end_time if shift.end_time else datetime.now()
        has_deals = Deal.objects.filter(date_time__range=(shift.start_time, end_shift)).exists()
        if not has_deals:
            # Пустая смена
            if shift.admin:
                bonus = shift.admin.role.maney_null
                calculation_income(shift.admin.name, bonus)
                add_deal(shift.admin.name, shift.start_time.strftime('%Y-%m-%d %H:%M'), 'пустая смена', 'Пустая смена', 0, bonus, 'фиксировано')
            if shift.barman:
                bonus = shift.barman.role.maney_null
                calculation_income(shift.barman.name, bonus)
                add_deal(shift.barman.name, shift.start_time.strftime('%Y-%m-%d %H:%M'), 'пустая смена', 'Пустая смена', 0, bonus, 'фиксировано')