
from collections import defaultdict
import re
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

        combined_questionwise = {}
        combined_questionwise.update(right_culture_questionwise)
        combined_questionwise.update(leadership_style_questionwise)
        combined_questionwise.update(leadership_staff_dev_questionwise)
        combined_questionwise.update(educational_quality_questionwise)
        combined_questionwise.update(engagement_with_management_questionwise)

        return combined_questionwise
    
    @staticmethod
    def find_comparision_year_data(record1, record2):
        record1 = record1 or {}
        record2 = record2 or {}

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

            diff_data[question] = team_diff

        sorted_diff_data = dict(
            sorted(diff_data.items(), key=lambda item: item[1], reverse=True)
        )
        return sorted_diff_data
    
    
    @staticmethod
    def questionwise_find_total_response(records):
        question_grouped = defaultdict(list)
        for row in records:
            question = row.get("Question")
            if not question:
                continue
            question_grouped[question].append(row)
        first_question = next(iter(question_grouped))
        length = len(question_grouped[first_question])
        return length
          
        
        
            
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
                rater_groups_set.add(group)
                if group is None or value is None:
                    continue
                
                grouped[group].append(value)

            avg_result = {}

            sub_vals = grouped.get("Subordinates", [])
            oth_vals = grouped.get("Others", [])

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

            l1_vals = grouped.get("L1 Manager", [])
            l2_vals = grouped.get("L2 Manager", [])

            combined_mgr = l1_vals + l2_vals
            if combined_mgr:
                avg_result["Manager"] = round(
                    sum(combined_mgr) / len(combined_mgr), 2
                )
                rater_groups_set.discard("L1 Manager")
                rater_groups_set.discard("L2 Manager")
            elif "L1 Manager" in rater_groups_set or "L2 Manager" in rater_groups_set:
                avg_result["Manager"] = None
                rater_groups_set.discard("L1 Manager")
                rater_groups_set.discard("L2 Manager")

            for group, values in grouped.items():
                if group in ["Subordinates", "Others", "L1 Manager", "L2 Manager"]:
                    continue
                
                avg_result[group] = round(sum(values) / len(values), 2)

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

            result = {}
            sub_vals = list(groups.get("Subordinates") or [])
            oth_vals = list(groups.get("Others") or [])
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

            self_avg = avg(groups.get("Self"))
            if self_avg is not None:
                result["Self"] = self_avg

            mgr_avg = avg(groups.get("Manager"))
            if mgr_avg is not None:
                result["Manager"] = mgr_avg

            if result:
                out[question] = result

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
                comment = item
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
                rate_group=item.get("Rater Group")
            else:
                comment = item
            if rate_group == "Self" :
                continue

            # comment = item.get("Comment")
            # ignore_values = {"nil", "-", "no comment", "no comments", "na", "none"}
            if comment and comment.strip() :
                comments.append(comment.strip())

        return comments 


   