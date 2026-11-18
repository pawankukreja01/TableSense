"""Rules are evaluated under a lock on the visit. All money is in pence."""

from datetime import timedelta
from zoneinfo import ZoneInfo
from django.utils import timezone
from .models import Event, Item, Line, Rule, Signal, Suggestion


def log(
    table,
    kind,
    visit=None,
    rec=None,
    origin="system",
    detail="",
    verification="operational",
):
    return Event.objects.create(
        table=table,
        visit=visit,
        suggestion=rec,
        kind=kind,
        origin=origin,
        detail=detail,
        verification=verification,
    )


def allowed(rule, visit, signal, ordered, now):
    item = rule.candidate
    tags = {t.strip().lower() for t in item.tags.split(",")}
    current = now.astimezone(ZoneInfo(visit.table.venue.timezone)).time()
    if rule.start and rule.end:
        within = (
            rule.start <= current < rule.end
            if rule.start < rule.end
            else current >= rule.start or current < rule.end
        )
        if not within:
            return False
    offer = getattr(rule, "promotion", None)
    return (
        (not offer or offer.eligible(now))
        and rule.active
        and item.active
        and item.available
        and item.price > 0
        and item.approved_until > now
        and item.id not in ordered
        and set(signal.preferences) <= tags
        and not rule.exclusions.filter(pk__in=ordered).exists()
    )


def ordered_ids(visit):
    return set(
        Line.objects.filter(signal__visit=visit).values_list("item_id", flat=True)
    )


class RuleScorer:
    def score(self, rule):
        return (
            int(rule.trigger_id is not None),
            rule.priority,
            getattr(getattr(rule, "promotion", None), "price", rule.candidate.price)
            - rule.candidate.cost,
            -rule.pk,
        )


class OrderSignalAdapter:
    origin = ""

    def record(self, visit, key, items, stage, preferences, capture_seconds):
        signal = Signal.objects.create(
            visit=visit,
            key=key,
            origin=self.origin,
            stage=stage,
            preferences=preferences,
            capture_seconds=capture_seconds,
        )
        Line.objects.bulk_create(
            [Line(signal=signal, item=item, quantity=qty) for item, qty in items]
        )
        return signal


class StaffSelectorAdapter(OrderSignalAdapter):
    origin = "staff"


class MockPOSAdapter(OrderSignalAdapter):
    origin = "mock_pos"


def evaluate(visit, signal, scorer=None):
    now = timezone.now()
    venue = visit.table.venue
    history = Suggestion.objects.filter(visit=visit)
    history.filter(status="ready").update(status="superseded")
    ordered = ordered_ids(visit)
    categories = set(
        Item.objects.filter(pk__in=ordered).values_list("category", flat=True)
    )
    rules = Rule.objects.filter(venue=venue, stage=signal.stage).select_related(
        "candidate"
    )
    candidates = [
        r
        for r in rules
        if (r.trigger_id in ordered or (not r.trigger_id and r.category in categories))
        and allowed(r, visit, signal, ordered, now)
    ]
    if candidates and not visit.eligible:
        visit.eligible = True
        visit.save(update_fields=["eligible"])
        log(visit.table, "recommendation_eligible", visit)
    if visit.control:
        return
    budget = min(
        2,
        venue.session_cap - history.count(),
        venue.stage_cap - history.filter(signal__stage=signal.stage).count(),
    )
    excluded = set(history.filter(status="dismissed").values_list("item_id", flat=True))
    for rule in sorted(candidates, key=(scorer or RuleScorer()).score, reverse=True):
        if budget <= 0:
            break
        if (
            rule.candidate_id in excluded
            or history.filter(rule=rule).count() >= rule.max_shows
        ):
            continue
        item = rule.candidate
        offer = getattr(rule, "promotion", None)
        expiry = min(now + timedelta(seconds=venue.seconds), item.approved_until)
        Suggestion.objects.create(
            visit=visit,
            signal=signal,
            rule=rule,
            item=item,
            price=offer.price if offer else item.price,
            trace={
                "promotion": offer.pk if offer else None,
                "rule": rule.pk,
                "rule_version": rule.updated.isoformat(),
                "catalog_version": item.updated.isoformat(),
                "reason": rule.reason,
                "score": list((scorer or RuleScorer()).score(rule)),
            },
            expires=min(expiry, offer.end, offer.use_by_cutoff) if offer else expiry,
        )
        excluded.add(item.pk)
        budget -= 1


def current(visit):
    result = []
    now = timezone.now()
    ordered = ordered_ids(visit)
    for rec in (
        Suggestion.objects.select_for_update()
        .filter(visit=visit, status="ready")
        .select_related("item", "rule__candidate", "signal")
        .order_by("pk")
    ):
        if rec.expires <= now:
            rec.status = "timed_out"
            log(visit.table, "recommendation_timed_out", visit, rec)
        elif (
            rec.item.updated.isoformat() != rec.trace["catalog_version"]
            or rec.rule.updated.isoformat() != rec.trace["rule_version"]
            or not allowed(rec.rule, visit, rec.signal, ordered, now)
        ):
            rec.status = "invalidated"
        else:
            result.append(rec)
            continue
        rec.save(update_fields=["status"])
    return result
