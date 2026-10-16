import json

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def is_version_response(output: str) -> bool:
    try:
        response: JsonValue = json.loads(output)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(response, dict)
        and "version" in response
        and isinstance(response["version"], str)
        and bool(response["version"].strip())
    )
