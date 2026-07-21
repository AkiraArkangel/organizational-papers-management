from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from documents.forms import AccountLoginForm


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('documents.urls')),
    path('login/', auth_views.LoginView.as_view(
        authentication_form=AccountLoginForm,
        template_name='documents/login.html',
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Media files are now served via custom views - no static file serving needed
