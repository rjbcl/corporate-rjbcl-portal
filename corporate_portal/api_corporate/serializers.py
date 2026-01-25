from rest_framework import serializers #type: ignore
from .models import GroupEndowment, GroupInformation
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer to add user type and company info to the token.
    """
    username_field = 'username'
    
    def validate(self, attrs):
        # Authenticate user
        username = attrs.get('username')
        password = attrs.get('password')
        
        # Debug logging
        print(f"Attempting to authenticate: {username}")
        
        # Try to authenticate
        user = authenticate(username=username, password=password)
        
        if user is None:
            print(f"Authentication failed for: {username}")
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.is_active:
            print(f"User is inactive: {username}")
            raise serializers.ValidationError('User account is disabled')
        
        print(f"User authenticated successfully: {username}")
        
        # Store user for later use
        self.user = user
        
        # Get the token using parent class
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        # Add custom claims
        user_type = user.get_user_type()
        
        data['user_type'] = user_type
        data['username'] = user.username
        
        # Add company-specific data
        if user_type == 'company':
            company = user.company_profile
            data['company_id'] = company.company_id
            data['company_name'] = company.company_name
            data['is_active'] = company.isactive
        
        # Add individual-specific data
        elif user_type == 'individual':
            individual = user.individual_profile
            data['user_id'] = individual.user_id
            data['user_full_name'] = individual.user_full_name
            data['group_id'] = individual.group_id.group_id if individual.group_id else None
        
        return data
    
class GroupInformationSerializer(serializers.ModelSerializer):
    """
    Serializer for GroupInformation model (tblGroupInformation table).
    """
    
    class Meta:
        model = GroupInformation
        fields = [
            'row_id',
            'group_name',
            'group_name_nepali',
            'discount_rate',
            'fiscal_year',
            'short_name',
            'master_policy_no',
            'group_id',
            'created_by',
            'created_date',
            'is_active',
            'group_type',
            'account_number',
            'p_seq',
            'g_seq',
            'modified_by',
            'modified_date',
            'r_seq',
            'plan_id',
            'adb_discount_rate',
            'retirement_age',
            'min_age',
            'max_age',
            'min_term',
            'max_term',
            'rebate',
            'p2_seq',
            'doc',
            'g_loan',
            's_policy',
            'adb_amount',
            'extra_premium',
            'mode',
            'remarks',
            'adb_rate',
            'extra_load',
            'is_adb',
        ]
        read_only_fields = fields  # All fields are read-only

class GroupEndowmentSerializer(serializers.ModelSerializer):
    """
    Serializer for GroupEndowment model (tblGroupEndowment table).
    Represents individual policies under group insurance.
    """
    
    class Meta:
        model = GroupEndowment
        fields = '__all__'  # Include all fields