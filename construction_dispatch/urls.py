"""
URL configuration for construction_dispatch project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from order_management.views_permission import permission_denied_handler

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/orders/", permanent=False)),  # ルートURLをordersにリダイレクト
    path("orders/", include("order_management.urls")),  # app_nameを使用（namespace指定不要）
    path("subcontracts/", include("subcontract_management.urls", namespace="subcontract_management")),
]

# カスタムエラーハンドラー
handler403 = permission_denied_handler

# Media files (user uploaded content) - development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
