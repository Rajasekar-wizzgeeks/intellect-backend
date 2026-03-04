from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController
import asyncio




class FeedbackController:

    
    async def get_feedback_data_excel(self,file):
        try:
            if file is None or file.file is None:
                return JSONResponse(
                    status_code=400,
                    content={"message": "File is required."}
                )

            df = pd.read_excel(file.file)
            df = df.replace([np.nan, np.inf, -np.inf], None)
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)

            data = df.to_dict(orient="records")

            name=data[0].get('Employee Name') or data[0].get('Name') or 'Employee Name'
            right_culture = [
                row for row in data if row.get("Name") == "Creating the Right Culture"
            ]
            leadership_style = [
                row for row in data if row.get("Name") == "Leadership Style"
            ]
            leadership_staff_dev = [
                row for row in data if row.get("Name") == "Leadership for Staff Performance & Development"
            ]
            educational_quality = [
                row for row in data if row.get("Name") == "Educational Quality & Student Outcomes"
            ]
            engagement_with_management = [
                row for row in data if row.get("Name") == "Engagement with Management"
            ]
            general = [
                row for row in data if row.get("Name") == "General"
            ]

            right_culture_competency = CommonFunctions.questionwise_avg_by_rate_group(right_culture)
            leadership_style_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_style)
            leadership_staff_dev_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_staff_dev)
            educational_quality_competency = CommonFunctions.questionwise_avg_by_rate_group(educational_quality)
            engagement_with_management_competency = CommonFunctions.questionwise_avg_by_rate_group(engagement_with_management)

            overall_questionwise_data = {}

            overall_questionwise_data.update(right_culture_competency)
            overall_questionwise_data.update(leadership_style_competency)
            overall_questionwise_data.update(leadership_staff_dev_competency)
            overall_questionwise_data.update(educational_quality_competency)
            overall_questionwise_data.update(engagement_with_management_competency)

            general_competency=CommonFunctions.grouped_question(general)
            abc_questions=CommonFunctions.count_abc_responses(general_competency)
            workplace_culture=CommonFunctions.get_workplace_culture_data(general_competency,"workplace culture")
            stand_out_leader_thing=CommonFunctions.get_workplace_culture_data(general_competency,'stand out as a leader')
            continue_doing_thing=CommonFunctions.get_workplace_culture_data(general_competency,'do more often or keep doing')
            stop_altogether=CommonFunctions.get_workplace_culture_data(general_competency,'stop altogether')
            action_areas_thing_data=CommonFunctions.get_workplace_culture_data(general_competency,'differently, adjust or change to improve')

            workplace_culture_words=CommonFunctions.count_workplace_culture_words(workplace_culture)
            stand_out_leader_thing_words=CommonFunctions.count_workplace_culture_words(stand_out_leader_thing)
            continue_doing_thing_words=CommonFunctions.get_non_self_comments(continue_doing_thing)
            stop_doing_thing_words=CommonFunctions.get_non_self_comments(stop_altogether)
            predominant_leader_thing=CommonFunctions.get_non_self_comments(stand_out_leader_thing)
            action_areas_thing_data_comment=CommonFunctions.get_non_self_comments(action_areas_thing_data)
            
            action_areas_thing_data_extended = []
            action_areas_thing_data_extended.append(stand_out_leader_thing_words)
            action_areas_thing_data_extended.append(continue_doing_thing_words)
            action_areas_thing_data_extended.append(stop_doing_thing_words)
            action_areas_thing_data_extended.extend(action_areas_thing_data_comment)
            controller = LLMGenerationController()

            continue_prompt = """
You are a STRICT Educational Feedback Formatter.

OBJECTIVE:
Return ONLY clearly positive comments.

FILTERING RULES:
Keep a comment ONLY if it clearly expresses:
- Appreciation
- Strength
- Encouragement
- Positive quality
- Good practice
- Constructive positive expectation

REMOVE completely:
- Negative comments
- Complaints
- Criticism
- Neutral statements
- Mixed sentiment (positive + negative together)
- "-", "---"
- "Nil", "NIL"
- "no comment", "no comments"
- "nothing"
- Empty text
- Anything unclear in sentiment

CORE RULE:
INPUT COMMENT = OUTPUT COMMENT.
Do NOT rewrite, rephrase, expand, shorten, or add new words.
Do NOT change sentence structure.

ALLOWED:
- Fix very minor grammar or spacing issues only.
- Apply Markdown bold (**text**) ONLY to clearly positive traits or qualities that already exist in the sentence.
- Do NOT invent new words for bolding.
- Do NOT bold the entire sentence unless the full sentence is purely a positive trait.

IMPORTANT:
- If a comment is not clearly positive → REMOVE it completely.
- One valid input comment → exactly one output comment.
- Preserve original wording.
- Preserve order.

OUTPUT:
Return ONLY valid JSON:
{
  "continue_doing": [string]
}

No explanations.
Only JSON.
"""
            stop_prompt = """
You are a STRICT Educational Feedback Formatter.

OBJECTIVE:
Return ONLY clearly negative meaning comments (complaints, problems, harmful behavior).

DEFINITION OF NEGATIVE COMMENT:
A comment must clearly express:
- Complaint
- Dissatisfaction
- Unfair treatment
- Bias
- Poor behavior
- Harmful action
- Negative experience
- Clear criticism

FILTERING RULES:
Keep the comment ONLY if the overall meaning is clearly negative.

REMOVE completely:
- Positive comments
- Appreciation
- Advisory suggestions without complaint
- General expectations stated politely
- Neutral statements
- Mixed sentiment (positive + negative together)
- "-", "---"
- "Nil", "NIL"
- "no comment", "no comments"
- "nothing"
- Empty text
- Anything unclear in sentiment

CORE RULE:
INPUT COMMENT = OUTPUT COMMENT.
Do NOT rewrite, rephrase, expand, shorten, or add words.
Do NOT change sentence structure.
Do NOT add prefixes like "Avoid", "Stop", etc.

ALLOWED:
- Fix very minor grammar or spacing issues only.
- Highlight ONLY the exact explicit negative words or phrases already present using:
  <span style="color:red"><strong>negative phrase</strong></span>
- Do NOT highlight neutral or advisory words.
- Do NOT create new negative wording.
- Do NOT highlight the entire sentence unless the full sentence is completely negative.

IMPORTANT:
- If the comment is not clearly negative in overall meaning → REMOVE it completely.
- One valid input comment → exactly one output comment.
- Preserve original wording.
- Preserve order.

OUTPUT:
Return ONLY valid JSON:
{
  "stop_doing": [string]
}

No explanations.
Only JSON.
"""
            predominant_prompt = """
You are a STRICT Educational Feedback Formatter.

OBJECTIVE:
Return ONLY clearly positive leadership qualities or traits for predominant_leader_thing.

FILTERING RULES:
Keep a comment ONLY if it clearly expresses:
- Positive leadership quality
- Strong character trait
- Appreciation of leadership style
- Supportive or fair leadership behavior
- Strength in management or guidance

REMOVE completely:
- Negative comments
- Complaints
- Criticism
- Neutral statements
- Advisory suggestions without clear appreciation
- Mixed sentiment (positive + negative together)
- "-", "---"
- "Nil", "NIL"
- "no comment", "no comments"
- "nothing"
- Empty text
- Anything unclear in sentiment

CORE RULE:
INPUT COMMENT = OUTPUT COMMENT.
Do NOT rewrite, rephrase, expand, shorten, or add words.
Do NOT change sentence structure.
Do NOT add prefixes like "Continue" or any other words.

ALLOWED:
- Fix very minor grammar or spacing issues only.
- Apply Markdown bold (**text**) ONLY to clearly positive leadership traits already written in the sentence.
- Do NOT invent new words for bolding.
- Do NOT bold the entire sentence unless the full sentence is purely a positive leadership trait.

IMPORTANT:
- If a comment is not clearly positive → REMOVE it completely.
- One valid input comment → exactly one output comment.
- Preserve original wording.
- Preserve order.

OUTPUT:
Return ONLY valid JSON:
{
  "predominant_leader_thing": [string]
}

No explanations.
Only JSON.
"""
            stand_out_leader_simple_prompt = """
You are a leadership feedback processor.

You will receive a list of short leadership-related phrases.

Your task:

1. Convert each phrase into simple, easy-to-understand words.
2. Keep phrases short (maximum 3 words).
3. Use clear and common vocabulary.
4. If the original phrase contains the word "leadership", keep the word "Leadership" in the final phrase.
5. If the original phrase does NOT contain "leadership", do NOT add "Leadership" as a suffix.
6. Remove words like "and", "approach", "role modeling", "command", etc., and simplify them.
7. Expand or refine the list to exactly 12 unique traits.
8. Avoid duplicate meanings.
9. Do NOT add explanations.

Return output in STRICT JSON format:

{
  "stand_out_leader": [
    "Simple Phrase 1",
    "Simple Phrase 2"
  ]
}

Rules:
- Maximum 12 items.
- Each item maximum 3 words.
- Use simple, clear English.
- No extra text.
- No explanations.
- No duplicate traits.
"""

            continue_feedback_schema = {
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
            stop_feedback_schema = {
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
            predominant_schema = {
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
            stand_out_leader_thing_schema = {
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

            
            
            async def run_parallel_analysis():
                task1 =asyncio.to_thread( controller.analysis_comment_to_generate,
                    continue_doing_thing_words,
                    system_prompt=continue_prompt,
                    feedback_schema=continue_feedback_schema
                )

                task2 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    stop_doing_thing_words,
                    system_prompt=stop_prompt,
                    feedback_schema=stop_feedback_schema
                )

                task3 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    predominant_leader_thing,
                    system_prompt=predominant_prompt,
                    feedback_schema=predominant_schema
                )
                 
                task4 = asyncio.to_thread(controller.generate_action_areas,
                    action_areas_thing_data_extended
                )

                task5 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    stand_out_leader_thing_words,
                    system_prompt=stand_out_leader_simple_prompt,
                    feedback_schema=stand_out_leader_thing_schema
                )
               
                results = await asyncio.gather(task1, task2, task3, task4, task5)
                return results  


            analysis_general_continue_doing, \
            analysis_general_stop_doing, \
            analysis_general_predominant_leader_thing, \
            action_areas_thing_llm_generate, \
            stand_out_leader_thing_generate = await run_parallel_analysis()     
            print("stand_out_leader_thing_generate", stand_out_leader_thing_generate)
            
            return JSONResponse(
                status_code=200,
                content={
                    "name": name,
                    "competency_summary_overall":{
                     'leadership_style': CommonFunctions.overall_avg_by_group(leadership_style_competency),
                     'educational_quality': CommonFunctions.overall_avg_by_group(educational_quality_competency),
                     'leadership_staff_dev': CommonFunctions.overall_avg_by_group(leadership_staff_dev_competency),
                     'right_culture': CommonFunctions.overall_avg_by_group(right_culture_competency),
                     'engagement_with_management': CommonFunctions.overall_avg_by_group(engagement_with_management_competency)
                    },
                    "strengths": CommonFunctions.find_strengths_separately(overall_questionwise_data),
                    "area_of_improvement": CommonFunctions.find_area_of_improvement_separately(overall_questionwise_data),
                    "right_culture_competency": right_culture_competency,
                    "leadership_style_competency": leadership_style_competency,
                    "leadership_staff_dev_competency": leadership_staff_dev_competency,
                    "educational_quality_competency": educational_quality_competency,
                    "engagement_with_management_competency": engagement_with_management_competency,
                    "nominee_leadership":abc_questions,
                    "workplace_culture":workplace_culture_words,
                    "predominant_leader_most_thing":stand_out_leader_thing_generate['structured']['stand_out_leader'] if stand_out_leader_thing_generate['structured'] else [],
                    "continue_doing_thing":analysis_general_continue_doing['structured']['continue_doing'] if analysis_general_continue_doing['structured'] else [],
                    "stop_doing_thing":analysis_general_stop_doing['structured']['stop_doing'] if analysis_general_stop_doing['structured'] else [],
                    "predominant_leader_thing":analysis_general_predominant_leader_thing['structured']['predominant_leader_thing'] if analysis_general_predominant_leader_thing['structured'] else [],
                    "action_areas_thing":action_areas_thing_llm_generate['structured']
                
                }
            )
                

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"message": f"Error : {str(e)}"}
            )