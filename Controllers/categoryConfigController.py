import re
from Models.categoryConfig import CategoryConfig
from Utils.apiException import ApiException

class CategoryConfigController:
    @staticmethod
    def _resequence_orders():
        configs = list(CategoryConfig.objects.order_by('order'))
        for idx, conf in enumerate(configs, start=1):
            if conf.order != idx:
                conf.order = idx
                conf.save()

    @staticmethod
    def get_all():
        CategoryConfigController._resequence_orders()
        configs = CategoryConfig.objects.order_by('order')
        return [c.to_dict() for c in configs]

    @staticmethod
    def create(data: dict):
        name = data.get("name", "").strip()
        if not name:
            raise ApiException("Category name is required", status_code=400)
        
        existing = CategoryConfig.objects(name=name).first()
        if existing:
            raise ApiException(f"Category with name '{name}' already exists", status_code=400)

        # Determine target order
        order = data.get("order")
        if order is None or order < 1:
            max_cat = CategoryConfig.objects.order_by('-order').first()
            order = (max_cat.order + 1) if max_cat else 1

        # Shift existing categories at or after this order by +1
        CategoryConfig.objects(order__gte=order).update(inc__order=1)

        clean_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        toc_id = data.get("toc_id") or f"toc-qual-{clean_slug}"
        default_page = data.get("default_page") or (30 + order * 2)
        feedback_key = data.get("feedback_key") or f"{name} Feedback"

        config = CategoryConfig(
            name=name,
            description=data.get("description", "").strip(),
            feedback_key=feedback_key,
            order=order,
            toc_id=toc_id,
            default_page=default_page,
            role_weights=data.get("role_weights", {}),
            behaviors=data.get("behaviors", [])
        )
        config.save()
        CategoryConfigController._resequence_orders()
        return config.to_dict()

    @staticmethod
    def update(config_id: str, data: dict):
        config = CategoryConfig.objects(id=config_id).first()
        if not config:
            raise ApiException("Category configuration not found", status_code=440)

        name = data.get("name", "").strip()
        if name and name != config.name:
            existing = CategoryConfig.objects(name=name, id__ne=config_id).first()
            if existing:
                raise ApiException(f"Category with name '{name}' already exists", status_code=400)
            config.name = name

        clean_slug = re.sub(r'[^a-z0-9]+', '-', config.name.lower()).strip('-')
        config.toc_id = f"toc-qual-{clean_slug}"
        if not config.default_page:
            config.default_page = 30 + (config.order or 1) * 2

        if "description" in data:
            config.description = data["description"].strip()
        if "feedback_key" in data and data["feedback_key"]:
            config.feedback_key = data["feedback_key"].strip()

        new_order = data.get("order")
        old_order = config.order

        if "role_weights" in data:
            config.role_weights = data["role_weights"]
        if "behaviors" in data:
            config.behaviors = data["behaviors"]

        if new_order is not None and new_order != old_order:
            if new_order < old_order:
                CategoryConfig.objects(id__ne=config.id, order__gte=new_order, order__lt=old_order).update(inc__order=1)
            else:
                CategoryConfig.objects(id__ne=config.id, order__gt=old_order, order__lte=new_order).update(dec__order=1)
            config.order = new_order

        config.save()
        CategoryConfigController._resequence_orders()
        return config.to_dict()

    @staticmethod
    def delete(config_id: str):
        config = CategoryConfig.objects(id=config_id).first()
        if not config:
            raise ApiException("Category configuration not found", status_code=440)
        config.delete()
        CategoryConfigController._resequence_orders()
        return {"message": "Category configuration deleted successfully"}

    @staticmethod
    def reorder(orders_list: list):
        for item in orders_list:
            cid = item.get("id")
            order = item.get("order")
            if cid and order is not None:
                CategoryConfig.objects(id=cid).update_one(set__order=order)
        CategoryConfigController._resequence_orders()
        return CategoryConfigController.get_all()
