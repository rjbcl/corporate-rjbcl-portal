from rest_framework import serializers  # type: ignore
from .models import GroupEndowment, GroupInformation
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer  # type: ignore
from django.contrib.auth import authenticate  # type: ignore


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that adds user type and company info to the token.
    Only company users can obtain tokens via this serializer.
    """
    username_field = 'username'

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError('Invalid credentials')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')

        self.user = user

        refresh = self.get_token(user)

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        user_type = user.get_user_type()
        data['user_type'] = user_type
        data['username'] = user.username

        if user_type == 'company':
            company = user.company_profile.company
            data['company_id'] = company.company_id
            data['company_name'] = company.company_name
            data['is_active'] = company.isactive

        return data


class GroupInformationSerializer(serializers.ModelSerializer):
    """
    Serializer for GroupInformation model (view_copo_groupInformation).
    """

    class Meta:
        model = GroupInformation
        fields = [
            'group_id',
            'group_name',
            'group_name_nepali',
            'is_active',
            'total_members_count',
            'total_active_policies',
            'total_premium',
            'total_sa',
            'death_claim',
            'surrender_claim',
            'maturity_claim',
            'transfer_claim',
            'terminate_claim',
            'cancel_claim',
        ]
        read_only_fields = fields


class GroupEndowmentSerializer(serializers.ModelSerializer):
    """
    Serializer for GroupEndowment model (tblGroupEndowment).
    Represents individual policies under group insurance.
    """

    class Meta:
        model = GroupEndowment
        fields = '__all__'