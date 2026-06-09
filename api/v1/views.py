from rest_framework.views import APIView

from core.responses import APIResponse


class APIv1RootView(APIView):
    """API v1 root — version metadata only."""

    def get(self, request):
        return APIResponse.success(
            data={"version": "v1", "status": "ready"},
            message="Royal Furniture Pro API v1",
            endpoint=request.path,
        )
