CONTINUE_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "continue_doing": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Formatted comments describing practices to continue."
        },
    },
    "required": [
        "continue_doing",
    ],
}

STOP_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "stop_doing": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Formatted comments describing practices to stop."
        },
    },
    "required": [
        "stop_doing"
    ]
}

PREDOMINANT_SCHEMA = {
    "type": "object",
    "properties": {
        "predominant_leader_thing": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Formatted comments describing predominant leadership traits."
        }
    },
    "required": [
        "predominant_leader_thing"
    ]
}

STAND_OUT_LEADER_THING_SCHEMA = {
    "type": "object",
    "properties": {
        "stand_out_leader": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Formatted comments stand_out_leader leadership traits."
        }
    },
    "required": [
        "stand_out_leader"
    ]
}

WORKPLACE_CULTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "workplace_culture": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Formatted comments workplace_culture"
        }
    },
    "required": [
        "workplace_culture"
    ]
}

ACTION_AREAS_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "continue": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Strengths that should be continued."
        },
        "start": {
            "type": "array",
            "items": {"type": "string"},
            "description": "New actions or improvements to begin."
        },
        "stop": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Practices that should be reduced or stopped."
        }
    },
    "required": [
        "continue",
        "start",
        "stop"
    ]
}
