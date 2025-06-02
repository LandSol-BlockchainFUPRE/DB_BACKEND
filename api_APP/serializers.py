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
        model = UserProfile
        fields = [
            'fullname', 'date_of_birth',
            'residential_address', 'id_number',"password"
        ]
        # Add other fields as needed, e.g., is_staff, is_active


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            'fullname', 'date_of_birth',
            'residential_address','id_number',"password"
        ]


# your_app/serializers.py

from django.contrib.auth import get_user_model # Or your UserProfile model path
# Assuming UserProfile is your custom user model. If it's the default User, use User.
# from .models import UserProfile # Or wherever your UserProfile is

# If UserProfile is the same as settings.AUTH_USER_MODEL:
#UserProfile = get_user_model()


class PropertySerializer(serializers.ModelSerializer):
    """
    Serializer for the Property model.
    """
    # For displaying owner details (read-only):
    current_owner_details = UserSerializer(source='current_owner', read_only=True)

    # For accepting the owner ID on create/update (writeable):
    # DRF will automatically treat this as a PrimaryKeyRelatedField
    # if 'current_owner' is in the 'fields' list and not explicitly defined otherwise.
    # You could also be explicit:
    # current_owner = serializers.PrimaryKeyRelatedField(queryset=UserProfile.objects.all())

    proof_of_ownership_document = serializers.FileField(required=False, allow_null=True, use_url=True) # use_url=True is good for GET

    class Meta:
        model = Property
        fields = [
            'id', 'full_address', 'property_type', 'unique_property_identifier',
            'description',
            'current_owner',  # <--- ADD THIS FOR WRITING (expects UserProfile ID)
            'current_owner_details', # <--- This is for GET requests (read-only)
            'proof_of_ownership_document', 'gps_latitude', 'gps_longitude',
            'survey_plan_hash','ipfs_hash', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'ipfs_hash') # ipfs_hash is set by the model's save method
        # If you made current_owner explicit with PrimaryKeyRelatedField, you don't need it in extra_kwargs
        # extra_kwargs = {
        #     'current_owner': {'write_only': True} # If you ONLY want to accept ID and not show it in GET
        # }


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




class NINInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NINInfo
        # Specify all fields from the NINInfo model to be included in the serializer.
        # Alternatively, you could use `fields = '__all__'` to include all fields.
        fields = [
            'id', # Django's default primary key, useful for API operations
            'nin',
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'phone_number',
            'email',
            'date_registered',
        ]
        # You can add extra_kwargs for specific field options, e.g., read_only, write_only
        extra_kwargs = {
            'date_registered': {'read_only': True}, # date_registered should generally not be set by the client
        }











# ../serializers.py (or your app's serializers.py)



User = get_user_model()

class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text="User's username")
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, help_text="User's password")
    # No model needed as it's not a ModelSerializer

class TokenUserResponseSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True, help_text="Authentication token")
    user_id = serializers.IntegerField(read_only=True, help_text="User's unique ID")
    username = serializers.CharField(read_only=True, help_text="User's username")
    # email = serializers.EmailField(read_only=True, source='user.email') # If you want to include email

class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_null=True, help_text="A success or informational message.")
    detail = serializers.CharField(required=False, allow_null=True, help_text="A detailed message, often used by DRF for errors.")
    error = serializers.CharField(required=False, allow_null=True, help_text="An error message.")

    # This helps drf-yasg understand that not all fields are always present.
    # For actual serialization, you'd ensure only relevant fields are populated.
    # For Swagger, it will list all as optional.

class ProtectedDataSerializer(serializers.Serializer):
    user = serializers.CharField(help_text="Username of the authenticated user.")
    message = serializers.CharField(help_text="A message indicating successful access to protected content.")