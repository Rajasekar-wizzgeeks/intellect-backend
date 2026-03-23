
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
import os
import json

from Controllers.prompts import ACTION_AREAS_SYSTEM_PROMPT
from Controllers.schemas import ACTION_AREAS_FEEDBACK_SCHEMA


class LLMGenerationController:

    def generate_action_areas(self, data):
        try:
            system_prompt = ACTION_AREAS_SYSTEM_PROMPT
            feedback_schema = ACTION_AREAS_FEEDBACK_SCHEMA
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
            return {
                "content": "{}",
                "structured": {},
                "error": str(e),
            }
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
            usage = getattr(response, "usage_metadata", None)
            if usage:
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
            return {
                "content": "{}",
                "structured": {},
                "error": str(e),
            }
    

        
