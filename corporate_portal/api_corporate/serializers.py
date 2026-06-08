from rest_framework import serializers  # type: ignore
from .models import GroupEndowment, GroupInformation


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