"""
URL configuration for TerraAPI project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from rest_framework.documentation import include_docs_urls
from django.urls import include, re_path
from django.contrib import admin
from django.urls import path
from api_APP import views
from api_APP.endpoints import digitalsig, login_endpoint,transactions,property,document
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="TERRA API",
      default_version='v1.0',
      description="Advance API request header method for terra properties and GIS  ",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="blockchainfupre@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('admin/', admin.site.urls),


    path('user-profiles/', login_endpoint.user_profile_list_create, name='userprofile-list-create'),
    path('user-profiles/<int:pk>/', login_endpoint.user_profile_detail_update_delete, name='userprofile-detail'), # pk is user_id

    path('properties/', property.property_list_create, name='property-list-create'),
    path('properties/<uuid:pk>/', property.property_detail_update_delete, name='property-detail'),

    path('documents/', document.document_list_create, name='document-list-create'),
    path('documents/<uuid:pk>/', document.document_detail_update_delete, name='document-detail'),

    path('transactions/', transactions.transaction_list_create, name='transaction-list-create'),
    path('transactions/<uuid:pk>/', transactions.transaction_detail_update_delete, name='transaction-detail'),

    path('digital-signatures/', digitalsig.digital_signature_list_create, name='digitalsignature-list-create'),
    path('digital-signatures/<uuid:pk>/', digitalsig.digital_signature_detail_update_delete, name='digitalsignature-detail'),


    re_path(r'^playground/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^docs/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger/', schema_view.with_ui(cache_timeout=0), name='schema-json'),
    #re_path(r'^docs/', include_docs_urls(title='My API title')),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
