from app import db
import json

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(128)) # Original filename or display name
    filepath = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Lineage / Version Control
    parent_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=True) # Source dataset
    action_type = db.Column(db.String(32), nullable=True) # e.g. 'upload', 'impute', 'encode', 'psm'
    action_log = db.Column(db.Text, nullable=True) # JSON Logs of parameters
    
    # Metadata stored as JSON string
    _metadata_json = db.Column("metadata", db.Text)
    
    project = db.relationship('Project', foreign_keys=[project_id], backref=db.backref('datasets', lazy=True, cascade="all, delete-orphan"))
    parent = db.relationship('Dataset', remote_side=[id], backref=db.backref('children', lazy=True, cascade="all, delete-orphan"))

    @property
    def meta_data(self):
        if self._metadata_json:
            return json.loads(self._metadata_json)
        return {}

    @meta_data.setter
    def meta_data(self, value):
        self._metadata_json = json.dumps(value)

    def __repr__(self):
        return '<Dataset {}>'.format(self.name)

# Event listener for file cleanup
from sqlalchemy import event
import os

@event.listens_for(Dataset, 'after_delete')
def receive_after_delete(mapper, connection, target):
    """
    Automatically delete the physical file when a Dataset record is deleted.
    """
    if target.filepath and os.path.exists(target.filepath):
        try:
            os.remove(target.filepath)
        except OSError:
            # Log warning in production, for now pass
            pass
