from fastapi import HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from collections import defaultdict
import asyncio
import re
import uuid
import time
import os

import redis

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

_feedback_redis_conn = None
_feedback_rq_queue = None
_feedback_rq_result_ttl_seconds = int(os.getenv("FEEDBACK_RQ_RESULT_TTL_SECONDS", "3600"))

def _get_feedback_redis_conn():
    global _feedback_redis_conn
    if _feedback_redis_conn is not None:
        return _feedback_redis_conn

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _feedback_redis_conn = redis.Redis.from_url(redis_url)
    return _feedback_redis_conn

def _get_feedback_rq_queue():
    global _feedback_rq_queue
    if _feedback_rq_queue is not None:
        return _feedback_rq_queue

    if os.name == "nt":
        raise HTTPException(
            status_code=500,
            detail="RQ requires fork and is not supported in native Windows Python. Run the backend + rq-worker via Docker/WSL/Linux.",
        )

    try:
        from rq import Queue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RQ import error: {str(e)}")

    queue_name = os.getenv("FEEDBACK_RQ_QUEUE", "feedback")
    _feedback_rq_queue = Queue(name=queue_name, connection=_get_feedback_redis_conn())
    return _feedback_rq_queue

def _rq_continue_job(continue_words):
    controller = LLMGenerationController()
    result = CommonFunctions.timed_task(
        "LLM continue_doing",
        controller.analysis_comment_to_generate,
        continue_words,
        CONTINUE_PROMPT,
        CONTINUE_FEEDBACK_SCHEMA,
    )
    return result.get('structured', {}).get('continue_doing', []) if isinstance(result, dict) else []

def _rq_stop_job(stop_words):
    controller = LLMGenerationController()
    result = CommonFunctions.timed_task(
        "LLM stop_doing",
        controller.analysis_comment_to_generate,
        stop_words,
        STOP_PROMPT,
        STOP_FEEDBACK_SCHEMA,
    )
    return result.get('structured', {}).get('stop_doing', []) if isinstance(result, dict) else []

class FeedbackController:
    async def start_feedback_excel_base_job(self, file):
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
                df = pd.read_excel(uploaded_file.file, engine="openpyxl")
                df = df.replace([np.nan, np.inf, -np.inf], None)
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].astype(str)
                return df.to_dict(orient="records") if df is not None else []

            file1_data = read_excel_records(files[0])
            comparision_data = {}

            if len(files) == 2:
                file2_data = read_excel_records(files[1])
                f1 = CommonFunctions.all_question_wise_data(file1_data)
                f2 = CommonFunctions.all_question_wise_data(file2_data)
                comparision_data = CommonFunctions.find_comparision_year_data(f1, f2)

            if len(files) == 3:
                file2_data = read_excel_records(files[1])
                file3_data = read_excel_records(files[2])
                f1 = CommonFunctions.all_question_wise_data(file1_data)
                f2 = CommonFunctions.all_question_wise_data(file2_data)
                f3 = CommonFunctions.all_question_wise_data(file3_data)
                comparision_data = CommonFunctions.find_comparision_multi_year_data(f1, f2, f3)

            data = file1_data

            if not data:
                return JSONResponse(
                    status_code=400,
                    content={"message": "No data found in uploaded file."}
                )

            name = data[0].get("Employee Name") or data[0].get("Name") or "Employee Name"

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
                        exceptItem = [
                            'Nominee Name','Employee Name','Employee ID','Nominee ID',
                            'Rater Group','Rate Group','Rating','Comment','Declined Comment','Name','Question'
                        ]
                        if question not in exceptItem:
                            general_competency[question] = [r.get(col) for r in data]

                right_culture_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Creating the Right Culture', []))
                leadership_style_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Leadership Style', []))
                leadership_staff_dev_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Leadership for Staff Performance & Development', []))
                educational_quality_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Educational Quality & Student Outcomes', []))
                engagement_with_management_competency = CommonFunctions.questionwise_avg_from_rating_lists(category_data.get('Engagement with Management', []))

                rate_groups = [
                    (r.get('Rate Group') or r.get('Rater Group'))
                    for r in data
                    if isinstance(r, dict)
                ]

                response_by_group = {
                    "Self": 0,
                    "Manager": 0,
                    "Subordinates": 0
                }

                for rg in rate_groups:
                    if not rg:
                        continue

                    rg_norm = str(rg).strip().lower()

                    if rg_norm == "self":
                        response_by_group["Self"] += 1
                    elif "manager" in rg_norm:
                        response_by_group["Manager"] += 1
                    elif rg_norm in ("subordinates", "others"):
                        response_by_group["Subordinates"] += 1

                total_response = {
                    "total": sum(response_by_group.values()),
                    **response_by_group
                }

            overall_questionwise_data = {}
            overall_questionwise_data.update(right_culture_competency)
            overall_questionwise_data.update(leadership_style_competency)
            overall_questionwise_data.update(leadership_staff_dev_competency)
            overall_questionwise_data.update(educational_quality_competency)
            overall_questionwise_data.update(engagement_with_management_competency)

            abc_questions = CommonFunctions.count_abc_responses(general_competency)
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

            action_extended = [
                stand_out_leader_words,
                continue_words,
                stop_words,
                *action_words,
            ]

            controller = LLMGenerationController()
            results = await asyncio.gather(
                asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM predominant_leader_thing",
                    controller.analysis_comment_to_generate,
                    predominant_words,
                    CONTINUE_PROMPT,
                    PREDOMINANT_SCHEMA,
                ),
                asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM action_areas",
                    controller.generate_action_areas,
                    action_extended,
                ),
                asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM stand_out_leader",
                    controller.analysis_comment_to_generate,
                    stand_out_leader_words,
                    STAND_OUT_LEADER_SIMPLE_PROMPT,
                    STAND_OUT_LEADER_THING_SCHEMA,
                ),
                asyncio.to_thread(
                    CommonFunctions.timed_task,
                    "LLM workplace_culture",
                    controller.analysis_comment_to_generate,
                    workplace_culture_words,
                    WORKPLACE_CULTURE_PROMPT,
                    WORKPLACE_CULTURE_SCHEMA,
                ),
            )

            (
                analysis_general_predominant_leader_thing,
                action_areas_thing_llm_generate,
                stand_out_leader_thing_generate,
                workplace_culture_generated_words,
            ) = results

            base_response = {
                "name": name,
                "total_response": total_response,
                "comparision_average": comparision_data,
                "competency_summary_overall": {
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
                "nominee_leadership": abc_questions,
                "workplace_culture": workplace_culture_generated_words.get('structured', {}).get('workplace_culture', []),
                "predominant_leader_most_thing": stand_out_leader_thing_generate.get('structured', {}).get('stand_out_leader', []),
                "continue_doing_thing": [],
                "stop_doing_thing": [],
                "predominant_leader_thing": analysis_general_predominant_leader_thing.get('structured', {}).get('predominant_leader_thing', []),
                "action_areas_thing": action_areas_thing_llm_generate.get('structured', {}),
            }

            queue = _get_feedback_rq_queue()
            continue_job = queue.enqueue(
                _rq_continue_job,
                continue_words,
                result_ttl=_feedback_rq_result_ttl_seconds,
                job_timeout=int(os.getenv("FEEDBACK_RQ_JOB_TIMEOUT_SECONDS", "900")),
            )
            stop_job = queue.enqueue(
                _rq_stop_job,
                stop_words,
                result_ttl=_feedback_rq_result_ttl_seconds,
                job_timeout=int(os.getenv("FEEDBACK_RQ_JOB_TIMEOUT_SECONDS", "900")),
            )

            return {
                "job_id": str(uuid.uuid4()),
                "continue_job_id": continue_job.id,
                "stop_job_id": stop_job.id,
                **base_response,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error : {str(e)}")

    async def run_continue_doing_by_job(self, job_id: str):
        if os.name == "nt":
            raise HTTPException(
                status_code=500,
                detail="RQ is not supported in native Windows Python. Run via Docker/WSL/Linux.",
            )

        try:
            from rq.job import Job
            rq_job = Job.fetch(job_id, connection=_get_feedback_redis_conn())
        except Exception:
            raise HTTPException(status_code=404, detail="Job not found")

        if rq_job.is_finished:
            result = rq_job.result or []
            return {
                "status": "finished",
                "continue_doing_thing": result if isinstance(result, list) else [],
            }
        if rq_job.is_failed:
            return {
                "status": "failed",
                "continue_doing_thing": [],
            }
        return {
            "status": rq_job.get_status(),
            "continue_doing_thing": [],
        }

    async def run_stop_doing_by_job(self, job_id: str):
        if os.name == "nt":
            raise HTTPException(
                status_code=500,
                detail="RQ is not supported in native Windows Python. Run via Docker/WSL/Linux.",
            )

        try:
            from rq.job import Job
            rq_job = Job.fetch(job_id, connection=_get_feedback_redis_conn())
        except Exception:
            raise HTTPException(status_code=404, detail="Job not found")

        if rq_job.is_finished:
            result = rq_job.result or []
            return {
                "status": "finished",
                "stop_doing_thing": result if isinstance(result, list) else [],
            }
        if rq_job.is_failed:
            return {
                "status": "failed",
                "stop_doing_thing": [],
            }
        return {
            "status": rq_job.get_status(),
            "stop_doing_thing": [],
        }