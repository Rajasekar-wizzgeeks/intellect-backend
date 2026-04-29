
import json
from datetime import datetime
from fastapi.responses import StreamingResponse
import pandas as pd
import numpy as np
import re
import os

import asyncio
from collections import defaultdict
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
                    file1_data=read_excell_file(__files[0])
                    data = file1_data
                    profile = extract_profile(data)
                    grouped=defaultdict(list)
                    category_data = {}
                    general_competency = {}
                    for row in data:
                        grouped[row.get("Name")].append(row)

                    if "Name" in data[0]:
                        leadership = grouped["Leadership"]
                        leadership_feedback = grouped["Leadership Feedback"]
                        bandwidth = grouped["Bandwidth"]
                        bandwidth_feedback = grouped["Bandwidth Feedback"]
                        sales_and_customer_centricity = grouped["Sales and Customer Centricity"]
                        sales_and_customer_centricity_feedback = grouped["Sales and Customer Centricity Feedback"]
                        collaboration = grouped["Collaboration"]
                        collaboration_feedback = grouped["Collaboration Feedback"]
                        operational_excellence = grouped["Operational Excellence"]
                        operational_excellence_feedback = grouped["Operational Excellence Feedback"]
                        result_orientation = grouped["Result Orientation"]
                        result_orientation_feedback = grouped["Result Orientation Feedback"]
                        expertise_and_communication = grouped["Expertise and Communication"]
                        expertise_and_communication_feedback = grouped["Expertise and Communication Feedback"]
                        category_data = {
                            "Leadership": leadership,
                            "Leadership Feedback": leadership_feedback,
                            "Bandwidth": bandwidth,
                            "Bandwidth Feedback": bandwidth_feedback,
                            "Sales and Customer Centricity": sales_and_customer_centricity,
                            "Sales and Customer Centricity Feedback": sales_and_customer_centricity_feedback,
                            "Collaboration": collaboration,
                            "Collaboration Feedback": collaboration_feedback,
                            "Operational Excellence": operational_excellence,
                            "Operational Excellence Feedback": operational_excellence_feedback,
                            "Result Orientation": result_orientation,
                            "Result Orientation Feedback": result_orientation_feedback,
                            "Expertise and Communication": expertise_and_communication,
                            "Expertise and Communication Feedback": expertise_and_communication_feedback
                        }
                    
                    else:
                        def extract_category(column):
                            if not column:
                                return None, None

                            column = column.strip() 

                            match = re.match(r"\s*\[\s*(.*?)\s*\]\s*(.*)", column)

                            if match:
                                category = match.group(1).strip()   
                                question = match.group(2).strip() 
                                return category, question

                            return None, column

                        
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
                                    rg = row.get("Rate Group") or row.get("Rater Group") or row.get("Rater type") or "Unknown"
                                    values_by_rate_group.setdefault(rg, []).append(row.get(col))
                                category_data[category].append({question: values_by_rate_group})
                            else:
                                exceptItem = ['Assessment name','Feedback type','Question template','Created by','Created on','Feedback recipient ID','Feedback recipient name','Feedback recipient status','Gender','Feedback recipient email ID','DOJ','Organzation unit','Department','Designation','Location','Rater Group','Rate Group','Rater type','Rater ID','Rater name','Rater status','Rater email ID','Rating','Comment','Declined Comment','Name','Question']
                                if question not in exceptItem:
                                    general_competency[question] = [r.get(col) for r in data]
                    behavioural_indications = CommonFunctions.lbscore_broken_down_by_behavioural_indications(category_data)
                    overall_behavioural_indications,feedbacks=CommonFunctions.lbscore_overall_summary_of_scores(category_data)
                    hidden_strengths,blind_spots,area_of_improvements,strengths = CommonFunctions.get_highlights(behavioural_indications)
                    competency_summary = CommonFunctions.get_competency_summary(overall_behavioural_indications)
                    return {
                        "profile":profile,
                        "behavioural_indications": behavioural_indications,
                        "overall_behavioural_indications":overall_behavioural_indications,
                        "general_competency": general_competency,
                        "feedbacks":feedbacks,
                        "hidden_strengths":hidden_strengths,
                        "blind_spots":blind_spots,
                        "area_of_improvements":area_of_improvements,
                        "strengths":strengths,
                        "competency_summary":competency_summary
                      }
                    # yield json.dumps(file1_data)
                pre = await asyncio.to_thread(preprocess_base_sync, files)
                payload = {'type': 'profile', 'data': pre.get('profile', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'behavioural_indications', 'data': pre.get('behavioural_indications', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'feedbacks', 'data': pre.get('feedbacks', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'overall_behavioural_indications', 'data': pre.get('overall_behavioural_indications', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'hidden_strengths', 'data': pre.get('hidden_strengths', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'blind_spots', 'data': pre.get('blind_spots', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'area_of_improvements', 'data': pre.get('area_of_improvements', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'strengths', 'data': pre.get('strengths', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'general_competency', 'data': pre.get('general_competency', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                payload = {'type': 'competency_summary', 'data': pre.get('competency_summary', {})}
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
     