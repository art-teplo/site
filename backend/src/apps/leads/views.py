from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.core.utils import client_ip

from .serializers import LeadCreateSerializer
from .tasks import notify_lead


class LeadBurstThrottle(AnonRateThrottle):
    scope = 'leads_burst'


class LeadDayThrottle(AnonRateThrottle):
    scope = 'leads_day'


class LeadCreateView(generics.CreateAPIView):
    """Приём заявки с сайта. Единственная открытая запись в API."""

    serializer_class = LeadCreateSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [LeadBurstThrottle, LeadDayThrottle]

    def create(self, request, *args, **kwargs):  # noqa: ARG002
        # Honeypot: поле скрыто от людей. Боту отвечаем «принято», не сохраняя
        if request.data.get('website'):
            return Response(
                {'ok': True},
                status=status.HTTP_201_CREATED,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save(
            consent_at=timezone.now(),
            consent_ip=client_ip(request),
        )
        transaction.on_commit(lambda: notify_lead.delay(lead.pk))
        return Response(
            {'ok': True},
            status=status.HTTP_201_CREATED,
        )
