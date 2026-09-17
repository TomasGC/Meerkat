import json


def lambda_handler(event, context):
    """Delete a user by id."""
    user_id = event.get("pathParameters", {}).get("id")
    return {"statusCode": 204, "body": json.dumps({"id": user_id})}
