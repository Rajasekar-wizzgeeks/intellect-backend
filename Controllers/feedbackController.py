from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from Utils.common import CommonFunctions
from Controllers.llmGenerationController import LLMGenerationController
from Controllers.prompts import CONTINUE_PROMPT, STOP_PROMPT, STAND_OUT_LEADER_SIMPLE_PROMPT, WORKPLACE_CULTURE_PROMPT
from Controllers.schemas import CONTINUE_FEEDBACK_SCHEMA, STOP_FEEDBACK_SCHEMA, PREDOMINANT_SCHEMA, STAND_OUT_LEADER_THING_SCHEMA, WORKPLACE_CULTURE_SCHEMA
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
            comparision_data={}
            if len(files) == 2:
                file2_data = read_excel_records(files[1])
                comparision_file1 = file1_data
                comparision_file2 = file2_data
                file2_question_data = CommonFunctions.all_question_wise_data(comparision_file1)
                file3_question_data = CommonFunctions.all_question_wise_data(comparision_file2)
                comparision_data=CommonFunctions.find_comparision_year_data(file2_question_data,file3_question_data)

            if len(files) == 3:
                file2_data = read_excel_records(files[1])
                file3_data = read_excel_records(files[2])
                comparision_file1 = file2_data
                comparision_file2 = file3_data
                file1_question_data = CommonFunctions.all_question_wise_data(file1_data)
                file2_question_data = CommonFunctions.all_question_wise_data(comparision_file1)
                file3_question_data = CommonFunctions.all_question_wise_data(comparision_file2)
                comparision_data=CommonFunctions.find_comparision_multi_year_data(file1_question_data,file2_question_data,file3_question_data)

            data = file1_data
            
            if not data:
                return JSONResponse(
                    status_code=400,
                    content={"message": "No data found in uploaded file."}
                )
            

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

                rate_groups = [
                    (r.get('Rate Group') or r.get('Rater Group'))
                    for r in data
                    if isinstance(r, dict)
                ]
                rate_groups = [rg for rg in rate_groups if rg is not None]
                # total_response_count = len(rate_groups) if rate_groups else len(data)
                response_by_group = {
                    "Self": 0,
                    "Manager": 0,
                    "Subordinates": 0
                }
                for rg in rate_groups:
                    rg_norm = str(rg).strip().lower()
                    # rv=row.get('Rating')
                    # if not rv:
                    #     continue
                    if rg_norm == "self":
                        response_by_group["Self"] += 1
                    elif "manager" in rg_norm:
                        response_by_group["Manager"] += 1
                    elif rg_norm == "subordinates" or rg_norm == "others":
                        response_by_group["Subordinates"] += 1
                total_response_count = response_by_group["Self"] + response_by_group["Manager"] + response_by_group["Subordinates"]
                total_response={
                    "total": total_response_count,
                    **response_by_group
                }

            
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

            continue_prompt = CONTINUE_PROMPT
            stop_prompt = STOP_PROMPT
            stand_out_leader_simple_prompt = STAND_OUT_LEADER_SIMPLE_PROMPT
            workplace_culture_prompt = WORKPLACE_CULTURE_PROMPT


            continue_feedback_schema = CONTINUE_FEEDBACK_SCHEMA
            stop_feedback_schema = STOP_FEEDBACK_SCHEMA
            predominant_schema = PREDOMINANT_SCHEMA
            stand_out_leader_thing_schema = STAND_OUT_LEADER_THING_SCHEMA
            workplace_culture_schema = WORKPLACE_CULTURE_SCHEMA

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
            # print("Comparision Data:", comparision_data)  
            # analysis_general_continue_doing=controller.analysis_comment_to_generate(continue_doing_thing_words,
            #         system_prompt=continue_prompt,
            #         feedback_schema=continue_feedback_schema)
            # analysis_general_stop_doing=controller.analysis_comment_to_generate(
            #          stop_doing_thing_words,
            #         system_prompt=stop_prompt,
            #         feedback_schema=stop_feedback_schema)
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
                    "comparision_average":comparision_data,
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