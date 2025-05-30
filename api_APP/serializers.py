from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth import authenticate



from django.contrib.auth import get_user_model
from django.conf import settings # To reference settings.AUTH_USER_MODEL if needed directly

from .models import UserProfile, Property, Document, Transaction, DigitalSignature

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        # Add other fields as needed, e.g., is_staff, is_active


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    """
    # 'user' field is the OneToOneField and primary_key, so it will represent the user_id.
    # For displaying user details:
    user_details = UserSerializer(source='user', read_only=True)

    # Make FileFields optional if they are blank=True, null=True in the model
    scanned_id_front = serializers.FileField(required=False, allow_null=True)
    scanned_id_back = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'user_details', 'date_of_birth', 'nationality',
            'residential_address', 'phone_number', 'tax_identification_number',
            'id_type', 'id_number', 'id_issuing_authority', 'id_issue_date',
            'id_expiry_date', 'scanned_id_front', 'scanned_id_back',
            'biometric_hash', 'blockchain_wallet_address'
        ]
        # The 'user' field is the primary key of UserProfile and references User.id
        # It's writable on creation (to link to an existing User).
        # If UserProfile is created via a signal from User creation, this might be handled differently.


class PropertySerializer(serializers.ModelSerializer):
    """
    Serializer for the Property model.
    """
    # 'current_owner' will be the ID for write operations.
    # For displaying owner details:
    current_owner_details = UserSerializer(source='current_owner', read_only=True)

    # Make FileField optional
    proof_of_ownership_document = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Property
        fields = [
            'id', 'full_address', 'property_type', 'unique_property_identifier',
            'description', 'current_owner', 'current_owner_details',
            'proof_of_ownership_document', 'gps_latitude', 'gps_longitude',
            'survey_plan_hash', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Document model.
    """
    # 'property' will be the ID for write operations.
    property_details = PropertySerializer(source='property', read_only=True) # Optional: for rich display

    # 'uploaded_by' will be the ID for write operations.
    # It allows null as per model.
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True, allow_null=True)

    class Meta:
        model = Document
        fields = [
            'id', 'property', 'property_details', 'document_type', 'document_file',
            'document_hash', 'uploaded_by', 'uploaded_by_details', 'upload_date'
        ]
        read_only_fields = ('id', 'upload_date')
        # 'uploaded_by' can be null, so ensure it's not required if not set during creation
        extra_kwargs = {
            'uploaded_by': {'required': False, 'allow_null': True}
        }


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Transaction model.
    """
    # 'property', 'seller', 'buyer' will be IDs for write operations.
    property_details = PropertySerializer(source='property', read_only=True) # Optional
    seller_details = UserSerializer(source='seller', read_only=True)
    buyer_details = UserSerializer(source='buyer', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'property', 'property_details', 'seller', 'seller_details',
            'buyer', 'buyer_details', 'transaction_price', 'transaction_date',
            'status', 'blockchain_transaction_hash', 'blockchain_block_number',
            'blockchain_timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class DigitalSignatureSerializer(serializers.ModelSerializer):
    """
    Serializer for the DigitalSignature model.
    """
    # 'document', 'signer' will be IDs for write operations.
    document_details = DocumentSerializer(source='document', read_only=True) # Optional
    signer_details = UserSerializer(source='signer', read_only=True)

    class Meta:
        model = DigitalSignature
        fields = [
            'id', 'document', 'document_details', 'signer', 'signer_details',
            'signature_value', 'signer_public_key', 'signed_at',
            'document_hash_at_signing', 'blockchain_signature_hash'
        ]
        read_only_fields = ('id', 'signed_at')


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    Requires 'username' (or 'email') and 'password'.
    """
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Custom validation to ensure either username or email is provided,
        but not both, and that password is present.
        """
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not (username or email):
            raise serializers.ValidationError(
                "Either username or email must be provided."
            )
        if username and email:
            raise serializers.ValidationError(
                "Cannot provide both username and email. Please use one."
            )
        if not password:
            raise serializers.ValidationError(
                "Password is required."
            )
        return data

