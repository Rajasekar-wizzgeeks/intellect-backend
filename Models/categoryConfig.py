from mongoengine import Document, StringField, IntField, DictField, ListField

class CategoryConfig(Document):
    name = StringField(required=True, unique=True)              
    description = StringField(required=True, default="")       
    feedback_key = StringField(required=True)                  
    order = IntField(required=True)                            
    toc_id = StringField(required=True)                        
    default_page = IntField(required=True)                      
    role_weights = DictField(default=dict)                     
    behaviors = ListField(StringField(), default=list)          
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "feedback_key": self.feedback_key,
            "order": self.order,
            "toc_id": self.toc_id,
            "default_page": self.default_page,
            "role_weights": self.role_weights,
            "behaviors": self.behaviors
        }
