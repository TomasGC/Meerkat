# KNOWN VIOLATIONS: SOLID (SRP — god class)


class GodService:
    """Violates Single Responsibility Principle."""

    def handle_user(self, user):
        pass

    def send_email(self, to, body):
        pass

    def generate_report(self, data):
        pass

    def save_to_db(self, obj):
        pass

    def calculate_tax(self, amount):
        return amount * 0.2

    def render_html(self, template, context):
        pass
