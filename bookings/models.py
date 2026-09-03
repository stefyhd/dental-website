from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=100)
    duration = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Patient(models.Model):
    name = models.CharField(max_length=120, db_index=True)
    phone = models.CharField(max_length=30, unique=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.phone}"

class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "În așteptare"
        CONFIRMED = "confirmed", "Confirmată"
        REJECTED = "rejected", "Respinsă"
        CANCELLED = "cancelled", "Anulată"
        COMPLETED = "completed", "Finalizată"
        NO_SHOW = "no_show", "Neprezentat"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    date = models.DateField()
    time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(blank=True)

    follow_up_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="follow_ups",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.date} {self.time}"


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Luni"
        TUESDAY = 1, "Marți"
        WEDNESDAY = 2, "Miercuri"
        THURSDAY = 3, "Joi"
        FRIDAY = 4, "Vineri"
        SATURDAY = 5, "Sâmbătă"
        SUNDAY = 6, "Duminică"

    weekday = models.IntegerField(choices=Weekday.choices, unique=True)
    opening_time = models.TimeField(default="09:00")
    closing_time = models.TimeField(default="17:00")
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["weekday"]

    def __str__(self):
        if self.is_closed:
            return f"{self.get_weekday_display()} - Închis"
        return f"{self.get_weekday_display()} - {self.opening_time}–{self.closing_time}"


class ScheduleBlock(models.Model):
    date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    reason = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        if self.all_day:
            return f"{self.date} - {self.end_date or self.date} - toată ziua"
        return f"{self.date} - {self.start_time}–{self.end_time}"