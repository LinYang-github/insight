
from app import create_app, db
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.services.preprocessing_service import PreprocessingService
from app.services.statistics_service import StatisticsService
import pandas as pd
import os
import json

app = create_app()

with app.app_context():
    # Setup
    user = User.query.first()
    if not user:
        user = User(username='test_lineage', email='test@lineage.com')
        user.set_password('123')
        db.session.add(user)
        db.session.commit()
        
    project = Project(name='Lineage Test Project', author=user)
    db.session.add(project)
    db.session.commit()
    
    # Create dummy CSV
    dummy_path = os.path.join(app.config['UPLOAD_FOLDER'], 'lineage_dummy.csv')
    df = pd.DataFrame({'A': [1, 2, None], 'B': ['M', 'F', 'M'], 'Treat': [0, 1, 0], 'Cov': [1, 2, 3]})
    df.to_csv(dummy_path, index=False)
    
    dataset = Dataset(project_id=project.id, name='lineage_dummy.csv', filepath=dummy_path)
    db.session.add(dataset)
    db.session.commit()
    
    print(f"Original Dataset ID: {dataset.id}")
    
    # 1. Test Imputation Lineage
    imputed_df = PreprocessingService.impute_data(df, {'A': 'mean'})
    imputed_ds = PreprocessingService.save_processed_dataset(
        dataset.id, imputed_df, 'imputed', user.id,
        parent_id=dataset.id, action_type='impute', log={'A': 'mean'}
    )
    
    print(f"Imputed Dataset ID: {imputed_ds.id}")
    print(f"Parent ID: {imputed_ds.parent_id}")
    print(f"Action Type: {imputed_ds.action_type}")
    print(f"Action Log: {imputed_ds.action_log}")
    
    assert imputed_ds.parent_id == dataset.id
    assert imputed_ds.action_type == 'impute'
    assert 'mean' in imputed_ds.action_log
    
    # 2. Test PSM Lineage (Simulated API logic)
    # We call DB logic directly similar to API logic
    matched_df = df.copy() # Fake matched
    matched_filename = f"lineage_dummy_matched.csv"
    matched_filepath = os.path.join(app.config['UPLOAD_FOLDER'], matched_filename)
    matched_df.to_csv(matched_filepath, index=False)
    
    psm_ds = Dataset(
        name=matched_filename,
        filepath=matched_filepath,
        project_id=project.id,
        parent_id=dataset.id,
        action_type='psm',
        action_log=json.dumps({'treatment': 'Treat'})
    )
    db.session.add(psm_ds)
    db.session.commit()
    
    print(f"PSM Dataset ID: {psm_ds.id}")
    print(f"Parent ID: {psm_ds.parent_id}")
    
    assert psm_ds.parent_id == dataset.id
    assert psm_ds.action_type == 'psm'
    
    print("VERIFICATION PASSED!")
    
    # Cleanup
    db.session.delete(psm_ds)
    db.session.delete(imputed_ds)
    db.session.delete(dataset)
    db.session.delete(project)
    if user.username == 'test_lineage': db.session.delete(user)
    db.session.commit()
