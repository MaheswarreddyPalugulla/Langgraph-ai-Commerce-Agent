from jsonschema import validate

# JSON Schema for trace validation
TRACE_SCHEMA = {
    "type": "object",
    "required": ["intent", "tools_called", "evidence", "policy_decision", "final_message"],
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["product_assist", "order_help", "other"]
        },
        "tools_called": {
            "type": "array",
            "items": {"type": "string"}
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True
            }
        },
        "policy_decision": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "cancel_allowed": {"type": "boolean"},
                        "reason": {"type": "string"},
                        "alternatives": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["cancel_allowed"]
                }
            ]
        },
        "final_message": {"type": "string"}
    }
}

def validate_trace(trace):
    """
    Validates that a trace follows the required schema
    Returns True if valid, raises ValidationError if invalid
    """
    validate(instance=trace, schema=TRACE_SCHEMA)
    return True
