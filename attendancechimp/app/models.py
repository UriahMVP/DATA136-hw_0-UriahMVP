"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo

import logging
import string
import random

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(models.Model):
    name = models.CharField(max_length=100)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE)
    meeting_sched = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)

    course = models.CharField(max_length=20, unique=True, null=True, blank=True)

    mon = models.BooleanField(default=False)
    tue = models.BooleanField(default=False)
    wed = models.BooleanField(default=False)
    thu = models.BooleanField(default=False)
    fri = models.BooleanField(default=False)
    sat = models.BooleanField(default=False)
    sun = models.BooleanField(default=False)

    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def meets_on_day(self, weekday):
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        return getattr(self, days[weekday])

    def __str__(self):
        return self.name

# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return str(self.student) + " - " + str(self.course)

class Lecture(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    qr_identifier = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.course.name + " - " + str(self.date)

# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------

class QRCodeUpload(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="qr_uploads/")

    def __str__(self):
        return str(self.student) + " - " + str(self.uploaded_at)

# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------

def getUploadsForCourse(course):
    selected_course = Course.objects.filter(course=course).first()

    if selected_course is None:
        return []

    if selected_course.start_time is None or selected_course.end_time is None:
        return []

    uploads = QRCodeUpload.objects.filter(
        lecture__course=selected_course
    )

    valid_uploads = []
    chicago = ZoneInfo("America/Chicago")

    for upload in uploads:
        local_dt = timezone.localtime(upload.uploaded_at, chicago)

        weekday = local_dt.weekday()
        upload_time = local_dt.time()

        if (
            selected_course.meets_on_day(weekday)
            and selected_course.start_time <= upload_time <= selected_course.end_time
        ):
            valid_uploads.append(upload)

    return valid_uploads


