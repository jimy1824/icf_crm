from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.serializers import SearchResultSerializer
from apps.search.services import GlobalSearchService


class GlobalSearchView(APIView):
    """
    FM-22: global search across leads, clients, campaigns, communications.
    BRU-35: results pre-filtered by role + tenant before return.
    GET /api/v1/search/?q=<query>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': [], 'query': query})
        results = GlobalSearchService.search(
            tenant=request.user.tenant,
            user=request.user,
            query=query,
        )
        serializer = SearchResultSerializer(results, many=True)
        return Response({'results': serializer.data, 'query': query})
