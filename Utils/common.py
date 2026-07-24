from collections import defaultdict
import re
import time
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import asyncio
import json
import numpy as np


class CommonFunctions:

    @staticmethod
    def grouped_question(records):
        question_grouped = defaultdict(list)
        def clean_question(text):
            text = text.replace("_x000D_", " ")
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        
        for row in records:
            question = clean_question(row.get("Question", ""))
            if not question:
                continue
            question_grouped[question].append(row)

        return question_grouped
    
    
    @staticmethod
    def all_question_wise_data(file1_records):
        if isinstance(file1_records, list) and file1_records and isinstance(file1_records[0], dict) and "Name" in file1_records[0]:
            right_culture = [
                row for row in file1_records if row.get("Name") == "Creating the Right Culture"
            ]
            leadership_style = [
                row for row in file1_records if row.get("Name") == "Leadership Style"
            ]
            leadership_staff_dev = [
                row for row in file1_records if row.get("Name") == "Leadership for Staff Performance & Development"
            ]
            educational_quality = [
                row for row in file1_records if row.get("Name") == "Educational Quality & Student Outcomes"
            ]
            engagement_with_management = [
                row for row in file1_records if row.get("Name") == "Engagement with Management"
            ]

            right_culture_questionwise = CommonFunctions.questionwise_avg_by_rate_group(right_culture)
            leadership_style_questionwise = CommonFunctions.questionwise_avg_by_rate_group(leadership_style)
            leadership_staff_dev_questionwise = CommonFunctions.questionwise_avg_by_rate_group(leadership_staff_dev)
            educational_quality_questionwise = CommonFunctions.questionwise_avg_by_rate_group(educational_quality)
            engagement_with_management_questionwise = CommonFunctions.questionwise_avg_by_rate_group(engagement_with_management)
        else:
            category_data = CommonFunctions.categories_google_excel_sheet(file1_records)
            right_culture_questionwise = CommonFunctions.questionwise_avg_from_rating_lists(
                    category_data.get('Creating the Right Culture', [])
                )
            leadership_style_questionwise = CommonFunctions.questionwise_avg_from_rating_lists(
                category_data.get('Leadership Style', []) or
                category_data.get('Leadership Personality & Style', [])
            )
            leadership_staff_dev_questionwise = CommonFunctions.questionwise_avg_from_rating_lists(
                category_data.get('Leadership for Staff Performance & Development', [])
            )
            educational_quality_questionwise = CommonFunctions.questionwise_avg_from_rating_lists(
                category_data.get('Educational Quality & Student Outcomes', [])
            )
            engagement_with_management_questionwise = CommonFunctions.questionwise_avg_from_rating_lists(
                category_data.get('Engagement with Management', [])
            )
        combined_questionwise = {}
        combined_questionwise.update(right_culture_questionwise)
        combined_questionwise.update(leadership_style_questionwise)
        combined_questionwise.update(leadership_staff_dev_questionwise)
        combined_questionwise.update(educational_quality_questionwise)
        combined_questionwise.update(engagement_with_management_questionwise)

        return combined_questionwise
    

    @staticmethod
    def categories_google_excel_sheet(file1_records):
        def extract_category(column):
                    match = re.match(r"\[(.*?)\]\s*(.*)", column)
                    if match:
                        return match.group(1), match.group(2)
                    return None, column
        category_data = {}
        columns = list(file1_records[0].keys()) if isinstance(file1_records, list) and file1_records and isinstance(file1_records[0], dict) else []
        for col in columns:
            if "Average" in col:
                continue
            category, question = extract_category(col)
            if category:
                if category not in category_data:
                    category_data[category] = []
                values_by_rate_group = {}
                for row in file1_records:
                    rate_group = row.get("Rate Group") or row.get("Rater Group") or "Unknown"
                    values_by_rate_group.setdefault(rate_group, []).append(row.get(col))

                category_data[category].append({
                    question: values_by_rate_group
                })
        
        return category_data
            


    @staticmethod
    def find_comparision_year_data(record1, record2):
        record1 = record1 or {}
        record2 = record2 or {}

        def normalize_question_key(text):
            return re.sub(r"\s+", " ", str(text)).strip()

        alias_map = {
            "Helps to resolve issues/remove roadblocks in the job": "Helps in resolving issues/remove roadblocks in the job",
            "Helps in resolving issues/remove roadblocks in the job": "Helps in resolving issues/remove roadblocks in the job",
            "Works with teachers to set high academic standards": "Works with teachers to set high academic standards",
            "Works with teachers to set high academic standards that rise above minimum expectations": "Works with teachers to set high academic standards",
            "Has created a work culture that recognizes and rewards merit": "Has created a work culture that rewards merit",
            "Has created a work culture that rewards merit": "Has created a work culture that rewards merit",
            "Facilitates opportunities for teachers to transfer and mentor other teachers on best practices": "Facilitates opportunities for teachers to share best practices/ mentor other teachers",
            "Facilitates opportunities for teachers to share best practices/ mentor other teachers": "Facilitates opportunities for teachers to share best practices/ mentor other teachers",
            "Provides clear, timely feedback on performance, including successes and areas of improvement": "Provides clear, timely feedback on performance, including successes and areas of improvement",
            "Gives clear feedback about performance or when anything goes right or wrong": "Provides clear, timely feedback on performance, including successes and areas of improvement",
        }
        alias_map = {normalize_question_key(k): v for k, v in alias_map.items()}

        def remap_record(record):
            new_record = {}
            for q, val in record.items():
                canon_q = alias_map.get(normalize_question_key(q), q)
                if canon_q not in new_record:
                    new_record[canon_q] = {}
                for k, v in (val or {}).items():
                    new_record[canon_q][k] = v
            return new_record

        record1 = remap_record(record1)
        record2 = remap_record(record2)

        all_questions = set(record1.keys()) | set(record2.keys())
        diff_data = {}
        manager_diff_data={}

        team_score_key = "Subordinates"
        manager_score_key="Manager"
        threshold = 0.1

        for question in all_questions:
            groups1 = record1.get(question) or {}
            groups2 = record2.get(question) or {}

            v1 = groups1.get(team_score_key)
            v2 = groups2.get(team_score_key)

            m1=groups1.get(manager_score_key)
            m2=groups2.get(manager_score_key)
            

            if v1 is None or v2 is None:
                continue
            if m1 is None or m2 is None:
                continue



            team_diff = round(v1 - v2, 2)
            manager_diff=round(m1 - m2,2)
            if abs(team_diff) <= threshold:
                continue
            if abs(manager_diff) <= threshold:
                continue

            diff_data[question] = {"team_diff1": team_diff}
            manager_diff_data[question]={"manager_diff1": manager_diff}

        sorted_diff_data = dict(
            sorted(diff_data.items(), key=lambda item: item[1].get('team_diff1', 0), reverse=True) 

        )

        sorted_manager_diff_data=dict(
                        sorted(manager_diff_data.items(), key=lambda item: item[1].get('manager_diff1', 0), reverse=True)
        )
        
        return sorted_diff_data,sorted_manager_diff_data
    

    @staticmethod
    def find_comparision_multi_year_data(record1, record2,record3):
        record1 = record1 or {}
        record2 = record2 or {}
        record3 = record3 or {}

        def normalize_question_key(text):
            return re.sub(r"\s+", " ", str(text)).strip()

        alias_map = {
            "Helps to resolve issues/remove roadblocks in the job": "Helps in resolving issues/remove roadblocks in the job",
            "Helps in resolving issues/remove roadblocks in the job": "Helps in resolving issues/remove roadblocks in the job",
            "Works with teachers to set high academic standards": "Works with teachers to set high academic standards",
            "Works with teachers to set high academic standards that rise above minimum expectations": "Works with teachers to set high academic standards",
            "Has created a work culture that recognizes and rewards merit": "Has created a work culture that rewards merit",
            "Has created a work culture that rewards merit": "Has created a work culture that rewards merit",
            "Facilitates opportunities for teachers to transfer and mentor other teachers on best practices": "Facilitates opportunities for teachers to share best practices/ mentor other teachers",
            "Facilitates opportunities for teachers to share best practices/ mentor other teachers": "Facilitates opportunities for teachers to share best practices/ mentor other teachers",
            "Provides clear, timely feedback on performance, including successes and areas of improvement": "Provides clear, timely feedback on performance, including successes and areas of improvement",
            "Gives clear feedback about performance or when anything goes right or wrong": "Provides clear, timely feedback on performance, including successes and areas of improvement",
        }
        alias_map = {normalize_question_key(k): v for k, v in alias_map.items()}

        def remap_record(record):
            new_record = {}
            for q, val in record.items():
                canon_q = alias_map.get(normalize_question_key(q), q)
                if canon_q not in new_record:
                    new_record[canon_q] = {}
                for k, v in (val or {}).items():
                    new_record[canon_q][k] = v
            return new_record

        record1 = remap_record(record1)
        record2 = remap_record(record2)
        record3 = remap_record(record3)

        all_questions = set(record1.keys()) | set(record2.keys()) | set(record3.keys())
        diff_data = {}
        manager_diff_data={}

        team_score_key = "Subordinates"
        manager_score_key="Manager"
        threshold = 0.1

        for question in all_questions:
            groups1 = record1.get(question) or {}
            groups2 = record2.get(question) or {}
            groups3 = record3.get(question) or {}

            v1 = groups1.get(team_score_key)
            v2 = groups2.get(team_score_key)
            v3 = groups3.get(team_score_key)

            m1=groups1.get(manager_score_key)
            m2=groups2.get(manager_score_key)
            m3=groups3.get(manager_score_key)

            if v1 is None or v2 is None or v3 is None:
                continue
            if m1 is None or m2 is None or m3 is None:
                continue

            team_diff1 = round(v1 - v2, 2)
            team_diff2 = round(v2 - v3, 2)
            manager_diff_1=round(m1 - m2,2)
            manager_diff_2=round(m2 - m3,2)

            if abs(team_diff1) <= threshold or abs(team_diff2) <= threshold:
                continue
            if abs(manager_diff_1) <= threshold or abs(manager_diff_2) <= threshold:
                continue
            
            diff_data[question] = {
                "team_diff1": team_diff1,
                "team_diff2": team_diff2,
            }
            manager_diff_data[question]={
                "manager_diff_1": manager_diff_1,
                "manager_diff_2": manager_diff_2
            }

        sorted_diff_data = dict(
                sorted(
                    diff_data.items(),
                    key=lambda item: item[1].get("team_diff1", 0),
                    reverse=True
                )
            )
        sorted_manager_diff_data = dict(
                sorted(
                    manager_diff_data.items(),
                    key=lambda item: item[1].get("manager_diff_1", 0),
                    reverse=True
                )
            )
        return sorted_diff_data, sorted_manager_diff_data
    
    
    @staticmethod
    def questionwise_find_total_response(records):
        if not records:
            return {
                "total_response": 0,
                "response_by_group": {
                    "Self": 0,
                    "Manager": 0,
                    "Subordinates": 0
                }
            }

        question_grouped = defaultdict(list)
        for row in records:
            if not isinstance(row, dict):
                continue
            question = row.get("Question")
            if not question:
                continue
            question_grouped[question].append(row)

        if not question_grouped:
            return {
                "total_response": 0,
                "response_by_group": {
                    "Self": 0,
                    "Manager": 0,
                    "Subordinates": 0
                }
            }

        first_question = next(iter(question_grouped))
        question_records = question_grouped[first_question]

        counts = {
            "Self": 0,
            "Manager": 0,
            "Subordinates": 0
        }

        for row in question_records:
            rg = row.get("Rater Group") or row.get("Rate Group")
            if not rg:
                continue
            rg_norm = str(rg).strip().lower()
            if rg_norm == "self":
                counts["Self"] += 1
            elif "manager" in rg_norm:
                counts["Manager"] += 1
            elif rg_norm == "subordinates" or rg_norm == "others":
                counts["Subordinates"] += 1
        total=counts["Manager"]+counts["Subordinates"]+counts["Self"]
        return {
            "total": total,
            **counts
        }
          
        
        
            
            
    @staticmethod
    def questionwise_avg_by_rate_group(records):
        question_grouped = defaultdict(list)
        for row in records:
            question = row.get("Question")
            if not question:
                continue
            question_grouped[question].append(row)

        final_output = {}
        for question, rows in question_grouped.items():
            grouped = defaultdict(list)
            rater_groups_set = set()
            for item in rows:
                group = item.get("Rater Group")
                value = item.get("Rating")

                if group is None:
                    continue

                group_norm = str(group).strip().lower()
                if group_norm == "self":
                    group = "Self"
                elif "manager" in group_norm:
                    group = "Manager"
                elif group_norm == "subordinates":
                    group = "Subordinates"
                elif group_norm == "others":
                    group = "Others"
                else:
                    group = str(group).strip()

                rater_groups_set.add(group)
                if value is None:
                    continue
                
                grouped[group].append(value)

            avg_result = {}

            def filter_numeric(values):
                numeric_values = []
                for v in values:
                    if isinstance(v, (int, float)):
                        numeric_values.append(v)
                    elif isinstance(v, str):
                        try:
                            numeric_values.append(float(v))
                        except (ValueError, TypeError):
                            continue
                return numeric_values

            sub_vals = filter_numeric(grouped.get("Subordinates", []))
            oth_vals = filter_numeric(grouped.get("Others", []))

            combined_people = sub_vals + oth_vals
            if combined_people:
                avg_result["Subordinates"] = round(
                    sum(combined_people) / len(combined_people), 2
                )
                rater_groups_set.discard("Subordinates")
                rater_groups_set.discard("Others")
            elif "Subordinates" in rater_groups_set or "Others" in rater_groups_set:
                avg_result["Subordinates"] = None
                rater_groups_set.discard("Subordinates")
                rater_groups_set.discard("Others")

            mgr_vals = filter_numeric(grouped.get("Manager", []))
            if mgr_vals:
                avg_result["Manager"] = round(
                    sum(mgr_vals) / len(mgr_vals), 2
                )
                rater_groups_set.discard("Manager")
            elif "Manager" in rater_groups_set:
                avg_result["Manager"] = None
                rater_groups_set.discard("Manager")

            for group, values in grouped.items():
                if group in ["Subordinates", "Others", "Manager"]:
                    continue
                
                numeric_vals = filter_numeric(values)
                if numeric_vals:
                    avg_result[group] = round(sum(numeric_vals) / len(numeric_vals), 2)

            for group in rater_groups_set:
                if group not in avg_result:
                    avg_result[group] = None

            final_output[question] = avg_result
        final_output = dict(
            sorted(
                final_output.items(),
                key=lambda x: (x[1].get("Subordinates") is None, x[1].get("Subordinates") or 0),
                reverse=True
            )
        )
        return final_output


    @staticmethod
    def questionwise_avg_from_rating_lists(questionwise_rating_lists, merge_others_into_subordinates=True, ndigits=2):
        if not questionwise_rating_lists:
            return {}

        if isinstance(questionwise_rating_lists, list):
            merged = {}
            for item in questionwise_rating_lists:
                if isinstance(item, dict):
                    merged.update(item)
            questionwise_rating_lists = merged

        def avg(values):
            cleaned = []
            for v in values or []:
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    cleaned.append(float(v))
                    continue
                try:
                    cleaned.append(float(v))
                except (TypeError, ValueError):
                    continue
            if not cleaned:
                return None
            return round(sum(cleaned) / len(cleaned), ndigits)

        out = {}
        for question, groups in (questionwise_rating_lists or {}).items():
            if not isinstance(groups, dict):
                continue

            normalized_groups = {}
            for group_key, group_values in groups.items():
                group_norm = str(group_key).strip().lower()
                if group_norm == "self":
                    norm_key = "Self"
                elif "manager" in group_norm:
                    norm_key = "Manager"
                elif group_norm == "subordinates":
                    norm_key = "Subordinates"
                elif group_norm == "others":
                    norm_key = "Others"
                else:
                    continue

                if isinstance(group_values, list):
                    values_list = group_values
                elif group_values is None:
                    values_list = []
                else:
                    values_list = [group_values]

                normalized_groups.setdefault(norm_key, []).extend(values_list)

            result = {}
            sub_vals = list(normalized_groups.get("Subordinates") or [])
            oth_vals = list(normalized_groups.get("Others") or [])
            if merge_others_into_subordinates and (sub_vals or oth_vals):
                sub_avg = avg(sub_vals + oth_vals)
                if sub_avg is not None:
                    result["Subordinates"] = sub_avg
            # else:
            #     sub_avg = avg(sub_vals)
            #     if sub_avg is not None:
            #         result["Subordinates"] = sub_avg
            #     oth_avg = avg(oth_vals)
            #     if oth_avg is not None:
            #         result["Others"] = oth_avg

            self_avg = avg(normalized_groups.get("Self"))
            if self_avg is not None:
                result["Self"] = self_avg

            mgr_avg = avg(normalized_groups.get("Manager"))
            if mgr_avg is not None:
                result["Manager"] = mgr_avg

            if result:
                out[question] = result

        out = dict(
            sorted(
                out.items(),
                key=lambda x: (x[1].get("Subordinates") is None, x[1].get("Subordinates", 0)),
                reverse=True
            )
        )
        return out


    @staticmethod
    def overall_avg_by_group(questionwise_data):
        grouped = defaultdict(list)

        for question, groups in questionwise_data.items():
            for group, value in groups.items():
                if value is None:
                    continue
                grouped[group].append(value)

        final_avg = {}
        for group, values in grouped.items():
            final_avg[group] = round(sum(values) / len(values), 2)
        
        return final_avg


    @staticmethod
    def find_strengths_separately(questionwise_data):
        sub_strengths = []
        mgr_strengths = []

        for question, groups in questionwise_data.items():
            sub_val = groups.get("Subordinates")
            mgr_val = groups.get("Manager")

            if sub_val is not None and sub_val > 4.5:
                sub_strengths.append({
                    "question": question,
                    "score": sub_val
                })

            if mgr_val is not None and mgr_val > 4:
                mgr_strengths.append({
                    "question": question,
                    "score": mgr_val
                })

        sub_strengths.sort(key=lambda x: x["score"], reverse=True)
        mgr_strengths.sort(key=lambda x: x["score"], reverse=True)

        return {
            "Subordinates": sub_strengths,
            "Manager": mgr_strengths
        }

    @staticmethod
    def find_area_of_improvement_separately(questionwise_data):
        sub_strengths = []
        mgr_strengths = []

        for question, groups in questionwise_data.items():
            sub_val = groups.get("Subordinates")
            mgr_val = groups.get("Manager")

            if sub_val is not None and sub_val < 4.5:
                sub_strengths.append({
                    "question": question,
                    "score": sub_val
                })

            if mgr_val is not None and mgr_val < 4:
                mgr_strengths.append({
                    "question": question,
                    "score": mgr_val
                })

        sub_strengths.sort(key=lambda x: x["score"])
        mgr_strengths.sort(key=lambda x: x["score"])

        return {
            "Subordinates": sub_strengths,
            "Manager": mgr_strengths
        }


    @staticmethod
    def detect_option(comment_clean, option_map, threshold=0.3):
        """
        Detect option using cosine similarity
        """
        texts = list(option_map.values())
        letters = list(option_map.keys())

        corpus = [comment_clean] + texts

        vectorizer = TfidfVectorizer().fit_transform(corpus)
        vectors = vectorizer.toarray()

        comment_vector = vectors[0]
        option_vectors = vectors[1:]

        similarities = cosine_similarity([comment_vector], option_vectors)[0]

        best_index = similarities.argmax()
        best_score = similarities[best_index]

        if best_score >= threshold:
            return letters[best_index]

        return None


    @staticmethod
    def count_abc_responses(data):
        if not data:
            return {}

        question, records = next(iter(data.items()))

        question_clean = question.replace("_x000D_", "").strip()
        question_clean = re.sub(r"\s+", " ", question_clean)
        has_abc = re.search(
            r'[Aa]\s*/\s*[Bb]\s*/\s*[Cc]|\(?[Aa]\s*/\s*[Bb]\s*/\s*[Cc]\)?|(?=.*[Aa]\))(?=.*[Bb]\))(?=.*[Cc]\))',
            question_clean,
            re.DOTALL
        )
        if not has_abc:
            return {}

        option_map = {}
        question_clean = re.sub(r"\([^)]*\)", "", question_clean)
        option_parts = re.findall(
            r"\b([AaBbCc])\b\s*[\)\]\.:\-]\s*(.+?)(?=\s*\b[AaBbCc]\b\s*[\)\]\.:\-]|$)",
            question_clean
        )
        if option_parts:
            for letter, text in option_parts:
                option_map[letter.upper()] = text.strip().lower()
        else:
            option_map = {"A": "a", "B": "b", "C": "c"}

        option_counts = defaultdict(int)
        
        for item in records:        
            comment = None
            if isinstance(item, dict):
                comment = item.get("Comment")
            else:
                comment = str(item)
            if not comment:
                # print("Empty comment found, skipping...",item)
                continue

            comment_clean = comment.strip().lower()
            detected_option = None
            letter_match = re.search(
                r"\b(" + "|".join(option_map.keys()) + r")\b",
                comment_clean,
                re.IGNORECASE
            )

            if letter_match:
                detected_option = letter_match.group(1).upper()

            if not detected_option:
                for letter, option_text in option_map.items():
                    if option_text in comment_clean:
                        detected_option = letter
                        break

            if not detected_option:
                detected_option = CommonFunctions.detect_option(
                    comment_clean,
                    option_map,
                    threshold=0.3
                )

            if detected_option:
                option_counts[detected_option] += 1

        for opt in option_map.keys():
            option_counts.setdefault(opt, 0)
        

        per_option = {}
        for letter, text in option_map.items():
            per_option[letter] = {
                "text": text.capitalize(),
                "count": option_counts.get(letter, 0),
                "percentage": round((option_counts.get(letter, 0) / len(records)) * 100, 2) if len(records) > 0 else 0
            }

        return per_option


    @staticmethod
    # def get_workplace_culture_data(data,question_type):
    #     for question, records in data.items():
    #         if  question_type in question.lower():
    #             return records
    #     return []

    def get_workplace_culture_data(data, question_type):
            keyword_map = {
                "continue_doing": [
                    "continue doing",
                    "keep doing",
                    "do more often",
                    "continue",
                    "keep doing more"
                ],
                "stop_doing": [
                    "stop altogether",
                    "stop doing",
                    "stop",
                    "avoid doing"
                ],
                "workplace_culture": [
                    "workplace culture"
                ],
                "stand_out_leader": [
                    "stand out as a leader",
                    "stand out leader",
                    "leader stand out"
                ],
                "action_area":[
                    "differently, adjust or change"
                ]
            }
            keywords = keyword_map.get(question_type, [question_type])
            for question, records in data.items():
                q = question.lower()
                for keyword in keywords:
                    if keyword in q:
                        return records

            return []

    @staticmethod
    def count_workplace_culture_words(records):
        word_counts = defaultdict(int)

        for item in records:
            comment = None
            if isinstance(item, dict):
                comment = item.get("Comment")
            else:
                comment = item
            
            if comment is not None and not isinstance(comment, str):
                comment = str(comment)

            if not comment or comment == "nil":
                continue

            words = comment.split(",")

            for word in words:
            
                    clean_word = word.strip().lower()

                    clean_word = re.sub(r"[^\w\s-]", "", clean_word)

                    if clean_word and clean_word !='nil' :
                        word_counts[clean_word] += 1
        sorted_items = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:30]
        top_words = [word for word, _ in sorted_items]
        return top_words

    @staticmethod
    def get_non_self_comments(records):
        comments = []

        for item in records:
            comment = None
            rate_group = None
            if isinstance(item, dict):
                comment = item.get("Comment")
                # Check both Rater Group and Rate Group
                rate_group = item.get("Rater Group") or item.get("Rate Group")
            else:
                comment = item
            
            if comment is not None and not isinstance(comment, str):
                comment = str(comment)

            # Case-insensitive check for Self
            if rate_group and str(rate_group).strip().lower() == "self":
                continue

            if comment:
                c_clean = comment.strip()
                if c_clean and c_clean.lower() not in {"nil", "n/a", "na", "-", "none", "no comment", "no comments"}:
                    comments.append(c_clean)

        return comments 

    @staticmethod
    def dedupe_exact_comments(comments):
        if not comments:
            return []

        def norm_key(s):
            s_norm = str(s).strip().lower()
            s_norm = re.sub(r"[^\w\s]", "", s_norm)
            s_norm = re.sub(r"\s+", " ", s_norm).strip()
            return s_norm

        def cleanliness_score(s):
            s_str = str(s)
            punct = len(re.findall(r"[^\w\s]", s_str))
            spaces = len(re.findall(r"\s{2,}", s_str))
            return (punct, spaces, len(s_str))

        seen = {}
        out = []
        for c in comments:
            key = norm_key(c)
            if key in seen:
                idx = seen[key]
                if cleanliness_score(c) < cleanliness_score(out[idx]):
                    out[idx] = c
                continue
            seen[key] = len(out)
            out.append(c)

        return out

    @staticmethod
    def lbscore_broken_down_by_behavioural_indications(category_data):
        def extract_score(value):
            if not value:
                return None

            value = str(value).strip()

            if value.upper() == "NA":
                return None

            parts = value.split("–")
            try:
                return int(parts[0].strip())
            except:
                return None
           
        def get_highlight(self_score, other_score):
            if self_score == "NA" or other_score == "NA":
                return ""
            if self_score >= 3.5 and other_score >= 3.5:
                return "Strength"
            elif self_score <= 3.0 and other_score <= 3.5:
                return "Area of Improvement"
            elif (self_score <= 3.0 and other_score > 3.5 and (other_score - self_score) >= 0.5):
                return "Hidden Strength"
            elif (self_score >= 3.5 and other_score <= 3.0 and (self_score - other_score) >= 0.5):
                return "Blind Spot"
            elif self_score > 3 and 3 < other_score < 3.5:
                return "Proficient"
            return ""           

        result = {}
        if not isinstance(category_data,dict):
            return {}
        for category,category_items in category_data.items():
            if "Feedback" in category:
                continue

            for category_item in category_items:
                if not isinstance(category_item,dict):
                    continue
                if category not in result:
                    result[category] = {}
                for question,values in category_item.items():
                    score = {}
                    gap ={}
                    for rater_type,values in values.items():
                        num = [extract_score(v) for v in values if extract_score(v) is not None]

                        if not num:
                            score[rater_type] = "NA"
                        else:
                            score[rater_type] = round(sum(num) / len(num),2)

                    self_score = score.get("Self", "NA")

                    others_values = []
                    for rater_type in ["Manager", "Peer", "Subordinate"]:
                        val = score.get(rater_type)
                        if val is not None and val != "NA":
                            others_values.append(val)
                    others_avg = round(sum(others_values) / len(others_values), 2) if others_values else "NA"

                    highlights = {}

                    highlights["self"] = get_highlight(self_score, others_avg)

                    manager_score = score.get("Manager", "NA")
                    highlights["manager"] = get_highlight(self_score, manager_score)

                    peer_score = score.get("Peer", "NA")
                    highlights["peer"] = get_highlight(self_score, peer_score)

                    subordinate_score = score.get("Subordinate", "NA")
                    highlights["subordinate"] = get_highlight(self_score, subordinate_score)

                    gap["self_gap"] = 0

                    gap["manager_gap"] = (
                        round((self_score - manager_score)* -1,2)
                        if self_score != "NA" and manager_score != "NA"
                        else "NA"
                    )

                    gap["peer_avg"] = (
                        round((self_score - peer_score)* -1,2)
                        if self_score != "NA" and peer_score != "NA"
                        else "NA"
                    )

                    gap["subordinate_avg"] = (
                        round((self_score - subordinate_score)*-1,2)
                        if self_score != "NA" and subordinate_score != "NA"
                        else "NA"
                    )

                    clean_question = re.sub(r"^\d+\.\s*", "", question).strip()

                    if clean_question not in result[category]:
                        result[category][clean_question] = []

                    result[category][clean_question].append({
                        "score": score,
                        "gap": gap,
                        "highlights": highlights
                    })

        return result
    
    @staticmethod
    def lbscore_overall_summary_of_scores(category_data,is_avg_of_avg=False):
        if not isinstance(category_data,dict):
            return {}
        category_wise_overall_scores = {}
        feedbacks = {}

        for category,category_items in category_data.items():
            if "Feedback" in category:
                feedbacks[category] = category_items
            else:
                def extract_score(value):
                    if not value:
                        return None

                    value = str(value)

                    parts = value.split("–")
                    try:
                        return int(parts[0].strip())
                    except:
                        return None
                manager_sum = self_sum = peer_sum = subordinate_sum = 0
                manager_count = self_count = peer_count = subordinate_count = 0
                total_sum = 0
                total_count = 0
                for category_item in category_items:
                    score = {}
                    for question,values in category_item.items():
                        for rater_type,r_values in values.items():
                            num = [extract_score(v) for v in r_values if extract_score(v) is not None ]
                            avg = sum(num)/len(num) if num else 0
            
                            if rater_type != "Self":
                                total_sum += sum(num)
                                total_count += len(num)

                            if rater_type == "Manager":
                                manager_sum += avg
                                manager_count += 1

                            elif rater_type == "Self":
                                self_sum += avg
                                self_count += 1

                            elif rater_type == "Peer":
                                peer_sum += avg
                                peer_count += 1              

                            elif rater_type == "Subordinate":
                                subordinate_sum += avg
                                subordinate_count += 1

                final_manager_avg = round(manager_sum / manager_count, 2) if manager_count else 0   
                final_self_avg = round(self_sum / self_count, 2) if self_count else 0
                final_peer_avg = round(peer_sum / peer_count, 2) if peer_count else 0
                final_subordinate_avg = round(subordinate_sum / subordinate_count, 2) if subordinate_count else 0
                final_total_avg_except_self=final_manager_avg+final_peer_avg+final_subordinate_avg
                if is_avg_of_avg :
                    final_others_avg = round((final_total_avg_except_self/3),2)
                else:
                    final_others_avg = round((total_sum/total_count),2) 
                spider_chart_others_avg=round((final_peer_avg+final_subordinate_avg)/2,1)
                category_wise_overall_scores[category] = {
                    "manager_avg": final_manager_avg,
                    "self_avg":final_self_avg,
                    "peer_avg": final_peer_avg,
                    "subordinate_avg":final_subordinate_avg ,
                    "others_avg":final_others_avg,
                    "spider_chart_others_avg":spider_chart_others_avg
                }

        return category_wise_overall_scores,feedbacks   

    @staticmethod
    def get_highlights(category_data,is_avg_of_avg=False):
        hidden_strength_results = []
        blind_spot_results = []
        area_improvement_candidates = []
        strengths = []
        if not category_data:
            return [],[],[],[]

        def strip_serial(q):
            return re.sub(r"^\d+\.\s*", "", q).strip()

        # def iter_questions(data):
        #     for key, val in data.items():
        #         if isinstance(val, dict) and val and isinstance(next(iter(val.values())), list):
        #             for q, items in val.items():
        #                 yield q, items
        #         else:
        #             yield key, val


        for competency, competency_data in category_data.items():
            if not competency_data:
                continue
            if "Feedback" in competency:
                continue
            for question_data in competency_data:
                if not isinstance(question_data, dict):
                    continue
                question, value = next(iter(question_data.items()))
                if not isinstance(value, dict):
                    continue
                clean_question = strip_serial(question)
                manager_scores = value.get("Manager") or []
                self_scores = value.get("Self") or []
                peer_scores = value.get("Peer") or []
                subordinate_scores = value.get("Subordinate") or []

                manager_avg = sum(manager_scores)/len(manager_scores) if manager_scores else 0
                self_avg = sum(self_scores)/len(self_scores) if self_scores else 0
                peer_avg = sum(peer_scores)/len(peer_scores) if peer_scores else 0
                subordinate_avg = sum(subordinate_scores)/len(subordinate_scores) if subordinate_scores else 0

                if is_avg_of_avg:
                    others = (manager_avg + peer_avg + subordinate_avg) / 3
                else:
                    all_others = manager_scores + peer_scores + subordinate_scores
                    others = sum(all_others) / len(all_others) if all_others else 0
                gap_hidden_strength = others - self_avg
                gap_blind_spot = self_avg - others

                if gap_blind_spot >= 0.5 and self_avg >= 3.5:
                    blind_spot_results.append({
                        "question": clean_question,
                        "self": self_avg,
                        "others_avg": round(others, 2),
                        "gap": round(gap_blind_spot, 2)
                    })

                if gap_hidden_strength >= 0.5 and self_avg <= 3:
                    hidden_strength_results.append({
                        "question": clean_question,
                        "self": self_avg,
                        "others": round(others, 2),
                        "gap": round(gap_hidden_strength, 2)
                    })

                area_improvement_candidates.append({
                    "question": clean_question,
                    "others": round(others, 2),
                })

                strengths.append({
                    "question": clean_question,
                    "others": round(others, 2),
                })
                area_improvement_candidates = sorted(area_improvement_candidates, key=lambda x: x["others"])[:5]
                strengths = sorted(strengths, key=lambda x: x["others"], reverse=True)[:5]

        final_result_strengths = sorted(hidden_strength_results, key=lambda x: x["gap"], reverse=True)[:5]
        final_result_blind_spots = sorted(blind_spot_results, key=lambda x: x["gap"], reverse=True)[:5]

        return final_result_strengths, final_result_blind_spots, area_improvement_candidates, strengths

                    
    @staticmethod
    def get_competency_summary(employee_wise_category_data,is_avg_of_avg=False):

        ROLE_WEIGHTS = {
            "Delivery": {
                "Leadership": 50,
                "Bandwidth": 100,
                "Sales and Customer Centricity": 100,
                "Collaboration": 50,
                "Operational Excellence": 100,
                "Result Orientation": 50,
                "Expertise and Communication": 50
            },

            "Business": {
                "Leadership": 50,
                "Bandwidth": 50,
                "Sales and Customer Centricity": 100,
                "Collaboration": 50,
                "Operational Excellence": 50,
                "Result Orientation": 100,
                "Expertise and Communication": 100
            },

            "CORP": {
                "Leadership": 50,
                "Bandwidth": 50,
                "Sales and Customer Centricity": 50,
                "Collaboration": 100,
                "Operational Excellence": 50,
                "Result Orientation": 100,
                "Expertise and Communication": 100
            },

            "CEO": {
                "Leadership": 100,
                "Bandwidth": 50,
                "Sales and Customer Centricity": 100,
                "Collaboration": 50,
                "Operational Excellence": 50,
                "Result Orientation": 100,
                "Expertise and Communication": 50
            }
        }

        employee_results = {}

        all_scores = []

        stream_scores = {}

        for employee_name, employee_data in employee_wise_category_data.items():

            total_score = 0.0

            competency_summary = {}

            role = (employee_data[0].get("Function")or "Business")

            weights = ROLE_WEIGHTS.get(role,ROLE_WEIGHTS["Business"])

            competencies = set()

            for response in employee_data:

                for key in response.keys():

                    if key not in [
                        "Function",
                        "Rater type"
                    ] and "Feedback" not in key:

                        competencies.add(key)

            for competency in competencies:

                manager_scores = []
                peer_scores = []
                subordinate_scores = []
                self_scores = []
                total_scores = 0
                total_count = 0

                for response in employee_data:

                    rater_type = response.get(
                        "Rater type"
                    )

                    scores = response.get(
                        competency,
                        []
                    )

                    if rater_type!="Self":
                        total_scores += sum(scores)
                        total_count += len(scores)

                    if rater_type == "Manager":
                        manager_scores.extend(scores)

                    elif rater_type == "Peer":
                        peer_scores.extend(scores)

                    elif rater_type == "Subordinate":
                        subordinate_scores.extend(scores)

                    elif rater_type == "Self":
                        self_scores.extend(scores)

                manager_avg = round(
                    np.mean(manager_scores),
                    2
                ) if manager_scores else 0

                peer_avg = round(
                    np.mean(peer_scores),
                    2
                ) if peer_scores else 0

                subordinate_avg = round(
                    np.mean(subordinate_scores),
                    2
                ) if subordinate_scores else 0

                self_avg = round(
                    np.mean(self_scores),
                    2
                ) if self_scores else 0


                if is_avg_of_avg:
                    others_avg = (
                            manager_avg +
                            peer_avg +
                            subordinate_avg
                        ) / 3
                    
                else:

                    others_avg = (total_scores/total_count) if total_scores else 0 

                weight = weights.get(
                        competency,
                        0
                )


                weighted_score = (others_avg / 5) * weight
                

                total_score += weighted_score

                competency_summary[
                    competency
                ] = {
                    "manager_avg": manager_avg,
                    "peer_avg": peer_avg,
                    "subordinate_avg": subordinate_avg,
                    "self_avg": self_avg,
                    "others_avg": others_avg,
                    "weight": weight,
                    "weighted_score": weighted_score
                }

     

            overall_score = round(
                total_score,
                2
            )

            all_scores.append(overall_score)


            if role not in stream_scores:
                stream_scores[role] = []

            stream_scores[role].append(
                overall_score
            )


            employee_results[employee_name] = {
                "role": role,
                "overall_score": overall_score,
                "competency_summary": competency_summary
            }

        cohort_q1 = round(
            np.percentile(all_scores, 25),
            2
        )

        cohort_median = round(
            np.percentile(all_scores, 50),
            2
        )

        cohort_q3 = round(
            np.percentile(all_scores, 75),
            2
        )

        final_output = {}

        for employee_name, result in employee_results.items():

            overall_score = result[
                "overall_score"
            ]

            role = result["role"]

            if overall_score <= cohort_q1:
                cohort_position = "1st Quartile"

            elif overall_score <= cohort_median:
                cohort_position = "2nd Quartile"

            elif overall_score <= cohort_q3:
                cohort_position = "3rd Quartile"

            else:
                cohort_position = "4th Quartile"

            role_scores = stream_scores[role]

            stream_q1 = round(
                np.percentile(role_scores, 25),
                2
            )

            stream_median = round(
                np.percentile(role_scores, 50),
                2
            )

            stream_q3 = round(
                np.percentile(role_scores, 75),
                2
            )

            if overall_score <= stream_q1:
                stream_position = "1st Quartile"

            elif overall_score <= stream_median:
                stream_position = "2nd Quartile"

            elif overall_score <= stream_q3:
                stream_position = "3rd Quartile"

            else:
                stream_position = "4th Quartile"

            final_output[employee_name] = {

                "role": role,

                "overall_score": overall_score,

                "competency_summary": result["competency_summary"],

                "quartile_by_cohort": {

                    "position": cohort_position,

                    "quartiles": {

                        "minimum_score": min(all_scores),

                        "first_quartile": cohort_q1,

                        "median": cohort_median,

                        "third_quartile": cohort_q3,

                        "maximum_score": max(all_scores)
                    }
                },


                "quartile_by_stream": {

                    "position": stream_position,

                    "quartiles": {

                        "minimum_score": min(role_scores),

                        "first_quartile": stream_q1,

                        "median": stream_median,

                        "third_quartile": stream_q3,

                        "maximum_score": max(role_scores)
                    }
                }
            }

        return final_output

    
    @staticmethod
    def get_headlines(overall_questionwise_data):
        highest_team_avg=sorted(
            [
                item for item in overall_questionwise_data.items()
                if item[1].get("Subordinates") is not None
            ],
            key=lambda x: x[1].get("Subordinates") or 0,
            reverse=True)[:3]

        lowest_team_avg = sorted(
            [
                item for item in overall_questionwise_data.items()
                if item[1].get("Subordinates") is not None
            ],
            key=lambda x: x[1].get("Subordinates") or 0,
            reverse=False)[:3]

        highest_manager_avg = sorted(
            [
                item for item in overall_questionwise_data.items()
                if item[1].get("Manager") is not None
            ],
            key=lambda x: x[1].get("Manager") or 0,
            reverse=True)[:3]
        
        lowest_manager_avg = sorted(
            [
                item for item in overall_questionwise_data.items()
                if item[1].get("Manager") is not None
            ],
            key=lambda x: x[1].get("Manager") or 0,
            reverse=False)[:3]

        return highest_team_avg, lowest_team_avg, highest_manager_avg, lowest_manager_avg

    @staticmethod
    def get_overall_averages_by_principal(all_records):
        employee_summary = defaultdict(
            lambda: {
                "team_total": 0,
                "team_count": 0,
                "manager_total": 0,
                "manager_count": 0
            }
        )
        for row in all_records:
           employee = row.get("Employee Name")   
           if not employee:
             continue
           rater_type = row.get("Rate Group","") or row.get("Rater Group","") or row.get("Rater type","") 
           rater_type = rater_type.strip().lower()
           rating = row.get("Rating")
           if not isinstance(rating, (int,float)):
            continue
           if rater_type in ["subordinates","others"]:
             employee_summary[employee]["team_total"] += rating
             employee_summary[employee]["team_count"] += 1
       
           elif "manager" in rater_type:
             employee_summary[employee]["manager_total"] += rating
             employee_summary[employee]["manager_count"] += 1
       
        team_summary=[]
        manager_summary=[]
        for employee, data in employee_summary.items():
            if data["team_count"] > 0:
                avg = round(data["team_total"] / data["team_count"], 2)
                team_summary.append({"employee": employee, "average": avg,  "responses":
                data["team_count"]})
            if data["manager_count"] > 0:
                avg = round(data["manager_total"] / data["manager_count"], 2)
                manager_summary.append({"employee": employee, "average": avg, "responses":
                data["manager_count"]})


        team_summary = sorted(team_summary, key=lambda x: x["average"],reverse=True)
        manager_summary = sorted(manager_summary, key=lambda x: x["average"],reverse=True)

        overall_principal_averages = {
            "team_summary": team_summary,
            "manager_summary": manager_summary
        }

        return overall_principal_averages

    @staticmethod
    def get_summary_framework_recap(all_records):
        principal_names = set()

        survey_questions = set()

        competencies = set()

        available_groups = set()

        for row in all_records:

            employee = row.get("Employee Name")

            if employee:
                principal_names.add(employee)

            question = row.get("Question")

            if question:
                survey_questions.add(question)

            competency = row.get("Name")

            if competency and competency != "General":

                competencies.add(competency)

            group = (
                row.get("Rater Group")
                or row.get("Rate Group")
            )

            if group:
                available_groups.add(group)

        principal_count = len(principal_names)

        survey_question_count = len(survey_questions)

        competency_count = len(competencies)

        qualitative_question_count = 5

        total_questions = (
            survey_question_count
            + qualitative_question_count
        )

        survey_framework_recap = {

            "principal_count":principal_count,

            "responses_given_by":list(available_groups),

            "survey_question_count":survey_question_count,

            "qualitative_question_count":qualitative_question_count,

            "total_questions":total_questions,

            "competency_count":competency_count,

            "competencies":list(competencies)
        }

        return survey_framework_recap

    @staticmethod
    def get_all_comments(all_records):
       comments = []
       seen = set()
       for record in all_records:
           rater_type = record.get("Rate Group","") or record.get("Rater Group","") or record.get("Rater type","") 
           rater_type = rater_type.strip().lower()
           employee_name = record.get("Employee Name","")
           question = record.get("Question","")
           if rater_type in ["subordinates","others"]:
              normalized_group ="team"
           else:
              normalized_group ="manager"
           comment_key = f"{employee_name}_{question}_{normalized_group}"
           if comment_key not in seen:
               seen.add(comment_key)
               comments.append({"employee": employee_name, "question": question,"rater_type":normalized_group})    
       return comments
           
           
    @staticmethod
    def get_employee_wise_overall_data(all_records):
        employee_wise_data = defaultdict(list)
        for r in all_records:
            employee_name = r.get("Employee Name","") or r.get("Feedback recipient name")
            if not employee_name:
                continue
            employee_wise_data[employee_name].append(r)
        return employee_wise_data

    @staticmethod
    def get_leadership_profiles(employee_wise_overall_data):
        employee_cards = []
        for employee,rows in employee_wise_overall_data.items():
            question_wise_data = CommonFunctions.questionwise_avg_by_rate_group(rows)
            highest_team_avg,lowest_team_avg,highest_manager_avg,lowest_manager_avg = CommonFunctions.get_headlines(question_wise_data)
            team_response_count = 0
            manager_response_count = 0
            for r in rows:
                rater_type = r.get("Rate Group","") or r.get("Rater Group","") or r.get("Rater type","")
                rater_type = rater_type.strip().lower()
                if rater_type in ["subordinates","others","teams"]:
                    team_response_count += 1
                elif "manager" in rater_type:
                    manager_response_count += 1   
            formatted_highest_team = []
            formatted_lowest_team = []
            formatted_highest_manager = []
            formatted_lowest_manager = []

            

            for question, values in highest_team_avg:
                formatted_highest_team.append({"question":question,"average":values.get("Subordinates")})
            
            for question, values in lowest_team_avg:
                formatted_lowest_team.append({"question":question,"average":values.get("Subordinates")})

            for question, values in highest_manager_avg:
                formatted_highest_manager.append({"question":question,"average":values.get("Manager")})

            for question, values in lowest_manager_avg:
                formatted_lowest_manager.append({"question":question,"average":values.get("Manager")})
 
            
            employee_cards.append({
                    "employee":employee,
                    "team_responses":team_response_count,
                    "manager_responses":manager_response_count,
                    "highest_team_avg":formatted_highest_team,
                    "lowest_team_avg":formatted_lowest_team,
                    "highest_manager_avg":formatted_highest_manager,
                    "lowest_manager_avg":formatted_lowest_manager,
                })
            
        return employee_cards
        
    @staticmethod
    def get_competency_summary_institution(competency_data):
        values = []

        for question, value in competency_data.items():
          for group, val in value.items():
            if group == "Self":
                continue

            if val is not None:
                values.append(val)

        if not values:
            return {
                "min": 0,
                "avg": 0,
                "max": 0
            }

        return {

            "min":round(min(values), 2),

            "avg":round(sum(values) / len(values),2),

            "max":round(max(values), 2)
        }
    
    @staticmethod
    def get_self_rating_notes(all_records):
        self_ratings = defaultdict(dict)
        for row in all_records:
            if not isinstance(row, dict):
                continue
            rater_type = row.get("Rate Group","") or row.get("Rater Group","") or row.get("Rater type","") 
            if not rater_type:
                continue
            rater_type = str(rater_type).strip().lower()
            if rater_type != "self":
                continue
            
            employee = row.get("Employee Name") or row.get("Name")
            if not employee:
                continue
            
            question = row.get("Question")
            if not question:
                continue
                
            rating = row.get("Rating")
            if rating is None:
                continue
            try:
                val = float(rating)
            except (ValueError, TypeError):
                continue
                
            self_ratings[employee][question] = val

        # Now, calculate counts per employee
        employee_counts = {}
        for employee, q_ratings in self_ratings.items():
            total_rated = len(q_ratings)
            count_5 = sum(1 for q, r in q_ratings.items() if r == 5.0)
            if total_rated > 0:
                employee_counts[employee] = (count_5, total_rated)

        # Group employees by their (count_5, total_rated)
        groups = defaultdict(list)
        for employee, (count_5, total_rated) in employee_counts.items():
            if count_5 > 0 and (count_5 / total_rated >= 0.5 or count_5 >= 15):
                groups[(count_5, total_rated)].append(employee)

        # Sort groups: count_5 descending, then total_rated descending
        sorted_keys = sorted(groups.keys(), key=lambda x: (x[0], x[1]), reverse=True)

        notes = []
        for key in sorted_keys:
            count_5, total_rated = key
            employees = sorted(groups[key])
            
            if len(employees) == 1:
                names_str = employees[0]
            elif len(employees) == 2:
                names_str = f"{employees[0]} and {employees[1]}"
            else:
                names_str = ", ".join(employees[:-1]) + f" and {employees[-1]}"
                
            notes.append(f"{names_str} (Rating 5 for {count_5} out of {total_rated} questions)")
            
        return notes
    
    @staticmethod
    def calculate_participant_and_cohort_rating(employee_wise_category_data,target_employee):

        participant_data = (
            employee_wise_category_data[
                target_employee
            ]
        )

        competencies = set()

        for response in participant_data:

            for key in response.keys():

                if key not in [
                    "Function",
                    "Rater type"
                ]:
                    competencies.add(key)

        final_output = {}

        for competency in competencies:

            if "Feedback" in competency:
                continue

            your_rating = {
                "self": [],
                "manager": [],
                "peer": [],
                "team_member": []
            }

            for response in participant_data:

                rater_type = (
                    response["Rater type"]
                )

                scores = response.get(
                    competency,
                    []
                )

                avg = round(
                    np.mean(scores),
                    2
                ) if scores else 0

                if rater_type == "Self":
                    your_rating["self"].append(avg)

                elif rater_type == "Manager":
                    your_rating["manager"].append(avg)

                elif rater_type == "Peer":
                    your_rating["peer"].append(avg)

                elif rater_type == "Subordinate":
                    your_rating[
                        "team_member"
                    ].append(avg)

            # -------------------------------------------------
            # FINAL PARTICIPANT AVG
            # -------------------------------------------------

            for key in your_rating:

                values = your_rating[key]

                your_rating[key] = round(
                    np.mean(values),
                    2
                ) if values else 0

            # -------------------------------------------------
            # COHORT
            # -------------------------------------------------

            cohort_rating = {
                "self": [],
                "manager": [],
                "peer": [],
                "team_member": []
            }

            # all employees
            for _, employee_data in (
                employee_wise_category_data.items()
            ):

                for response in employee_data:

                    rater_type = (
                        response["Rater type"]
                    )

                    scores = response.get(
                        competency,
                        []
                    )

                    avg = round(
                        np.mean(scores),
                        2
                    ) if scores else 0

                    if rater_type == "Self":
                        cohort_rating[
                            "self"
                        ].append(avg)

                    elif rater_type == "Manager":
                        cohort_rating[
                            "manager"
                        ].append(avg)

                    elif rater_type == "Peer":
                        cohort_rating[
                            "peer"
                        ].append(avg)

                    elif rater_type == "Subordinate":
                        cohort_rating[
                            "team_member"
                        ].append(avg)

            # -------------------------------------------------
            # FINAL COHORT AVG
            # -------------------------------------------------

            for key in cohort_rating:

                values = cohort_rating[key]

                cohort_rating[key] = round(
                    np.mean(values),
                    2
                ) if values else 0

            # -------------------------------------------------
            # STORE
            # -------------------------------------------------

            final_output[competency] = {

                "your_rating": your_rating,

                "cohort_rating": cohort_rating
            }

        return final_output

    @staticmethod
    def timed_task(name, func, *args, **kwargs):
        start = time.time()
        thread_id = threading.get_ident()

        print(f"[START] {name} | Thread: {thread_id} | Time: {round(start,2)}")

        result = func(*args, **kwargs)

        end = time.time()
        print(f"[END]   {name} | Thread: {thread_id} | Duration: {round(end - start, 2)} sec")

        return result
