from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    MAX_MEMBERS = 6

    def member_count(self):
        return self.members.count()

    def is_full(self):
        return self.member_count() >= self.MAX_MEMBERS


class Member(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "household")

    def is_admin(self):
        return self.role == self.ROLE_ADMIN


class Chore(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLAIMED = "claimed"
    STATUS_COMPLETED = "completed"
    STATUS_DISPUTED = "disputed"
    STATUS_FINALIZED = "finalized"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLAIMED, "Claimed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_DISPUTED, "Disputed"),
        (STATUS_FINALIZED, "Finalized"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=1)
    due_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    created_by = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="created_chores")
    claimed_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="claimed_chores")
    reminder_level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    dispute_window_hours = models.PositiveIntegerField(default=24)
    finalized_at = models.DateTimeField(null=True, blank=True)

    def claim(self, member):
        if self.status != self.STATUS_OPEN:
            raise ValueError("Chore is not open for claiming")
        if self.claimed_by is not None:
            raise ValueError("Chore already claimed")
        self.claimed_by = member
        self.status = self.STATUS_CLAIMED
        self.reminder_level = 0
        self.save()

    def complete(self):
        if self.status != self.STATUS_CLAIMED:
            raise ValueError("Chore must be claimed before completing")
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save()

    def dispute(self):
        if self.status != self.STATUS_COMPLETED:
            raise ValueError("Only completed chores can be disputed")
        self.status = self.STATUS_DISPUTED
        self.save()

    def is_dispute_window_open(self):
        if not self.completed_at:
            return False
        from datetime import timedelta
        return timezone.now() < self.completed_at + timedelta(hours=self.dispute_window_hours)

    def finalize(self):
        if self.status != self.STATUS_COMPLETED:
            raise ValueError("Only completed chores can be finalized")
        self.status = self.STATUS_FINALIZED
        self.finalized_at = timezone.now()
        self.save()
        PointLog.objects.create(
            chore=self,
            member=self.claimed_by,
            points=self.points,
            household=self.household,
        )

    def escalate_reminder(self):
        if self.status == self.STATUS_OPEN:
            self.reminder_level += 1
            self.save()


class PointLog(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="point_logs")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="point_logs")
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="point_logs")
    points = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
