import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP


class OTPError(Exception):
    pass


def send_verification_otp(user):
    user.email_otps.filter(is_used=False).update(is_used=True)
    code = f"{secrets.randbelow(1000000):06d}"
    EmailOTP.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_LIFETIME_MINUTES),
    )
    send_mail(
        subject="Verify your HR Admin account",
        message=f"Hello {user.first_name},\n\nYour verification code is {code}. It expires in {settings.OTP_LIFETIME_MINUTES} minutes.",
        from_email=None,
        recipient_list=[user.email],
    )


def verify_otp(user, code):
    otp = user.email_otps.filter(is_used=False).first()
    if otp is None:
        raise OTPError("There is no active code for this account. Please request a new one.")
    if otp.expires_at < timezone.now():
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        raise OTPError("This code has expired. Please request a new one.")
    if not check_password(code, otp.code_hash):
        raise OTPError("Incorrect code.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    user.is_active = True
    user.email_verified = True
    user.save(update_fields=["is_active", "email_verified"])
