import json
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import numpy as np
from collections import defaultdict
import asyncio
import re
import os
from datetime import datetime

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
    def __init__(self):
        self.now = datetime.now()
        self.formatted_date = self.now.strftime("%b %Y")
    
    async def start_feedback_excel_base_job(self, file):
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        async def event_generator():
            try:
                if file is None:
                    payload = {'error': 'File is required.'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                files = file if isinstance(file, (list, tuple)) else [file]
                if any(f is None or getattr(f, "file", None) is None for f in files):
                    payload = {'error': 'File is required.'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                def preprocess_base_sync(_files):
                    def read_excel_records(uploaded_file):
                        uploaded_file.file.seek(0)
                        df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                        df = df.replace([np.nan, np.inf, -np.inf], None)
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]):
                                df[col] = df[col].astype(str)
                        return df.to_dict(orient="records") if df is not None else []

                    file1_data = read_excel_records(_files[0])
                    if not file1_data:
                        return {"error": "No data found in uploaded file."}

                    name = file1_data[0].get("Employee Name") or file1_data[0].get("Name") or "Employee Name"

                    comparision_data = {}
                    manager_comparision_data = {}
                    if len(_files) == 2:
                        file2_data = read_excel_records(_files[1])
                        f1 = CommonFunctions.all_question_wise_data(file1_data)
                        f2 = CommonFunctions.all_question_wise_data(file2_data)
                        comparision_data,manager_comparision_data = CommonFunctions.find_comparision_year_data(f1, f2)
                        print(f"DEBUG: Comparison data (2 files): {bool(comparision_data)}")

                    if len(_files) == 3:
                        file2_data = read_excel_records(_files[1])
                        file3_data = read_excel_records(_files[2])
                        f1 = CommonFunctions.all_question_wise_data(file1_data)
                        f2 = CommonFunctions.all_question_wise_data(file2_data)
                        f3 = CommonFunctions.all_question_wise_data(file3_data)
                        comparision_data,manager_comparision_data = CommonFunctions.find_comparision_multi_year_data(f1, f2, f3)
                        print(f"DEBUG: Comparison data (3 files): {bool(comparision_data)}")

                    data = file1_data
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

                    strengths = CommonFunctions.find_strengths_separately(overall_questionwise_data)
                    improvements = CommonFunctions.find_area_of_improvement_separately(overall_questionwise_data)
                    abc_questions = CommonFunctions.count_abc_responses(general_competency)

                    workplace_culture = CommonFunctions.get_workplace_culture_data(general_competency, "workplace_culture")
                    stand_out = CommonFunctions.get_workplace_culture_data(general_competency, "stand_out_leader")
                    continue_data = CommonFunctions.get_workplace_culture_data(general_competency, "continue_doing")
                    stop_data = CommonFunctions.get_workplace_culture_data(general_competency, "stop_doing")
                    action_data = CommonFunctions.get_workplace_culture_data(general_competency, "action_area")

                    get_non_self = CommonFunctions.get_non_self_comments
                    continue_words = CommonFunctions.dedupe_exact_comments(get_non_self(continue_data))
                    stop_words = CommonFunctions.dedupe_exact_comments(get_non_self(stop_data))
                    predominant_words = CommonFunctions.dedupe_exact_comments(get_non_self(stand_out))

                    workplace_culture_words = CommonFunctions.count_workplace_culture_words(workplace_culture)
                    stand_out_leader_words = CommonFunctions.count_workplace_culture_words(stand_out)
                    action_words = get_non_self(action_data)

                    action_extended = [stand_out_leader_words, continue_words, stop_words, *action_words]

                    return {
                        "name": name,
                        "comparision_average": comparision_data,
                        "manager_comparision_data":manager_comparision_data,
                        "total_response": total_response,
                        "competency_summary_overall": competencies,
                        "right_culture_competency": right_culture_competency,
                        "leadership_style_competency": leadership_style_competency,
                        "leadership_staff_dev_competency": leadership_staff_dev_competency,
                        "educational_quality_competency": educational_quality_competency,
                        "engagement_with_management_competency": engagement_with_management_competency,
                        "strengths": strengths,
                        "area_of_improvement": improvements,
                        "nominee_leadership": abc_questions,
                        "predominant_words": predominant_words,
                        "action_extended": action_extended,
                        "stand_out_leader_words": stand_out_leader_words,
                        "workplace_culture_words": workplace_culture_words,
                    }

                pre = await asyncio.to_thread(preprocess_base_sync, files)
                if not isinstance(pre, dict) or pre.get("error"):
                    payload = {'error': (pre.get('error') if isinstance(pre, dict) else 'Failed to process file.')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                payload = {'type': 'meta', 'name': pre.get('name'),'date':self.formatted_date}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'comparision_average', 'comparision_average': pre.get('comparision_average', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type':'manager_comparision_average', 'manager_comparision_average': pre.get('manager_comparision_data', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'total_response', 'total_response': pre.get('total_response', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {
                    'type': 'competencies',
                    'competency_summary_overall': pre.get('competency_summary_overall', {}),
                    'right_culture_competency': pre.get('right_culture_competency', {}),
                    'leadership_style_competency': pre.get('leadership_style_competency', {}),
                    'leadership_staff_dev_competency': pre.get('leadership_staff_dev_competency', {}),
                    'educational_quality_competency': pre.get('educational_quality_competency', {}),
                    'engagement_with_management_competency': pre.get('engagement_with_management_competency', {}),
                }
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {
                    'type': 'strengths_area_of_improvement',
                    'strengths': pre.get('strengths', []),
                    'area_of_improvement': pre.get('area_of_improvement', []),
                }
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'nominee_leadership', 'nominee_leadership': pre.get('nominee_leadership', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                controller = LLMGenerationController()
                
                async def run_and_yield(name, task, *args):
                    res = await asyncio.to_thread(CommonFunctions.timed_task, name, task, *args)
                    return name, res

                tasks = [
                    run_and_yield("LLM predominant_leader_thing", controller.analysis_comment_to_generate, pre.get('predominant_words', []), CONTINUE_PROMPT, PREDOMINANT_SCHEMA),
                    run_and_yield("LLM action_areas", controller.generate_action_areas, pre.get('action_extended', [])),
                    run_and_yield("LLM stand_out_leader", controller.analysis_comment_to_generate, pre.get('stand_out_leader_words', []), STAND_OUT_LEADER_SIMPLE_PROMPT, STAND_OUT_LEADER_THING_SCHEMA),
                    run_and_yield("LLM workplace_culture", controller.analysis_comment_to_generate, pre.get('workplace_culture_words', []), WORKPLACE_CULTURE_PROMPT, WORKPLACE_CULTURE_SCHEMA)
                ]

                for future in asyncio.as_completed(tasks):
                    task_name, result = await future
                    if not isinstance(result, dict):
                        payload = {'type': 'error', 'source': task_name, 'error': 'Invalid LLM response'}
                        yield f"data: {json.dumps(payload)}\n\n"
                        continue
                    if result.get('error'):
                        payload = {'type': 'error', 'source': task_name, 'error': result.get('error')}
                        yield f"data: {json.dumps(payload)}\n\n"
                        continue
                    if task_name == "LLM predominant_leader_thing":
                        payload = {'type': 'predominant_leader_thing', 'predominant_leader_thing': result.get('structured', {}).get('predominant_leader_thing', [])}
                        yield f"data: {json.dumps(payload)}\n\n"
                    elif task_name == "LLM action_areas":
                        payload = {'type': 'action_areas_thing', 'action_areas_thing': result.get('structured', {})}
                        yield f"data: {json.dumps(payload)}\n\n"
                    elif task_name == "LLM stand_out_leader":
                        payload = {'type': 'predominant_leader_most_thing', 'predominant_leader_most_thing': result.get('structured', {}).get('stand_out_leader', [])}
                        yield f"data: {json.dumps(payload)}\n\n"
                    elif task_name == "LLM workplace_culture":
                        payload = {'type': 'workplace_culture', 'workplace_culture': result.get('structured', {}).get('workplace_culture', [])}
                        yield f"data: {json.dumps(payload)}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                payload = {'error': str(e)}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

    async def extract_continue_doing_from_excel(self, file):
        if file is None:
            raise HTTPException(status_code=400, detail="File is required.")

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }

        files = file if isinstance(file, (list, tuple)) else [file]
        if any(f is None or getattr(f, "file", None) is None for f in files):
            raise HTTPException(status_code=400, detail="File is required.")

        async def event_generator():
            try:
                def preprocess_continue_sync(_files):
                    uploaded_file = _files[0]
                    uploaded_file.file.seek(0)
                    df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                    df = df.replace([np.nan, np.inf, -np.inf], None)
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].astype(str)
                    data = df.to_dict(orient="records") if df is not None else []
                    if not data:
                        return {"error": "No data found in uploaded file."}

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
                    continue_words = CommonFunctions.dedupe_exact_comments(CommonFunctions.get_non_self_comments(continue_data))
                    return {"continue_words": continue_words}

                pre = await asyncio.to_thread(preprocess_continue_sync, files)
                if not isinstance(pre, dict) or pre.get("error"):
                    payload = {'error': (pre.get('error') if isinstance(pre, dict) else 'Failed to process file.')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                controller = LLMGenerationController()
                
                llm_task = asyncio.create_task(asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM continue_doing",
                    controller.analysis_comment_to_generate,
                    pre.get('continue_words', []),
                    CONTINUE_PROMPT,
                    CONTINUE_FEEDBACK_SCHEMA,
                ))

                while not llm_task.done():
                    payload = {'type': 'processing'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(15) 

                result = await llm_task
                if not isinstance(result, dict):
                    payload = {'type': 'error', 'error': 'Invalid LLM response'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if result.get('error'):
                    payload = {'type': 'error', 'error': result.get('error')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                payload = {'type': 'continue_doing_thing', 'data': result.get('structured', {}).get('continue_doing', [])}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                payload = {'error': str(e)}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

    async def extract_stop_doing_from_excel(self, file):
        if file is None:
            raise HTTPException(status_code=400, detail="File is required.")

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }

        files = file if isinstance(file, (list, tuple)) else [file]
        if any(f is None or getattr(f, "file", None) is None for f in files):
            raise HTTPException(status_code=400, detail="File is required.")

        async def event_generator():
            try:
                def preprocess_stop_sync(_files):
                    uploaded_file = _files[0]
                    uploaded_file.file.seek(0)
                    df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                    df = df.replace([np.nan, np.inf, -np.inf], None)
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].astype(str)
                    data = df.to_dict(orient="records") if df is not None else []
                    if not data:
                        return {"error": "No data found in uploaded file."}

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
                    stop_words = CommonFunctions.dedupe_exact_comments(CommonFunctions.get_non_self_comments(stop_data))
                    return {"stop_words": stop_words}

                pre = await asyncio.to_thread(preprocess_stop_sync, files)
                if not isinstance(pre, dict) or pre.get("error"):
                    payload = {'error': (pre.get('error') if isinstance(pre, dict) else 'Failed to process file.')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                controller = LLMGenerationController()
                
                llm_task = asyncio.create_task(asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM stop_doing",
                    controller.analysis_comment_to_generate,
                    pre.get('stop_words', []),
                    STOP_PROMPT,
                    STOP_FEEDBACK_SCHEMA,
                ))

                while not llm_task.done():
                    payload = {'type': 'processing'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(15)

                result = await llm_task
                if not isinstance(result, dict):
                    payload = {'type': 'error', 'error': 'Invalid LLM response'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if result.get('error'):
                    payload = {'type': 'error', 'error': result.get('error')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                payload = {'type': 'stop_doing_thing', 'data': result.get('structured', {}).get('stop_doing', [])}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                payload = {'error': str(e)}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)