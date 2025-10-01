from collections import defaultdict
from datetime import timedelta, time
from django.utils import timezone
from django.shortcuts import render, redirect
from .forms import LoginForm, DealForm
from django.contrib.auth import authenticate, login as auth_login
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from .forms import DealForm
from .models import Service, Deal, Personal
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_datetime
from dateutil.parser import parse

hours = 24
shift_start_hour = 9
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect("index")
            else:
                form.add_error(None, "Неверное имя пользователя или пароль")
    else:
        form = LoginForm()
    return render(request, "blog/login.html", {"form": form})



def index(request):
    now = timezone.now()
    shift_start_time = time(hour=shift_start_hour, minute=0, second=0)
    if now.time() >= shift_start_time:
        shift_start = now.replace(hour=shift_start_hour, minute=0, second=0, microsecond=0)
    else:
        shift_start = (now - timedelta(days=1)).replace(hour=shift_start_hour, minute=0, second=0, microsecond=0)

    if request.method == "POST":
        form = DealForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            print("Ошибки формы:", form.errors)
    else:
        form = DealForm()
    deals = Deal.objects.filter(date_time__gte=shift_start).order_by('-date_time')
    return render(request, "blog/index.html", {
        "form": form,
        "deals": deals,
        "hours": hours
    })


def history(request):
    deals = Deal.objects.all().order_by("-date_time")
    start_post = request.GET.get("start")
    end_post = request.GET.get("end")

    if start_post and end_post:
        start, end = sorted([start_post, end_post])
        start_dt = parse(start)
        end_dt = parse(end)
        if start_dt and end_dt:
            # Make timezone-aware if not already
            if not start_dt.tzinfo:
                start_dt = timezone.make_aware(start_dt)
            if not end_dt.tzinfo:
                end_dt = timezone.make_aware(end_dt)
            deals = deals.filter(date_time__range=(start_dt, end_dt)).order_by("-date_time")
        calc = history_calculation(deals)
        return render(request, "blog/history.html", {"post": deals, "calc": calc})

    else:
        calc = None
        return render(request, "blog/history.html", {"post": deals, "calc": calc})


def history_calculation(deals):
    data = {
        "service_u": 0,
        "service_t": 0,
        "total": 0
    }
    for deal in deals:
        if not deal.personal or not deal.personal.role:
            continue
        deal_amount = getattr(deal, 'maney', 0) or getattr(deal, 'money', 0) or 0
        if deal.personal.role.params_one:
            data["service_u"] += deal_amount
        elif deal.personal.role.params_two:
            data["service_t"] += deal_amount
        data["total"] += deal_amount
    return data


def palindrim(start_post, end_post):
    if start_post > end_post:
        return end_post, start_post
    return start_post, end_post
@require_GET
def get_services(request):
    services_id = request.GET.get('services_id')
    if services_id:
        try:
            services = Service.objects.filter(service_id=services_id).values('id', 'name')
            return JsonResponse({'services': list(services), 'status': 'success', 'count': services.count()})
        except Exception as e:
            return JsonResponse({'services': [], 'status': 'error', 'message': str(e)})
    return JsonResponse({'services': [], 'status': 'no_id'})

def calculation(request):
    post = None
    calc = None
    start_post = request.GET.get("start")
    end_post = request.GET.get("end")

    if start_post and end_post:
        post = Deal.objects.all().order_by("-date_time")
        start, end = sorted([start_post, end_post])
        start_dt = parse(start)
        end_dt = parse(end)
        if start_dt and end_dt:
            if not start_dt.tzinfo:
                start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
            if not end_dt.tzinfo:
                end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
            post = post.filter(date_time__range=(start_dt, end_dt)).order_by("-date_time")
            calc = calculation_calculation(post)

    return render(request, "blog/analysis_service.html", {
        "post": post,
        "masters": calc["masters"] if calc else None
    })
def calculation_calculation(deals):
    data = {"masters": []}
    masters_dict = {}

    for deal in deals:
        if not deal.personal or not deal.personal.role:
            continue

        master_name = deal.personal.name
        role = deal.personal.role
        role_percent = role.maney
        if master_name not in masters_dict:
            masters_dict[master_name] = {
                "name": master_name,
                "percent": role_percent,
                "sum_income": 0,
                "income": 0,
                "deals": []
            }

        amount = deal.maney or 0
        if role.params_one and deal.services.name.lower().startswith("услуг"):
            income = amount * (role_percent / 100)
        elif role.params_two and deal.services.name.lower().startswith("товар"):
            income = amount * (role_percent / 100)
        else:
            income = 0

        deal_data = {
            "id": deal.id,
            "name": deal.service.name if deal.service else "не определено",
            "datetime": deal.date_time.strftime("%d %B %H:%M"),
            "price": deal.maney,
        }
        masters_dict[master_name]["deals"].append(deal_data)
        masters_dict[master_name]["sum_income"] += deal.maney
        masters_dict[master_name]["income"] += int(income)

    for master in masters_dict.values():
        if master["sum_income"] == 0 and master["deals"]:
            master["income"] = 500

    data["masters"] = list(masters_dict.values())
    return data



def count_days_without_income(post):
    if not post:
        return 0
    deals = sorted(post, key=lambda x: x.date_time)
    start_date = deals[0].date_time.date()
    end_date = deals[-1].date_time.date()
    days = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    deal_dates = {deal.date_time.date() for deal in deals if deal.maney > 0}
    days_without_income = sum(1 for day in days if day not in deal_dates)

    return days_without_income



def calculation_chart(request):
    # Получаем сделки за период (пример)
    post = Deal.objects.all().order_by("-date_time")

    start_post = request.GET.get("start")
    end_post = request.GET.get("end")

    if start_post and end_post:
        start, end = sorted([start_post, end_post])
        start_dt = parse(start)
        end_dt = parse(end)
        if start_dt and end_dt:
            if not start_dt.tzinfo:
                start_dt = timezone.make_aware(start_dt)
            if not end_dt.tzinfo:
                end_dt = timezone.make_aware(end_dt)
            post = post.filter(date_time__range=(start_dt, end_dt))

    calc = calculation_calculation(post)
    masters_chart = []
    for master in calc["masters"]:
        masters_chart.append({
            "name": master["name"],
            "income": master["income"],
            "sum_income": master["sum_income"]
        })

    # Передаем в шаблон
    return render(request, "blog/calculation_products.html", {
        "masters_chart": masters_chart
    })








from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Coalesce, TruncDate
from .models import Deal

def calculation_products_view(request):
    """
    Отображение страницы с выбором товаров/услуг.
    """
    product_names_qs = Deal.objects.values_list(
        Coalesce('service__name', 'services__name', Value('не определено')), flat=True
    ).distinct()[:48]
    product_names = list(product_names_qs)

    return render(request, "blog/calculation_products.html", {
        "product_names": product_names
    })


@require_POST
def aggregate_products_api(request):
    """
    Возвращает JSON с количеством покупок по дате для выбранных товаров.
    """
    start = request.POST.get("start")
    end = request.POST.get("end")
    products = request.POST.getlist("products[]") or request.POST.getlist("products")

    if not (start and end and products):
        return HttpResponseBadRequest("Укажите start, end и products")

    def parse_local(dt_str):
        dt = parse_datetime(dt_str)
        if dt is None:
            dt = parse_datetime(dt_str.replace("T", " "))
        return dt

    start_dt = parse_local(start)
    end_dt = parse_local(end)
    if not start_dt or not end_dt:
        return HttpResponseBadRequest("Неправильный формат даты")

    if not start_dt.tzinfo:
        start_dt = timezone.make_aware(start_dt)
    if not end_dt.tzinfo:
        end_dt = timezone.make_aware(end_dt)

    qs = Deal.objects.filter(date_time__range=(start_dt, end_dt))

    # Фильтруем по выбранным товарам
    q_filter = Q(service__name__in=products) | Q(services__name__in=products)
    qs = qs.filter(q_filter)

    annotated = qs.annotate(
        product_name=Coalesce(F('service__name'), F('services__name'), Value('не определено')),
        day=TruncDate('date_time')
    ).values('product_name', 'day').annotate(cnt=Count('id')).order_by('product_name', 'day')

    result = {}
    for row in annotated:
        name = row['product_name']
        day = row['day'].isoformat()
        cnt = row['cnt']
        result.setdefault(name, []).append({"date": day, "count": cnt})

    # пустые списки для выбранных товаров без сделок
    for p in products:
        result.setdefault(p, [])

    return JsonResponse(result)




from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Coalesce, TruncDate
from .models import Deal, Personal, Services, Service

def calculation_user_product_view(request):
    """
    Страница выбора сотрудников и товаров/услуг.
    """
    # Получаем список сотрудников
    personal_list = Personal.objects.all().values_list('name', flat=True)

    # Получаем список товаров/услуг из сделок
    product_names_qs = Deal.objects.values_list(
        Coalesce('service__name', 'services__name', Value('не определено')), flat=True
    ).distinct()[:48]
    product_names = list(product_names_qs)

    return render(request, "blog/analysis_service.html", {
        "product_names": product_names,
        "personal_list": personal_list
    })


@require_POST
def aggregate_user_product_api(request):
    """
    Возвращает JSON с количеством покупок по дате для выбранных пользователей и товаров.
    """
    start = request.POST.get("start")
    end = request.POST.get("end")
    users = request.POST.getlist("users[]") or request.POST.getlist("users")
    products = request.POST.getlist("products[]") or request.POST.getlist("products")

    if not (start and end and users and products):
        return HttpResponseBadRequest("Укажите start, end, users и products")

    def parse_local(dt_str):
        dt = parse_datetime(dt_str)
        if dt is None:
            dt = parse_datetime(dt_str.replace("T"," "))
        return dt

    start_dt = parse_local(start)
    end_dt = parse_local(end)
    if not start_dt or not end_dt:
        return HttpResponseBadRequest("Неправильный формат даты")

    if not start_dt.tzinfo:
        start_dt = timezone.make_aware(start_dt)
    if not end_dt.tzinfo:
        end_dt = timezone.make_aware(end_dt)

    qs = Deal.objects.filter(date_time__range=(start_dt, end_dt))

    # фильтруем по выбранным пользователям
    qs = qs.filter(personal__name__in=users)

    # фильтруем по выбранным товарам/услугам
    q_filter = Q(service__name__in=products) | Q(services__name__in=products)
    qs = qs.filter(q_filter)

    annotated = qs.annotate(
        product_name=Coalesce(F('service__name'), F('services__name'), Value('не определено')),
        user_name=F('personal__name'),
        day=TruncDate('date_time')
    ).values('user_name','product_name','day').annotate(cnt=Count('id')).order_by('user_name','product_name','day')

    result = {}
    for row in annotated:
        user = row['user_name']
        product = row['product_name']
        day = row['day'].isoformat()
        cnt = row['cnt']
        result.setdefault(user, {}).setdefault(product, []).append({"date": day, "count": cnt})

    # пустые списки для выбранных пользователей и товаров без сделок
    for u in users:
        result.setdefault(u,{})
        for p in products:
            result[u].setdefault(p,[])

    return JsonResponse(result)



from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count
from .models import Deal, Personal

def analysis_view(request):
    """Страница с формой и графиком"""
    personals = Personal.objects.all()
    return render(request, "blog/analysis.html", {"personals": personals})


@require_POST
def analysis_api(request):
    """API для анализа услуг сотрудника"""
    start = request.POST.get("start")
    end = request.POST.get("end")
    personal_id = request.POST.get("personal")

    if not start or not end or not personal_id:
        return JsonResponse({"error": "Укажите все параметры"}, status=400)

    try:
        personal = Personal.objects.get(id=personal_id)
    except Personal.DoesNotExist:
        return JsonResponse({"error": "Сотрудник не найден"}, status=404)

    # Фильтруем сделки
    deals = Deal.objects.filter(
        personal=personal,
        date_time__date__gte=start,
        date_time__date__lte=end
    )

    # Группируем по услугам
    stats = deals.values("service__name").annotate(total=Count("id")).order_by("-total")

    # JSON для фронта
    data = {
        "personal": personal.name,
        "services": [{"name": s["service__name"] or "не определено", "count": s["total"]} for s in stats],
    }
    return JsonResponse(data)


from django.db.models import Count
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.http import JsonResponse
from .models import Deal, Service, Personal


def analysis_product_view(request):
    """Страница анализа по товарам/услугам"""
    services = Service.objects.all()
    personals = Personal.objects.all()
    return render(request, "blog/analysis_product.html", {
        "services": services,
        "personals": personals
    })


@require_POST
def analysis_product_api(request):
    """API анализа: сколько раз продавали товар/услугу"""
    start = request.POST.get("start")
    end = request.POST.get("end")
    personal_id = request.POST.get("personal")

    if not start or not end:
        return JsonResponse({"error": "Укажите даты"}, status=400)

    deals = Deal.objects.filter(
        date_time__date__gte=start,
        date_time__date__lte=end
    )

    if personal_id:
        deals = deals.filter(personal_id=personal_id)

    # группируем по товару/услуге
    stats = deals.values("service__name").annotate(total=Count("id")).order_by("-total")

    data = {
        "items": [{"name": s["service__name"] or "Без названия", "count": s["total"]} for s in stats]
    }
    return JsonResponse(data)
