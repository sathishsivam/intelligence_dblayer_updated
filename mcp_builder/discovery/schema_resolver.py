def resolve_schema(schema, spec):
    """
    Recursively resolve OpenAPI $ref references.

    Handles:
    - direct $ref
    - nested objects
    - arrays
    - properties
    - additionalProperties
    """

    if not isinstance(schema, dict):
        return schema

    # Direct $ref
    if "$ref" in schema:
        ref = schema["$ref"]

        if ref.startswith("#/"):
            parts = ref[2:].split("/")

            current = spec

            for part in parts:
                current = current.get(part)

                if current is None:
                    return schema

            return resolve_schema(current, spec)

    # Recursively resolve properties
    if "properties" in schema:
        schema["properties"] = {
            name: resolve_schema(value, spec)
            for name, value in schema["properties"].items()
        }

    # Resolve array items
    if "items" in schema:
        schema["items"] = resolve_schema(
            schema["items"],
            spec,
        )

    # Resolve additionalProperties
    if isinstance(schema.get("additionalProperties"), dict):
        schema["additionalProperties"] = resolve_schema(
            schema["additionalProperties"],
            spec,
        )

    # Resolve composition schemas
    for keyword in ("allOf", "anyOf", "oneOf"):

        if keyword in schema:

            schema[keyword] = [
                resolve_schema(item, spec)
                for item in schema[keyword]
            ]

    return schema
