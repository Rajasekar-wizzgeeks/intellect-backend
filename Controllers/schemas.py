CONTINUE_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "continue_doing": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "representative_comment": {
                        "type": "string"
                    },
                    "comments_belong_to_this_group": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["representative_comment"]
            }
        }
    },
    "required": ["continue_doing"]
}

STOP_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "stop_doing": {
            "type": "array",
            "description": "List of grouped and ungrouped feedback comments describing practices to stop.",
            "items": {
                "type": "object",
                "properties": {
                    "representative_comment": {
                        "type": "string",
                        "description": "Representative comment. Includes (xN) if grouped."
                    },
                    "comments_belong_to_this_group": {
                        "type": "array",
                        "description": "All comments belonging to this group. Empty if single.",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["representative_comment"]
            }
        }
    },
    "required": ["stop_doing"]
}

PREDOMINANT_SCHEMA = {
    "type": "object",
    "properties": {
        "predominant_leader_thing": {
            "type": "array",
            "description": "List of grouped and ungrouped comments describing predominant leadership traits.",
            "items": {
                "type": "object",
                "properties": {
                    "representative_comment": {
                        "type": "string",
                        "description": "Representative leadership trait comment. Includes (xN) if grouped."
                    },
                    "comments_belong_to_this_group": {
                        "type": "array",
                        "description": "All comments belonging to this group. Empty if single.",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["representative_comment"]
            }
        }
    },
    "required": ["predominant_leader_thing"]
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


LEADERSHIP_THEME_CLUSTER_SCHEMA = {
    "type": "object",
    "properties": {

        "team_feedback": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "theme": {
                        "type": "string",
                        "description": "Concise semantic theme representing similar leadership behaviours or feedback."
                    },

                    "employees": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        },

                        "description": "Unique employee names associated with this theme."
                    },

                    "questions": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        },

                        "description": "Semantically similar questions/comments grouped under the same theme."
                    }
                },

                "required": [
                    "theme",
                    "employees",
                    "questions"
                ]
            },

            "description": "Clustered semantically similar team feedback themes."
        },

        "manager_feedback": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "theme": {
                        "type": "string",
                        "description": "Concise semantic theme representing similar leadership behaviours or feedback."
                    },

                    "employees": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        },

                        "description": "Unique employee names associated with this theme."
                    },

                    "questions": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        },

                        "description": "Semantically similar questions/comments grouped under the same theme."
                    }
                },

                "required": [
                    "theme",
                    "employees",
                    "questions"
                ]
            },

            "description": "Clustered semantically similar manager feedback themes."
        }
    },

    "required": [
        "team_feedback",
        "manager_feedback"
    ]
}

LEADER_PROFILE_SCHEMA = {
    "type": "object",

    "properties": {

        "strengths": {

            "type": "array",

            "items": {
                "type": "string"
            },

            "description":
                "Leadership strengths inferred from highest-rated team behaviours."
        },

        "development_areas": {

            "type": "array",

            "items": {
                "type": "string"
            },

            "description":
                "Leadership improvement areas inferred from lowest-rated team behaviours."
        }
    },

    "required": [
        "strengths",
        "development_areas"
    ]
}