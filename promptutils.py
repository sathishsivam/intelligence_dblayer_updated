

def build_messages(prompt_template, user_query: str):
    messages = prompt_template.format_messages(user_query=user_query)

    system_msg = "\n".join(
        [m.content for m in messages if m.type == "system"]
    )

    user_msg = "\n".join(
        [m.content for m in messages if m.type == "human"]
    )
    print(system_msg)
    return system_msg, user_msg



