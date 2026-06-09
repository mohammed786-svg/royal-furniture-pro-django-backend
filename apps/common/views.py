from rest_framework.views import APIView

from core.cache import redis_health_check
from core.database import health_check as db_health_check
from core.responses import APIResponse


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db_ok = db_health_check()
        redis_ok = redis_health_check()
        healthy = db_ok and redis_ok
        return APIResponse.success(
            data={
                "status": "healthy" if healthy else "degraded",
                "database": db_ok,
                "redis": redis_ok,
            },
            message="Health check",
            status_code=200 if healthy else 503,
        )
