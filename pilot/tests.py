from datetime import timedelta
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from .models import *


class PilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        cache.clear()
        self.client.force_login(User.objects.get(username="demo-owner"))
        self.tab = Table.objects.get(label="Table 07")
        self.steak = Item.objects.get(name="Grilled Steak")
        self.mush = Item.objects.get(name="Garlic Mushrooms")
        self.visit = self.post("tables/%s/open" % self.tab.id, {}).json()["visit"]
        self.guest = Client()
        self.token = self.bind(self.tab)

    def post(self, url, d):
        return self.client.post("/api/" + url, d, content_type="application/json")

    def bind(self, t):
        code = self.post(f"tables/{t.id}/device", {}).json()["code"]
        return self.post("pair", {"code": code}).json()["token"]

    def signal(self, items=None, key="123", **kwargs):
        return self.post(
            f"visits/{self.visit}/signals",
            {
                "key": key,
                "lines": [{"item": i.pk, "quantity": 1} for i in items or [self.steak]],
                **kwargs,
            },
        )

    def display(self, token=None, d=None):
        kw = {"HTTP_AUTHORIZATION": "Bearer " + (token or self.token)}
        if d is None:
            return self.guest.get("/api/display", **kw).json()
        return self.guest.post(
            "/api/display", d, content_type="application/json", **kw
        ).json()

    def test_walkthrough(self):
        self.assertEqual(self.signal().status_code, 200)
        cards = self.display()["cards"]
        self.assertEqual(
            [(r["name"], r["price"]) for r in cards],
            [("Garlic Mushrooms", 450), ("Fresh Lemonade", 325)],
        )
        ids = [r["id"] for r in cards]
        self.display(d={"action": "shown", "ids": ids})
        self.display(d={"action": "shown", "ids": ids})
        self.assertEqual(Event.objects.filter(kind="recommendation_shown").count(), 2)
        self.assertFalse(self.display(d={"action": "dismiss", "ids": ids})["cards"])
        for outcome in ("requested", "fulfilled", "fulfilled"):
            self.assertEqual(
                self.post(
                    f"suggestions/{ids[0]}/outcome", {"status": outcome}
                ).status_code,
                200,
            )
        self.assertEqual(Outcome.objects.count(), 2)
        self.post(f"visits/{self.visit}/close", {})
        self.post(f"tables/{self.tab.pk}/open", {})
        self.assertFalse(self.display()["cards"])
        self.assertFalse(self.display()["with"])

    def test_table_isolation_and_revoke(self):
        other = self.bind(Table.objects.get(label="Table 05"))
        self.signal()
        self.assertFalse(self.display(other)["cards"])
        self.post(f"tables/{self.tab.pk}/device", {"action": "unpair"})
        self.assertEqual(
            self.guest.get(
                "/api/display", HTTP_AUTHORIZATION="Bearer " + self.token
            ).status_code,
            404,
        )

    def test_single_use_code(self):
        code = self.post(f"tables/{self.tab.pk}/device", {}).json()["code"]
        self.assertEqual(self.post("pair", {"code": code}).status_code, 200)
        self.assertEqual(self.post("pair", {"code": code}).status_code, 404)

    def test_mock_retry(self):
        self.signal(origin="mock_pos")
        self.assertTrue(self.signal(origin="mock_pos").json()["duplicate"])
        self.assertEqual(Signal.objects.count(), 1)
        self.assertEqual(Suggestion.objects.count(), 2)

    def test_known_order_and_unavailability(self):
        self.mush.available = False
        self.mush.save()
        self.signal([self.steak, Item.objects.get(name="Fresh Lemonade")])
        self.assertFalse(self.display()["cards"])

    def test_dietary_and_exclusions(self):
        self.mush.tags = ""
        self.mush.save()
        Rule.objects.get(
            trigger=self.steak, candidate__name="Fresh Lemonade"
        ).exclusions.add(self.steak)
        self.signal(preferences=["vegetarian"])
        self.assertFalse(self.display()["cards"])

    def test_catalog_and_timeout_invalidation(self):
        self.signal()
        self.mush.price = 600
        self.mush.save()
        Suggestion.objects.exclude(item=self.mush).update(
            expires=timezone.now() - timedelta(seconds=1)
        )
        self.assertFalse(self.display()["cards"])
        self.assertEqual(
            Event.objects.filter(kind="recommendation_timed_out").count(), 1
        )

    def test_stale_catalog(self):
        Item.objects.update(approved_until=timezone.now())
        self.signal()
        self.assertFalse(self.display()["cards"])

    def test_dismissal_and_frequency(self):
        Venue.objects.update(session_cap=8, stage_cap=8)
        Rule.objects.update(max_shows=5)
        self.signal()
        self.display(
            d={"action": "dismiss", "ids": [r["id"] for r in self.display()["cards"]]}
        )
        self.signal(key="two")
        self.assertFalse(self.display()["cards"])

    def test_stage_cap_and_dessert(self):
        self.signal()
        self.signal(key="two")
        self.assertFalse(self.display()["cards"])
        self.signal(key="dessert", stage="dessert")
        self.assertEqual(self.display()["cards"][0]["name"], "Lemon Sorbet")

    def test_control(self):
        self.post(f"visits/{self.visit}/close", {})
        Venue.objects.update(control_percent=100)
        self.visit = self.post(f"tables/{self.tab.pk}/open", {}).json()["visit"]
        Venue.objects.update(control_percent=0)
        self.signal()
        self.assertTrue(Visit.objects.get(pk=self.visit).eligible)
        self.assertFalse(self.display()["cards"])

    def test_permissions(self):
        self.client.force_login(User.objects.get(username="demo-staff"))
        for url in ("rules", "settings", "report", "items"):
            self.assertEqual(self.client.get("/api/" + url).status_code, 403)
        self.assertEqual(self.post(f"tables/{self.tab.pk}/device", {}).status_code, 403)
        self.client.logout()
        self.assertIn(self.client.get("/api/floor").status_code, [401, 403])

    def test_tenant_boundaries(self):
        v = Venue.objects.create(name="Other")
        t = Table.objects.create(venue=v, label="Table 07")
        self.assertEqual(self.post(f"tables/{t.pk}/open", {}).status_code, 404)
        other = Item.objects.create(
            venue=v,
            name="Private",
            category="Main",
            price=200,
            cost=100,
            approved_until=timezone.now(),
        )
        self.assertEqual(self.signal([other]).status_code, 404)
        self.assertEqual(
            self.post(
                "rules",
                {"trigger": other.pk, "candidate": self.mush.pk, "reason": "Test"},
            ).status_code,
            400,
        )
        self.assertNotIn(
            other.pk, [i["id"] for i in self.client.get("/api/floor").json()["menu"]]
        )

    def test_trace_and_csv(self):
        self.signal()
        self.assertIn("catalog_version", Suggestion.objects.first().trace)
        self.assertIn(
            "verification", self.client.get("/api/events.csv").content.decode()
        )

    def test_invalid_request(self):
        self.assertEqual(
            self.post(
                f"visits/{self.visit}/signals",
                {"key": "bad", "lines": [{"item": self.steak.pk, "quantity": 0}]},
            ).status_code,
            400,
        )
        self.assertEqual(Signal.objects.count(), 0)

    def test_promotions_disabled(self):
        self.assertEqual(self.client.get("/api/promotions").status_code, 404)

    def test_special_lifecycle(self):
        with self.settings(PROMOTIONS=True):
            now = timezone.now()
            data = {
                "trigger": self.steak.pk,
                "candidate": Item.objects.get(name="Chocolate Brownie").pk,
                "price": 300,
                "stock": 1,
                "reason": "Chocolate to finish your steak dinner.",
                "start": (now - timedelta(minutes=1)).isoformat(),
                "end": (now + timedelta(minutes=10)).isoformat(),
                "use_by_cutoff": (now + timedelta(hours=1)).isoformat(),
                "confirmed_fit": True,
                "trusted_stock": True,
            }
            self.assertEqual(
                self.post("promotions", {**data, "confirmed_fit": False}).status_code,
                400,
            )
            self.assertEqual(
                self.post(
                    "promotions", {**data, "use_by_cutoff": now.isoformat()}
                ).status_code,
                400,
            )
            pk = self.post("promotions", data).json()["id"]
            self.signal(stage="dessert")
            self.assertIn(300, [r["price"] for r in self.display()["cards"]])
            self.post("promotions", {"withdraw": pk})
            self.assertNotIn(300, [r["price"] for r in self.display()["cards"]])

    def test_guest_hint_stream_authorization(self):
        self.assertIn(self.guest.get("/api/display/updates").status_code, [401, 403])
        r = self.guest.get(
            "/api/display/updates", HTTP_AUTHORIZATION="Bearer " + self.token
        )
        self.assertEqual(r["Content-Type"], "text/event-stream")
        self.assertTrue(r.streaming)

    def test_stale_session_cleared(self):
        self.signal()
        Visit.objects.filter(pk=self.visit).update(
            started=timezone.now() - timedelta(hours=13)
        )
        self.assertEqual(self.display()["cards"], [])
        self.assertIsNotNone(Visit.objects.get(pk=self.visit).closed)

    def test_menu_and_pairing_edits_affect_live_state(self):
        self.signal()
        url = f"/api/items/{self.mush.pk}"
        self.assertEqual(
            self.client.patch(
                url, {"available": False}, content_type="application/json"
            ).status_code,
            200,
        )
        self.assertEqual(
            [c["name"] for c in self.display()["cards"]], ["Fresh Lemonade"]
        )
        r = Rule.objects.get(trigger=self.steak, candidate__name="Fresh Lemonade")
        self.assertEqual(
            self.client.patch(
                f"/api/rules/{r.pk}", {"priority": 999}, content_type="application/json"
            ).status_code,
            200,
        )
        self.assertEqual(self.display()["cards"], [])

    def test_burger_fries_and_pizza_examples(self):
        self.signal(
            [
                Item.objects.get(name="House Burger"),
                Item.objects.get(name="Seasoned Fries"),
            ]
        )
        self.assertEqual(
            [c["name"] for c in self.display()["cards"]], ["Fresh Lemonade"]
        )
        self.post(f"visits/{self.visit}/close", {})
        self.visit = self.post(f"tables/{self.tab.pk}/open", {}).json()["visit"]
        self.signal([Item.objects.get(name="Margherita Pizza")])
        self.assertEqual(
            [(c["name"], c["price"]) for c in self.display()["cards"]],
            [("Garlic Bread", 400), ("Sparkling Water", 250)],
        )
