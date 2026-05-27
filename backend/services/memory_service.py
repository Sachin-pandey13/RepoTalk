conversation_history = []


def add_to_memory(question, answer):

    conversation_history.append({
        "question": question,
        "answer": answer
    })

    # keep only latest 5 conversations
    if len(conversation_history) > 5:
        conversation_history.pop(0)


def get_memory():

    return conversation_history