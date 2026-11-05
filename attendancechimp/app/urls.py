from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('time', views.time_view, name='time'),
    path('sum', views.sum_view, name='sum'),
    path("", views.index, name="home"),
    path("index.html", views.index, name="index_html"),
    path("new", views.new, name="new"),
    path("new_course", views.new_course),
    path("new_lecture", views.new_lecture),
    path("new_qr_upload", views.new_qr_upload),
    path("createUser",views.createUser,name="createUser"),
    path("createCourse", views.createCourse),
    path("createLecture", views.createLecture),
    path("createQRCodeUpload", views.createQRCodeUpload),
    path("dumpUploads", views.dumpUploads),
]
