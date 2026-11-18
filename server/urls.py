from django.urls import path, re_path
from django.http import FileResponse
from django.conf import settings
from django.views.decorators.cache import never_cache
from pilot import api


def index(request):
    return FileResponse(
        open(settings.BASE_DIR / "frontend/dist/index.html", "rb"),
        content_type="text/html",
    )


urlpatterns = [
    path("api/health", api.health),
    path("api/bootstrap", api.bootstrap),
    path("api/login", api.signin),
    path("api/logout", api.signout),
    path("api/floor", api.floor),
    re_path(r"^api/(?P<kind>items|rules)(?:/(?P<pk>\d+))?$", api.catalog),
    path("api/tables/<int:pk>/open", api.open_visit),
    path("api/visits/<int:pk>/close", api.close_visit),
    path("api/visits/<int:pk>/signals", api.signal),
    path("api/suggestions/<int:pk>/outcome", api.outcome),
    path("api/tables/<int:pk>/device", api.manage_device),
    path("api/tables/<int:pk>/problem", api.problem),
    path("api/pair", api.pair),
    path("api/display/updates", api.updates),
    path("api/display", never_cache(api.screen)),
    path("api/settings", api.config),
    path("api/promotions", api.promotions),
    path("api/report", api.report),
    path("api/events.csv", api.report, {"export": True}),
    path("", never_cache(index)),
]
