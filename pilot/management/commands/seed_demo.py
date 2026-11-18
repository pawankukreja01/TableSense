from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from pilot.models import User, Venue, Membership, Item, Rule, Table


class Command(BaseCommand):
    help = "Seed local sample data and demo accounts once."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if not settings.DEMO_MODE:
            raise CommandError("Demo mode is disabled.")
        v, created = Venue.objects.get_or_create(name="Demo Bistro")
        if not created:
            return
        for role in ("owner", "staff"):
            user = User.objects.create_user("demo-" + role, password="bistro-demo")
            Membership.objects.create(user=user, venue=v, role=role)
        for i in range(1, 9):
            Table.objects.create(venue=v, label=f"Table {i:02}")
        rows = [
            ("Grilled Steak", "Main", 2100, 780, "steak", ""),
            ("House Burger", "Main", 1450, 490, "burger", ""),
            ("Margherita Pizza", "Main", 1300, 340, "pizza", "vegetarian"),
            ("Garden Bowl", "Main", 1250, 340, "garden", "vegan,vegetarian"),
            ("Garlic Mushrooms", "Side", 450, 140, "mushrooms", "vegetarian"),
            ("Seasoned Fries", "Side", 350, 95, "fries", "vegan,vegetarian"),
            ("Garlic Bread", "Side", 400, 110, "bread", "vegetarian"),
            ("Leaf Salad", "Side", 450, 135, "garden", "vegan,vegetarian"),
            ("Fresh Lemonade", "Drink", 325, 85, "lemonade", "vegan,vegetarian"),
            ("Sparkling Water", "Drink", 250, 80, "", "vegan,vegetarian"),
            ("Mint Tea", "Drink", 275, 60, "", "vegan,vegetarian"),
            ("Espresso", "Drink", 250, 65, "", "vegan,vegetarian"),
            ("Chocolate Brownie", "Dessert", 550, 190, "", "vegetarian"),
            ("Lemon Sorbet", "Dessert", 475, 140, "", "vegan,vegetarian"),
            ("Vanilla Gelato", "Dessert", 495, 155, "", "vegetarian"),
        ]
        items = []
        for name, cat, price, cost, image, tags in rows:
            items.append(
                Item.objects.create(
                    venue=v,
                    name=name,
                    category=cat,
                    price=price,
                    cost=cost,
                    image=f"/images/{image}.jpg" if image else "",
                    tags=tags,
                    allergens="Demo entry. Confirm ingredients with the waiter.",
                    approved_until=timezone.now() + timedelta(days=30),
                )
            )
        for trigger, candidate, priority, reason in [
            (
                0,
                4,
                90,
                "Garlic and earthy mushrooms complement the char on your steak.",
            ),
            (0, 8, 80, "Fresh citrus balances the richness of grilled steak."),
            (1, 5, 90, "A crisp, lightly seasoned side for your house burger."),
            (1, 8, 80, "A bright citrus pairing for your burger."),
            (2, 6, 90, "Warm garlic bread for the last of your tomato sauce."),
            (2, 9, 80, "A cool, sparkling finish alongside your pizza."),
            (3, 10, 80, "Fresh mint complements your garden bowl."),
        ]:
            Rule.objects.create(
                venue=v,
                trigger=items[trigger],
                candidate=items[candidate],
                priority=priority,
                reason=reason,
            )
        Rule.objects.create(
            venue=v,
            category="Main",
            candidate=items[13],
            stage="dessert",
            reason="A light citrus finish to your meal.",
        )
