from rest_framework import serializers
from .models import Item, Rule


class ItemForm(serializers.ModelSerializer):
    class Meta:
        model = Item
        exclude = ["venue"]

    def validate_image(self, value):
        if value and not (value.startswith("https://") or value.startswith("/images/")):
            raise serializers.ValidationError(
                "Use an HTTPS image URL or a bundled image."
            )
        return value


class RuleForm(serializers.ModelSerializer):
    class Meta:
        model = Rule
        exclude = ["venue"]
        extra_kwargs = {
            "trigger": {"required": False},
            "exclusions": {"required": False},
        }

    def validate(self, data):
        def field(key):
            return data.get(key, getattr(self.instance, key, None))

        if bool(field("trigger")) == bool(field("category")):
            raise serializers.ValidationError(
                "Select exactly one trigger item or category."
            )
        if field("category") and field("category") not in dict(
            Item._meta.get_field("category").choices
        ):
            raise serializers.ValidationError("Unknown trigger category.")
        if bool(field("start")) != bool(field("end")):
            raise serializers.ValidationError("Enter both times for a service window.")
        for item in [field("trigger"), field("candidate"), *data.get("exclusions", [])]:
            if item and item.venue_id != self.context["venue"].pk:
                raise serializers.ValidationError("Unknown item for this venue.")
        return data
