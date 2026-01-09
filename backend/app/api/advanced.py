from flask import Blueprint, request, jsonify
from app.api.auth import token_required
from app.services.data_service import DataService
from app.services.advanced_modeling_service import AdvancedModelingService
from app.services.modeling_service import ModelingService

advanced_bp = Blueprint('advanced', __name__)

@advanced_bp.route('/rcs', methods=['POST'])
@token_required
def fit_rcs(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    # Load Data
    try:
         df, dataset = DataService.load_data(dataset_id, current_user)
    except Exception as e:
         return jsonify({'message': str(e)}), 404
         
    target = data.get('target')
    event_col = data.get('event_col') # Optional (for Cox)
    exposure = data.get('exposure')
    covariates = data.get('covariates', [])
    model_type = data.get('model_type', 'cox') # cox, logistic
    knots = int(data.get('knots', 3))
    
    # Validation
    required_cols = [exposure, target] + covariates
    if event_col: required_cols.append(event_col)
    
    # Validation
    features = [exposure] + covariates
    try:
         # Target formatting for check
         tgt_arg = target
         if model_type == 'cox' and event_col:
             tgt_arg = {'time': target, 'event': event_col}
             
         ModelingService.check_data_integrity(df, features, tgt_arg)
    except ValueError as e:
         return jsonify({'message': str(e)}), 400
        
    try:
        results = AdvancedModelingService.fit_rcs(
            df, target, event_col, exposure, covariates, model_type, knots
        )
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'message': f"RCS Analysis failed: {str(e)}"}), 500


@advanced_bp.route('/subgroup', methods=['POST'])
@token_required
def subgroup_analysis(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    try:
         df, dataset = DataService.load_data(dataset_id, current_user)
    except Exception as e:
         return jsonify({'message': str(e)}), 404
         
    target = data.get('target')
    event_col = data.get('event_col')
    exposure = data.get('exposure')
    covariates = data.get('covariates', [])
    subgroups = data.get('subgroups', []) # List of categorical vars
    model_type = data.get('model_type', 'cox')
    
    if not subgroups:
         return jsonify({'message': 'No subgroups provided.'}), 400
         
    try:
        results = AdvancedModelingService.perform_subgroup(
            df, target, event_col, exposure, subgroups, covariates, model_type
        )
        return jsonify({'forest_data': results}), 200
    except Exception as e:
        return jsonify({'message': f"Subgroup Analysis failed: {str(e)}"}), 500

@advanced_bp.route('/cif', methods=['POST'])
@token_required
def calculate_cif(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    try:
         df, dataset = DataService.load_data(dataset_id, current_user)
    except Exception as e:
         return jsonify({'message': str(e)}), 404
         
    time_col = data.get('time_col')
    event_col = data.get('event_col')
    group_col = data.get('group_col') # Optional
    
    if not time_col or not event_col:
        return jsonify({'message': 'Time and Event columns are required.'}), 400
        
    try:
        results = AdvancedModelingService.calculate_cif(
            df, time_col, event_col, group_col
        )
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'message': f"CIF Calculation failed: {str(e)}"}), 500

@advanced_bp.route('/nomogram', methods=['POST'])
@token_required
def generate_nomogram(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    try:
         df, dataset = DataService.load_data(dataset_id, current_user)
    except Exception as e:
         return jsonify({'message': str(e)}), 404
    
    target = data.get('target')
    event_col = data.get('event_col')
    model_type = data.get('model_type', 'logistic')
    predictors = data.get('predictors', [])
    
    if not predictors:
         return jsonify({'message': 'Predictors are required'}), 400

    # Validation
    try:
         tgt_arg = target
         if model_type == 'cox' and event_col:
             tgt_arg = {'time': target, 'event': event_col}
         ModelingService.check_data_integrity(df, predictors, tgt_arg)
    except Exception as e:
         return jsonify({'message': str(e)}), 400

    try:
        results = AdvancedModelingService.generate_nomogram(
            df, target, event_col, model_type, predictors
        )
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'message': f"Nomogram generation failed: {str(e)}"}), 500
