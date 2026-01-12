@statistics_bp.route('/iptw', methods=['POST'])
@token_required
def perform_iptw(current_user):
    """
    执行逆概率加权 (IPTW)。
    """
    data = request.get_json()
    try:
        from app.services.data_service import DataService
        from app.services.preprocessing_service import PreprocessingService 
        from flask import g
        
        df = DataService.load_data(Dataset.query.get(data.get('dataset_id')).filepath)
        res = StatisticsService.perform_iptw(
            df,
            data.get('treatment'),
            data.get('covariates'),
            weight_type=data.get('weight_type', 'ATE'),
            stabilized=data.get('stabilized', True),
            truncate=data.get('truncate', True)
        )
        
        if data.get('save'):
            # Create subset DF with weights
            subset_df = df.loc[res['indices']].copy()
            subset_df['iptw_weight'] = res['weights']
            
            new_id = PreprocessingService.save_processed_dataset(
                data.get('dataset_id'), subset_df, 'iptw', g.user.id,
                log={'type': 'iptw', 'treatment': data.get('treatment')}
            ).id
            res['new_dataset_id'] = new_id
            
        return jsonify(res)
    except Exception as e:
        return jsonify({'message': str(e)}), 500
