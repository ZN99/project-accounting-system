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
from order_management.views_permission import permission_denied_handler

from order_management import urls as order_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("orders/", include("order_management.urls", namespace="order_management")),
    path("subcontracts/", include("subcontract_management.urls", namespace="subcontract_management")),
    path("", include(order_urls)),  # ルートURLをorder_managementに割り当て（名前空間なし）
]

# カスタムエラーハンドラー
handler403 = permission_denied_handler

# Media files (user uploaded content) - development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
