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

from Utils import common
from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController

from Controllers.prompts import (
    FREQUENTLY_OCCURING_SUGGESTIONS,
    LEADER_PROFILE_PROMPT
)
from Controllers.schemas import (
    PREDOMINANT_SCHEMA,
    LEADERSHIP_THEME_CLUSTER_SCHEMA,
    LEADER_PROFILE_SCHEMA
)

class FeedbackSummaryController:
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
                        if "Attribute Name" in df.columns:
                            df = df.rename(columns={"Attribute Name": "Name"})
                        df = df.replace([np.nan, np.inf, -np.inf], None)
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]):
                                df[col] = df[col].astype(str)
                        return df.to_dict(orient="records") if df is not None else []


                    all_records=[]
                    for f in _files:
                        all_records.extend(read_excel_records(f))
                    if not all_records:
                        return {"error": "No data found in uploaded file."}

                    name = all_records[0].get("Employee Name") or all_records[0].get("Name") or "Employee Name"

                    comparision_data = {}
                    manager_comparision_data = {}

                    data = all_records
                    grouped = defaultdict(list)
                    for row in data:
                        grouped[row.get("Name")].append(row)

                    if "Name" in data[0]:
                        right_culture = grouped["Creating the Right Culture"]
                        leadership_style = grouped["Leadership Style"] or grouped["Leadership Personality & Style"]
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
                        leadership_style_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Leadership Style', []) or category_data.get('Leadership Personality & Style', []))
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
                    
                    highest_team_avg,lowest_team_avg,highest_manager_avg,lowest_manager_avg = CommonFunctions.get_headlines(overall_questionwise_data)
                    institution_competency_summary = {
                        "right_culture": CommonFunctions.get_competency_summary_institution(right_culture_competency),
                        "leadership_style": CommonFunctions.get_competency_summary_institution(leadership_style_competency),
                        "leadership_staff_dev": CommonFunctions.get_competency_summary_institution(leadership_staff_dev_competency),
                        "educational_quality": CommonFunctions.get_competency_summary_institution(educational_quality_competency),
                        "engagement_with_management": CommonFunctions.get_competency_summary_institution(engagement_with_management_competency),
                    }

                    headlines = {
                        "hightest_team_avg": highest_team_avg,
                        "lowest_team_avg": lowest_team_avg,
                        "hightest_manager_avg": highest_manager_avg,
                        "lowest_manager_avg": lowest_manager_avg,
                    }
                    
                    overall_principal_averages = CommonFunctions.get_overall_averages_by_principal(all_records)
                    comments_with_employee_name = CommonFunctions.get_all_comments(all_records)
                    employee_wise_overall_data = CommonFunctions.get_employee_wise_overall_data(all_records)
                    summary_framework_recap = CommonFunctions.get_summary_framework_recap(all_records)
                    leadership_profile_data = CommonFunctions.get_leadership_profiles(employee_wise_overall_data)
                    notes = CommonFunctions.get_self_rating_notes(all_records)
                    
                    return {
                        "name": name,
                        "total_response": total_response,
                        "all_records":all_records,
                        "headlines":headlines,
                        "overall_questionwise_data":overall_questionwise_data,
                        "summary_framework_recap":summary_framework_recap,
                        # "summary_by_competency_for_the_institution":summary_by_competency_for_the_institution,
                        "institution_competency_summary":institution_competency_summary,
                        "overall_principal_averages":overall_principal_averages,
                        "comments_with_employee_name":comments_with_employee_name,
                        "leadership_profile_data":leadership_profile_data,
                        "notes": notes
                    }

                pre = await asyncio.to_thread(preprocess_base_sync, files)
                if not isinstance(pre, dict) or pre.get("error"):
                    payload = {'error': (pre.get('error') if isinstance(pre, dict) else 'Failed to process file.')}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                payload = {'type': 'institution_competency_summary', 'institution_competency_summary': pre.get('institution_competency_summary', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'summary_framework_recap', 'summary_framework_recap': pre.get('summary_framework_recap', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'headlines', 'headlines': pre.get('headlines', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'overall_principal_averages', 'overall_principal_averages': pre.get('overall_principal_averages', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                # payload = {'type': 'summary_by_competency_for_the_institution', 'summary_by_competency_for_the_institution': pre.get('summary_by_competency_for_the_institution', {})}
                # yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'comments_with_employee_name', 'comments_with_employee_name': pre.get('comments_with_employee_name', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'overall_questionwise_data', 'overall_questionwise_data': pre.get('overall_questionwise_data', {})}
                yield f"data: {json.dumps(payload)}\n\n"

                payload = {'type': 'notes', 'notes': pre.get('notes', []), 'data': pre.get('notes', [])}
                yield f"data: {json.dumps(payload)}\n\n"

                leadership_profile_data = pre.get('leadership_profile_data', {})
                for r in leadership_profile_data:
                                    
                        controller = LLMGenerationController()
                        highest_team_avg = r.get("highest_team_avg", [])
                        lowest_team_avg = r.get("lowest_team_avg", [])
                        highest_manager_avg = r.get("highest_manager_avg", [])
                        lowest_manager_avg = r.get("lowest_manager_avg", [])
                
                        async def run_and_yield(name, task, *args):
                            res = await asyncio.to_thread(CommonFunctions.timed_task, name, task, *args)
                            return name, res

                        tasks=[
                            run_and_yield("highest_team_avg", controller.analysis_comment_to_generate, json.dumps(highest_team_avg),LEADER_PROFILE_PROMPT,LEADER_PROFILE_SCHEMA),
                            run_and_yield("lowest_team_avg", controller.analysis_comment_to_generate, json.dumps(lowest_team_avg),LEADER_PROFILE_PROMPT,LEADER_PROFILE_SCHEMA),
                            # run_and_yield("highest_manager_avg", controller.analysis_comment_to_generate, json.dumps(highest_manager_avg),LEADER_PROFILE_PROMPT,LEADER_PROFILE_SCHEMA),
                            # run_and_yield("lowest_manager_avg", controller.analysis_comment_to_generate, json.dumps(lowest_manager_avg),LEADER_PROFILE_PROMPT,LEADER_PROFILE_SCHEMA),
                        ]

                        results = await asyncio.gather(*tasks)
                        highest_team_avg_result = next((r for n, r in results if n == "highest_team_avg"), None)
                        lowest_team_avg_result = next((r for n, r in results if n == "lowest_team_avg"), None)
                        # highest_manager_avg_result = next((r for n, r in results if n == "highest_manager_avg"), None)
                        # lowest_manager_avg_result = next((r for n, r in results if n == "lowest_manager_avg"), None)

                        leader_profiles = {
                            "highest_team_avg": highest_team_avg_result,
                            "lowest_team_avg": lowest_team_avg_result,
                        }

                        r["leader_profiles"] = leader_profiles

                payload = {'type': 'leadership_profile_data', 'leadership_profile_data': pre.get('leadership_profile_data', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                
                # payload = {'type': 'institution_competency_summary', 'institution_competency_summary': pre.get('institution_competency_summary', {})}
                # yield f"data: {json.dumps(payload)}\n\n"

                # payload = {'type': 'overall_questionwise_data', 'overall_questionwise_data': pre.get('overall_questionwise_data', {})}
                # yield f"data: {json.dumps(payload)}\n\n"

                # payload = {'type': 'meta', 'name': pre.get('name'),'date':self.formatted_date}
                # yield f"data: {json.dumps(payload)}\n\n"

                
              

                
                controller = LLMGenerationController()

                async def run_and_yield(name, task, *args):
                    res = await asyncio.to_thread(CommonFunctions.timed_task, name, task, *args)
                    return name, res

                tasks = [
                    run_and_yield("LLM Frequently_occuring_suggestions", controller.analysis_comment_to_generate, json.dumps(pre.get('comments_with_employee_name', [])),FREQUENTLY_OCCURING_SUGGESTIONS, LEADERSHIP_THEME_CLUSTER_SCHEMA),
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
                    if task_name == "LLM Frequently_occuring_suggestions":
                        payload = {'type': 'frequently_occuring_suggestions', 'frequently_occuring_suggestions': result.get('structured', {})}
                        yield f"data: {json.dumps(payload)}\n\n"


                yield "data: [DONE]\n\n"

            except Exception as e:
                payload = {'error': str(e)}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
