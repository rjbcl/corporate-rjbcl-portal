from rest_framework import serializers #type: ignore
from .models import GroupEndowment, GroupInformation


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