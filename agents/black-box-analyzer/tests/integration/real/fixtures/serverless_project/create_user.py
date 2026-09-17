import json


def lambda_handler(event, context):
    """Create a user from an API Gateway proxy event."""
    body = json.loads(event.get("body") or "{}")
    return {"statusCode": 201, "body": json.dumps({"email": body.get("email")})}
