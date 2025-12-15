from django.urls import path
from .views import BlogView, CommentView, BlogDetailView, CommentDetailView

urlpatterns = [
    path('api/blogs/', BlogView.as_view()),
    path('api/comments/', CommentView.as_view()),

    path('api/blogs/<int:pk>', BlogDetailView.as_view()),
    path('api/comments/<int:pk>', CommentDetailView.as_view())

]