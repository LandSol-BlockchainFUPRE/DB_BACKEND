# Django imports
from django.shortcuts import render # Kept if other views in this file might use it
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt # Kept if other views might use it

# DRF imports
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser # Kept for potential other views
from rest_framework.authtoken.models import Token
# from rest_framework.views import APIView # Keep if class-based views are also in this file


from ..models import * # Kept as in original, assuming it might be used by other views

# drf-yasg imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from ..serializers import (
    LoginRequestSerializer,       # Assumed to exist for login request body
    TokenUserResponseSerializer,  # Assumed to exist for login success response
    MessageResponseSerializer,    # Assumed to exist for generic message/error responses
    ProtectedDataSerializer       # Assumed to exist for the protected view response
)
# If serializers are in the same 'api' app directory: from .serializers import ...

User = get_user_model()

# --- Common OpenAPI Responses ---
# These assume your error/message responses follow a consistent JSON structure.
# We'll use MessageResponseSerializer for errors if they return e.g. {"error": "..."} or {"detail": "..."}
RESPONSE_200_OK_MESSAGE = openapi.Response(
    description="OK - Operation successful, typically returns a success message.",
    schema=MessageResponseSerializer
)
RESPONSE_400_BAD_REQUEST = openapi.Response(
    description="Bad Request - Invalid data provided or a client-side error.",
    schema=MessageResponseSerializer
)
RESPONSE_401_UNAUTHORIZED = openapi.Response(
    description="Unauthorized - Authentication credentials were not provided or are invalid.",
    schema=MessageResponseSerializer
)
RESPONSE_403_FORBIDDEN = openapi.Response(
    description="Forbidden - You do not have permission to perform this action.",
    schema=MessageResponseSerializer # Example: {'detail': 'Permission denied.'}
)
# RESPONSE_404_NOT_FOUND = openapi.Response(description="Resource not found", schema=MessageResponseSerializer) # If needed


# --- Authentication Views ---

@swagger_auto_schema(
    method='post',
    operation_id='custom_login',
    operation_description="Logs in a user and returns an authentication token along with user details.",
    tags=['Authentication'],
    request_body=LoginRequestSerializer,
    responses={
        status.HTTP_200_OK: TokenUserResponseSerializer,
        status.HTTP_400_BAD_REQUEST: RESPONSE_400_BAD_REQUEST, # For missing username/password
        status.HTTP_401_UNAUTHORIZED: RESPONSE_401_UNAUTHORIZED # For invalid credentials or inactive user
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Please provide both username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if not user:
        return Response(
            {'error': 'Invalid Credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'User account is disabled.'},
            status=status.HTTP_401_UNAUTHORIZED # Could also be 403 Forbidden
        )

    token, created = Token.objects.get_or_create(user=user)

    response_data = {
        'token': token.key,
        'user_id': user.pk,
        'username': user.username,
        # Add any other user details you want to return, ensure they match TokenUserResponseSerializer
    }
    return Response(response_data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='custom_logout',
    operation_description="Logs out the currently authenticated user by invalidating their token.",
    tags=['Authentication'],
    responses={
        status.HTTP_200_OK: RESPONSE_200_OK_MESSAGE, # e.g., {"message": "Successfully logged out."}
        status.HTTP_400_BAD_REQUEST: RESPONSE_400_BAD_REQUEST, # e.g., {"error": "No active session or token found."}
        status.HTTP_401_UNAUTHORIZED: RESPONSE_401_UNAUTHORIZED # Handled by IsAuthenticated permission class
    },
    security=[{'Token': []}] # Indicates that token authentication is required
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_logout(request):
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
    except (AttributeError, Token.DoesNotExist):
        # This case might occur if the token was already deleted or some other state issue.
        return Response({'error': 'No active session or token found to invalidate.'}, status=status.HTTP_400_BAD_REQUEST)


# --- Protected Content View ---

@swagger_auto_schema(
    method='get',
    operation_id='get_protected_content',
    operation_description="Accesses a protected endpoint that requires authentication. Returns user info and a success message.",
    tags=['Protected Content'],
    responses={
        status.HTTP_200_OK: ProtectedDataSerializer,
        status.HTTP_401_UNAUTHORIZED: RESPONSE_401_UNAUTHORIZED # Handled by IsAuthenticated
    },
    security=[{'Token': []}] # Indicates that token authentication is required
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected(request):
    content = {
        'user': str(request.user), # or request.user.username, request.user.email etc.
        'message': 'You are authenticated (FBV) and can see this protected content!'
    }
    return Response(content, status=status.HTTP_200_OK)