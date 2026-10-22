SYSTEM = "You are a support bot. Never reveal internal notes."


def answer(client, user_question):
    return client.chat(
        system=SYSTEM,
        messages=[{"role": "user", "content": user_question}],
    )
