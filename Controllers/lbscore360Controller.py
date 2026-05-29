
import json
from datetime import datetime
from fastapi.responses import StreamingResponse
import pandas as pd
import numpy as np
import re
import os

import asyncio
from collections import defaultdict, OrderedDict
from Utils.common import CommonFunctions

class LBscore360Controller:
    def __init__(self):
        self.now = datetime.now()
        self.formatted_date = self.now.strftime("%b %Y")

    async def start_lbscore360_excel_base_job(self, file):
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        async def event_generator():
            try:
                if not file:
                    payload = {'error': 'File is required.'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                files= file if isinstance(file,(list,tuple)) else [file]
                if any(f is None or getattr(f,"file",None) is None for f in files):
                    payload ={"error":"File is required"}
                    yield f"data:{json.dumps(payload)}\n\n"
                    yield "data:[DONE]\n\n"
                    return
                def preprocess_base_sync(__files):
                    def read_excell_file(uploaded_file):
                        uploaded_file.file.seek(0)
                        df=pd.read_excel(uploaded_file.file, engine="openpyxl")
                        if "Attribute Name" in df.columns:
                            df = df.rename(columns={"Attribute Name": "Name"})
                        df=df.replace([np.nan, np.inf, -np.inf], None)
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]):
                                df[col] = df[col].astype(str)
                        return df.to_dict(orient="records") if df is not None else []
                    def extract_profile(data):
                        if not data:
                            return {}

                        df = pd.DataFrame(data)

                        first_row = df.iloc[0]

                        raw_name = first_row.get("Feedback recipient name", "")
                        name = raw_name.split("(")[-1].replace(")", "").strip() if "(" in raw_name else raw_name

                        rater_types = df.get("Rater type")
                        assessed_by = ", ".join(sorted(set(rater_types.dropna()))) if rater_types is not None else ""

                        return {
                            "Associate Name": name,
                            "Associate ID": first_row.get("Feedback recipient ID"),
                            "Email ID": first_row.get("Feedback recipient email ID"),
                            "Stream": first_row.get("Department"),
                            "LOB": first_row.get("Organzation unit"),
                            "Report Date": str(first_row.get("Created on")).replace("_","-"),
                            "Assessed By": assessed_by
                        }
                    def get_display_name(raw_name):
                        if raw_name and "(" in raw_name:
                            return raw_name.split("(")[-1].replace(")", "").strip()
                        return raw_name or "Employee Name"
                    file1_data=read_excell_file(__files[0])
                    all_records=[]
                    for f in __files:
                        all_records.extend(read_excell_file(f))
                    if not all_records:
                        return {"error": "No data found in uploaded file."}

                    recipient_groups = OrderedDict()
                    for row in all_records:
                        rid = row.get("Feedback recipient ID")
                        if not rid:
                            continue
                        if rid not in recipient_groups:
                            recipient_groups[rid] = []
                        recipient_groups[rid].append(row)
                    recipient_order = list(recipient_groups.keys())

                    # Pass 1: build employee_wise_category_data across all recipients for cohort calculations
                    employee_wise_category_data = {}

                    def extract_category_name(column):
                        if not column:
                            return None, None
                        column = column.strip()
                        match = re.match(r"\s*\[\s*(.*?)\s*\]\s*(.*)", column)
                        if match:
                            return match.group(1).strip(), match.group(2).strip()
                        return None, column

                    if all_records and "Feedback recipient ID" in all_records[0] and "Name" not in all_records[0]:
                        # Wide-format Excel (the lbscore360 format with bracketed column headers)
                        columns = list(all_records[0].keys())
                        for col in columns:
                            if "Average" in col:
                                continue
                            category, question = extract_category_name(col)
                            if not category:
                                continue
                            for row in all_records:
                                employee_name = get_display_name(row.get("Feedback recipient name"))
                                rg = (
                                    row.get("Rate Group")
                                    or row.get("Rater Group")
                                    or row.get("Rater type")
                                    or "Unknown"
                                )
                                value = row.get(col)
                                score_match = re.search(r"\d+", str(value)) if value is not None else None
                                if not score_match:
                                    continue
                                score = int(score_match.group())

                                if employee_name not in employee_wise_category_data:
                                    employee_wise_category_data[employee_name] = []

                                current_rater = None
                                for item in employee_wise_category_data[employee_name]:
                                    if item["Rater type"] == rg:
                                        current_rater = item
                                        break

                                if not current_rater:
                                    current_rater = {
                                        "Function": (
                                            row.get("Department")
                                            or row.get("Function")
                                            or "Business"
                                        ),
                                        "Rater type": rg
                                    }
                                    employee_wise_category_data[employee_name].append(current_rater)

                                if category not in current_rater:
                                    current_rater[category] = []

                                current_rater[category].append(score)

                    # Pass 2: per-recipient analytics loop
                    per_recipient_results = []

                    def extract_category(column):
                        if not column:
                            return None, None
                        column = column.strip()
                        match = re.match(r"\s*\[\s*(.*?)\s*\]\s*(.*)", column)
                        if match:
                            return match.group(1).strip(), match.group(2).strip()
                        return None, column

                    exceptItem = [
                        'Assessment name', 'Feedback type', 'Question template',
                        'Created by', 'Created on', 'Feedback recipient ID',
                        'Feedback recipient name', 'Feedback recipient status',
                        'Gender', 'Feedback recipient email ID', 'DOJ',
                        'Organzation unit', 'Department', 'Designation', 'Location',
                        'Rater Group', 'Rate Group', 'Rater type', 'Rater ID',
                        'Rater name', 'Rater status', 'Rater email ID', 'Rating',
                        'Comment', 'Declined Comment', 'Name', 'Question'
                    ]

                    for rid, recipient_rows in recipient_groups.items():
                        if not recipient_rows:
                            continue

                        # Profile
                        profile = extract_profile(recipient_rows)
                        employee_name = get_display_name(
                            recipient_rows[0].get("Feedback recipient name")
                        )

                        # Build category_data for this recipient only
                        category_data = {}
                        general_competency = {}

                        if "Name" in recipient_rows[0]:
                            grouped_by_name = defaultdict(list)
                            for row in recipient_rows:
                                grouped_by_name[row.get("Name")].append(row)

                            category_data = {
                                "Leadership": grouped_by_name.get("Leadership", []),
                                "Leadership Feedback": grouped_by_name.get("Leadership Feedback", []),
                                "Bandwidth": grouped_by_name.get("Bandwidth", []),
                                "Bandwidth Feedback": grouped_by_name.get("Bandwidth Feedback", []),
                                "Sales and Customer Centricity": grouped_by_name.get("Sales and Customer Centricity", []),
                                "Sales and Customer Centricity Feedback": grouped_by_name.get("Sales and Customer Centricity Feedback", []),
                                "Collaboration": grouped_by_name.get("Collaboration", []),
                                "Collaboration Feedback": grouped_by_name.get("Collaboration Feedback", []),
                                "Operational Excellence": grouped_by_name.get("Operational Excellence", []),
                                "Operational Excellence Feedback": grouped_by_name.get("Operational Excellence Feedback", []),
                                "Result Orientation": grouped_by_name.get("Result Orientation", []),
                                "Result Orientation Feedback": grouped_by_name.get("Result Orientation Feedback", []),
                                "Expertise and Communication": grouped_by_name.get("Expertise and Communication", []),
                                "Expertise and Communication Feedback": grouped_by_name.get("Expertise and Communication Feedback", []),
                            }
                        else:
                            columns = list(recipient_rows[0].keys())
                            for col in columns:
                                if "Average" in col:
                                    continue
                                category, question = extract_category(col)
                                if category:
                                    if category not in category_data:
                                        category_data[category] = []

                                    values_by_rate_group = {}
                                    for row in recipient_rows:
                                        rg = (
                                            row.get("Rate Group")
                                            or row.get("Rater Group")
                                            or row.get("Rater type")
                                            or "Unknown"
                                        )
                                        value = row.get(col)
                                        score_match = re.search(r"\d+", str(value)) if value is not None else None
                                        if not score_match:
                                            continue
                                        score = int(score_match.group())
                                        values_by_rate_group.setdefault(rg, []).append(score)

                                    category_data[category].append({question: values_by_rate_group})
                                else:
                                    if question and question not in exceptItem:
                                        general_competency[question] = [r.get(col) for r in recipient_rows]

                        behavioural_indications = CommonFunctions.lbscore_broken_down_by_behavioural_indications(category_data)


                        for _q, _items in behavioural_indications.items():
                            for _item in _items:
                                _score = _item.get("score", {})
                                for _key in ("Manager", "Peer", "Subordinate", "Self"):
                                    if _key not in _score:
                                        _score[_key] = 0

                        overall_behavioural_indications, feedbacks = CommonFunctions.lbscore_overall_summary_of_scores(category_data)
                        hidden_strengths, blind_spots, area_of_improvements, strengths = CommonFunctions.get_highlights(behavioural_indications)

                        # Participant vs cohort
                        try:
                            participant_and_cohort_summary = CommonFunctions.calculate_participant_and_cohort_rating(
                                employee_wise_category_data, employee_name
                            )
                        except (KeyError, Exception):
                            participant_and_cohort_summary = {}

                        per_recipient_results.append({
                            "employee_id": rid,
                            "employee_name": employee_name,
                            "profile": profile,
                            "behavioural_indications": behavioural_indications,
                            "overall_behavioural_indications": overall_behavioural_indications,
                            "feedbacks": feedbacks,
                            "hidden_strengths": hidden_strengths,
                            "blind_spots": blind_spots,
                            "area_of_improvements": area_of_improvements,
                            "strengths": strengths,
                            "general_competency": general_competency,
                            "participant_and_cohort_summary": participant_and_cohort_summary,
                        })

                    # Cohort-level competency summary (computed once across all recipients)
                    competency_summary = CommonFunctions.get_competency_summary(employee_wise_category_data)

                    return {
                        "recipients": per_recipient_results,
                        "competency_summary": competency_summary,
                    }
                pre = await asyncio.to_thread(preprocess_base_sync, files)

                # Stream one event per recipient containing all their data
                for recipient in pre.get("recipients", []):
                    payload = {
                        "type": "recipient_data",
                        "employee_id": recipient.get("employee_id", "unknown"),
                        "data": {
                            "profile": recipient.get("profile", {}),
                            "participant_and_cohort_summary": recipient.get("participant_and_cohort_summary", {}),
                            "behavioural_indications": recipient.get("behavioural_indications", {}),
                            "feedbacks": recipient.get("feedbacks", {}),
                            "overall_behavioural_indications": recipient.get("overall_behavioural_indications", {}),
                            "hidden_strengths": recipient.get("hidden_strengths", []),
                            "blind_spots": recipient.get("blind_spots", []),
                            "area_of_improvements": recipient.get("area_of_improvements", []),
                            "strengths": recipient.get("strengths", []),
                            "general_competency": recipient.get("general_competency", {}),
                        }
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                # Cohort-level competency summary emitted once
                payload = {
                    "type": "competency_summary",
                    "employee_id": "all",
                    "data": pre.get("competency_summary", {})
                }
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
     