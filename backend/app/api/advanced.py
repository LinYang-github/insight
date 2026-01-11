from flask import Blueprint, request, jsonify
from app.api.auth import token_required
from app.models.dataset import Dataset
from app.services.data_service import DataService
from app.services.advanced_modeling_service import AdvancedModelingService
from app.services.modeling_service import ModelingService
from app import db

advanced_bp = Blueprint('advanced', __name__)

@advanced_bp.route('/rcs', methods=['POST'])
@token_required
def fit_rcs(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    # Load Data
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'message': 'Dataset not found'}), 404
        
    # Load Data (Deferred to after params parsing to know columns)
    # dataset = Dataset.query.get(dataset_id) # Already got dataset object 
    
    # Move param parsing UP before loading
    target = data.get('target')
    event_col = data.get('event_col') # Optional (for Cox)
    exposure = data.get('exposure')
    covariates = data.get('covariates', [])
    model_type = data.get('model_type', 'cox') # cox, logistic
    knots = int(data.get('knots', 3))
    
    # Validation
    required_cols = [exposure, target] + covariates
    if event_col: required_cols.append(event_col)
    
    # Optimization: Load only required columns
    df = DataService.load_data_optimized(dataset.filepath, columns=required_cols)
    
    # Validation
    features = [exposure] + covariates
    # Target formatting for check
    tgt_arg = target
    if model_type == 'cox' and event_col:
        tgt_arg = {'time': target, 'event': event_col}
        
    ModelingService.check_data_integrity(df, features, tgt_arg)
        
    results = AdvancedModelingService.fit_rcs(
        df, target, event_col, exposure, covariates, model_type, knots
    )
    return jsonify(results), 200


@advanced_bp.route('/subgroup', methods=['POST'])
@token_required
def subgroup_analysis(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'message': 'Dataset not found'}), 404
        
    # Parse params first
    target = data.get('target')
    event_col = data.get('event_col')
    exposure = data.get('exposure')
    covariates = data.get('covariates', [])
    subgroups = data.get('subgroups', []) # List of categorical vars
    model_type = data.get('model_type', 'cox')
    
    if not subgroups:
         return jsonify({'message': 'No subgroups provided.'}), 400
         
    # Optimization
    required = [target, exposure] + covariates + subgroups
    if event_col: required.append(event_col)
    # Deduplicate
    required = list(set(required))
    
    df = DataService.load_data_optimized(dataset.filepath, columns=required)
          
    results = AdvancedModelingService.perform_subgroup(
        df, target, event_col, exposure, subgroups, covariates, model_type
    )
    return jsonify(results), 200

@advanced_bp.route('/cif', methods=['POST'])
@token_required
def calculate_cif(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'message': 'Dataset not found'}), 404
        
    time_col = data.get('time_col')
    event_col = data.get('event_col')
    group_col = data.get('group_col') # Optional
    
    if not time_col or not event_col:
        return jsonify({'message': 'Time and Event columns are required.'}), 400
        
    required = [time_col, event_col]
    if group_col: required.append(group_col)
    
    df = DataService.load_data_optimized(dataset.filepath, columns=required)
    
    results = AdvancedModelingService.calculate_cif(
        df, time_col, event_col, group_col
    )
    return jsonify(results), 200

@advanced_bp.route('/nomogram', methods=['POST'])
@token_required
def generate_nomogram(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'message': 'Dataset not found'}), 404
        
    target = data.get('target')
    event_col = data.get('event_col')
    model_type = data.get('model_type', 'logistic')
    predictors = data.get('predictors', [])
    
    if not predictors:
         return jsonify({'message': 'Predictors are required'}), 400

    required = [target] + predictors
    if event_col: required.append(event_col)
    
    df = DataService.load_data_optimized(dataset.filepath, columns=required)

    # Validation
    tgt_arg = target
    if model_type == 'cox' and event_col:
        tgt_arg = {'time': target, 'event': event_col}
    ModelingService.check_data_integrity(df, predictors, tgt_arg)

    results = AdvancedModelingService.generate_nomogram(
        df, target, event_col, model_type, predictors
    )
    return jsonify(results), 200

@advanced_bp.route('/compare-models', methods=['POST'])
@token_required
def compare_models(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'message': 'Dataset not found'}), 404
        
    target = data.get('target')
    event_col = data.get('event_col') # Optional (for Cox)
    model_configs = data.get('models', [])
    model_type = data.get('model_type', 'logistic')
    
    if not target or not model_configs:
         return jsonify({'message': 'Target and Models are required'}), 400
         
    # Optimization: Collect all unique features needed
    required = set([target])
    if event_col: required.add(event_col)
    
    # Basic Config Validation
    for conf in model_configs:
        if 'name' not in conf or 'features' not in conf:
             return jsonify({'message': 'Invalid model config format. Need name and features.'}), 400
        for f in conf['features']:
            required.add(f)
            
    df = DataService.load_data_optimized(dataset.filepath, columns=list(required))
             
    results = AdvancedModelingService.compare_models(
        df, target, model_configs, model_type, event_col
    )
    return jsonify(results), 200
