from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Membership
from .serializers import MembershipSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def membership_me(request):
    membership, _ = Membership.objects.get_or_create(
        user=request.user,
        defaults={"status": Membership.Status.NONE},
    )
    return Response(MembershipSerializer(membership).data, status=status.HTTP_200_OK)
