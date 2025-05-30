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


# --- Document Views ---

@swagger_auto_schema(
    method='get',
    operation_id='list_documents',
    operation_description="Retrieve a list of all documents. Can be filtered by 'property_id'.",
    tags=['Documents'],
    manual_parameters=[
        openapi.Parameter('property_id', openapi.IN_QUERY, description="Filter documents by Property UUID", type=openapi.TYPE_STRING),
    ],
    responses={200: DocumentSerializer(many=True), 401: RESPONSE_401_UNAUTHORIZED}
)
@swagger_auto_schema(
    method='post',
    operation_id='create_document',
    operation_description="Upload a new document. 'property' (Property UUID) must be provided. 'uploaded_by' is set automatically.",
    tags=['Documents'],
    request_body=DocumentSerializer, # uploaded_by will be ignored from request body and set to request.user
    responses={
        201: DocumentSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # For document_file
def document_list_create(request):
    """
    List all documents or create a new one.
    'uploaded_by' is automatically set to the authenticated user on creation.
    """
    if request.method == 'GET':
        documents = Document.objects.all()
        property_id = request.query_params.get('property_id')
        if property_id:
            documents = documents.filter(property_id=property_id)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = DocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_document',
    operation_description="Retrieve a specific document by its UUID.",
    tags=['Documents'],
    responses={
        200: DocumentSerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_document',
    operation_description="Update a specific document by its UUID. 'uploaded_by' field is generally not updatable.",
    tags=['Documents'],
    request_body=DocumentSerializer,
    responses={
        200: DocumentSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user is not uploader/admin
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_document',
    operation_description="Delete a specific document by its UUID.",
    tags=['Documents'],
    responses={
        204: openapi.Response(description="Document deleted successfully"),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user is not uploader/admin
        404: RESPONSE_404_NOT_FOUND
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # For document_file
def document_detail_update_delete(request, pk): # pk is Document UUID
    """
    Retrieve, update or delete a document instance.
    """
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Permission check: Only uploader or admin can modify/delete
    can_modify = (request.user == document.uploaded_by or request.user.is_staff)

    if request.method == 'GET':
        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not can_modify:
            return Response({'detail': 'You do not have permission to modify this document.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Prevent changing uploaded_by unless admin (or make it fully immutable in serializer)
        original_uploaded_by = document.uploaded_by
        serializer = DocumentSerializer(document, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            instance = serializer.save()
            if 'uploaded_by' in request.data and instance.uploaded_by != original_uploaded_by and not request.user.is_staff:
                # Revert if a non-admin tried to change it and uploaded_by was in payload
                instance.uploaded_by = original_uploaded_by
                instance.save(update_fields=['uploaded_by'])
            return Response(DocumentSerializer(instance, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not can_modify:
            return Response({'detail': 'You do not have permission to delete this document.'}, status=status.HTTP_403_FORBIDDEN)
        document.delete() # File itself is not deleted from storage by default, handle if needed
        return Response(status=status.HTTP_204_NO_CONTENT)