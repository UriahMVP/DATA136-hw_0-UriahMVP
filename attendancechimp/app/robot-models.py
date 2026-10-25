# LLM: ChatGPT

# Prompt
"""
You are the LLM responsible for generating a the model.py file for the following specifications.


AttendanceChimp tracks class attendance via QR codes:

Users: students and instructors (two roles).
Courses: each has one instructor. Students can enroll in multiple courses.
Lectures: individual class meetings, each associated with a course.
QR Code Uploads: photos uploaded by students, each associated with a student and a lecture.

Design requirements: simple to use, supports attendance analytics, robust to cheating.

1. Draw an Entity Relations (ER) Diagram

Your diagram should show all entities, their attributes, and the relationships between them:

InstructorProfile / StudentProfile tables (instead of one Users table – think why...)
Course table with at least name, instructor, meeting schedule
Enrollment table: links students to courses (many-to-many)
Lecture table: linked to a course, has a date and a QR identifier
QRCodeUpload table: linked to a student and (optionally) a lecture

2. Implement the tables from the list above in models.py

Edit attendancechimp/app/models.py and define Django model classes for each table from the ER diagram (see Django documentation / class slides). Write a detailed docstring and, if applicable, helper functions.

Generate the models.py code according to these specifications.

return the python code in chat
"""

# LLM Generated Code Begins
"""
AttendanceChimp Django Models
-----------------------------

This module defines the database models for AttendanceChimp, a QR-code-based
class attendance tracking application.

Entity Relationships:
    User (Django authentication)
        |-- InstructorProfile (One-to-One)
        |-- StudentProfile (One-to-One)

    InstructorProfile (1) ---- (Many) Course
    StudentProfile (Many) ---- (Many) Course [through Enrollment]
    Course (1) ---- (Many) Lecture
    StudentProfile (1) ---- (Many) QRCodeUpload
    Lecture (1) ---- (Many) QRCodeUpload

Models:
    1. InstructorProfile: Instructor information and authentication.
    2. StudentProfile: Student information and authentication.
    3. Course: Courses taught by instructors.
    4. Enrollment: Student enrollment in courses.
    5. Lecture: Individual course meetings with unique QR codes.
    6. QRCodeUpload: Student-submitted QR code images for attendance.

Attendance verification:
    - Each lecture has a unique QR identifier.
    - QR codes have a limited validity window.
    - Students must be enrolled in a course to receive attendance credit.
    - Each student can submit one upload per lecture.
    - Attendance is counted only when an upload is verified.

Additional server-side verification is necessary to prevent QR sharing,
image manipulation, and other forms of attendance fraud.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InstructorProfile(models.Model):
    """
    Stores information about an instructor.

    Each instructor is linked to a Django authentication user through a
    one-to-one relationship. Separating instructor and student profiles
    allows each role to have its own attributes and relationships.

    Attributes:
        user: Associated Django user account.
        department: Academic department of the instructor.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )

    department = models.CharField(
        max_length=100,
        blank=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StudentProfile(models.Model):
    """
    Stores information about a student.

    Each student is linked to a Django authentication user through a
    one-to-one relationship.

    A student can enroll in multiple courses and upload QR code images
    to record attendance.

    Attributes:
        user: Associated Django user account.
        student_id: Unique university student identifier.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    student_id = models.CharField(
        max_length=50,
        unique=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Course(models.Model):
    """
    Represents a course offered by an instructor.

    Each course has exactly one instructor but can contain many students.
    Students enroll through the Enrollment model, allowing a many-to-many
    relationship between students and courses.

    Attributes:
        name: Name of the course.
        instructor: Instructor responsible for the course.
        meeting_schedule: Days and times when the course meets.
        students: Students enrolled through the Enrollment model.
    """

    name = models.CharField(
        max_length=200,
    )

    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    meeting_schedule = models.CharField(
        max_length=200,
        help_text="Example: Monday/Wednesday 10:30 AM - 11:50 AM",
    )

    students = models.ManyToManyField(
        StudentProfile,
        through="Enrollment",
        related_name="courses",
    )

    def __str__(self):
        return self.name

    def enrollment_count(self):
        """Return the number of students enrolled in this course."""
        return self.enrollments.count()

    def lecture_count(self):
        """Return the number of lectures associated with this course."""
        return self.lectures.count()

    def attendance_rate(self, student):
        """
        Calculate a student's attendance percentage for completed lectures.

        Only verified QR code uploads count toward attendance.

        Args:
            student: A StudentProfile instance.

        Returns:
            Attendance percentage between 0 and 100.

        Raises:
            ValueError: If the student is not enrolled in the course.
        """
        if not self.enrollments.filter(student=student).exists():
            raise ValueError("Student is not enrolled in this course.")

        completed_lectures = self.lectures.filter(
            qr_valid_until__lte=timezone.now()
        )

        total = completed_lectures.count()

        if total == 0:
            return 0.0

        attended = QRCodeUpload.objects.filter(
            student=student,
            lecture__in=completed_lectures,
            status=QRCodeUpload.Status.VERIFIED,
        ).count()

        return round((attended / total) * 100, 2)


class Enrollment(models.Model):
    """
    Represents a student's enrollment in a course.

    This model resolves the many-to-many relationship between students
    and courses.

    Each student may enroll in multiple courses, and each course may
    contain multiple students.

    A database constraint prevents duplicate enrollments.

    Attributes:
        student: Student enrolled in the course.
        course: Course the student is enrolled in.
        enrolled_at: Timestamp when the enrollment was created.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"


class Lecture(models.Model):
    """
    Represents an individual class meeting.

    Each lecture belongs to one course and has a unique QR identifier
    used to verify student attendance.

    QR identifiers are generated using UUIDs to make them difficult
    to guess. A validity window limits when a QR code can be used.

    Attributes:
        course: Course associated with the lecture.
        date: Calendar date of the lecture.
        qr_identifier: Unique UUID identifying the lecture's QR code.
        qr_valid_from: Beginning of the QR code validity window.
        qr_valid_until: End of the QR code validity window.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lectures",
    )

    date = models.DateField()

    qr_identifier = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    qr_valid_from = models.DateTimeField()

    qr_valid_until = models.DateTimeField()

    def __str__(self):
        return f"{self.course.name} - {self.date}"

    def clean(self):
        """Ensure the QR validity window is correctly ordered."""
        super().clean()

        if (
            self.qr_valid_from is not None
            and self.qr_valid_until is not None
            and self.qr_valid_until <= self.qr_valid_from
        ):
            raise ValidationError(
                "QR expiration must occur after QR activation."
            )

    def is_qr_active(self, at_time=None):
        """
        Check whether this lecture's QR code is currently valid.

        Args:
            at_time: Optional datetime to check. Defaults to now.

        Returns:
            True if the QR code is active, otherwise False.
        """
        if at_time is None:
            at_time = timezone.now()

        return (
            self.qr_valid_from <= at_time <= self.qr_valid_until
        )

    def attendance_count(self):
        """Return the number of verified student attendance records."""
        return self.qr_uploads.filter(
            status=QRCodeUpload.Status.VERIFIED
        ).count()


class QRCodeUpload(models.Model):
    """
    Represents a QR code image uploaded by a student.

    Every upload belongs to a student and may optionally be associated
    with a lecture. The lecture field is nullable to support uploads
    that have not yet been matched to a lecture.

    Each upload has a verification status. Attendance is only credited
    when the upload is marked VERIFIED.

    Verification requires:
        1. The upload to be associated with a lecture.
        2. The student to be enrolled in the lecture's course.
        3. The decoded QR identifier to match the lecture's identifier.
        4. The upload timestamp to fall within the QR validity window.

    Attributes:
        student: Student who submitted the image.
        lecture: Associated lecture, if identified.
        image: Uploaded QR code photograph.
        decoded_qr_identifier: UUID extracted from the uploaded image.
        uploaded_at: Timestamp of the upload.
        status: Pending, verified, or rejected.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_uploads",
    )

    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        related_name="qr_uploads",
        null=True,
        blank=True,
    )

    image = models.ImageField(
        upload_to="qr_uploads/",
    )

    decoded_qr_identifier = models.UUIDField(
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lecture"],
                name="unique_student_lecture_upload",
            )
        ]

    def __str__(self):
        lecture_name = str(self.lecture) if self.lecture else "Unassigned"
        return f"{self.student} - {lecture_name} - {self.status}"

    def clean(self):
        """
        Validate the upload's relationship and verification status.

        Prevents attendance credit for students who are not enrolled
        in the associated course or whose QR code is invalid.
        """
        super().clean()

        if self.lecture_id and self.student_id:
            is_enrolled = Enrollment.objects.filter(
                student_id=self.student_id,
                course_id=self.lecture.course_id,
            ).exists()

            if not is_enrolled:
                raise ValidationError(
                    "Student must be enrolled in the lecture's course."
                )

        if self.status == self.Status.VERIFIED:
            if not self.lecture_id:
                raise ValidationError(
                    "A verified upload must be associated with a lecture."
                )

            if self.decoded_qr_identifier != self.lecture.qr_identifier:
                raise ValidationError(
                    "QR identifier does not match the lecture."
                )

            if not self.lecture.is_qr_active(self.uploaded_at):
                raise ValidationError(
                    "QR code was not valid at the upload time."
                )

    def save(self, *args, **kwargs):
        """
        Run model validation before saving an upload.

        This enforces the validation rules for normal model saves,
        including saves made outside Django forms.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def is_verified(self):
        """Return True if this upload has been verified."""
        return self.status == self.Status.VERIFIED
