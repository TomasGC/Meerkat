# KNOWN VIOLATIONS: LawOfDemeter>=2


def get_user_city(context):
    # Three-level property chain — violates LoD
    return context.user.address.city


def find_record(app):
    # Deep method chain
    return app.service.repository.find_by_id(42)
