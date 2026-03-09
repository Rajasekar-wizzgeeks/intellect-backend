
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
import os
import json


class LLMGenerationController:

    def generate_action_areas(self, data):
        try:
            system_prompt = """You are an Educational Feedback Analysis Expert.

Your task is to analyze multiple feedback comments and generate a short, clear, and structured summary.

OBJECTIVE
- Identify key strengths.
- Identify key improvement areas.
- Group similar feedback together.
- Prioritize the most frequently mentioned themes.
- Rewrite all feedback into simple, polite, and professional language.

IMPORTANT REWRITING RULE
- Never copy the original feedback sentence directly.
- Always rewrite comments into respectful and constructive wording.
- Convert criticism into improvement-focused suggestions.
- Ensure every sentence is clear, polite, and easy to understand.
- Avoid harsh or blaming language.

CLASSIFICATION STEP (VERY IMPORTANT)

Before writing the final output, classify feedback into three categories:

1. CONTINUE  
Positive behaviours, strengths, and good practices that should continue.

2. START  
New actions, improvements, or practices that could be introduced.

3. STOP  
Behaviours that should be reduced, limited, or avoided.

STOP DETECTION RULE (VERY IMPORTANT)

A comment belongs to STOP if it suggests reducing, limiting, or avoiding a behaviour.

Common STOP themes include:
- Too many meetings
- Interrupting staff
- Poor communication tone
- Delayed responses
- Lack of listening
- Micromanagement
- Public criticism
- Excessive pressure
- Unclear instructions
- Rushed decisions

If feedback implies reducing a behaviour, classify it under STOP.

Always rewrite it in polite improvement language.

Example transformations:

"Too many meetings"  
→ "Consider limiting the number of meetings to improve efficiency."

"Does not listen to staff"  
→ "It may be helpful to encourage more active listening to staff feedback."

"Publicly criticizes staff"  
→ "It would be beneficial to avoid public criticism of staff."

OUTPUT RULES (STRICT)

Return ONLY valid JSON.  
Do NOT add explanations.  
Do NOT use markdown.  
Do NOT add extra text before or after the JSON.

JSON STRUCTURE

{
"immediate_action_summary": "short 3-4 sentence paragraph",
"continue": ["point 1", "point 2", "point 3"],
"start": ["point 1", "point 2", "point 3"],
"stop": ["point 1", "point 2", "point 3"]
}

SECTION RULES

IMMEDIATE ACTION SUMMARY
- Write 3 to 4 short sentences.
- Focus only on the most important improvement themes.
- Highlight key areas that may need attention.
- Use constructive and professional language.
- Keep sentences simple and easy to understand.

CONTINUE
- Maximum 3 points.
- Each point must be a short sentence.
- Highlight positive practices or strengths that should continue.
- Use positive and encouraging language.

START
- Maximum 3 points.
- Each point must be short and actionable.
- Use polite suggestions such as:
  "It would be helpful to..."
  "Consider introducing..."
  "It may be beneficial to..."
  "Encouraging more..."

STOP
- Maximum 3 points.
- Each point must represent a behaviour that should be reduced, limited, or avoided.
- Use polite and respectful phrasing.

Examples:
"It may be helpful to reduce..."
"Consider limiting..."
"It would be beneficial to avoid..."
"It may be helpful to minimize..."

STOP EXTRACTION RULE

If negative or improvement-related feedback exists, at least one point must appear in the STOP section.

Do not move all negative feedback to START.

LANGUAGE STYLE RULES

- Use simple and clear English.
- Each point must contain only ONE idea.
- Maximum 12–15 words per point.
- Avoid complex vocabulary.
- Avoid aggressive or blaming tone.
- Ensure all points sound polite and professional.

GROUPING RULES

- Combine similar comments into one summarized point.
- Prioritize the most frequently mentioned themes.
- Avoid repeating the same idea.
- Ensure each point represents a clear theme from the feedback.

CLARITY RULE

- Each point must describe ONE clear idea.
- Do NOT combine multiple topics in one sentence.

MISSING DATA RULE

If there are no relevant comments for a section, return:

"No significant concerns identified in this area."

FINAL CHECK BEFORE OUTPUT

- Ensure each section has a maximum of 3 points.
- Ensure all points are polite and easy to understand.
- Ensure there is no repetition across sections.
- Ensure the response is valid JSON.
- Ensure no text appears outside the JSON.

Return ONLY the JSON output.
    """
            feedback_schema = {
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
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema= feedback_schema
                    ),
                    
                contents=data
            )

            response_text=response.text
            try:
                structured = json.loads(response_text)
                json_output = json.dumps(structured, indent=2)

            except json.JSONDecodeError:
                structured = {}
                json_output = "{}"

            return {
                "content": json_output,    
                "structured": structured          
            }
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"message": f"Error : {str(e)}"}
            )
    
    def analysis_comment_to_generate(self, data,system_prompt=None,feedback_schema=None):
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema= feedback_schema,
                    # max_output_tokens=15024,  
                    # temperature=0.2
                    ),
                    
                contents=data
            )
            usage = response.usage_metadata
            print("Prompt Tokens:", usage.prompt_token_count)
            print("Completion Tokens:", usage.candidates_token_count)
            print("Total Tokens:", usage.total_token_count)
            response_text=response.text
            # response_text=""
         
            try:
                structured = json.loads(response_text)
                json_output = json.dumps(structured, indent=2)

            except json.JSONDecodeError:
                structured = {}
                json_output = "{}"

            

            return {
                "content": json_output,    
                "structured": structured       
            }
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"message": f"Error : {str(e)}"}
            )

    

        
