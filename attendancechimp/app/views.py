"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

import io
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import (
    StudentProfile,
    InstructorProfile,
    Course,
    Lecture,
    QRCodeUpload,
)

# from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
#                      Lecture, QRCodeUpload, is_instructor, is_student,
#                      getUploadsForCourse)

CDT = ZoneInfo("America/Chicago")

# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html)."""
    context = {
        "current_time": datetime.now(CDT).strftime("%H:%M"),
        "logged_in_user": request.user
    }
    return render(request, 'app/index.html', context)

def time_view(request):
    """Return the current Central time in HH:MM format."""
    current_time = datetime.now(CDT)
    return HttpResponse(current_time.strftime("%H:%M"))

def sum_view(request):
    """Return the sum of two numbers as an HTML paragraph."""
    n1 = float(request.GET.get("n1", 0))
    n2 = float(request.GET.get("n2", 0))

    return HttpResponse(f"<p>{n1 + n2}</p>", content_type="text/html")

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------

@require_GET
def new(request):
    """Display the user registration form."""
    return render(request, "app/new.html")

@csrf_exempt
@require_POST
@transaction.atomic
def createUser(request):
    """Create a new student or instructor account."""

    username = request.POST.get("user_name", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    is_student = request.POST.get("is_student")

    if not username or not email or not password:
        return HttpResponseBadRequest("Missing required fields.")

    if is_student not in ("0", "1"):
        return HttpResponseBadRequest("Invalid role.")

    if User.objects.filter(email__iexact=email).exists():
        return HttpResponseBadRequest("Email already registered.")

    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest("Username already taken.")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    if is_student == "1":
        StudentProfile.objects.create(user=user)
    else:
        InstructorProfile.objects.create(user=user)

    login(request, user)

    return HttpResponse("User created successfully.", status=200)

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------

def new_course(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    return render(request, "app/new_course.html")

def new_lecture(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    courses = Course.objects.all()
    return render(request, "app/new_lecture.html", {"courses": courses})

def new_qr_upload(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    return render(request, "app/new_qr_upload.html")

@csrf_exempt
def createCourse(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    instructor = InstructorProfile.objects.filter(user=request.user).first()
    if instructor is None:
        return HttpResponse(status=401)

    if request.method != "POST":
        return HttpResponse(status=405)

    name = request.POST.get("course-name")
    start = request.POST.get("start-time")
    end = request.POST.get("end-time")

    days = []
    for day in ["mon", "tue", "wed", "thu", "fri"]:
        if request.POST.get("day-" + day):
            days.append(day)

    schedule = f"{','.join(days)} {start}-{end}"

    Course.objects.create(
        name=name,
        instructor=instructor,
        meeting_sched=schedule
    )

    return HttpResponse(status=200)


@csrf_exempt
def createLecture(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    instructor = InstructorProfile.objects.filter(user=request.user).first()
    if instructor is None:
        return HttpResponse(status=401)

    if request.method != "POST":
        return HttpResponse(status=405)

    name = request.POST.get("choice")
    course = Course.objects.filter(name=name).first()

    if course is None:
        return HttpResponse(status=400)

    Lecture.objects.create(
        course=course,
        date=timezone.localdate(),
        qr_identifier=str(uuid.uuid4())
    )

    return HttpResponse(status=200)

@csrf_exempt
def createQRCodeUpload(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    student = StudentProfile.objects.filter(user=request.user).first()
    if student is None:
        return HttpResponse(status=401)

    if request.method != "POST":
        return HttpResponse(status=405)

    image = request.FILES.get("imageUpload")

    if image is None:
        return HttpResponse(status=400)

    QRCodeUpload.objects.create(
        student=student,
        image=image
    )

    return HttpResponse(status=200)

def dumpUploads(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    instructor = InstructorProfile.objects.filter(user=request.user).first()
    if instructor is None:
        return HttpResponse(status=401)

    if request.method != "GET":
        return HttpResponse(status=405)

    data = []

    for upload in QRCodeUpload.objects.all():
        data.append({
            "username": upload.student.user.username,
            "upload_time": (
                timezone.localtime(upload.uploaded_at)
                .strftime("%Y-%m-%d %H:%M:%S") 
            )
        })

    return JsonResponse(data, safe=False)

# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



