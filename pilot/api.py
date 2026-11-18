import csv, hashlib, secrets, uuid, re
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction, connection
from django.http import HttpResponse, Http404
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    AuthenticationFailed,
)
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from .catalog import ItemForm, RuleForm
from .engine import current, evaluate, log, MockPOSAdapter, StaffSelectorAdapter
from .models import (
    Promotion,
    Device,
    Event,
    Item,
    Membership,
    Outcome,
    Rule,
    Signal,
    Suggestion,
    Table,
    Venue,
    Visit,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def member(req, manager=False):
    if not req.user or not req.user.is_authenticated:
        raise AuthenticationFailed()
    m = get_object_or_404(Membership.objects.select_related("venue"), user=req.user)
    if manager and m.role == "staff":
        raise PermissionDenied()
    return m


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValidationError(f"{label} must be between {low} and {high}.")
    return value


class PerIP(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PairLimit(PerIP):
    scope = "pair"


@api_view(["GET"])
@ensure_csrf_cookie
def bootstrap(req):
    m = (
        Membership.objects.filter(user=req.user).select_related("venue").first()
        if req.user
        else None
    )
    return Response(
        {
            "demo": settings.DEMO_MODE,
            "promotions": settings.PROMOTIONS,
            "role": m.role if m else None,
            "name": m.venue.name if m else None,
        }
    )


@api_view(["POST"])
@throttle_classes([PerIP])
@csrf_protect
def signin(req):
    user = authenticate(
        username=req.data.get("username"), password=req.data.get("password")
    )
    if not user or not Membership.objects.filter(user=user).exists():
        raise AuthenticationFailed("Check your username and password.")
    login(req, user)
    return Response({"ok": True})


@api_view(["POST"])
def signout(req):
    member(req)
    logout(req)
    return Response({"ok": True})


def card(rec):
    return {
        "id": rec.pk,
        "name": rec.item.name,
        "image": rec.item.image,
        "category": rec.item.category,
        "price": rec.price,
        "special": bool(rec.trace.get("promotion")),
        "reason": rec.trace["reason"],
        "expires": rec.expires,
    }


def expire_stale(venue):
    cutoff = timezone.now() - timedelta(hours=12)
    for visit in Visit.objects.select_for_update().filter(
        table__venue=venue, closed=None, started__lt=cutoff
    ):
        visit.closed = timezone.now()
        visit.save(update_fields=["closed"])
        visit.suggestion_set.filter(status="ready").update(status="closed")
        log(visit.table, "session_closed", visit, detail="12-hour session timeout")


@api_view(["GET"])
@transaction.atomic
def floor(req):
    m = member(req)
    expire_stale(m.venue)
    tables = []
    now = timezone.now()
    for t in Table.objects.filter(venue=m.venue).order_by("label"):
        visit = Visit.objects.select_for_update().filter(table=t, closed=None).first()
        dev = Device.objects.filter(table=t).first()
        online = bool(
            dev
            and dev.token_hash
            and dev.last_seen
            and dev.last_seen > now - timedelta(seconds=20)
        )
        if (
            dev
            and dev.token_hash
            and dev.last_seen
            and not online
            and not dev.offline_logged
        ):
            Device.objects.filter(pk=dev.pk).update(offline_logged=True)
            log(t, "device_offline", visit)
        recs = current(visit) if visit else []
        history = (
            Suggestion.objects.filter(visit=visit)
            .select_related("item")
            .order_by("-pk")
            if visit
            else []
        )
        tables.append(
            {
                "id": t.pk,
                "label": t.label,
                "visit": visit.pk if visit else None,
                "control": bool(visit and visit.control),
                "paired": bool(dev and dev.token_hash),
                "online": online,
                "last_seen": dev.last_seen if dev else None,
                "battery": dev.battery if dev else None,
                "version": dev.version if dev else "",
                "cards": [card(r) for r in recs],
                "history": [
                    {
                        **card(r),
                        "seen": r.seen,
                        "status": r.status,
                        "trace": r.trace if m.role != "staff" else None,
                        "outcomes": list(
                            r.outcome_set.values_list("status", flat=True)
                        ),
                    }
                    for r in history
                ],
            }
        )
    return Response(
        {
            "tables": tables,
            "menu": (
                ItemForm(
                    Item.objects.filter(venue=m.venue).order_by("pk"), many=True
                ).data
                if m.role != "staff"
                else list(
                    Item.objects.filter(venue=m.venue, active=True).values(
                        "id", "name", "price", "category", "image", "available"
                    )
                )
            ),
            "venue": m.venue.name,
            "currency": m.venue.currency,
            "role": m.role,
        }
    )


@api_view(["GET", "POST", "PATCH"])
@transaction.atomic
def catalog(req, kind, pk=None):
    m = member(req, True)
    model, form = (Item, ItemForm) if kind == "items" else (Rule, RuleForm)
    rows = model.objects.filter(venue=m.venue)
    if req.method == "GET":
        return Response(form(rows.order_by("pk"), many=True).data)
    if (pk is None) != (req.method == "POST"):
        raise ValidationError("Use POST to create and PATCH to edit.")
    row = get_object_or_404(rows.select_for_update(), pk=pk) if pk else None
    if kind == "rules" and row and hasattr(row, "promotion"):
        raise ValidationError(
            "Withdraw this special and approve a replacement to change its rule."
        )
    data = form(row, data=req.data, partial=row is not None, context={"venue": m.venue})
    data.is_valid(raise_exception=True)
    data.save(venue=m.venue)
    return Response(data.data)


@api_view(["POST"])
@transaction.atomic
def open_visit(req, pk):
    m = member(req)
    t = get_object_or_404(Table.objects.select_for_update(), pk=pk, venue=m.venue)
    expire_stale(m.venue)
    if Visit.objects.filter(table=t, closed=None).exists():
        raise ValidationError("This table already has an open session.")
    key = uuid.uuid4()
    v = Visit.objects.create(
        key=key,
        table=t,
        control=int(digest(str(key))[:12], 16) % 100 < m.venue.control_percent,
    )
    log(t, "session_started", v, origin="staff")
    return Response({"visit": v.pk})


def locked_visit(req, pk):
    m = member(req)
    return get_object_or_404(
        Visit.objects.select_for_update(),
        pk=pk,
        table__venue=m.venue,
        closed=None,
        started__gt=timezone.now() - timedelta(hours=12),
    )


@api_view(["POST"])
@transaction.atomic
def close_visit(req, pk):
    v = locked_visit(req, pk)
    v.closed = timezone.now()
    v.save(update_fields=["closed"])
    v.suggestion_set.filter(status="ready").update(status="closed")
    log(v.table, "session_closed", v, origin="staff")
    return Response({"ok": True})


@api_view(["POST"])
@transaction.atomic
def signal(req, pk):
    v = locked_visit(req, pk)
    d = req.data
    key = d.get("key")
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise ValidationError("A unique signal key is required.")
    origin = d.get("origin", "staff")
    if origin not in ("staff", "mock_pos") or (
        origin == "mock_pos" and not settings.DEMO_MODE
    ):
        raise ValidationError("Unsupported signal source.")
    existing = Signal.objects.filter(visit=v, key=key).first()
    if existing:
        return Response({"id": existing.pk, "duplicate": True})
    stage = d.get("stage", "main")
    prefs = d.get("preferences", [])
    if (
        stage not in ("main", "dessert")
        or not isinstance(prefs, list)
        or any(p not in ["vegetarian", "vegan"] for p in prefs)
    ):
        raise ValidationError("Unsupported stage or preference.")
    rows = d.get("lines")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 60:
        raise ValidationError("Select at least one ordered item.")
    items = []
    for line in rows:
        if not isinstance(line, dict):
            raise ValidationError("Invalid order line.")
        item = get_object_or_404(
            Item, pk=integer(line.get("item"), 1, 2**31, "Item"), venue=v.table.venue
        )
        items.append((item, integer(line.get("quantity"), 1, 99, "Quantity")))
    adapter = MockPOSAdapter() if origin == "mock_pos" else StaffSelectorAdapter()
    s = adapter.record(
        v,
        key,
        items,
        stage,
        prefs,
        integer(d.get("capture_seconds", 0), 0, 86400, "Capture time"),
    )
    log(
        v.table,
        "order_signal_received",
        v,
        origin=origin,
        detail=", ".join(i.name for i, _ in items)[:200],
    )
    evaluate(v, s)
    return Response({"id": s.pk, "duplicate": False})


@api_view(["POST"])
@transaction.atomic
def outcome(req, pk):
    m = member(req)
    r = get_object_or_404(
        Suggestion.objects.select_for_update(), pk=pk, visit__table__venue=m.venue
    )
    status = req.data.get("status")
    if status not in ("requested", "fulfilled", "not_fulfilled", "unknown"):
        raise ValidationError("Unknown outcome.")
    if not r.seen:
        raise ValidationError("This suggestion has no confirmed impression.")
    if Outcome.objects.filter(
        suggestion=r, status__in=["fulfilled", "not_fulfilled"]
    ).exclude(status=status).exists() and status in ("fulfilled", "not_fulfilled"):
        raise ValidationError("A final outcome is already recorded.")
    _, created = Outcome.objects.get_or_create(
        suggestion=r, status=status, defaults={"staff": req.user}
    )
    if created and status == "fulfilled" and r.trace.get("promotion"):
        p = Promotion.objects.select_for_update().get(pk=r.trace["promotion"])
        p.stock = max(0, p.stock - 1)
        p.save(update_fields=["stock"])
    if created:
        log(
            r.visit.table,
            "staff_marked_" + status,
            r.visit,
            r,
            "staff",
            r.item.name,
            "manual_unverified",
        )
    return Response({"ok": True})


@api_view(["POST"])
@transaction.atomic
def manage_device(req, pk):
    m = member(req, True)
    t = get_object_or_404(Table.objects.select_for_update(), pk=pk, venue=m.venue)
    dev, _ = Device.objects.get_or_create(table=t)
    if req.data.get("action") == "unpair":
        dev.delete()
        return Response({"ok": True})
    code = secrets.token_hex(4).upper()
    dev.code_hash = digest(code)
    dev.code_until = timezone.now() + timedelta(minutes=5)
    dev.save()
    return Response({"code": code, "expires": dev.code_until})


@api_view(["POST"])
@throttle_classes([PairLimit])
@transaction.atomic
def pair(req):
    code = str(req.data.get("code", "")).strip().upper()
    dev = get_object_or_404(
        Device.objects.select_for_update(),
        code_hash=digest(code),
        code_until__gt=timezone.now(),
    )
    token = secrets.token_urlsafe(32)
    dev.token_hash = digest(token)
    dev.code_hash = ""
    dev.code_until = None
    dev.last_seen = None
    dev.battery = None
    dev.save()
    return Response({"token": token})


def device(req):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthenticationFailed("Pair this display.")
    return get_object_or_404(
        Device.objects.select_for_update(), token_hash=digest(auth[7:])
    )


@api_view(["GET", "POST"])
@transaction.atomic
def screen(req):
    dev = device(req)
    t = dev.table
    expire_stale(t.venue)
    v = Visit.objects.select_for_update().filter(table=t, closed=None).first()
    recs = current(v) if v else []
    action = req.data.get("action") if req.method == "POST" else None
    if action in ("dismiss", "shown"):
        ids = req.data.get("ids", [])
        for r in recs:
            if r.pk not in ids:
                continue
            if action == "shown" and not r.seen:
                r.seen = True
                r.save(update_fields=["seen"])
                log(t, "recommendation_shown", v, r, "display", r.item.name)
            if action == "dismiss":
                r.status = "dismissed"
                r.save(update_fields=["status"])
                log(t, "recommendation_dismissed", v, r, "display", r.item.name)
        if action == "dismiss":
            recs = current(v)
    dev.last_seen = timezone.now()
    dev.version = "web-1.0"
    dev.offline_logged = False
    if req.data.get("battery") is not None:
        dev.battery = integer(req.data["battery"], 0, 100, "Battery")
    dev.save()
    return Response(
        {
            "venue": t.venue.name,
            "table": t.label,
            "currency": t.venue.currency,
            "logo": t.venue.logo,
            "accent": t.venue.accent,
            "demo": settings.DEMO_MODE,
            "battery": dev.battery,
            "cards": [card(r) for r in recs],
            "with": (
                ", ".join(
                    dict.fromkeys(
                        name
                        for name in v.signal_set.values_list(
                            "line__item__name", flat=True
                        )
                        if name
                    )
                )
                if recs
                else ""
            ),
        }
    )


@api_view(["GET", "POST"])
def config(req):
    v = member(req, True).venue
    if req.method == "POST":
        for k, lo, hi in [
            ("control_percent", 0, 100),
            ("seconds", 10, 600),
            ("session_cap", 1, 12),
            ("stage_cap", 1, 6),
        ]:
            if k in req.data:
                setattr(v, k, integer(req.data[k], lo, hi, k))
        accent = req.data.get("accent", v.accent)
        logo = req.data.get("logo", v.logo)
        name = str(req.data.get("name", v.name)).strip()
        if (
            not name
            or len(name) > 80
            or not re.fullmatch(r"#[0-9a-fA-F]{6}", str(accent))
            or (logo and not str(logo).startswith("https://"))
        ):
            raise ValidationError("Check venue name, hex accent and HTTPS logo.")
        v.name, v.accent, v.logo = name, accent, logo
        v.save()
    return Response(
        {
            k: getattr(v, k)
            for k in (
                "name",
                "accent",
                "logo",
                "control_percent",
                "seconds",
                "session_cap",
                "stage_cap",
            )
        }
    )


@api_view(["POST"])
def problem(req, pk):
    t = get_object_or_404(Table, pk=pk, venue=member(req).venue)
    note = str(req.data.get("detail", "")).strip()[:200]
    if not note:
        raise ValidationError("Describe the issue.")
    log(t, "device_problem", origin="staff", detail=note)
    return Response({"ok": True})


@api_view(["GET"])
def report(req, export=False):
    v = member(req, True).venue
    events = Event.objects.filter(table__venue=v).order_by("-pk")
    rows = events.values(
        "key",
        "created",
        "table__label",
        "visit_id",
        "suggestion_id",
        "kind",
        "origin",
        "verification",
        "detail",
    )
    if export:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tablesense-events.csv"'
        writer = csv.writer(response)
        writer.writerow(rows._fields)
        for row in rows.iterator():
            writer.writerow(
                [
                    (
                        "'" + x
                        if isinstance(x, str)
                        and x.startswith(("=", "-", "+", "@", "\t", "\r"))
                        else x
                    )
                    for x in row.values()
                ]
            )
        return response
    groups = []
    for control in (False, True):
        visits = Visit.objects.filter(table__venue=v, control=control)
        ev = events.filter(visit__in=visits)
        groups.append(
            {
                "group": "Control" if control else "Treatment",
                "sessions": visits.count(),
                "eligible": visits.filter(eligible=True).count(),
                **{
                    k: ev.filter(kind=k).count()
                    for k in [
                        "recommendation_shown",
                        "recommendation_dismissed",
                        "staff_marked_requested",
                        "staff_marked_fulfilled",
                    ]
                },
            }
        )
    return Response(
        {
            "groups": groups,
            "events": list(rows[:100]),
            "capture_seconds": list(
                Signal.objects.filter(visit__table__venue=v, origin="staff")
                .order_by("-pk")
                .values_list("capture_seconds", flat=True)[:100]
            ),
        }
    )


@api_view(["GET"])
def health(req):
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"status": "ok"})


@api_view(["GET", "POST"])
@transaction.atomic
def promotions(req):
    if not settings.PROMOTIONS:
        raise Http404
    m = member(req, True)
    rows = Promotion.objects.filter(rule__venue=m.venue)
    if req.method == "GET":
        now = timezone.now()
        return Response(
            [
                {
                    "id": p.pk,
                    "name": p.rule.candidate.name,
                    "stock": p.stock,
                    "price": p.price,
                    "end": p.end,
                    "eligible": p.eligible(now),
                    "withdrawn": p.withdrawn,
                }
                for p in rows.select_related("rule__candidate")
            ]
        )
    if req.data.get("withdraw"):
        p = get_object_or_404(rows.select_for_update(), pk=req.data["withdraw"])
        if not p.withdrawn:
            p.withdrawn = timezone.now()
            p.save(update_fields=["withdrawn"])
            for t in Table.objects.filter(venue=m.venue):
                log(t, "promotion_withdrawn", origin="manager", detail=str(p.pk))
        return Response({"ok": True})
    d = req.data
    candidate = get_object_or_404(
        Item,
        pk=d.get("candidate"),
        venue=m.venue,
        active=True,
        available=True,
        approved_until__gt=timezone.now(),
    )
    trigger = get_object_or_404(Item, pk=d.get("trigger"), venue=m.venue)
    try:
        start, end, cutoff = [
            parse_datetime(d.get(k, "")) for k in ("start", "end", "use_by_cutoff")
        ]
        valid = start < end <= cutoff and end > timezone.now()
    except (ValueError, TypeError):
        valid = False
    if (
        not valid
        or d.get("confirmed_fit") is not True
        or d.get("trusted_stock") is not True
    ):
        raise ValidationError(
            "Confirm suitability and stock. End must follow start and precede or equal the use-by cutoff."
        )
    reason = str(d.get("reason", "")).strip()
    if not reason or len(reason) > 160:
        raise ValidationError("Provide a pairing reason.")
    rule = Rule.objects.create(
        venue=m.venue,
        trigger=trigger,
        candidate=candidate,
        stage="dessert",
        priority=100,
        reason=reason,
    )
    p = Promotion.objects.create(
        rule=rule,
        price=integer(d.get("price"), 1, candidate.price, "Approved price"),
        stock=integer(d.get("stock"), 1, 9999, "Available servings"),
        start=start,
        end=end,
        use_by_cutoff=cutoff,
        confirmed_fit=True,
        trusted_stock=True,
        approved_by=req.user,
    )
    return Response({"id": p.pk})


@api_view(["GET"])
def updates(req):
    """Guest-scoped invalidation hints. The state endpoint remains authoritative."""
    import time
    from django.http import StreamingHttpResponse

    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise AuthenticationFailed()
    key = digest(header[7:])
    dev = get_object_or_404(Device, token_hash=key)

    def stream():
        latest = 0
        for tick in range(12):
            if not Device.objects.filter(pk=dev.pk, token_hash=key).exists():
                yield "data: reset\n\n"
                return
            event = (
                Event.objects.filter(
                    table_id=dev.table_id,
                    kind__in=(
                        "session_started",
                        "session_closed",
                        "order_signal_received",
                        "promotion_withdrawn",
                    ),
                )
                .order_by("-pk")
                .values_list("pk", flat=True)
                .first()
                or 0
            )
            if event != latest:
                yield "data: refresh\n\n"
                latest = event
            elif tick % 4 == 0:
                yield ": heartbeat\n\n"
            time.sleep(1)

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"
    return response
