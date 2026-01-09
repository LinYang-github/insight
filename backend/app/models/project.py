from datetime import datetime
from app import db

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    active_dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=True)
    
    # Relationships
    active_dataset = db.relationship('Dataset', foreign_keys=[active_dataset_id])
    
    # Future fields: study_design, data_path, status, etc.

    def __repr__(self):
        return '<Project {}>'.format(self.name)
