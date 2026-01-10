"""
app.api.statistics.py

医学统计分析相关路由。
提供基线特征表 (Table 1)、Kaplan-Meier 生存曲线及倾向性评分匹配 (PSM) 的 API 支持。
"""
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
    """
    获取基线特征统计数据。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    group_by = data.get('group_by') # Optional
    variables = data.get('variables') # List of vars
    
    if not dataset_id or not variables:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    result = StatisticsService.generate_table_one(df, group_by, variables)
    return jsonify({
        'table1': result['table_data'],
        'methodology': result['methodology']
    }), 200

@statistics_bp.route('/km', methods=['POST'])
@token_required
def generate_km(current_user):
    """
    生成 Kaplan-Meier 生存曲线数据。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    time_col = data.get('time')
    event_col = data.get('event')
    group_col = data.get('group') # Optional
    
    if not dataset_id or not time_col or not event_col:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    result = StatisticsService.generate_km_data(df, time_col, event_col, group_col)
    return jsonify({'km_data': result}), 200

@statistics_bp.route('/psm', methods=['POST'])
@token_required
def perform_psm(current_user):
    """
    执行倾向性评分匹配 (PSM)。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    treatment = data.get('treatment')
    covariates = data.get('covariates')
    save_result = data.get('save', False)
    
    if not dataset_id or not treatment or not covariates:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
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
        # For lineage in PSM, we treat original dataset as parent
        import json
        new_dataset = Dataset(
            name=new_filename,
            filepath=new_filepath,
            project_id=dataset.project_id,
            parent_id=dataset.id,
            action_type='psm',
            action_log=json.dumps({'treatment': treatment, 'covariates': covariates})
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

@statistics_bp.route('/table1/export', methods=['POST'])
@token_required
def export_table1(current_user):
    """
    导出学术标准的三线表 (Table 1) 为 CSV 文件。
    """
    from flask import Response
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    group_by = data.get('group_by')
    variables = data.get('variables')
    
    if not dataset_id or not variables:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
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

@statistics_bp.route('/recommend-covariates', methods=['POST'])
@token_required
def recommend_covariates(current_user):
    """
    基于处理变量推荐协变量。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    treatment = data.get('treatment')
    
    if not dataset_id or not treatment:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    recommendations = StatisticsService.recommend_covariates(df, treatment)
    return jsonify({'recommendations': recommendations}), 200

@statistics_bp.route('/check-health', methods=['POST'])
@token_required
def check_health(current_user):
    """
    检查变量健康状况。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    variables = data.get('variables')
    
    if not dataset_id or not variables:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    report = StatisticsService.check_data_health(df, variables)
    return jsonify({'report': report}), 200

@statistics_bp.route('/distribution', methods=['POST'])
@token_required
def get_distribution(current_user):
    """
    获取变量分布数据。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    variable = data.get('variable')
    
    if not dataset_id or not variable:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    dist_data = StatisticsService.get_distribution(df, variable)
    return jsonify({'distribution': dist_data}), 200

@statistics_bp.route('/check-collinearity', methods=['POST'])
@token_required
def check_collinearity(current_user):
    """
    检查共线性。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    features = data.get('features') # list of strings
    
    if not dataset_id or not features:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    result = StatisticsService.check_multicollinearity(df, features)
    return jsonify(result), 200

@statistics_bp.route('/recommend-model', methods=['POST'])
@token_required
def recommend_model(current_user):
    """
    智能推荐建模策略。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    if not dataset_id:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    
    recommendation = StatisticsService.recommend_modeling_strategy(df)
    return jsonify({'recommendation': recommendation}), 200
