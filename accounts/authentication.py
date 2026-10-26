from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .tokens import ACCESS, TokenError, decode_token, get_user_from_payload


class JWTAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).decode("utf-8").split()
        if not header:
            return None
        if len(header) != 2 or header[0] != self.keyword:
            raise AuthenticationFailed("Authorization header must be: Bearer <access token>.")

        try:
            payload = decode_token(header[1], ACCESS)
            user = get_user_from_payload(payload)
        except TokenError as error:
            raise AuthenticationFailed(str(error))

        request.token_payload = payload
        return user, header[1]

    def authenticate_header(self, request):
        return self.keyword