from rest_framework import serializers #type: ignore
from .models import GroupEndowment, GroupInformation
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer #type: ignore
from django.contrib.auth import authenticate #type: ignore


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
            # Basic group information
            'group_id',
            'group_name',
            'group_name_nepali',
            'is_active',
            
            # Aggregated statistics
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
    Serializer for GroupEndowment model (tblGroupEndowment table).
    Represents individual policies under group insurance.
    """
    
    class Meta:
        model = GroupEndowment
        fields = '__all__'  # Include all fields