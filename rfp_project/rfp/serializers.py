from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Quote, Rfp, Vendor, Category
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'password'
        )

    def create(self, user_data):
        password = user_data.pop('password')
        user = User(**user_data)
        user.set_password(password)
        user.save()
        return user

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info
        user_data = UserSerializer(self.user).data

        data["user"] = user_data

        # If user is a vendor, return vendor info too
        if hasattr(self.user, "vendor_profile"):
            data["vendor"] = VendorSerializer(self.user.vendor_profile).data

        return data

class VendorRegistrationSerializer(serializers.Serializer):

    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only = True, min_length = 8)

    gst_number = serializers.CharField(required=True)
    pan_card_number = serializers.CharField(required=True)
    mobile_number = serializers.CharField(required=True)
    number_of_employee = serializers.IntegerField(required=False, default=1)
    revenue = serializers.DecimalField(max_digits=12,decimal_places=2, required=False, default=0)
    category = serializers.PrimaryKeyRelatedField(queryset = Category.objects.all(), required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # lazy import to avoid circular import
        from .models import Category
        self.fields['category'].queryset = Category.objects.all()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_gst_number(self, value):
        if Vendor.objects.filter(gst_number=value).exists():
            raise serializers.ValidationError("GST number already exists")
        return value
        
    def validate_pan_card_number(self, value):
        if Vendor.objects.filter(pan_card_number = value).exists():
            raise serializers.ValidationError("PAN Card number already registered")
        return value

    def create(self, vendor_data):
        category = vendor_data.pop('category', None)
        password = vendor_data.pop('password')

        user = User(
            username = vendor_data.pop('username'),
            email = vendor_data.pop('email'),
            first_name = vendor_data.pop('first_name',''),
            last_name = vendor_data.pop('last_name', '')
        )
        user.set_password(password)
        user.save()

        vendor = Vendor.objects.create(
            user=user,
            gst_number=vendor_data.pop('gst_number'),
            pan_card_number=vendor_data.pop('pan_card_number'),
            mobile_number=vendor_data.pop('mobile_number'),
            number_of_employee=vendor_data.pop('number_of_employee', 1),
            revenue=vendor_data.pop('revenue', 0),
            category=category
        )

        send_vendor_registration_email(user)
        return {
            'user': user,
            'vendor': vendor
        }

class AdminRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, min_length = 8)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password'
        )

    def create(self, admin_data):
        password = admin_data.pop('password')

        user = User(**admin_data)
        user.is_staff = True
        user.set_password(password)
        user.save()
        return user

class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = "__all__"


class VendorSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id',
            'first_name',
            'last_name',
            'email', 
            'revenue',
            'number_of_employee',
            'gst_number',
            'gst_image',
            'pan_card_number',
            'pan_card_image',
            'mobile_number',
            'category',
            'vendor_status'
            ]

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, ojb):
        return ojb.user.last_name

    def get_email(self, obj):
        return obj.user.email

class VendorToCategorySerializer(serializers.ModelSerializer):
    vendor_name = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id',
            'vendor_name'
        ]

    def get_vendor_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}"
        return full_name or obj.user.username

class RfpSerializer(serializers.ModelSerializer):
    assigned_vendor = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        required=True
    )

    vendors = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True
    )

    class Meta:
        model = Rfp
        fields = [
            'id',
            'name',
            'description',
            'quantity',
            'last_date',
            'min_price',
            'max_price',
            'category',
            'assigned_vendor',
            'vendors',
        ]

    def validate(self, data):
        category = data.get('category')
        assigned_vendor = data.get('assigned_vendor')

        if assigned_vendor and assigned_vendor.category != category:
            raise serializers.ValidationError(
                {"assigned_vendor": "This vendor does not belong to the selected category."}
            )

        return data

class QuoteSerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.user.get_full_name", read_only=True)
    rfp_item_name = serializers.CharField(source="rfp.name", read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id",
            "rfp",
            "vendor",
            "vendor_name",
            "rfp_item_name",
            "price",
            "quantity",
            "description",
            "total_cost",
            "created_at",
        ]
        read_only_fields = ['vendor']

    def create(self, validated_data):
        vendor = self.context['request'].user.vendor_profile
        validated_data['vendor'] = vendor
        return super().create(validated_data)

def send_vendor_registration_email(user):
    subject = "Registration Successful - RFP Management"

    # Render HTML template
    html_body = render_to_string("emails/vendor_welcome.html", {
        "first_name": user.first_name,
        "login_url": "http://localhost:5173/"
    })

    text_body = f"Hello {user.first_name},\nYour RFP account was created successfully."

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        # to=[user.email]
        to=["almaaz.ahmed@velsof.com"]
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


# # app_name/serializers.py

# from rest_framework import serializers
# from .models import Category, Vendor, Rfp, Quote
# from django.contrib.auth import get_user_model
# from rest_framework import serializers
# from .models import Vendor
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = '__all__'


# class VendorSerializer(serializers.ModelSerializer):
#     # Optional: show related user fields as read-only
#     user_email = serializers.EmailField(source='user.email', read_only=True)
#     user_first_name = serializers.CharField(source='user.first_name', read_only=True)
#     user_last_name = serializers.CharField(source='user.last_name', read_only=True)

#     class Meta:
#         model = Vendor
#         fields = [
#             'id',
#             'user',          # you can make this read_only and set from request.user in the view
#             'user_email',
#             'user_first_name',
#             'user_last_name',
#             'revenue',
#             'number_of_employee',
#             'gst_number',
#             'gst_image',
#             'pan_card_number',
#             'pan_card_image',
#             'mobile_number',
#             'category',
#             'vendor_status',
#             'created_at',
#             'updated_at',
#         ]
#         read_only_fields = ['created_at', 'updated_at']


# class RfpSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Rfp
#         fields = '__all__'


# class QuoteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Quote
#         fields = '__all__'
#         read_only_fields = ['created_at']

# User = get_user_model()


# class VendorRegisterSerializer(serializers.ModelSerializer):
#     # User fields
#     email = serializers.EmailField(write_only=True)
#     password = serializers.CharField(write_only=True, min_length=8)
#     first_name = serializers.CharField(write_only=True)
#     last_name = serializers.CharField(write_only=True)

#     class Meta:
#         model = Vendor
#         # Vendor + embedded user fields
#         fields = [
#             'email', 'password', 'first_name', 'last_name',
#             'revenue', 'number_of_employee',
#             'gst_number', 'gst_image',
#             'pan_card_number', 'pan_card_image',
#             'mobile_number',
#             'category',
#         ]
#         extra_kwargs = {
#             'revenue': {'read_only': True},
#         }

#     def create(self, validated_data):
#         # Extract user fields
#         email = validated_data.pop('email')
#         password = validated_data.pop('password')
#         first_name = validated_data.pop('first_name')
#         last_name = validated_data.pop('last_name')

#         # Decide username – you can change this if your user model is custom
#         username = email

#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             first_name=first_name,
#             last_name=last_name,
#         )

#         # Create Vendor profile
#         vendor = Vendor.objects.create(
#             user=user,
#             **validated_data
#         )
#         return vendor


# class AdminRegisterSerializer(serializers.ModelSerializer):
#     """
#     Register an admin user (is_staff & optionally is_superuser).
#     This endpoint should be protected (only superuser or existing admin).
#     """

#     password = serializers.CharField(write_only=True, min_length=8)

#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password', 'first_name', 'last_name']

#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         user = User.objects.create(
#             **validated_data,
#             is_staff=True,
#             is_superuser=False,  # set True if you want this API to create superusers
#         )
#         user.set_password(password)
#         user.save()
#         return user



# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     """
#     Custom login serializer to return extra info in token & response:
#     - is_staff (admin)
#     - is_vendor and vendor_id (if vendor profile exists)
#     """

#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)

#         token['is_staff'] = user.is_staff
#         try:
#             vendor = user.vendor_profile
#             token['is_vendor'] = True
#             token['vendor_id'] = vendor.id
#         except Vendor.DoesNotExist:
#             token['is_vendor'] = False

#         return token

#     def validate(self, attrs):
#         data = super().validate(attrs)
#         user = self.user

#         data['is_staff'] = user.is_staff
#         data['username'] = user.get_username()
#         data['email'] = user.email

#         try:
#             vendor = user.vendor_profile
#             data['is_vendor'] = True
#             data['vendor_id'] = vendor.id
#         except Vendor.DoesNotExist:
#             data['is_vendor'] = False

#         return data

