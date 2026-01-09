
from flask import Blueprint, jsonify, request
from app.services.statistics_service import StatisticsService
from app.models.dataset import Dataset
from app.api.projects import token_required
from app import db # Need db to save new dataset
import pandas as pd
import os

statistics_bp = Blueprint('statistics', __name__)

@statistics_bp.route('/table1', methods=['POST'])
@token_required
def generate_table1(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    group_by = data.get('group_by') # Optional
    variables = data.get('variables') # List of vars
    
    if not dataset_id or not variables:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        
        result = StatisticsService.generate_table_one(df, group_by, variables)
        return jsonify({'table1': result}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@statistics_bp.route('/km', methods=['POST'])
@token_required
def generate_km(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    time_col = data.get('time')
    event_col = data.get('event')
    group_col = data.get('group') # Optional
    
    if not dataset_id or not time_col or not event_col:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        
        result = StatisticsService.generate_km_data(df, time_col, event_col, group_col)
        return jsonify({'km_data': result}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@statistics_bp.route('/psm', methods=['POST'])
@token_required
def perform_psm(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    treatment = data.get('treatment')
    covariates = data.get('covariates')
    save_result = data.get('save', False)
    
    if not dataset_id or not treatment or not covariates:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        
        result = StatisticsService.perform_psm(df, treatment, covariates)
        
        matched_dataset_id = None
        if save_result:
            # Reconstruct matched data
            matched_indices = result['matched_indices']
            matched_df = df.loc[matched_indices]
            
            # Save new file
            new_filename = f"{os.path.splitext(dataset.name)[0]}_matched.csv"
            new_filepath = os.path.join(os.path.dirname(dataset.filepath), new_filename)
            matched_df.to_csv(new_filepath, index=False)
            
            # Create new Dataset record
            new_dataset = Dataset(
                name=new_filename,
                filepath=new_filepath,
                project_id=dataset.project_id
            )
            # Add metadata?
            try:
                new_dataset.meta_data = DataService.get_initial_metadata(new_filepath)
            except:
                new_dataset.meta_data = dataset.meta_data # Fallback
            
            db.session.add(new_dataset)
            db.session.commit()
            matched_dataset_id = new_dataset.id
        
        # Don't send back indices, just verification stats
        response = {
            'balance': result['balance'],
            'stats': {k:v for k,v in result.items() if k in ['n_treated', 'n_control', 'n_matched']}
        }
        if matched_dataset_id:
            response['new_dataset_id'] = matched_dataset_id
            
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@statistics_bp.route('/table1/export', methods=['POST'])
@token_required
def export_table1(current_user):
    from flask import Response
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    group_by = data.get('group_by')
    variables = data.get('variables')
    
    if not dataset_id or not variables:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        
        # 1. Generate Table 1 data
        result = StatisticsService.generate_table_one(df, group_by, variables)
        
        # 2. Convert to DataFrame for CSV
        export_rows = []
        for item in result:
            row = {'Variable': item['variable']}
            # Add overall
            overall = item.get('overall', {})
            row['Overall'] = f"{overall.get('mean', '')} ± {overall.get('std', '')}" if 'mean' in overall else overall.get('desc', '')
            
            # Add groups
            for g_name, g_stats in item.get('groups', {}).items():
                 row[g_name] = f"{g_stats.get('mean', '')} ± {g_stats.get('std', '')}" if 'mean' in g_stats else g_stats.get('desc', '')
            
            row['P-value'] = item['p_value']
            row['Test'] = item['test']
            export_rows.append(row)
            
        export_df = pd.DataFrame(export_rows)
        
        # 3. Stream CSV
        # Use BOM for Excel compatibility (UTF-8-SIG)
        csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
        
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=table1_export.csv"}
        )
    except Exception as e:
        return jsonify({'message': str(e)}), 500
