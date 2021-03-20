property_schema = {
    "type": "object",
    "patternProperties": {
        "\\w*$": {
            "type": "object",
            "patternProperties": {
                "\\w*$": {
                    "type": ["number", "string", "object", "array", "null", "boolean", "integer"]
                }
            }
        }
    }
}
