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





@swagger_auto_schema(
    method='get',
    operation_id='list_nin_info_records',
    operation_description="Retrieve a list of all National Identification Number (NIN) records. Access might be restricted.",
    tags=['NIN Information'],
    responses={
        200: NINInfoSerializer(many=True),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If general users are not allowed to list
    }
)
@swagger_auto_schema(
    method='post',
    operation_id='create_nin_info_record',
    operation_description="Create a new NIN record. Typically restricted to administrative users.",
    tags=['NIN Information'],
    request_body=NINInfoSerializer,
    responses={
        201: NINInfoSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN,
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated]) # Adjust permissions as needed, e.g., IsAdminUser for POST
def nin_info_list_create(request):
    """
    List all NINInfo records or create a new one.
    Creation is typically restricted.
    """
    if request.method == 'GET':
        # Consider if all authenticated users should see all NINs, or apply filters/further restrictions.
        # For example, if only admins can list:
        # if not request.user.is_staff:
        #     return Response({'detail': 'You do not have permission to list NIN records.'}, status=status.HTTP_403_FORBIDDEN)
        nin_records = NINInfo.objects.all()
        serializer = NINInfoSerializer(nin_records, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        # Restrict POST to admin users or users with specific permissions
        if not request.user.is_staff: # Example: only staff/admin can create
            return Response({'detail': 'You do not have permission to create NIN records.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = NINInfoSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_nin_info_record',
    operation_description="Retrieve a specific NIN record by its internal ID.",
    tags=['NIN Information'],
    responses={
        200: NINInfoSerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If access is restricted
        404: RESPONSE_404_NOT_FOUND,
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_nin_info_record',
    operation_description="Update a specific NIN record by its internal ID. Typically restricted to administrative users.",
    tags=['NIN Information'],
    request_body=NINInfoSerializer,
    responses={
        200: NINInfoSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN,
        404: RESPONSE_404_NOT_FOUND,
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_nin_info_record',
    operation_description="Delete a specific NIN record by its internal ID. Typically restricted to administrative users.",
    tags=['NIN Information'],
    responses={
        204: openapi.Response(description="NIN Record deleted successfully"),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN,
        404: RESPONSE_404_NOT_FOUND,
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated]) # Adjust permissions as needed, e.g., IsAdminUser for PUT/DELETE
def nin_info_detail_update_delete(request, code): # pk here is the auto-generated ID of the NINInfo record
    """
    Retrieve, update or delete a NINInfo record instance.
    Update and Delete operations are typically restricted.
    """
    try:
        nin_record = NINInfo.objects.get(nin=code)
    except NINInfo.DoesNotExist:
        return Response({'detail': 'NIN Record not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Consider if the requesting user should be able to see this specific NIN record.
        # For example, if only admins can retrieve specific records:
        # if not request.user.is_staff:
        #    return Response({'detail': 'You do not have permission to view this NIN record.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = NINInfoSerializer(nin_record, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not request.user.is_staff: # Example: only staff/admin can update
            return Response({'detail': 'You do not have permission to update NIN records.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = NINInfoSerializer(nin_record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            # Prevent changing the 'nin' field itself after creation, if that's a business rule
            # if 'nin' in serializer.validated_data and serializer.validated_data['nin'] != nin_record.nin:
            #     return Response({'nin': ['The NIN field cannot be changed after creation.']}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not request.user.is_staff: # Example: only staff/admin can delete
            return Response({'detail': 'You do not have permission to delete NIN records.'}, status=status.HTTP_403_FORBIDDEN)
        nin_record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)