property_schema = {
    "type": "object",
    "patternProperties": {
        "\\w*$": {
            "type": "object",
            "patternProperties": {
                "\\w*$": {
                    "type": "string"
                }
            }
        }
    }
}
