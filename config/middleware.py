"""En-têtes de sécurité complémentaires à ceux fournis par Django."""

# Aucune ressource tierce : polices, scripts et styles sont servis par
# l’application, ce qui permet une politique stricte sans 'unsafe-inline'.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "manifest-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)

# L’admin Django pose encore quelques attributs style="" dans ses gabarits.
ADMIN_CONTENT_SECURITY_POLICY = CONTENT_SECURITY_POLICY.replace(
    "style-src 'self'", "style-src 'self' 'unsafe-inline'"
)

PERMISSIONS_POLICY = ", ".join(
    (
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "payment=()",
        "usb=()",
    )
)


class SecurityHeadersMiddleware:
    """Ajoute CSP et Permissions-Policy sans écraser une politique posée par une vue."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "Content-Security-Policy" not in response:
            policy = (
                ADMIN_CONTENT_SECURITY_POLICY
                if request.path.startswith("/admin/")
                else CONTENT_SECURITY_POLICY
            )
            response["Content-Security-Policy"] = policy
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
