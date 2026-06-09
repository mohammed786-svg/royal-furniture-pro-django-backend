from rest_framework.views import APIView

from core.responses import APIResponse


class APIv2RootView(APIView):
    def get(self, request):
        return APIResponse.success(
            data={"version": "v2", "status": "reserved"},
            message="Royal Furniture Pro API v2 (reserved)",
        )
