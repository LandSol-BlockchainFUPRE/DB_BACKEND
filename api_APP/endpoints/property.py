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


# --- Property Views ---

@swagger_auto_schema(
    method='get',
    operation_id='list_properties',
    operation_description="Retrieve a list of all properties.",
    tags=['Properties'],
    responses={200: PropertySerializer(many=True), 401: RESPONSE_401_UNAUTHORIZED}
)
@swagger_auto_schema(
    method='post',
    operation_id='create_property',
    operation_description="Create a new property. 'current_owner' should be a valid user ID.",
    tags=['Properties'],
    request_body=PropertySerializer,
    responses={
        201: PropertySerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # For proof_of_ownership_document
def property_list_create(request):
    """
    List all properties or create a new one.
    For POST, 'current_owner' (User ID) must be provided.
    """
    if request.method == 'GET':
        properties = Property.objects.all()
        serializer = PropertySerializer(properties, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PropertySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Optionally, set current_owner to request.user if not provided and allowed by business logic
            # serializer.save(current_owner=request.user) # If current_owner is meant to be the creator
            serializer.save() # Assumes current_owner ID is in request.data
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_property',
    operation_description="Retrieve a specific property by its UUID.",
    tags=['Properties'],
    responses={
        200: PropertySerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_property',
    operation_description="Update a specific property by its UUID.",
    tags=['Properties'],
    request_body=PropertySerializer,
    responses={
        200: PropertySerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user is not owner/admin
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_property',
    operation_description="Delete a specific property by its UUID. May fail if protected by other relations.",
    tags=['Properties'],
    responses={
        204: openapi.Response(description="Property deleted successfully"),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user is not owner/admin
        404: RESPONSE_404_NOT_FOUND,
        409: openapi.Response(description="Conflict - Cannot delete property due to existing references (e.g., transactions).")
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # For proof_of_ownership_document
def property_detail_update_delete(request, pk): # pk is Property UUID
    """
    Retrieve, update or delete a property instance.
    """
    try:
        property_obj = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Permission check: Only current owner or admin can modify/delete
    can_modify = (request.user == property_obj.current_owner or request.user.is_staff)

    if request.method == 'GET':
        serializer = PropertySerializer(property_obj, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not can_modify:
            return Response({'detail': 'You do not have permission to modify this property.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PropertySerializer(property_obj, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not can_modify:
            return Response({'detail': 'You do not have permission to delete this property.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            property_obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except models.ProtectedError as e:
             return Response(
                 {'detail': f'Cannot delete property: it is referenced by other objects (e.g., Transactions). {e}'},
                 status=status.HTTP_409_CONFLICT
             )