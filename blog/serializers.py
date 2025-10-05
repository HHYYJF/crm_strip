from rest_framework import serializers
from .models import Deal, Personal, Services, Service, Payment, Whom, Role, Shift


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class ShiftCreateSerializer(serializers.Serializer):
    admin_id = serializers.IntegerField()
    barman_id = serializers.IntegerField()

    def validate(self, data):
        if data['admin_id'] == data['barman_id']:
            raise serializers.ValidationError("Админ и бармен должны быть разными людьми")
        return data

class PersonalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personal
        fields = ['id', 'name', 'role']



class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'params_one', 'params_two', 'params_fre', 'maney']

class PersonalSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source='role', allow_null=True, write_only=True)

    class Meta:
        model = Personal
        fields = ['id', 'name', 'role', 'role_id']

class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ['id', 'name']

class ServiceSerializer(serializers.ModelSerializer):
    service = ServicesSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Services.objects.all(), source='service', allow_null=True, write_only=True)

    class Meta:
        model = Service
        fields = ['id', 'name', 'service', 'service_id']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'name']

class WhomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Whom
        fields = ['id', 'name']

class ShiftSerializer(serializers.ModelSerializer):
    admin = PersonalSerializer(read_only=True)
    admin_id = serializers.PrimaryKeyRelatedField(queryset=Personal.objects.all(), source='admin', allow_null=True, write_only=True)
    barman = PersonalSerializer(read_only=True)
    barman_id = serializers.PrimaryKeyRelatedField(queryset=Personal.objects.all(), source='barman', allow_null=True, write_only=True)

    class Meta:
        model = Shift
        fields = ['id', 'admin', 'admin_id', 'barman', 'barman_id', 'start_time', 'end_time', 'is_active']

class DealSerializer(serializers.ModelSerializer):
    personal = PersonalSerializer(read_only=True)
    personal_id = serializers.PrimaryKeyRelatedField(queryset=Personal.objects.all(), source='personal', allow_null=True, write_only=True)
    services = ServicesSerializer(read_only=True)
    services_id = serializers.PrimaryKeyRelatedField(queryset=Services.objects.all(), source='services', allow_null=True, write_only=True)
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), source='service', allow_null=True, write_only=True)
    payment = PaymentSerializer(read_only=True)
    payment_id = serializers.PrimaryKeyRelatedField(queryset=Payment.objects.all(), source='payment', allow_null=True, write_only=True)
    whom = WhomSerializer(read_only=True)
    whom_id = serializers.PrimaryKeyRelatedField(queryset=Whom.objects.all(), source='whom', allow_null=True, write_only=True)

    class Meta:
        model = Deal
        fields = [
            'id',
            'personal', 'personal_id',
            'services', 'services_id',
            'service', 'service_id',
            'payment', 'payment_id',
            'whom', 'whom_id',
            'maney',
            'date_time',
            'ais'
        ]
