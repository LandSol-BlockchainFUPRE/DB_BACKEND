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

from django.contrib.auth.models import User as addnew
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


# --- UserProfile Views ---

@swagger_auto_schema(
    method='get',
    operation_id='list_user_profiles',
    operation_description="Retrieve a list of all user profiles.",
    tags=['User Profiles'],
    responses={
        200: UserProfileSerializer(many=True),
        401: RESPONSE_401_UNAUTHORIZED,
    }
)
@swagger_auto_schema(
    method='post',
    operation_id='create_user_profile',
    operation_description="Create a new user profile. The 'user' field (profile's PK) must be an ID of an existing Django User without a profile.",
    tags=['User Profiles'],
    request_body=UserProfileSerializer,
    responses={
        201: UserProfileSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated]) # Or specific permissions
def user_profile_list_create(request):
    """
    List all user profiles or create a new one.
    For POST, 'user' (ID of an existing Django User) must be provided as it's the PK.
    """
    if request.method == 'GET':
        profiles = UserProfile.objects.all()
        serializer = UserProfileSerializer(profiles, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = UserProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            print("hhcygcygctgcgtgxxtcy cyuduttdr")
            # Ensure the user ID provided for the profile doesn't already have a profile
            user_id = serializer.validated_data.get('id_number') # Access the User object then its id
            print(user_id)
            if UserProfile.objects.filter(id_number=user_id).exists():
                 return Response(
                     {'user': [f'User profile for user ID {user_id} already exists.']},
                     status=status.HTTP_400_BAD_REQUEST
                 )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_user_profile',
    operation_description="Retrieve a specific user profile by user ID (which is the profile's PK).",
    tags=['User Profiles'],
    responses={
        200: UserProfileSerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        404: RESPONSE_404_NOT_FOUND,
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_user_profile',
    operation_description="Update a specific user profile by user ID (profile's PK).",
    tags=['User Profiles'],
    request_body=UserProfileSerializer,
    responses={
        200: UserProfileSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user tries to update profile not their own (add this logic)
        404: RESPONSE_404_NOT_FOUND,
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_user_profile',
    operation_description="Delete a specific user profile by user ID (profile's PK).",
    tags=['User Profiles'],
    responses={
        204: openapi.Response(description="User Profile deleted successfully"),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user tries to delete profile not their own (add this logic)
        404: RESPONSE_404_NOT_FOUND,
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated]) # Or specific permissions
@parser_classes([MultiPartParser, FormParser]) # For scanned_id_front/back
def user_profile_detail_update_delete(request, pk): # pk here is user_id
    """
    Retrieve, update or delete a user profile instance.
    'pk' is the User ID, as UserProfile's PK is 'user'.
    """
    try:
        profile = UserProfile.objects.get(pk=pk)
    except UserProfile.DoesNotExist:
        return Response({'detail': 'User Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Basic permission: user can only modify their own profile, or admin can modify any.
    is_owner = (profile.user == request.user)
    is_admin = request.user.is_staff

    if request.method == 'GET':
        # Allow any authenticated user to GET any profile, or restrict if needed
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not (is_owner or is_admin):
            return Response({'detail': 'You do not have permission to update this profile.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Prevent changing the 'user' field during an update as it's the PK
        if 'user' in request.data and request.data['user'] != profile.user_id:
             return Response({'user': ['Cannot change the user of an existing profile.']}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not (is_owner or is_admin): # Or more restrictive, e.g., only admin can delete
            return Response({'detail': 'You do not have permission to delete this profile.'}, status=status.HTTP_403_FORBIDDEN)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)