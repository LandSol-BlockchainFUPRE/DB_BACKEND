# models.py for your Django Property Signing and Verification System

from django.db import models
from django.contrib.auth.models import AbstractUser # Or get_user_model if extending directly
from django.conf import settings
from django.utils import timezone
import uuid
from django.core.validators import RegexValidator
import subprocess
from django.contrib.auth.models import User
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
    fullname = models.CharField(max_length=200, blank=False,null=False,
                                help_text="Link to the Django built-in User model.")
    date_of_birth = models.DateField(
        null=True, blank=True,
        help_text="User's date of birth (e.g., YYYY-MM-DD)."
    )
    residential_address = models.TextField(
        help_text="User's full residential address."
    )

    id_number = models.CharField(
        max_length=100, unique=True,
        help_text="Number of the government-issued identification."
    )
    password = models.CharField(max_length=200,null=False,blank=False,
        help_text="Enter Your Auth Token"         
    )
    def __str__(self):
        return f"Profile for {self.fullname}"


from django.db.models.signals import pre_save
from django.dispatch import receiver
@receiver(pre_save, sender=UserProfile) # Replace YourModelName with the actual name of your model
def create_user_before_save(sender, instance, **kwargs):
    if not instance.pk: # If the primary key is not set, it's a new object
        username = instance.id_number # Get username from your model instance
        password = instance.password # Get password from your model instance
        
        # Your original code:
        user = User.objects.create_user(username=username, password=password)
        user.save()

class Property(models.Model):
    """
    Represents a physical property being transacted on the blockchain.
    """
    PROPERTY_TYPES = [
        ('land', 'Land'),
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
        UserProfile, on_delete=models.PROTECT, related_name='owned_properties',
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
    ipfs_hash = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="InterPlanetary File System Block ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.unique_property_identifier} - {self.full_address[:50]}..."
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the file first so it exists on disk

        if self.proof_of_ownership_document and not self.ipfs_hash:
            try:
                # Run IPFS add command
                result = subprocess.run(
                    ["ipfs", "add", self.proof_of_ownership_document.path],
                    capture_output=True, text=True, check=True
                )

                # Extract IPFS hash (usually first token in last line)
                ipfs_output = result.stdout.strip().splitlines()[-1]
                ipfs_hash = ipfs_output.split()[1]  # "added <hash> <filename>"

                self.ipfs_hash = ipfs_hash
                super().save(update_fields=["ipfs_hash"])  # Save hash without recursion

            except subprocess.CalledProcessError as e:
                # Optional: Log error or raise custom exception
                print("Error running IPFS add:", e.stderr)





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
        UserProfile, on_delete=models.SET_NULL, null=True,
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




# Define a custom validator for NIN (11 digits)
nin_validator = RegexValidator(
    regex=r'^\d{11}$',
    message='NIN must be exactly 11 digits.',
    code='invalid_nin'
)

class NINInfo(models.Model):
    nin = models.CharField(
        max_length=11,
        unique=True,
        validators=[nin_validator],
        help_text="The 11-digit National Identification Number."
    )
    first_name = models.CharField(
        max_length=100,
        help_text="The first name of the individual."
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="The middle name of the individual (optional)."
    )
    last_name = models.CharField(
        max_length=100,
        help_text="The last name of the individual."
    )
    date_of_birth = models.DateField(
        help_text="The date of birth of the individual."
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="The phone number associated with the NIN (optional)."
    )
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        help_text="The email address associated with the NIN (optional)."
    )
    date_registered = models.DateTimeField(
        default=timezone.now,
        help_text="The date and time when this NIN record was created."
    )

    class Meta:
        verbose_name = "NIN Information"
        verbose_name_plural = "NIN Information"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        """
        Returns a string representation of the NINInfo instance.
        """
        return f"{self.first_name} {self.last_name} ({self.nin})"