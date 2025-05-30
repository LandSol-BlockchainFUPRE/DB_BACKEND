# models.py for your Django Property Signing and Verification System

from django.db import models
from django.contrib.auth.models import AbstractUser # Or get_user_model if extending directly
from django.conf import settings
from django.utils import timezone
import uuid

# If you're using a custom User model, you might extend AbstractUser directly.
# For simplicity and common practice, we'll assume Django's built-in User
# and create a UserProfile to extend it.
# from django.contrib.auth import get_user_model
# User = get_user_model()

class UserProfile(models.Model):
    """
    Extends Django's built-in User model to store additional personal and
    identification data for property system users.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                primary_key=True,
                                help_text="Link to the Django built-in User model.")
    date_of_birth = models.DateField(
        null=True, blank=True,
        help_text="User's date of birth (e.g., YYYY-MM-DD)."
    )
    nationality = models.CharField(
        max_length=100,
        help_text="User's nationality."
    )
    residential_address = models.TextField(
        help_text="User's full residential address."
    )
    phone_number = models.CharField(
        max_length=20, unique=True,
        help_text="User's phone number, must be unique."
    )
    tax_identification_number = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        help_text="User's Tax Identification Number (TIN) or equivalent."
    )
    id_type = models.CharField(
        max_length=50,
        choices=[
            ('passport', 'Passport'),
            ('national_id', 'National ID Card'),
            ('driver_license', 'Driver\'s License'),
            ('other', 'Other')
        ],
        help_text="Type of government-issued identification."
    )
    id_number = models.CharField(
        max_length=100, unique=True,
        help_text="Number of the government-issued identification."
    )
    id_issuing_authority = models.CharField(
        max_length=200,
        help_text="Authority that issued the identification."
    )
    id_issue_date = models.DateField(
        help_text="Date the identification was issued."
    )
    id_expiry_date = models.DateField(
        null=True, blank=True,
        help_text="Date the identification expires (if applicable)."
    )
    # Storing path to scanned ID copies. Actual files should be in a secure storage.
    # For a real system, consider a dedicated file storage solution (e.g., S3, Google Cloud Storage)
    # and store only references/hashes here.
    scanned_id_front = models.FileField(
        upload_to='user_ids/front/', null=True, blank=True,
        help_text="Scanned copy of the front of the ID."
    )
    scanned_id_back = models.FileField(
        upload_to='user_ids/back/', null=True, blank=True,
        help_text="Scanned copy of the back of the ID."
    )
    # Biometric data references (e.g., hash of biometric template)
    # Actual biometric data should never be stored directly in a database.
    biometric_hash = models.CharField(
        max_length=255, null=True, blank=True, unique=True,
        help_text="Cryptographic hash of user's biometric template (e.g., facial or fingerprint)."
    )
    # Blockchain wallet address for the user
    blockchain_wallet_address = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="User's public blockchain wallet address."
    )

    def __str__(self):
        return f"Profile for {self.user.get_full_name() or self.user.username}"

class Property(models.Model):
    """
    Represents a physical property being transacted on the blockchain.
    """
    PROPERTY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('land', 'Land'),
        ('apartment', 'Apartment'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_address = models.TextField(
        help_text="Full physical address of the property."
    )
    property_type = models.CharField(
        max_length=50, choices=PROPERTY_TYPES,
        help_text="Type of property (e.g., residential, commercial)."
    )
    unique_property_identifier = models.CharField(
        max_length=255, unique=True,
        help_text="Unique identifier for the property (e.g., Land Title Number, Cadastral Number)."
    )
    description = models.TextField(
        null=True, blank=True,
        help_text="Detailed description of the property (e.g., number of rooms, size)."
    )
    current_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_properties',
        help_text="The current legal owner of the property."
    )
    # Reference to proof of ownership document (e.g., scanned title deed)
    proof_of_ownership_document = models.FileField(
        upload_to='property_documents/proof_of_ownership/', null=True, blank=True,
        help_text="Scanned copy or reference to the current title deed/certificate of occupancy."
    )
    # Geospatial data (optional)
    gps_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Latitude coordinate of the property."
    )
    gps_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Longitude coordinate of the property."
    )
    # Hash of the property's legal survey plan, stored off-chain
    survey_plan_hash = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Cryptographic hash of the property's survey plan."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.unique_property_identifier} - {self.full_address[:50]}..."

class Document(models.Model):
    """
    Represents a legal document related to a property transaction (e.g., Sale Agreement, Deed of Assignment).
    """
    DOCUMENT_TYPES = [
        ('sale_agreement', 'Sale Agreement'),
        ('deed_of_assignment', 'Deed of Assignment'),
        ('power_of_attorney', 'Power of Attorney'),
        ('title_deed', 'Title Deed'),
        ('certificate_of_occupancy', 'Certificate of Occupancy'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='documents',
        help_text="The property this document pertains to."
    )
    document_type = models.CharField(
        max_length=100, choices=DOCUMENT_TYPES,
        help_text="Type of legal document."
    )
    # Path to the actual document file. For security and blockchain integration,
    # consider storing only the hash of the document on-chain, and the file off-chain.
    document_file = models.FileField(
        upload_to='legal_documents/',
        help_text="The actual legal document file (e.g., PDF)."
    )
    # Hash of the document content, which will be used for blockchain verification
    document_hash = models.CharField(
        max_length=255, unique=True,
        help_text="SHA-256 hash of the document content for blockchain integrity."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        help_text="User who uploaded this document."
    )
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for {self.property.unique_property_identifier}"

class Transaction(models.Model):
    """
    Represents a property transaction (e.g., sale, transfer) that involves signing and verification.
    """
    TRANSACTION_STATUSES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('signed', 'Signed'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Property, on_delete=models.PROTECT, related_name='transactions',
        help_text="The property involved in this transaction."
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='selling_transactions',
        help_text="The user selling the property."
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='buying_transactions',
        help_text="The user buying the property."
    )
    transaction_price = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="The agreed-upon price for the transaction."
    )
    transaction_date = models.DateField(
        default=timezone.now,
        help_text="The date the transaction is initiated or agreed upon."
    )
    status = models.CharField(
        max_length=50, choices=TRANSACTION_STATUSES, default='pending',
        help_text="Current status of the transaction."
    )
    # This will be the hash of the entire transaction data recorded on the blockchain
    blockchain_transaction_hash = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="The hash of this transaction as recorded on the blockchain."
    )
    # Block number where this transaction was recorded on the blockchain
    blockchain_block_number = models.BigIntegerField(
        null=True, blank=True,
        help_text="The block number on the blockchain where this transaction was confirmed."
    )
    # Timestamp from the blockchain when the transaction was confirmed
    blockchain_timestamp = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp from the blockchain when the transaction was confirmed."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction {self.id} for {self.property.unique_property_identifier}"

class DigitalSignature(models.Model):
    """
    Records a digital signature event for a specific document within a transaction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='signatures',
        help_text="The document that was signed."
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='signatures',
        help_text="The user who provided the digital signature."
    )
    # The actual digital signature string (e.g., cryptographic signature)
    signature_value = models.TextField(
        help_text="The actual digital signature string generated by the signer's private key."
    )
    # Public key used for verification
    signer_public_key = models.CharField(
        max_length=255,
        help_text="The public key of the signer used to verify the signature."
    )
    signed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the document was digitally signed."
    )
    # Hash of the document at the time of signing (should match Document.document_hash)
    document_hash_at_signing = models.CharField(
        max_length=255,
        help_text="The hash of the document content at the moment of signing."
    )
    # Optional: Reference to the blockchain transaction where this signature might be recorded
    blockchain_signature_hash = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="Optional: Hash of the blockchain transaction confirming this signature."
    )

    def __str__(self):
        return f"Signature by {self.signer.username} on {self.document.document_type} at {self.signed_at}"

    class Meta:
        # Ensures a user can't sign the same document multiple times with the same signature value
        # (though typically a new signature would be generated for each signing event if content changes)
        unique_together = ('document', 'signer', 'signature_value')
