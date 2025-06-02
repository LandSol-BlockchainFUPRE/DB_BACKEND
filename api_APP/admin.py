from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(NINInfo)
admin.site.register(UserProfile)
admin.site.register(Document)
admin.site.register(Transaction)
admin.site.register(DigitalSignature)
admin.site.register(Property)