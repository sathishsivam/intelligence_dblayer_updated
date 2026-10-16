from .models import InsightOption
import json


def parse_response(response):

    content = response.content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")

    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as ex:
        raise ValueError(
            f"InsightAgent returned invalid JSON:\n{content}"
        ) from ex

    validated = []

    for option in data.get("options", []):

        validated.append(
            InsightOption.model_validate(option).model_dump(exclude_none=True)
        )

    return {
        "recommended": data.get("recommended", ""),
        "options": validated
    }