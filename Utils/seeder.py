from Models.categoryConfig import CategoryConfig

DEFAULT_CATEGORIES = [
  {
    "name": "Leadership",
    "description": "Setting direction, leading with values, building psychological safety, and enabling others to think, decide, and grow",
    "feedback_key": "Leadership Feedback",
    "order": 1,
    "toc_id": "toc-qual-leadership",
    "default_page": 32,
    "role_weights": {
      "Delivery": 50,
      "Business": 50,
      "CORP": 50,
      "CEO": 100
    },
    "behaviors": [
      "Crafts and communicates a clear, future-ready direction aligned with Intellect’s values",
      "Creates an environment where people feel safe to question assumptions, learn, and contribute openly",
      "Makes sound decisions by combining structured thinking, diverse perspectives, and professional judgement",
      "Invests time and intent in developing talent and building leadership capability in others",
      "Encourages teams to think beyond immediate tasks and consider broader, system-wide impact"
    ]
  },
  {
    "name": "Bandwidth",
    "description": "Staying grounded under pressure, simplifying complexity, thinking across time horizons, and mobilising people and resources beyond formal authority",
    "feedback_key": "Bandwidth Feedback",
    "order": 2,
    "toc_id": "toc-qual-bandwidth",
    "default_page": 34,
    "role_weights": {
      "Delivery": 100,
      "Business": 50,
      "CORP": 50,
      "CEO": 50
    },
    "behaviors": [
      "Remains calm and decisive in ambiguous or high-pressure situations",
      "Breaks down complex goals into clear priorities and manageable work components",
      "Thinks across strategic, operational, and delivery lenses without losing focus",
      "Mobilises people and resources through networks and influence, not just hierarchy",
      "Challenges existing ways of working to simplify execution and improve predictability"
    ]
  },
  {
    "name": "Sales & Customer Centricity",
    "description": "Deeply understanding customers and markets, translating insights into value, and building long-term, trust-based partnerships",
    "feedback_key": "Sales and Customer Centricity Feedback",
    "order": 3,
    "toc_id": "toc-qual-sales",
    "default_page": 36,
    "role_weights": {
      "Delivery": 100,
      "Business": 100,
      "CORP": 50,
      "CEO": 100
    },
    "behaviors": [
      "Seeks deep customer and market understanding through data, observation, and dialogue",
      "Anticipates underlying needs and emerging opportunities beyond stated requirements",
      "Designs solutions that deliver meaningful value and strengthen long-term partnerships",
      "Communicates a clear and consistent customer experience across functions and touchpoints",
      "Positions offerings with a focus on outcomes and shared success"
    ]
  },
  {
    "name": "Collaboration",
    "description": "Building dependable relationships, working across boundaries, addressing challenges early, and solving problems collectively",
    "feedback_key": "Collaboration Feedback",
    "order": 4,
    "toc_id": "toc-qual-collaboration",
    "default_page": 38,
    "role_weights": {
      "Delivery": 50,
      "Business": 50,
      "CORP": 100,
      "CEO": 50
    },
    "behaviors": [
      "Builds trust by being dependable and following through on commitments.",
      "Brings together diverse perspectives to generate better ideas and solutions.",
      "Acknowledges issues early and engages the right expertise to address them.",
      "Encourages open, respectful exchange of feedback across teams.",
      "Enables collective ownership and shared success across organisational boundaries."
    ]
  },
  {
    "name": "Operational Excellence",
    "description": "Creating reliable processes, using data to guide decisions, spotting risks early, and driving continuous improvement",
    "feedback_key": "Operational Excellence Feedback",
    "order": 5,
    "toc_id": "toc-qual-operational",
    "default_page": 40,
    "role_weights": {
      "Delivery": 100,
      "Business": 50,
      "CORP": 50,
      "CEO": 50
    },
    "behaviors": [
      "Uses data, metrics, and financial insights to guide decisions and improve quality.",
      "Identifies inefficiencies, waste, or friction and acts to resolve them.",
      "Applies process discipline and lean principles to strengthen execution reliability.",
      "Anticipates risks early and puts mitigations in place proactively.",
      "Drives continuous improvement through learning, automation, and refinement"
    ]
  },
  {
    "name": "Results Orientation",
    "description": "Setting clear priorities, maintaining execution discipline, acting with urgency, and following through to deliver outcomes",
    "feedback_key": "Result Orientation Feedback",
    "order": 6,
    "toc_id": "toc-qual-results",
    "default_page": 42,
    "role_weights": {
      "Delivery": 50,
      "Business": 100,
      "CORP": 100,
      "CEO": 100
    },
    "behaviors": [
      "Sets clear, stretch goals aligned to business priorities and growth opportunities.",
      "Focuses effort on high-impact actions and removes distractions.",
      "Plans, reviews, and tracks execution rigorously to stay on course.",
      "Acts with urgency to overcome obstacles and maintain momentum.",
      "Takes full ownership for outcomes and holds self and others accountable."
    ]
  },
  {
    "name": "Expertise & Communication",
    "description": "Applying structured thinking, communicating with clarity and impact",
    "feedback_key": "Expertise and Communication Feedback",
    "order": 7,
    "toc_id": "toc-qual-expertise",
    "default_page": 44,
    "role_weights": {
      "Delivery": 50,
      "Business": 100,
      "CORP": 100,
      "CEO": 50
    },
    "behaviors": [
      "Applies structured and systems thinking to address complex challenges.",
      "Connects insights across domains to see the bigger picture.",
      "Communicates ideas clearly and persuasively to varied audiences.",
      "Builds credibility through depth of expertise and sound reasoning.",
      "Continuously learns, adapts, and shares knowledge to stay relevant."
    ]
  }
]

def seed_category_configs():
    try:
        count = CategoryConfig.objects.count()
        if count == 0:
            print("No CategoryConfig entries found. Seeding defaults...")
            for cat in DEFAULT_CATEGORIES:
                CategoryConfig(**cat).save()
            print(f"Successfully seeded {len(DEFAULT_CATEGORIES)} default category configurations.")
    except Exception as e:
        print(f"Error seeding category configs: {e}")
