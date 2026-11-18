import uuid
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Venue(models.Model):
    name = models.CharField(max_length=80)
    currency = models.CharField(max_length=3, default="GBP")
    timezone = models.CharField(max_length=60, default="Europe/London")
    control_percent = models.PositiveSmallIntegerField(default=0)
    seconds = models.PositiveIntegerField(default=120)
    session_cap = models.PositiveSmallIntegerField(default=4)
    stage_cap = models.PositiveSmallIntegerField(default=2)
    logo = models.URLField(blank=True)
    accent = models.CharField(max_length=7, default="#315b43")


class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10, choices=[(v, v) for v in ("owner", "manager", "staff")]
    )


class Table(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    label = models.CharField(max_length=30)

    class Meta:
        unique_together = ("venue", "label")


class Device(models.Model):
    table = models.OneToOneField(Table, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64, blank=True)
    code_until = models.DateTimeField(null=True)
    token_hash = models.CharField(max_length=64, blank=True)
    last_seen = models.DateTimeField(null=True)
    battery = models.PositiveSmallIntegerField(null=True)
    version = models.CharField(max_length=24, blank=True)
    offline_logged = models.BooleanField(default=False)


class Item(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    category = models.CharField(
        max_length=12, choices=[(v, v) for v in ("Main", "Side", "Drink", "Dessert")]
    )
    price = models.PositiveIntegerField(help_text="minor currency units")
    cost = models.PositiveIntegerField()
    description = models.CharField(max_length=220, blank=True)
    image = models.CharField(max_length=500, blank=True)
    tags = models.CharField(max_length=200, blank=True)
    allergens = models.CharField(max_length=250, blank=True)
    available = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    approved_until = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)


class Rule(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    trigger = models.ForeignKey(
        Item, on_delete=models.CASCADE, null=True, related_name="+"
    )
    category = models.CharField(max_length=12, blank=True)
    candidate = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=160)
    priority = models.PositiveSmallIntegerField(default=10)
    stage = models.CharField(
        max_length=12,
        choices=[("main", "main"), ("dessert", "dessert")],
        default="main",
    )
    max_shows = models.PositiveSmallIntegerField(default=1)
    exclusions = models.ManyToManyField(Item, blank=True, related_name="+")
    start = models.TimeField(null=True, blank=True)
    end = models.TimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    updated = models.DateTimeField(auto_now=True)


class Visit(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    started = models.DateTimeField(auto_now_add=True)
    closed = models.DateTimeField(null=True)
    control = models.BooleanField()
    eligible = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["table"], condition=Q(closed=None), name="one_open_visit"
            )
        ]


class Signal(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    origin = models.CharField(max_length=20)
    stage = models.CharField(max_length=12)
    preferences = models.JSONField(default=list)
    created = models.DateTimeField(default=timezone.now)
    capture_seconds = models.PositiveIntegerField(null=True)

    class Meta:
        unique_together = ("visit", "key")


class Line(models.Model):
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()


class Suggestion(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE)
    rule = models.ForeignKey(Rule, on_delete=models.PROTECT)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    price = models.PositiveIntegerField()
    trace = models.JSONField()
    expires = models.DateTimeField()
    status = models.CharField(max_length=20, default="ready")
    seen = models.BooleanField(default=False)


class Outcome(models.Model):
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    staff = models.ForeignKey(User, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("suggestion", "status")


class Event(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    visit = models.ForeignKey(Visit, null=True, on_delete=models.CASCADE)
    suggestion = models.ForeignKey(Suggestion, null=True, on_delete=models.CASCADE)
    kind = models.CharField(max_length=40)
    origin = models.CharField(max_length=24, default="system")
    verification = models.CharField(max_length=24, default="operational")
    detail = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)


class Promotion(models.Model):
    """Explicit manager inventory decision; only its attached rule may use the special price."""

    rule = models.OneToOneField(Rule, on_delete=models.PROTECT)
    price = models.PositiveIntegerField()
    stock = models.PositiveIntegerField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    use_by_cutoff = models.DateTimeField()
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT)
    confirmed_fit = models.BooleanField(default=False)
    trusted_stock = models.BooleanField(default=False)
    withdrawn = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)

    def eligible(self, now):
        from django.conf import settings

        return (
            settings.PROMOTIONS
            and self.confirmed_fit
            and self.trusted_stock
            and self.stock > 0
            and self.price > 0
            and self.start <= now < min(self.end, self.use_by_cutoff)
            and self.withdrawn is None
        )
