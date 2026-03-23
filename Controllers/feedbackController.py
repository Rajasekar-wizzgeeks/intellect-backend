import json
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import numpy as np
from collections import defaultdict
import asyncio
import re
import os

from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController
from Controllers.prompts import (
    CONTINUE_PROMPT,
    STOP_PROMPT,
    STAND_OUT_LEADER_SIMPLE_PROMPT,
    WORKPLACE_CULTURE_PROMPT,
)
from Controllers.schemas import (
    CONTINUE_FEEDBACK_SCHEMA,
    STOP_FEEDBACK_SCHEMA,
    PREDOMINANT_SCHEMA,
    STAND_OUT_LEADER_THING_SCHEMA,
    WORKPLACE_CULTURE_SCHEMA,
)

class FeedbackController:

    async def start_feedback_excel_base_job(self, file):
        async def event_generator():
            try:
                if file is None:
                    yield f"data: {json.dumps({'error': 'File is required.'})}\n\n"
                    return

                files = file if isinstance(file, (list, tuple)) else [file]
                if any(f is None or getattr(f, "file", None) is None for f in files):
                    yield f"data: {json.dumps({'error': 'File is required.'})}\n\n"
                    return

                def read_excel_records(uploaded_file):
                    uploaded_file.file.seek(0)
                    df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                    df = df.replace([np.nan, np.inf, -np.inf], None)
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].astype(str)
                    return df.to_dict(orient="records") if df is not None else []

                file1_data = read_excel_records(files[0])
                
                # Yield meta data early
                name = file1_data[0].get("Employee Name") or file1_data[0].get("Name") or "Employee Name"
                yield f"data: {json.dumps({'type': 'meta', 'name': name})}\n\n"

                comparision_data = {}
                if len(files) == 2:
                    file2_data = read_excel_records(files[1])
                    f1 = CommonFunctions.all_question_wise_data(file1_data)
                    f2 = CommonFunctions.all_question_wise_data(file2_data)
                    comparision_data = CommonFunctions.find_comparision_year_data(f1, f2)
                    print(f"DEBUG: Comparison data (2 files): {bool(comparision_data)}")

                if len(files) == 3:
                    file2_data = read_excel_records(files[1])
                    file3_data = read_excel_records(files[2])
                    f1 = CommonFunctions.all_question_wise_data(file1_data)
                    f2 = CommonFunctions.all_question_wise_data(file2_data)
                    f3 = CommonFunctions.all_question_wise_data(file3_data)
                    comparision_data = CommonFunctions.find_comparision_multi_year_data(f1, f2, f3)
                    print(f"DEBUG: Comparison data (3 files): {bool(comparision_data)}")
                
                yield f"data: {json.dumps({'type': 'comparision_average', 'data': comparision_data})}\n\n"

                data = file1_data
                if not data:
                    yield f"data: {json.dumps({'error': 'No data found in uploaded file.'})}\n\n"
                    return

                grouped = defaultdict(list)
                for row in data:
                    grouped[row.get("Name")].append(row)

                if "Name" in data[0]:
                    right_culture = grouped["Creating the Right Culture"]
                    leadership_style = grouped["Leadership Style"]
                    leadership_staff_dev = grouped["Leadership for Staff Performance & Development"]
                    educational_quality = grouped["Educational Quality & Student Outcomes"]
                    engagement_with_management = grouped["Engagement with Management"]
                    general = grouped["General"]

                    right_culture_competency = CommonFunctions.questionwise_avg_by_rate_group(right_culture)
                    leadership_style_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_style)
                    leadership_staff_dev_competency = CommonFunctions.questionwise_avg_by_rate_group(leadership_staff_dev)
                    educational_quality_competency = CommonFunctions.questionwise_avg_by_rate_group(educational_quality)
                    engagement_with_management_competency = CommonFunctions.questionwise_avg_by_rate_group(engagement_with_management)

                    total_response = CommonFunctions.questionwise_find_total_response(right_culture)
                    general_competency = CommonFunctions.grouped_question(general)

                else:
                    def extract_category(column):
                        match = re.match(r"\[(.*?)\]\s*(.*)", column)
                        if match:
                            return match.group(1), match.group(2)
                        return None, column

                    category_data = {}
                    general_competency = {}
                    columns = list(data[0].keys())

                    for col in columns:
                        if "Average" in col:
                            continue
                        category, question = extract_category(col)
                        if category:
                            if category not in category_data:
                                category_data[category] = []
                            values_by_rate_group = {}
                            for row in data:
                                rg = row.get("Rate Group") or row.get("Rater Group") or "Unknown"
                                values_by_rate_group.setdefault(rg, []).append(row.get(col))
                            category_data[category].append({question: values_by_rate_group})
                        else:
                            exceptItem = ['Nominee Name','Employee Name','Employee ID','Nominee ID','Rater Group','Rate Group','Rating','Comment','Declined Comment','Name','Question']
                            if question not in exceptItem:
                                general_competency[question] = [r.get(col) for r in data]

                    right_culture_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Creating the Right Culture', []))
                    leadership_style_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Leadership Style', []))
                    leadership_staff_dev_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Leadership for Staff Performance & Development', []))
                    educational_quality_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Educational Quality & Student Outcomes', []))
                    engagement_with_management_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Engagement with Management', []))

                    rate_groups = [(r.get('Rate Group') or r.get('Rater Group')) for r in data if isinstance(r, dict)]
                    response_by_group = {"Self": 0, "Manager": 0, "Subordinates": 0}
                    for rg in rate_groups:
                        if not rg: continue
                        rg_norm = str(rg).strip().lower()
                        if rg_norm == "self": response_by_group["Self"] += 1
                        elif "manager" in rg_norm: response_by_group["Manager"] += 1
                        elif rg_norm in ("subordinates", "others"): response_by_group["Subordinates"] += 1

                    total_response = {"total": sum(response_by_group.values()), **response_by_group}

                yield f"data: {json.dumps({'type': 'total_response', 'data': total_response})}\n\n"

                overall_questionwise_data = {}
                overall_questionwise_data.update(right_culture_competency)
                overall_questionwise_data.update(leadership_style_competency)
                overall_questionwise_data.update(leadership_staff_dev_competency)
                overall_questionwise_data.update(educational_quality_competency)
                overall_questionwise_data.update(engagement_with_management_competency)

                competencies = {
                    'leadership_style': CommonFunctions.overall_avg_by_group(leadership_style_competency),
                    'educational_quality': CommonFunctions.overall_avg_by_group(educational_quality_competency),
                    'leadership_staff_dev': CommonFunctions.overall_avg_by_group(leadership_staff_dev_competency),
                    'right_culture': CommonFunctions.overall_avg_by_group(right_culture_competency),
                    'engagement_with_management': CommonFunctions.overall_avg_by_group(engagement_with_management_competency)
                }
                yield f"data: {json.dumps({'type': 'competencies', 'summary': competencies, 'details': {
                    'right_culture': right_culture_competency,
                    'leadership_style': leadership_style_competency,
                    'leadership_staff_dev': leadership_staff_dev_competency,
                    'educational_quality': educational_quality_competency,
                    'engagement_with_management': engagement_with_management_competency
                }})}\n\n"

                strengths = CommonFunctions.find_strengths_separately(overall_questionwise_data)
                improvements = CommonFunctions.find_area_of_improvement_separately(overall_questionwise_data)
                yield f"data: {json.dumps({'type': 'strengths_improvements', 'strengths': strengths, 'improvements': improvements})}\n\n"

                abc_questions = CommonFunctions.count_abc_responses(general_competency)
                yield f"data: {json.dumps({'type': 'nominee_leadership', 'data': abc_questions})}\n\n"

                workplace_culture = CommonFunctions.get_workplace_culture_data(general_competency, "workplace_culture")
                stand_out = CommonFunctions.get_workplace_culture_data(general_competency, "stand_out_leader")
                continue_data = CommonFunctions.get_workplace_culture_data(general_competency, "continue_doing")
                stop_data = CommonFunctions.get_workplace_culture_data(general_competency, "stop_doing")
                action_data = CommonFunctions.get_workplace_culture_data(general_competency, "action_area")

                get_non_self = CommonFunctions.get_non_self_comments
                continue_words = get_non_self(continue_data)
                stop_words = get_non_self(stop_data)
                predominant_words = get_non_self(stand_out)

                workplace_culture_words = CommonFunctions.count_workplace_culture_words(workplace_culture)
                stand_out_leader_words = CommonFunctions.count_workplace_culture_words(stand_out)
                action_words = get_non_self(action_data)

                action_extended = [stand_out_leader_words, continue_words, stop_words, *action_words]

                controller = LLMGenerationController()
                
                async def run_and_yield(name, task, *args):
                    res = await asyncio.to_thread(CommonFunctions.timed_task, name, task, *args)
                    return name, res

                tasks = [
                    run_and_yield("LLM predominant_leader_thing", controller.analysis_comment_to_generate, predominant_words, CONTINUE_PROMPT, PREDOMINANT_SCHEMA),
                    run_and_yield("LLM action_areas", controller.generate_action_areas, action_extended),
                    run_and_yield("LLM stand_out_leader", controller.analysis_comment_to_generate, stand_out_leader_words, STAND_OUT_LEADER_SIMPLE_PROMPT, STAND_OUT_LEADER_THING_SCHEMA),
                    run_and_yield("LLM workplace_culture", controller.analysis_comment_to_generate, workplace_culture_words, WORKPLACE_CULTURE_PROMPT, WORKPLACE_CULTURE_SCHEMA)
                ]

                for future in asyncio.as_completed(tasks):
                    task_name, result = await future
                    if task_name == "LLM predominant_leader_thing":
                        yield f"data: {json.dumps({'type': 'predominant_leader_thing', 'data': result.get('structured', {}).get('predominant_leader_thing', [])})}\n\n"
                    elif task_name == "LLM action_areas":
                        yield f"data: {json.dumps({'type': 'action_areas_thing', 'data': result.get('structured', {})})}\n\n"
                    elif task_name == "LLM stand_out_leader":
                        yield f"data: {json.dumps({'type': 'predominant_leader_most_thing', 'data': result.get('structured', {}).get('stand_out_leader', [])})}\n\n"
                    elif task_name == "LLM workplace_culture":
                        yield f"data: {json.dumps({'type': 'workplace_culture', 'data': result.get('structured', {}).get('workplace_culture', [])})}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    async def extract_continue_doing_from_excel(self, file):
        if file is None:
            raise HTTPException(status_code=400, detail="File is required.")

        files = file if isinstance(file, (list, tuple)) else [file]
        if any(f is None or getattr(f, "file", None) is None for f in files):
            raise HTTPException(status_code=400, detail="File is required.")

        async def event_generator():
            try:
                uploaded_file = files[0]
                uploaded_file.file.seek(0)
                df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                df = df.replace([np.nan, np.inf, -np.inf], None)
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].astype(str)
                data = df.to_dict(orient="records") if df is not None else []
                if not data:
                    yield f"data: {json.dumps({'error': 'No data found in uploaded file.'})}\n\n"
                    return

                grouped = defaultdict(list)
                for row in data:
                    grouped[row.get("Name")].append(row)

                if "Name" in data[0]:
                    general = grouped["General"]
                    general_competency = CommonFunctions.grouped_question(general)
                else:
                    def extract_category(column):
                        match = re.match(r"\[(.*?)\]\s*(.*)", column)
                        if match:
                            return match.group(1), match.group(2)
                        return None, column

                    general_competency = {}
                    columns = list(data[0].keys())
                    for col in columns:
                        if "Average" in col:
                            continue
                        category, question = extract_category(col)
                        if category:
                            continue
                        exceptItem = [
                            'Nominee Name','Employee Name','Employee ID','Nominee ID',
                            'Rater Group','Rate Group','Rating','Comment','Declined Comment','Name','Question'
                        ]
                        if question not in exceptItem:
                            general_competency[question] = [r.get(col) for r in data]

                continue_data = CommonFunctions.get_workplace_culture_data(general_competency, "continue_doing")
                continue_words = CommonFunctions.get_non_self_comments(continue_data)

                controller = LLMGenerationController()
                
                llm_task = asyncio.create_task(asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM continue_doing",
                    controller.analysis_comment_to_generate,
                    continue_words,
                    CONTINUE_PROMPT,
                    CONTINUE_FEEDBACK_SCHEMA,
                ))

                while not llm_task.done():
                    yield "data: {\"type\": \"processing\"}\n\n"
                    await asyncio.sleep(15) 

                result = await llm_task
                yield f"data: {json.dumps({'type': 'continue_doing_thing', 'data': result.get('structured', {}).get('continue_doing', [])})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    async def extract_stop_doing_from_excel(self, file):
        if file is None:
            raise HTTPException(status_code=400, detail="File is required.")

        files = file if isinstance(file, (list, tuple)) else [file]
        if any(f is None or getattr(f, "file", None) is None for f in files):
            raise HTTPException(status_code=400, detail="File is required.")

        async def event_generator():
            try:
                uploaded_file = files[0]
                uploaded_file.file.seek(0)
                df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                df = df.replace([np.nan, np.inf, -np.inf], None)
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].astype(str)
                data = df.to_dict(orient="records") if df is not None else []
                if not data:
                    yield f"data: {json.dumps({'error': 'No data found in uploaded file.'})}\n\n"
                    return

                grouped = defaultdict(list)
                for row in data:
                    grouped[row.get("Name")].append(row)

                if "Name" in data[0]:
                    general = grouped["General"]
                    general_competency = CommonFunctions.grouped_question(general)
                else:
                    def extract_category(column):
                        match = re.match(r"\[(.*?)\]\s*(.*)", column)
                        if match:
                            return match.group(1), match.group(2)
                        return None, column

                    general_competency = {}
                    columns = list(data[0].keys())
                    for col in columns:
                        if "Average" in col:
                            continue
                        category, question = extract_category(col)
                        if category:
                            continue
                        exceptItem = [
                            'Nominee Name','Employee Name','Employee ID','Nominee ID',
                            'Rater Group','Rate Group','Rating','Comment','Declined Comment','Name','Question'
                        ]
                        if question not in exceptItem:
                            general_competency[question] = [r.get(col) for r in data]

                stop_data = CommonFunctions.get_workplace_culture_data(general_competency, "stop_doing")
                stop_words = CommonFunctions.get_non_self_comments(stop_data)

                controller = LLMGenerationController()
                
                llm_task = asyncio.create_task(asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM stop_doing",
                    controller.analysis_comment_to_generate,
                    stop_words,
                    STOP_PROMPT,
                    STOP_FEEDBACK_SCHEMA,
                ))

                while not llm_task.done():
                    yield "data: {\"type\": \"processing\"}\n\n"
                    await asyncio.sleep(15)

                result = await llm_task
                yield f"data: {json.dumps({'type': 'stop_doing_thing', 'data': result.get('structured', {}).get('stop_doing', [])})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")