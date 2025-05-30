from django.shortcuts import render
from rest_framework.response import Response
from ..models import *

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt


from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny # AllowAny for public endpoints
from rest_framework.parsers import MultiPartParser, FormParser # For file uploads


from rest_framework.authtoken.models import Token
import smtplib, ssl
from email.mime.text import MIMEText
from django.http import HttpResponseBadRequest, JsonResponse
from email.mime.multipart import MIMEMultipart

from ..serializers import *


User = get_user_model()

# --- Common OpenAPI Responses (optional, for consistency) ---
RESPONSE_400_BAD_REQUEST = openapi.Response(description="Bad Request - Invalid data provided")
RESPONSE_401_UNAUTHORIZED = openapi.Response(description="Unauthorized - Authentication credentials were not provided or are invalid")
RESPONSE_403_FORBIDDEN = openapi.Response(description="Forbidden - You do not have permission to perform this action")
RESPONSE_404_NOT_FOUND = openapi.Response(description="Resource not found")




# --- DigitalSignature Views ---

@swagger_auto_schema(
    method='get',
    operation_id='list_digital_signatures',
    operation_description="Retrieve a list of all digital signatures. Can be filtered by 'document_id'.",
    tags=['Digital Signatures'],
    manual_parameters=[
        openapi.Parameter('document_id', openapi.IN_QUERY, description="Filter signatures by Document UUID", type=openapi.TYPE_STRING),
    ],
    responses={200: DigitalSignatureSerializer(many=True), 401: RESPONSE_401_UNAUTHORIZED}
)
@swagger_auto_schema(
    method='post',
    operation_id='create_digital_signature',
    operation_description="Create a new digital signature for a document. 'signer' is set automatically. 'document_hash_at_signing' must match document's current hash.",
    tags=['Digital Signatures'],
    request_body=DigitalSignatureSerializer, # signer will be ignored from request and set to request.user
    responses={
        201: DigitalSignatureSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def digital_signature_list_create(request):
    """
    List all digital signatures or create a new one.
    'signer' is automatically set to the authenticated user on creation.
    """
    if request.method == 'GET':
        signatures = DigitalSignature.objects.all()
        document_id = request.query_params.get('document_id')
        if document_id:
            signatures = signatures.filter(document_id=document_id)
        serializer = DigitalSignatureSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = DigitalSignatureSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Validate document_hash_at_signing
            document_instance = serializer.validated_data.get('document')
            provided_hash = serializer.validated_data.get('document_hash_at_signing')
            if document_instance and provided_hash != document_instance.document_hash:
                return Response(
                    {'document_hash_at_signing': [f"Hash mismatch. Expected {document_instance.document_hash} for the document."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure user is not signing a document they already signed with the same content
            # (The model's unique_together already handles ('document', 'signer', 'signature_value'))
            # If business rule is one signature per user per document (regardless of value changes):
            # if DigitalSignature.objects.filter(document=document_instance, signer=request.user).exists():
            #     return Response(
            #         {'detail': 'You have already signed this version of the document.'},
            #         status=status.HTTP_400_BAD_REQUEST
            #     )

            serializer.save(signer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_digital_signature',
    operation_description="Retrieve a specific digital signature by its UUID.",
    tags=['Digital Signatures'],
    responses={
        200: DigitalSignatureSerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_digital_signature',
    operation_description="Updating digital signatures is generally disallowed or highly restricted. This endpoint might only allow updating non-critical fields like 'blockchain_signature_hash' by authorized users.",
    tags=['Digital Signatures'],
    request_body=DigitalSignatureSerializer,
    responses={
        # 200: DigitalSignatureSerializer, (If some updates are allowed)
        405: openapi.Response(description="Method Not Allowed - Signatures are immutable or this update path is not supported."),
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN,
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_digital_signature',
    operation_description="Deleting digital signatures is generally disallowed or highly restricted.",
    tags=['Digital Signatures'],
    responses={
        # 204: openapi.Response(description="Digital Signature deleted successfully"), (If allowed)
        405: openapi.Response(description="Method Not Allowed - Signatures cannot be deleted or this path is not supported."),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN,
        404: RESPONSE_404_NOT_FOUND
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def digital_signature_detail_update_delete(request, pk): # pk is DigitalSignature UUID
    """
    Retrieve, update or delete a digital signature instance.
    Updates and Deletes are typically restricted for digital signatures.
    """
    try:
        signature = DigitalSignature.objects.get(pk=pk)
    except DigitalSignature.DoesNotExist:
        return Response({'detail': 'Digital Signature not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Signatures are generally immutable.
    if request.method == 'GET':
        serializer = DigitalSignatureSerializer(signature, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Example: Only allow admin to update blockchain_signature_hash
        if not request.user.is_staff:
            return Response({'detail': 'You do not have permission to update signatures.'}, status=status.HTTP_403_FORBIDDEN)

        allowed_update_fields = {'blockchain_signature_hash'}
        if not all(key in allowed_update_fields for key in request.data.keys() if key != signature._meta.pk.name): # check if only allowed fields are being updated
             # If other fields than 'blockchain_signature_hash' are in request.data:
            is_updating_other_fields = any(field not in allowed_update_fields for field in request.data if field != 'id')
            if is_updating_other_fields:
                return Response({'detail': 'Only specific fields like blockchain_signature_hash can be updated on a signature.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DigitalSignatureSerializer(signature, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # A more common approach is to disallow PUT entirely:
        # return Response({'detail': 'Digital signatures cannot be updated.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


    elif request.method == 'DELETE':
        # Generally, signatures should not be deleted.
        # If deletion is allowed, restrict it, e.g., only admin and only if not part of a completed transaction.
        if not request.user.is_staff: # Example: only admin can delete
            return Response({'detail': 'You do not have permission to delete this signature.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Add more conditions if needed (e.g., related transaction status)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        # A more common approach:
        # return Response({'detail': 'Digital signatures cannot be deleted.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)