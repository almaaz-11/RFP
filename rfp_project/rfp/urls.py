from django.urls import path
from .views import (
    CategoryView, RfpView, VendorRegistrationView, AdminRegistrationView, VendorsByCategoryView,CategoryDetailView, 
    VendorView, VendorDetailView, QuoteView, RfpDetailView, QuoteDetailView, get_categories, forgot_password, reset_password)

urlpatterns = [
    path('register/vendor/', VendorRegistrationView.as_view(), name='register-vendor'),
    path('register/admin/', AdminRegistrationView.as_view(), name='register-admin'),
    path('get_category/', get_categories),
    path('category/', CategoryView.as_view()),
    path('category/<int:pk>', CategoryDetailView.as_view()),
    path('rfps/', RfpView.as_view()),
    path('rfps/<int:pk>', RfpDetailView.as_view()),
    path('vendors-by-category/', VendorsByCategoryView.as_view(), name='vendors-by-category'),
    path('vendor/', VendorView.as_view()),
    path('vendor/<int:pk>', VendorDetailView.as_view()),

    path('quotes/', QuoteView.as_view()),
    path('quotes/<int:pk>', QuoteDetailView.as_view()),

    path("auth/forgot-password/", forgot_password),
    path("auth/reset-password/", reset_password),
]


# from django.urls import path, include
# from rest_framework.routers import DefaultRouter

# from .views import CategoryViewSet, VendorViewSet, RfpViewSet, QuoteViewSet

# router = DefaultRouter()
# router.register(r'categories', CategoryViewSet, basename='category')
# router.register(r'vendors', VendorViewSet, basename='vendor')
# router.register(r'rfps', RfpViewSet, basename='rfp')
# router.register(r'quotes', QuoteViewSet, basename='quote')
# from .views import (
#     VendorRegisterView,
#     AdminRegisterView,
#     CustomTokenObtainPairView,
#     CustomTokenRefreshView,
# )

# app_name = 'accounts'

# urlpatterns = [
#     path('api/', include(router.urls)),
#     path('register/vendor/', VendorRegisterView.as_view(), name='vendor-register'),
#     path('register/admin/', AdminRegisterView.as_view(), name='admin-register'),
#     path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
#     path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
# ]

# # from django.urls import path
# # # from .views import categoryView, categoryDetailView
# # from .views import Categories, CategoryDetail

# # urlpatterns = [
# #     # path('api/category/', categoryView),
# #     # path('api/category/<int:pk>', categoryDetailView)

# #     # path('api/category/', Categories.as_view()),
# #     # path('api/category/<int:pk>', CategoryDetail.as_view()),
# # ]