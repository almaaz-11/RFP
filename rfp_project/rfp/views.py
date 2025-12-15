from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import generics, status, permissions
from .serializers import CategorySerializer, QuoteSerializer, RfpSerializer, VendorRegistrationSerializer, AdminRegistrationSerializer, UserSerializer, VendorSerializer,VendorToCategorySerializer,MyTokenObtainPairSerializer
from .models import Category, Quote, Rfp, Vendor
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from .permissions import IsAdmin, IsAdminOrVendor, IsVendor
from django.core.mail import send_mail
from django.conf import settings

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from django.contrib.auth.models import User


class VendorRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VendorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            user = data['user']
            vendor = data['vendor']
            user_data = UserSerializer(user).data

            return Response({
                'user': user_data,
                'vendor_id' : vendor.id,
                'message': 'Vendor registered successfully. Awaiting approval.'
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminRegistrationView(APIView):

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = AdminRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user' : UserSerializer(user).data, 'message': 'Admin Created.'
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_categories(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'pk'

class RfpView(generics.ListCreateAPIView):
    serializer_class = RfpSerializer

    def get_permissions(self):
        return [IsAdminOrVendor()]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Rfp.objects.all()

        # ensure vendor_profile exists
        if not hasattr(user, "vendor_profile"):
            return Rfp.objects.none()

        return Rfp.objects.filter(category=user.vendor_profile.category)

class RfpDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        return [IsAdminOrVendor()]
    queryset = Rfp.objects.all()
    serializer_class = RfpSerializer
    lookup_field = 'pk'


class VendorsByCategoryView(APIView):
    permission_classes = [permissions.AllowAny]
    """
    GET /vendors-by-category/?category_id=<id>
    Returns all approved vendors for the given category.
    """

    def get(self, request):
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': 'category_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        vendors = Vendor.objects.filter(
            category_id=category_id,
            vendor_status='APPROVED'
        )
        serializer = VendorToCategorySerializer(vendors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class VendorView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.all().order_by('-created_at')
    serializer_class = VendorSerializer

class VendorDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    lookup_field = 'pk'

class QuoteView(generics.ListCreateAPIView):
    serializer_class = QuoteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsVendor()]   
        return [IsAdminOrVendor()]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Quote.objects.all()

        return Quote.objects.filter(vendor=user.vendor_profile)

    def get_serializer_context(self):
        return {"request": self.request}


class QuoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuoteSerializer

    def get_permissions(self):
        return [IsAdminOrVendor()]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Quote.objects.all()

        return Quote.objects.filter(vendor=user.vendor_profile)

    def get_serializer_context(self):
        return {"request": self.request}

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"message": "If this email is registered, a reset link has been sent."})
        # Security best practice: do NOT reveal if user exists

    token_generator = PasswordResetTokenGenerator()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)

    reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"

    # send email
    html = render_to_string("emails/password_reset.html", {
        "first_name": user.first_name,
        "reset_url": reset_url,
    })

    email_msg = EmailMultiAlternatives(
        subject="Reset Your Password - RFP Management",
        body=f"Click the link to reset your password: {reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email_msg.attach_alternative(html, "text/html")
    email_msg.send()

    return Response({"message": "Password reset email sent!"}, status=200)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password(request):
    uid = request.data.get("uid")
    token = request.data.get("token")
    password = request.data.get("password")

    if not (uid and token and password):
        return Response({"error": "All fields are required"}, status=400)

    try:
        uid = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid)
    except:
        return Response({"error": "Invalid link"}, status=400)

    token_generator = PasswordResetTokenGenerator()

    if not token_generator.check_token(user, token):
        return Response({"error": "Invalid or expired token"}, status=400)

    user.set_password(password)
    user.save()

    return Response({"message": "Password has been reset successfully!"}, status=200)


# # app_name/views.py

# from rest_framework import viewsets, permissions
# from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

# from .models import Category, Vendor, Rfp, Quote
# from .serializers import (
#     CategorySerializer,
#     VendorSerializer,
#     RfpSerializer,
#     QuoteSerializer,
# )

# from rest_framework import generics, permissions
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# from .serializers import (
#     VendorRegisterSerializer,
#     AdminRegisterSerializer,
#     CustomTokenObtainPairSerializer,
# )


# class CategoryViewSet(viewsets.ModelViewSet):
#     """
#     Simple CRUD for categories.
#     """
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer
#     permission_classes = [IsAuthenticatedOrReadOnly]


# class VendorViewSet(viewsets.ModelViewSet):
#     """
#     CRUD for vendors.
#     If you want the vendor to always be linked to the logged-in user,
#     we can set user in perform_create().
#     """
#     queryset = Vendor.objects.all()
#     serializer_class = VendorSerializer
#     permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         # automatically set the user to the logged-in user
#         serializer.save(user=self.request.user)

#     def perform_update(self, serializer):
#         # usually you don't want to allow changing the user from API
#         serializer.save(user=self.request.user)


# class RfpViewSet(viewsets.ModelViewSet):
#     """
#     CRUD for RFPs.
#     """
#     queryset = Rfp.objects.all()
#     serializer_class = RfpSerializer
#     permission_classes = [IsAuthenticatedOrReadOnly]


# class QuoteViewSet(viewsets.ModelViewSet):
#     """
#     CRUD for Quotes.
#     """
#     queryset = Quote.objects.all()
#     serializer_class = QuoteSerializer
#     permission_classes = [IsAuthenticated]


# class VendorRegisterView(generics.CreateAPIView):
#     """
#     POST /api/auth/register/vendor/
#     {
#       "email": "...",
#       "password": "...",
#       "first_name": "...",
#       "last_name": "...",
#       "gst_number": "...",
#       "pan_card_number": "...",
#       "mobile_number": "...",
#       "category": 1
#     }
#     """
#     serializer_class = VendorRegisterSerializer
#     permission_classes = [permissions.AllowAny]


# class AdminRegisterView(generics.CreateAPIView):
#     """
#     POST /api/auth/register/admin/
#     Protected: only an existing admin/superuser can create new admins.
#     """
#     serializer_class = AdminRegisterSerializer
#     permission_classes = [permissions.IsAdminUser]


# class CustomTokenObtainPairView(TokenObtainPairView):
#     """
#     POST /api/auth/login/
#     {
#       "username": "...",
#       "password": "..."
#     }
#     """
#     serializer_class = CustomTokenObtainPairSerializer


# class CustomTokenRefreshView(TokenRefreshView):
#     """
#     POST /api/auth/token/refresh/
#     {
#       "refresh": "..."
#     }
#     """
#     pass


# # from django.http import Http404
# # from django.shortcuts import render
# # from rest_framework.mixins import ListModelMixin
# # from rest_framework.views import APIView
# # from .models import Category
# # from .serializers import CategorySerializer
# # from rest_framework import status
# # from rest_framework.response import Response
# # from rest_framework.decorators import api_view
# # from rest_framework import mixins, generics

# # Create your views here.
# # @api_view(['GET','POST'])
# # def  categoryView(request):
# #     if request.method == 'GET':
# #         categories = Category.objects.all()
# #         serializer = CategorySerializer(categories, many=True)
# #         return Response(serializer.data, status=status.HTTP_200_OK)
# #     elif request.method == 'POST':
# #         serializer = CategorySerializer(data = request.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=status.HTTP_201_CREATED)
# #         else:
# #             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# # @api_view(['GET','PUT','DELETE'])
# # def categoryDetailView(request, pk):
# #     try:
# #         category = Category.objects.get(pk=pk)
# #     except Category.DoesNotExist:
# #         return Response(status=status.HTTP_404_NOT_FOUND)

# #     if request.method == 'GET':
# #         serializer = CategorySerializer(category)
# #         return Response(serializer.data, status = status.HTTP_200_OK)
# #     elif request.method == 'PUT':
# #         serializer = CategorySerializer(category, data=request.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=status.HTTP_200_OK)
# #         else:
# #             return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

# #     if request.method == 'DELETE':
# #         category.delete()
# #         return Response(status=status.HTTP_204_NO_CONTENT)

# # class Categories(APIView):
# #     def get(self, request):
# #         category = Category.objects.all()
# #         serializer = CategorySerializer(category, many=True)
# #         return Response(serializer.data, status=status.HTTP_200_OK)

# #     def post(self, reqeust):
# #         serializer = CategorySerializer(data=reqeust.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=status.HTTP_201_CREATED)
# #         return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)


# # class CategoryDetail(APIView):
# #     def get_object(self, pk):
# #         try:
# #             return Category.objects.get(pk=pk)
# #         except Category.DoesNotExist:
# #             raise Http404

# #     def get(self, request, pk):
# #         category = self.get_object(pk)
# #         serializer = CategorySerializer(category)
# #         return Response(serializer.data, status=status.HTTP_200_OK)

# #     def put(self, request, pk):
# #         category = self.get_object(pk)
# #         serializer = CategorySerializer(category, request.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=status.HTTP_200_OK)
# #         return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

# #     def delete(self, request, pk):
# #         category = self.get_object(pk)
# #         category.delete()
# #         return Response(status=status.HTTP_204_NO_CONTENT)

# # class Categories(mixins.ListModelMixin,mixins.CreateModelMixin , generics.GenericAPIView):
# #     queryset = Category.objects.all()
# #     serializer_class = CategorySerializer

# #     def get(self, request):
# #         return self.list(request)

# #     def post(self, request):
# #         return self.create(request)

# # class CategoryDetail(mixins.RetrieveModelMixin,mixins.UpdateModelMixin,mixins.DestroyModelMixin, generics.GenericAPIView):
# #     queryset = Category.objects.all()
# #     serializer_class = CategorySerializer

# #     def get(self, request, pk):
# #         return self.retrieve(request, pk)
    
# #     def put(self, request, pk):
# #         return self.update(request, pk)

# #     def delete(self, request, pk):
# #         return self.destroy(request, pk)

# # class Categories(generics.ListCreateAPIView):
# #     queryset = Category.objects.all()
# #     serializer_class = CategorySerializer

# # class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
# #     queryset = Category.objects.all()
# #     serializer_class = CategorySerializer
# #     lookup_field = 'pk'

    







