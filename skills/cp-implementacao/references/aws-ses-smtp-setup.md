# AWS SES SMTP Setup for Django

## Overview

AWS SES (Simple Email Service) is used for transactional email (password reset, invites, notifications). It is NOT a corporate email hosting service — it only sends email, it does not provide inboxes.

## Prerequisites

- AWS account with SES access
- Domain registered in Route53 (or DNS managed elsewhere)
- IAM user with `AmazonSESFullAccess` policy

## Step-by-step

### 1. Verify the domain in SES

```bash
aws ses verify-domain-identity --domain crewbotic.ai
```

Returns a `VerificationToken` like `xrf26ZSJ+qk3Yn/VukKQceUK5qSSZPr2DPzLltbbpEA=`.

### 2. Add TXT record to Route53

```json
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "_amazonses.crewbotic.ai.",
      "Type": "TXT",
      "TTL": 300,
      "ResourceRecords": [{"Value": "\"xrf26ZSJ+qk3Yn/VukKQceUK5qSSZPr2DPzLltbbpEA=\""}]
    }
  }]
}
```

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1044394J0K90G3N5A17 \
  --change-batch file://change-batch.json
```

### 3. Create a dedicated IAM user for SES SMTP

```bash
aws iam create-user --user-name ses-smtp-crewbotic
aws iam attach-user-policy \
  --user-name ses-smtp-crewbotic \
  --policy-arn arn:aws:iam::aws:policy/AmazonSESFullAccess
```

### 4. Create SMTP credentials

```bash
aws iam create-access-key --user-name ses-smtp-crewbotic
```

Save the `SecretAccessKey` immediately — it's shown only once.

### 5. Django settings

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "email-smtp.us-east-1.amazonaws.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("AWS_SES_SMTP_USER")
EMAIL_HOST_PASSWORD = env("AWS_SES_SMTP_PASS")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@crewbotic.ai")
```

### 6. HTML email template

Create `accounts/templates/emails/password_reset.html` with inline-styled HTML:

- Background: `#F3F4F6`
- Card: white, `border-radius: 16px`
- Header: `#181B20` with orange `#F97316` accent
- Button: `#F97316` background, white text, `border-radius: 12px`
- Fallback text link below the button
- Footer with copyright

Use `django.template.loader.render_to_string()` to render, then `django.utils.html.strip_tags()` for plain text fallback.

### 7. Sending the email

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_password_reset_email(user, token_str):
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token_str}"
    html_message = render_to_string("emails/password_reset.html", {
        "reset_url": reset_url,
    })
    send_mail(
        subject="Redefinir sua senha - Crewbotic",
        message=strip_tags(html_message),
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
```

## Limits (SES Sandbox)

- 200 emails per 24-hour period
- 1 email per second
- Can only send to verified email addresses (not arbitrary recipients)
- To increase limits: request production access via AWS SES console

## Domain verification status

```bash
aws ses get-identity-verification-attributes --identities crewbotic.ai
```

Status `Pending` → `Success` after DNS propagation (minutes to hours).
