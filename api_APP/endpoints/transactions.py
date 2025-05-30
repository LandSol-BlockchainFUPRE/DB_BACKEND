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



# --- Transaction Views ---

@swagger_auto_schema(
    method='get',
    operation_id='list_transactions',
    operation_description="Retrieve a list of all transactions.",
    tags=['Transactions'],
    responses={200: TransactionSerializer(many=True), 401: RESPONSE_401_UNAUTHORIZED}
)
@swagger_auto_schema(
    method='post',
    operation_id='create_transaction',
    operation_description="Create a new transaction. 'property', 'seller' (User ID), and 'buyer' (User ID) must be provided.",
    tags=['Transactions'],
    request_body=TransactionSerializer,
    responses={
        201: TransactionSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def transaction_list_create(request):
    """
    List all transactions or create a new one.
    """
    if request.method == 'GET':
        transactions = Transaction.objects.all()
        # Optional: Filter by user (e.g., involved_user_id=request.user.id)
        # involved_user_id = request.query_params.get('involved_user_id')
        # if involved_user_id:
        #    transactions = transactions.filter(Q(seller_id=involved_user_id) | Q(buyer_id=involved_user_id))
        serializer = TransactionSerializer(transactions, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Business logic: Ensure seller owns the property
            property_obj = serializer.validated_data.get('property')
            seller_obj = serializer.validated_data.get('seller')
            if property_obj and seller_obj and property_obj.current_owner != seller_obj:
                return Response(
                    {'seller': [f"Seller ({seller_obj.username}) does not own the property ({property_obj.unique_property_identifier})."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Optional: Ensure seller is the request.user if that's a business rule
            # if seller_obj != request.user and not request.user.is_staff:
            #     return Response({'seller': ['You can only initiate transactions for yourself.']}, status=status.HTTP_403_FORBIDDEN)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_id='retrieve_transaction',
    operation_description="Retrieve a specific transaction by its UUID.",
    tags=['Transactions'],
    responses={
        200: TransactionSerializer,
        401: RESPONSE_401_UNAUTHORIZED,
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='put',
    operation_id='update_transaction',
    operation_description="Update a specific transaction by its UUID. Certain fields like seller/buyer/property might be restricted after creation.",
    tags=['Transactions'],
    request_body=TransactionSerializer,
    responses={
        200: TransactionSerializer,
        400: RESPONSE_400_BAD_REQUEST,
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user not involved or admin
        404: RESPONSE_404_NOT_FOUND
    }
)
@swagger_auto_schema(
    method='delete',
    operation_id='delete_transaction',
    operation_description="Delete a specific transaction by its UUID. Might be restricted based on status.",
    tags=['Transactions'],
    responses={
        204: openapi.Response(description="Transaction deleted successfully"),
        401: RESPONSE_401_UNAUTHORIZED,
        403: RESPONSE_403_FORBIDDEN, # If user not involved or admin, or status prevents deletion
        404: RESPONSE_404_NOT_FOUND
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def transaction_detail_update_delete(request, pk): # pk is Transaction UUID
    """
    Retrieve, update or delete a transaction instance.
    """
    try:
        transaction = Transaction.objects.get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'detail': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Permission check: Only seller, buyer, or admin can modify/delete
    can_modify = (request.user == transaction.seller or \
                  request.user == transaction.buyer or \
                  request.user.is_staff)

    if request.method == 'GET':
        serializer = TransactionSerializer(transaction, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not can_modify:
            return Response({'detail': 'You do not have permission to modify this transaction.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TransactionSerializer(transaction, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            # Re-validate seller ownership if property or seller is changed
            property_obj = serializer.validated_data.get('property', transaction.property) # Use original if not in payload
            seller_obj = serializer.validated_data.get('seller', transaction.seller)
            if property_obj and seller_obj and property_obj.current_owner != seller_obj:
                 return Response(
                    {'seller': [f"Proposed seller ({seller_obj.username}) does not own the property ({property_obj.unique_property_identifier})."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Add more business logic for updates (e.g., status transitions)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not can_modify: # Or more specific logic e.g. only admin for completed transactions
            return Response({'detail': 'You do not have permission to delete this transaction.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Optional: Restrict deletion based on status
        # if transaction.status not in ['pending', 'cancelled'] and not request.user.is_staff:
        #     return Response({'detail': f"Cannot delete transaction in '{transaction.status}' state."}, status=status.HTTP_403_FORBIDDEN)
        
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)