from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController
import asyncio
import json



class FeedbackController:

    
    async def get_feedback_data_excel(self,file):
        try:
            if file is None:
                return JSONResponse(
                    status_code=400,
                    content={"message": "File is required."}
                )

            files = file if isinstance(file, (list, tuple)) else [file]
            if any(f is None or getattr(f, "file", None) is None for f in files):
                return JSONResponse(
                    status_code=400,
                    content={"message": "File is required."}
                )

            def read_excel_records(uploaded_file):
                uploaded_file.file.seek(0)
                df = pd.read_excel(uploaded_file.file)
                df = clean_dataframe(df)
                return df.to_dict(orient="records") if df is not None else []

            def clean_dataframe(df):
                if df is not None:
                    df = df.replace([np.nan, np.inf, -np.inf], None)
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].astype(str)
                return df
            file1_data = read_excel_records(files[0])
            comparision_file1=[]
            comparision_file2=[]
            if len(files) > 1:
                file2_data = read_excel_records(files[1])
                comparision_file1 = file1_data
                comparision_file2 = file2_data
            if len(files) > 2:
                file2_data = read_excel_records(files[1])
                file3_data = read_excel_records(files[2])
                comparision_file1 = file2_data
                comparision_file2 = file3_data

            data = file1_data
            
            if not data:
                return JSONResponse(
                    status_code=400,
                    content={"message": "No data found in uploaded file."}
                )

             
            # file2_question_data = CommonFunctions.all_question_wise_data(comparision_file1)
            # file3_question_data = CommonFunctions.all_question_wise_data(comparision_file2)
            # comparision_data=CommonFunctions.find_comparision_year_data(file2_question_data,file3_question_data)
            # print("comparision_data", comparision_data)
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
            continue_doing_thing_words,continueQuestion=CommonFunctions.get_non_self_comments(continue_doing_thing)
            stop_doing_thing_words,stopQuestion=CommonFunctions.get_non_self_comments(stop_altogether)
            predominant_leader_thing,predominantQuestion=CommonFunctions.get_non_self_comments(stand_out_leader_thing)
            action_areas_thing_data_comment=CommonFunctions.get_non_self_comments(action_areas_thing_data)
            action_areas_thing_data_extended = []
            action_areas_thing_data_extended.append(stand_out_leader_thing_words)
            action_areas_thing_data_extended.append(continue_doing_thing_words)
            action_areas_thing_data_extended.append(stop_doing_thing_words)
            action_areas_thing_data_extended.extend(action_areas_thing_data_comment)
            controller = LLMGenerationController()

            continue_prompt = """
You are a STRICT Educational Comment Formatter.

INPUT:
You will receive:
{
  "question": "<question text>",
  "comments": ["comment1", "comment2", "comment3", ...]
}

OBJECTIVE:
Return comments that are clearly related to the given question and formatted properly.

STRICT RULES:

1. QUESTION RELEVANCE
- Every comment MUST be related to the given question.
- If a comment is unrelated to the question, remove it.

2. NO MERGING
- NEVER merge multiple comments.
- Each input comment must remain an individual item.
- One input comment = one output comment.

3. ORDER PRESERVATION
- Maintain the exact same order as the input list.
- Do NOT reorder comments.
- Do NOT collapse or combine comments.

Example:
Input:
[
 "comment1",
 "comment2",
 "comment3"
]

Output MUST be:
[
 "comment1",
 "comment2",
 "comment3"
]

4. MARKDOWN BOLD RULE
- Apply Markdown bold (**text**) ONLY to clearly positive traits or qualities already present in the sentence.
- Do NOT add new praise or new words.
- Do NOT bold entire sentences.
- Only bold the positive quality words.

Example:
"Encouragement"
→ "**Encouragement**"

"Clear communication with staff"
→ "**Clear communication** with staff"

5. DO NOT MODIFY MEANING
- Do NOT rewrite the comment meaning.
- Only apply formatting when needed.
- Do NOT generate new comments.

6. REMOVE INVALID COMMENTS
Remove comments that are:
- "-", "--", "---"
- "nil"
- "nothing"
- "NO COMMENT"
- empty text
- meaningless placeholders

7. KEEP COMMENTS SEPARATE
- Each comment must stay as its own array item.
- Never collapse comments into a paragraph.

OUTPUT FORMAT (STRICT):
Return ONLY valid JSON.

{
  "continue_doing": [
    "comment1",
    "comment2",
    "comment3"
  ]
}

STRICT OUTPUT RULES:
- No explanations
- No extra text
- No markdown outside comments
- Only the JSON object above
"""
            stop_prompt = """You are a STRICT Educational Comment Formatter.

INPUT:
You will receive:
{
  "question": "<question text>",
  "comments": ["comment1", "comment2", "comment3", ...]
}

OBJECTIVE:
Return comments that are clearly related to the given question and formatted properly.

STRICT RULES:

1. QUESTION RELEVANCE
- Every comment MUST be related to the given question.
- If a comment is unrelated to the question, remove it.

2. POSITIVE QUESTION RULE
- If the question asks about strengths, appreciation, encouragement, or "continue doing",
  then ONLY return comments with a positive tone.
- Remove comments that contain:
  - criticism
  - complaints
  - negative tone
  - mixed sentiment (positive + negative)

3. NEGATIVE PHRASE HIGHLIGHT RULE
- If a comment contains a clearly negative phrase, highlight ONLY the negative phrase using:

<span style="color:red"><strong>negative phrase</strong></span>

Examples:
"Do not judge people by one incident"

→ "<span style="color:red"><strong>Do not judge people by one incident</strong></span>"

"Avoid favoritism"

→ "<span style="color:red"><strong>Avoid favoritism</strong></span>"

- Only highlight the negative portion, not the entire sentence unless the full sentence is negative instruction.

4. NO MERGING
- NEVER merge multiple comments.
- Each input comment must remain an individual item.
- One input comment = one output comment.

5. ORDER PRESERVATION
- Maintain the exact same order as the input list.
- Do NOT reorder comments.
- Do NOT collapse or combine comments.

6. MARKDOWN BOLD RULE
- Apply Markdown bold (**text**) ONLY to clearly positive traits or qualities already present in the sentence.
- Do NOT add new praise or new words.
- Do NOT bold entire sentences.
- Only bold the positive quality words.

Examples:

"Encouragement"
→ "**Encouragement**"

"Clear communication with staff"
→ "**Clear communication** with staff"

7. DO NOT MODIFY MEANING
- Do NOT rewrite the comment meaning.
- Only apply formatting when needed.
- Do NOT generate new comments.

8. REMOVE INVALID COMMENTS
Remove comments that are:
- "-"
- "--"
- "---"
- "nil"
- "nothing"
- "NO COMMENT"
- empty text
- meaningless placeholders

9. KEEP COMMENTS SEPARATE
- Each comment must stay as its own array item.
- Never collapse comments into a paragraph.

OUTPUT FORMAT (STRICT):
Return ONLY valid JSON.

{
  "stop_doing": [
    "comment1",
    "comment2",
    "comment3"
  ]
}

STRICT OUTPUT RULES:
- No explanations
- No extra text
- No markdown outside comments
- Only the JSON object above

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

INPUT:
You will receive a list of short leadership-related phrases.

OBJECTIVE:
Simplify each phrase while keeping the original meaning.

TASK RULES:

1. SIMPLIFY PHRASES
- Convert each phrase into simple, easy-to-understand words.
- Keep phrases short (maximum 3 words).
- Use clear and common vocabulary.

2. LEADERSHIP WORD RULE
- If the original phrase contains the word "leadership", keep the word "Leadership" in the final phrase.
- If the original phrase does NOT contain "leadership", DO NOT add "Leadership".

3. WORD CLEANUP
Remove unnecessary words such as:
- "and"
- "approach"
- "role modeling"
- "command"
- similar filler or complex wording

Keep only the core leadership trait.

4. ORDER PRESERVATION (STRICT)
- Maintain the EXACT same order as the input list.
- Each input phrase must produce ONE output phrase.
- Do NOT reorder phrases.
- Do NOT merge phrases.

Example:

Input:
[
 "Strong leadership approach",
 "Clear communication",
 "Team motivation"
]

Output MUST keep order:
[
 "Strong Leadership",
 "Clear Communication",
 "Team Motivation"
]

5. EXPANSION RULE
- If the input list contains fewer than 12 traits, generate additional simple traits.
- Add new traits ONLY at the END of the list.
- Do NOT modify or reorder the original items.

6. UNIQUENESS RULE
- Ensure all traits are unique.
- Avoid duplicate meanings.

7. LENGTH RULE
- Maximum 12 items total.
- Each item maximum 3 words.

8. DO NOT ADD EXPLANATIONS
- Return only the phrases.

OUTPUT FORMAT (STRICT):
Return ONLY valid JSON.

{
  "stand_out_leader": [
    "Simple Phrase 1",
    "Simple Phrase 2"
  ]
}

STRICT OUTPUT RULES:
- Maximum 12 items
- Preserve input order
- Each phrase maximum 3 words
- No extra text
- No explanations
- Only the JSON object
"""
            workplace_culture_prompt = """You are an expert in workplace culture analysis.

Your task is to clean and filter a list of frequently mentioned workplace culture words extracted from survey comments.

INPUT:
A list of words or phrases extracted from employee feedback. The list is already sorted in descending order of frequency.

OBJECTIVE:
Return exactly 15 words or short phrases that best describe workplace culture.

KEEP only:
- Workplace culture adjectives
- Short descriptive phrases (1–3 words)
- Words that describe team environment, leadership culture, or work atmosphere.

REMOVE:
- Sentences or long explanations
- Irrelevant phrases
- Technical artifacts like "_x000d_"
- Words unrelated to workplace culture
- Duplicates or very similar variations
- Phrases longer than 3–4 words
- Random statements or descriptions

IMPORTANT RULES:
1. Do NOT change the order of the words.
2. Do NOT re-sort the list.
3. Only remove irrelevant items.
4. Return exactly 15 items.
5. If more than 15 valid words exist, keep the first 15 based on the original order.


OUTPUT FORMAT:
Return a JSON array.

Example:
Input:
["supportive", "good and happy", "the school environment is always changing", "collaborative", "events and learning opportunities"]

Output:
["supportive", "good and happy", "collaborative"]
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

            workplace_culture_schema = {
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

            
            continue_input_data = json.dumps({
    "question": continueQuestion ,
    "comments": continue_doing_thing_words
    })
            predominant_input_data = json.dumps({
    "question": predominantQuestion ,
    "comments": predominant_leader_thing
    })
            stop_input_data = json.dumps({
    "question": stopQuestion ,
    "comments": stop_doing_thing_words
    })
            
            async def run_parallel_analysis():
                task1 =asyncio.to_thread( controller.analysis_comment_to_generate,
                    continue_input_data,
                    system_prompt=continue_prompt,
                    feedback_schema=continue_feedback_schema
                )

                task2 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    stop_input_data,
                    system_prompt=stop_prompt,
                    feedback_schema=stop_feedback_schema
                )

                task3 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    predominant_input_data,
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

                task6 = asyncio.to_thread(controller.analysis_comment_to_generate,
                    workplace_culture_words,
                    system_prompt=workplace_culture_prompt,
                    feedback_schema=workplace_culture_schema
                )
               
                results = await asyncio.gather(task1, task2, task3, task4, task5, task6)
                # results = await asyncio.gather(task2)
                return results  


            analysis_general_continue_doing, \
            analysis_general_stop_doing, \
            analysis_general_predominant_leader_thing, \
            action_areas_thing_llm_generate, \
            stand_out_leader_thing_generate, \
            workplace_culture_generated_words = await run_parallel_analysis()     
            
            # analysis_general_stop_doing=controller.analysis_comment_to_generate(stop_input_data,stop_prompt,stop_feedback_schema)
            # print("analysis_general_stop_doing", analysis_general_stop_doing)


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
                    "workplace_culture":workplace_culture_generated_words['structured']['workplace_culture'] if workplace_culture_generated_words['structured'] else [],
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