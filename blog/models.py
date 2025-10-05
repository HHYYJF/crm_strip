from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=64, verbose_name="Роль сотрудника")
    params_one = models.BooleanField(default=False, verbose_name="Доход с услуг")
    params_two = models.BooleanField(default=False, verbose_name="Доход с товара")
    params_fre = models.BooleanField(default=False, verbose_name="Учитывание в истории")
    maney = models.PositiveSmallIntegerField(default=0, verbose_name="% с дохода")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

class Personal(models.Model):
    name = models.CharField(max_length=64, verbose_name="Имя сотрудника")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Роль сотрудника")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

class Services(models.Model):
    name = models.CharField(max_length=64, verbose_name="Вид - товар/услуга/спец услуга")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Вид"
        verbose_name_plural = "Виды"

class Service(models.Model):
    name = models.CharField(max_length=64, verbose_name="Вид услуги/товара")
    service = models.ForeignKey(Services, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид услуги/товара")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"

class Payment(models.Model):
    name = models.CharField(max_length=64, verbose_name="Вид оплаты")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Вид оплаты"
        verbose_name_plural = "Виды оплаты"

class Whom(models.Model):
    name = models.CharField(max_length=64, verbose_name="Кому оказывалась услуга")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Кому оказана услуга"
        verbose_name_plural = "Кому оказана услуга"

class Deal(models.Model):
    personal = models.ForeignKey(Personal, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Исполнитель")
    services = models.ForeignKey(Services, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид")
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Вид услуги/товара"
    )
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Вид оплаты")
    whom = models.ForeignKey(Whom, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Кому оказывалась услуга")
    maney = models.PositiveSmallIntegerField(default=0, verbose_name="Оплата")
    date_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")
    ais = models.BooleanField(default=True,verbose_name="Закрыты/открыты записи")

    def __str__(self):
        return f"#{self.id} {self.personal} {self.service}"

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"

class Shift(models.Model):
    admin = models.ForeignKey("Personal", on_delete=models.SET_NULL, null=True, related_name="shifts_as_admin", verbose_name="Администратор")
    barman = models.ForeignKey("Personal",  on_delete=models.SET_NULL, null=True, related_name="shifts_as_barman",verbose_name="Бармен")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Начало смены")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Окончание смены")
    is_active = models.BooleanField(default=True, verbose_name="Активная смена")
    def __str__(self):
        return f"Смена #{self.id}: {self.admin} и {self.barman} ({'активна' if self.is_active else 'закрыта'})"
    class Meta:
        verbose_name = "Смена"
        verbose_name_plural = "Смены"


