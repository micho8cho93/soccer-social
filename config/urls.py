from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from futbolapp.urls import public_urlpatterns
from futbolapp.views import landing_page, referee_login, referee_portal, referee_match_update

urlpatterns = [
    path('admin/', admin.site.urls),
    path('futbol/', include('futbolapp.urls')),
    path('public/', include(public_urlpatterns)),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', landing_page, name='landing_page'),
    path('referee_login/', referee_login, name='referee_login'),
    path('referee_portal/', referee_portal, name='referee_portal'),
    path('referee/match/<int:match_id>/update/', referee_match_update, name='referee_match_update'),
]