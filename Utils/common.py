from collections import defaultdict
import re
import time
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
                category_data.get('Leadership Style', [])
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

        team_score_key = "Subordinates"
        threshold = 0.1

        for question in all_questions:
            groups1 = record1.get(question) or {}
            groups2 = record2.get(question) or {}

            v1 = groups1.get(team_score_key)
            v2 = groups2.get(team_score_key)
            if v1 is None or v2 is None:
                continue

            team_diff = round(v1 - v2, 2)
            if abs(team_diff) <= threshold:
                continue

            diff_data[question] = {"team_diff1": team_diff}

        sorted_diff_data = dict(
            sorted(diff_data.items(), key=lambda item: item[1].get('team_diff1', 0), reverse=True)
        )
        return sorted_diff_data
    

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

        team_score_key = "Subordinates"
        threshold = 0.1

        for question in all_questions:
            groups1 = record1.get(question) or {}
            groups2 = record2.get(question) or {}
            groups3 = record3.get(question) or {}

            v1 = groups1.get(team_score_key)
            v2 = groups2.get(team_score_key)
            v3 = groups3.get(team_score_key)
            if v1 is None or v2 is None or v3 is None:
                continue

            team_diff1 = round(v1 - v2, 2)
            team_diff2 = round(v2 - v3, 2)
            if abs(team_diff1) <= threshold or abs(team_diff2) <= threshold:
                continue
            diff_data[question] = {
                "team_diff1": team_diff1,
                "team_diff2": team_diff2
            }

        sorted_diff_data = dict(
                sorted(
                    diff_data.items(),
                    key=lambda item: item[1].get("team_diff1", 0),
                    reverse=True
                )
            )
        return sorted_diff_data
    
    
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
                key=lambda x: (x[1].get("Subordinates") is None, x[1].get("Subordinates", 0)),
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
            "Subordinates": sub_strengths[:3],
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
            "Subordinates": sub_strengths[:3],
            "Manager": mgr_strengths[:3]
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
            rate_group=None
            if isinstance(item, dict):
                comment = item.get("Comment")
                rate_group = item.get("Rater Group")
            else:
                comment = item
            
            if comment is not None and not isinstance(comment, str):
                comment = str(comment)

            if rate_group == "Self" :
                continue

            # comment = item.get("Comment")
            # ignore_values = {"nil", "-", "no comment", "no comments", "na", "none"}
            if comment and comment.strip() :
                comments.append(comment.strip())

        return comments 

    @staticmethod
    def timed_task(name, func, *args, **kwargs):
        start = time.time()
        thread_id = threading.get_ident()

        print(f"[START] {name} | Thread: {thread_id} | Time: {round(start,2)}")

        result = func(*args, **kwargs)

        end = time.time()
        print(f"[END]   {name} | Thread: {thread_id} | Duration: {round(end - start, 2)} sec")

        return result
