from datetime import datetime

from django.db import models



class Services(models.Model):
    is_tovar = models.BooleanField(default=False, verbose_name="Товар")
    is_uslyga = models.BooleanField(default=False, verbose_name="Услуга")

    class Meta:
        verbose_name = "Вид"
        verbose_name_plural = "Виды"

    def __str__(self):
        return "товар" if self.is_tovar else "услуга"


class Role(models.Model):
    name = models.CharField(max_length=64, verbose_name="Роль сотрудника")
    maney_d = models.PositiveSmallIntegerField(default=0, verbose_name="Доход за продление смены")
    maney_null = models.PositiveSmallIntegerField(default=0, verbose_name="Цена за пустую смену")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"


class Personal(models.Model):
    name = models.CharField(max_length=64, verbose_name="Имя сотрудника")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Роль сотрудника")

    def __str__(self):
        return f'{self.name} , {self.role.name}'

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


class Service(models.Model):
    name = models.CharField(max_length=64, verbose_name="название")
    role = models.ForeignKey(Services, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид")
    percent_admin = models.PositiveSmallIntegerField(default=0, verbose_name="% админу за чью то услугу 5%")
    percent_barmen = models.PositiveSmallIntegerField(default=0, verbose_name="% бармену чей то товар 5%")
    percent_admin_ysluga = models.PositiveSmallIntegerField(default=0, verbose_name="% админу за услугу 50% ")
    percent_barmen_ysluga = models.PositiveSmallIntegerField(default=0, verbose_name="% бармену за услугу 50% ")
    percent_barmen_tanes = models.PositiveSmallIntegerField(default=0, verbose_name="% танцовщице 50% ")
    percent_barmen_admin = models.PositiveSmallIntegerField(default=0, verbose_name="фикса за продажу 1000 ")
    percent_smol = models.PositiveSmallIntegerField(default=0, verbose_name="спец процент")


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"

class Whom(models.Model):
    name = models.CharField(max_length=64, verbose_name="Кому оказывалась услуга")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Кому оказана услуга"
        verbose_name_plural = "Кому оказана услуга"

class Payment(models.Model):
    name = models.CharField(max_length=64, verbose_name="Вид оплаты")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Вид оплаты"
        verbose_name_plural = "Виды оплаты"

class Deal(models.Model):
    personal = models.ForeignKey(Personal, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Исполнитель")
    services = models.ForeignKey(Services, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид")
    service = models.ForeignKey(Service,on_delete=models.CASCADE, blank=True,null=True,verbose_name="Вид услуги/товара")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид оплаты")
    whom = models.ForeignKey(Whom, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Кому оказывалась услуга")
    maney = models.PositiveSmallIntegerField(default=0, verbose_name="Оплата")
    date_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")
    ais = models.BooleanField(default=True,verbose_name="Закрыты/открыты записи") # понимание что сегодня отоброжать

    def __str__(self):
        return f"#{self.id} {self.personal} {self.service} {self.ais}"

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"

class Shift(models.Model):
    admin = models.ForeignKey(Personal, on_delete=models.SET_NULL, null=True, related_name="shifts_as_admin", verbose_name="Администратор")
    barman = models.ForeignKey(Personal,  on_delete=models.SET_NULL, null=True, related_name="shifts_as_barman",verbose_name="Бармен")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Начало смены")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Окончание смены")
    is_active = models.BooleanField(default=True, verbose_name="Активная")
    def __str__(self):
        return f"Смена #{self.id}: {self.admin} и {self.barman} ({'активна' if self.is_active else 'закрыта'})"
    class Meta:
        verbose_name = "Смена"
        verbose_name_plural = "Смены"
