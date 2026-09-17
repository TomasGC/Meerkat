import json


def lambda_handler(event, context):
    """Return a single user by id."""
    user_id = event.get("pathParameters", {}).get("id")
    return {"statusCode": 200, "body": json.dumps({"id": user_id})}
