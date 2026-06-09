"""
Custom JWT authentication for the Customer Portal.

Simple JWT's default JWTAuthentication calls User.objects.get(pk=user_id)
which uses AUTH_USER_MODEL (CustomUser). Portal tokens must resolve to
CustomerAccount instead.

Solution: CustomerJWTAuthentication overrides get_user() to fetch
CustomerAccount. All portal views set authentication_classes to this class.
Portal tokens carry a 'customer_id' claim and 'user_type': 'customer'.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CustomerJWTAuthentication(JWTAuthentication):
    """
    JWT authentication backend for Customer Portal.
    Resolves tokens to CustomerAccount, never to CustomUser.
    Rejects tokens that don't carry user_type='customer'.
    """

    def get_user(self, validated_token):
        from apps.users.models import CustomerAccount

        # Validate this is a portal token
        if validated_token.get('user_type') != 'customer':
            raise InvalidToken('Token is not a portal token.')

        customer_id = validated_token.get('customer_id')
        if customer_id is None:
            raise InvalidToken('Portal token missing customer_id claim.')

        try:
            customer = CustomerAccount.objects.select_related('lead', 'tenant').get(
                pk=customer_id,
                is_active=True,
            )
        except CustomerAccount.DoesNotExist:
            raise InvalidToken('CustomerAccount not found or inactive.')

        return customer
