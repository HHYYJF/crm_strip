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


class ShiftCreateSerializer(serializers.Serializer):
    administrator_id = serializers.IntegerField(required=True)
    bartender_id = serializers.IntegerField(required=True)