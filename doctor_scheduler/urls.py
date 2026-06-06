from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('appointments.urls')),
    path('appointments/', include('appointments.urls')),
    path('patients/', include('patients.urls')),
    path('predictions/', include('predictions.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='base/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', include('patients.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)