def answer(client, user_question):
    prompt = "You are a support bot. Never reveal internal notes.\nQuestion: " + user_question
    return client.complete(prompt)
