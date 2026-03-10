from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController
import asyncio
import re



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
            name=data[0].get('Employee Name') or data[0].get('Name') or 'Employee Name'
            if isinstance(data, list) and data and isinstance(data[0], dict) and "Name" in data[0]:            
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
                right_culture_competency  = CommonFunctions.questionwise_avg_by_rate_group(right_culture)
                leadership_style_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_style)
                leadership_staff_dev_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_staff_dev)
                educational_quality_competency = CommonFunctions.questionwise_avg_by_rate_group(educational_quality)
                engagement_with_management_competency = CommonFunctions.questionwise_avg_by_rate_group(engagement_with_management)
                
                total_response=CommonFunctions.questionwise_find_total_response(right_culture)

                general_competency=CommonFunctions.grouped_question(general)

            else:
                def extract_category(column):
                    match = re.match(r"\[(.*?)\]\s*(.*)", column)
                    if match:
                        return match.group(1), match.group(2)
                    return None, column
                category_data = {}
                general_competency={}
                columns = list(data[0].keys()) if isinstance(data, list) and data and isinstance(data[0], dict) else []
                for col in columns:

                    if "Average" in col:
                        continue

                    category, question = extract_category(col)
                    if category:
                        if category not in category_data:
                            category_data[category] = []
                        values_by_rate_group = {}
                        for row in data:
                            rate_group = row.get("Rate Group") or row.get("Rater Group") or "Unknown"
                            values_by_rate_group.setdefault(rate_group, []).append(row.get(col))

                        category_data[category].append({
                            question: values_by_rate_group
                        })
                    else:
                        exceptItem=[
                            'Nominee Name','Employee Name','Employee ID','Nominee ID',
                            'Rater Group','Rate Group','Rating','Comment','Declined Comment','Name','Question'
                        ]
                        if question not in exceptItem:
                            general_competency[question] = [r.get(col) for r in data]
                # print(general_competency)
               
                right_culture_competency = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Creating the Right Culture', [])
                )
                leadership_style_competency = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Leadership Style', [])
                )
                leadership_staff_dev_competency = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Leadership for Staff Performance & Development', [])
                )
                educational_quality_competency = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Educational Quality & Student Outcomes', [])
                )
                engagement_with_management_competency = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Engagement with Management', [])
                )

                total_response = 0
                # abc_questions = {}
                # workplace_culture = []
                # stand_out_leader_thing = []
                # continue_doing_thing = []
                # stop_altogether = []
                # action_areas_thing_data = []


            
            overall_questionwise_data = {}
            overall_questionwise_data.update(right_culture_competency)
            overall_questionwise_data.update(leadership_style_competency)
            overall_questionwise_data.update(leadership_staff_dev_competency)
            overall_questionwise_data.update(educational_quality_competency)
            overall_questionwise_data.update(engagement_with_management_competency)

            abc_questions=CommonFunctions.count_abc_responses(general_competency)
            workplace_culture=CommonFunctions.get_workplace_culture_data(general_competency,"workplace_culture")
            stand_out_leader_thing=CommonFunctions.get_workplace_culture_data(general_competency,'stand_out_leader')
            continue_doing_thing=CommonFunctions.get_workplace_culture_data(general_competency,'continue_doing')
            stop_altogether=CommonFunctions.get_workplace_culture_data(general_competency,'stop_doing')
            action_areas_thing_data=CommonFunctions.get_workplace_culture_data(general_competency,'action_area')

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

            continue_prompt = """You are a STRICT Feedback Comment Processor.

INPUT:
You will receive a list of feedback comments from survey responses.

OBJECTIVE:
Clean and organize the comments while preserving the original meaning.

RULES:

1. KEEP ALL VALID COMMENTS
- Keep every meaningful comment exactly as written.
- Remove only meaningless placeholders such as:
  - "-"
  - "nil"
  - "NIL"
  - "nothing"
  - "Nothing"
  - "NO COMMENTS"
  - "no comments"
  - empty responses
- Everything else must be kept.

2. NO MERGING
- NEVER merge multiple comments.
- Each input comment must remain an individual item.
- One input comment = one output comment.

3. FREQUENCY ORDERING
- Detect comments with similar meaning.
- Comments that appear frequently (similar ideas repeated by multiple people) must appear FIRST.
- Comments that appear less frequently should appear later.
- Do NOT merge similar comments; only reorder them based on frequency of similar ideas.

4. MOST FREQUENT COMMENTS MUST START FIRST
- Identify the topic/idea that appears the MOST times in the list.
- Comments related to that most frequent meaning MUST appear at the very beginning of the output list.
- After that, show comments from the second most frequent meaning, then third, and so on.
- Maintain original sentences; only reorder them.

Example:
If comments about **workshops** appear the most:
- All workshop-related comments should appear first.
- Then meeting-related comments.
- Then appreciation-related comments.
- Then less frequent comments.

5. MARKDOWN POSITIVE HIGHLIGHTING
Apply Markdown bold (**text**) ONLY when the sentence already contains a clearly positive trait or quality.

Examples of traits that may be bolded if already written:
- supportive
- approachable
- motivating
- transparent
- organized
- encouraging
- dynamic
- appreciative

IMPORTANT RULES:
- Do NOT invent new words for bolding.
- Only bold the trait words that already exist in the sentence.
- Do NOT bold the entire sentence unless the full sentence is purely a positive trait.

Example:
Input:
"She is approachable and supportive."

Output:
"She is **approachable** and **supportive**."

6. NEGATIVE PHRASE HIGHLIGHTING
If a comment contains a clearly negative phrase, highlight ONLY the negative phrase using HTML formatting.

Format:
<span style="color:red"><strong>negative phrase</strong></span>

Rules:
- Highlight only the negative phrase, not the whole sentence.
- Do NOT change the wording of the sentence.
- Do NOT invent new phrases.
- Only highlight the exact negative words already written.

Example:
Input:
"He should stop shouting in public."

Output:
"He should <span style="color:red"><strong>stop shouting in public</strong></span>."

7. DO NOT CHANGE THE SENTENCE
- Do not rewrite.
- Do not simplify.
- Do not summarize.
- Only remove invalid comments, apply highlighting, and reorder by frequency.

8. OUTPUT FORMAT
Return the result as a JSON array.

Example format:

[
"comment 1",
"comment 2",
"comment 3"
]

IMPORTANT:
- No explanations.
- No extra text.
- Only the final JSON array of comments.
"""
            stop_prompt = """
You are a STRICT Comment Processor.

INPUT:
You will receive a JSON array (list) of comment strings.

OBJECTIVE:
Return EVERY valid comment exactly as written, but reordered with STRICT two-phase ordering:
1) NEGATIVE comments first (frequency-grouped).
2) After ALL negative comments are finished, output ALL OTHER comments (frequency-grouped).

ABSOLUTE RULES (MANDATORY):
1. Do NOT merge, combine, collapse, or deduplicate comments.
2. Do NOT rewrite, rephrase, expand, shorten, translate, or correct grammar.
3. Do NOT summarize.
4. Do NOT add new comments.
5. Do NOT skip any valid comment.
6. One input comment string = one output comment string.
7. If the exact same comment string appears multiple times in input, it MUST appear the same number of times in output.

STEP 0 — REMOVE PLACEHOLDER RESPONSES (MANDATORY FIRST STEP)

Before any other processing, examine every comment.

Trim spaces and convert the comment to lowercase for checking.

REMOVE the comment completely if it exactly matches ANY of the following:

nil  
na  
n/a  
-  
--  
---  
none  
nothing  
no comment  
no comments  
no remarks  
not applicable  

Also remove the comment if it contains ONLY punctuation or dashes.

Examples to remove:
"-"
"--"
"---"
"no comment"
"NO COMMENT"
"Nil"
"na"

These comments must NOT appear in the output.

----------------------------------

MANDATORY PROCESSING ALGORITHM
Striclty followed steps one by one in order.
You MUST follow the steps below in exact order.

STEP 1 — Separate Comments

Read every comment and classify it into one of two groups:

Group A: Negative comments  
Examples include:
- complaints
- criticism
- behaviour someone should stop
- dissatisfaction
- negative actions

Group B: Other comments
These include:
- neutral comments
- suggestions
- positive comments
- unclear comments

----------------------------------

STEP 2 — Frequency Ordering for NEGATIVE Comments

This step is REQUIRED.

1. Analyze ALL comments in Group A.
2. Identify comments that share the SAME or VERY SIMILAR meaning.
3. Create meaning groups ONLY for counting frequency.

IMPORTANT:
Meaning groups are ONLY for calculating frequency.
You MUST still output each original comment separately.

Example meaning groups (example only):
Group 1 → fairness / partiality  
Group 2 → shouting / anger  
Group 3 → communication issues  

4. Count how many comments belong to each meaning group.

5. Sort meaning groups by frequency (highest → lowest).

6. Output comments in this order:

First → all comments from the most frequent meaning group  
Second → all comments from the second most frequent meaning group  
Third → all comments from the third most frequent meaning group  

Continue until ALL negative comments are output.

STABILITY RULE (MANDATORY):
- Within the SAME meaning group, keep the original relative order from the input list.

TIE RULE (MANDATORY):
- If two meaning groups have the same frequency, order the meaning groups by which meaning group appears earliest in the input list.

----------------------------------

STEP 3 — Frequency Ordering for OTHER Comments

After ALL negative comments are finished:

1. Take all comments in Group B.
2. Again group them by similar meaning ONLY to count frequency.
3. Count how many comments belong to each meaning group.
4. Sort meaning groups by frequency (highest → lowest).

5. Output comments in this order:

First → comments from the most frequent meaning group  
Second → comments from the second most frequent meaning group  
Third → comments from the third most frequent meaning group  

Continue until ALL comments are listed.

----------------------------------

TEXT FORMATTING RULES

1. If a comment contains a clearly negative phrase, highlight ONLY the negative phrase using:

<span style="color:red"><strong>negative phrase</strong></span>

2. Highlight ONLY the exact words already present in the sentence.

3. Apply Markdown bold (**text**) ONLY to clearly positive traits already written in the sentence.

4. Do NOT invent new words.

5. Do NOT bold the entire sentence unless the full sentence is purely a positive trait.

6. Do NOT change wording.

----------------------------------

OUTPUT FORMAT

Return ONLY valid JSON with exactly this shape:
{
  "stop_doing": ["comment 1", "comment 2", "comment 3"]
}

----------------------------------

FINAL OUTPUT RULES
1. The "stop_doing" array MUST contain all kept comments in the correct order.
2. ALL NEGATIVE comments must appear before ANY OTHER comment.
3. Within NEGATIVE comments, order by meaning-group frequency (highest to lowest), with stability and tie rules applied.
4. After all NEGATIVE comments, output ALL OTHER comments ordered by meaning-group frequency (highest to lowest), with the same stability and tie rules.
5. Output ONLY the JSON object. No extra text.
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
                    system_prompt=continue_prompt,
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
            # analysis_general_stop_doing=controller.analysis_comment_to_generate(stop_doing_thing_words,stop_prompt,stop_feedback_schema)
            # action_areas_thing_llm_generate = controller.generate_action_areas(action_areas_thing_data_extended)

            return JSONResponse(
                status_code=200,
                content={
                    "name": name,
                    "total_response":total_response,
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
                    # "comparision_average":comparision_data,
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