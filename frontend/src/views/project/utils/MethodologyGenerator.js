/**
 * MethodologyGenerator.js
 * 
 * Auto-generate "Methods" section text for publications.
 */
export default class MethodologyGenerator {
    static generate(config, results) {
        const lines = []

        // 1. Model Type
        let typeText = ''
        switch (config.model_type) {
            case 'logistic': typeText = 'Multivariate logistic regression analysis'; break;
            case 'linear': typeText = 'Multivariate linear regression analysis'; break;
            case 'cox': typeText = 'Multivariate Cox proportional hazards regression analysis'; break;
            case 'random_forest': typeText = 'Random Forest machine learning model'; break;
            case 'xgboost': typeText = 'XGBoost (Extreme Gradient Boosting) model'; break;
            default: typeText = 'Statistical analysis';
        }
        lines.push(`${typeText} was performed to identify factors associated with the outcome.`);

        // 2. Metrics
        let metricText = ''
        if (['logistic', 'cox'].includes(config.model_type)) {
            const key = config.model_type === 'logistic' ? 'Odds Ratios (OR)' : 'Hazard Ratios (HR)';
            metricText = `Results were expressed as ${key} with 95% confidence intervals (95% CI).`;
        } else if (config.model_type === 'linear') {
            metricText = `Coefficients (Coef) with 95% confidence intervals were calculated.`;
        }
        if (metricText) lines.push(metricText);

        // 3. Significance Level
        lines.push("A two-sided P-value < 0.05 was considered statistically significant.");

        // 4. Software
        lines.push("All analyses were performed using the Insight Statistical Platform (v1.0).");

        // 5. Reference Levels
        if (config.ref_levels && Object.keys(config.ref_levels).length > 0) {
            const refs = []
            for (const [key, val] of Object.entries(config.ref_levels)) {
                refs.push(`${val} for ${key}`)
            }
            if (refs.length > 0) {
                lines.push(`Reference groups for categorical variables were set as follows: ${refs.join(', ')}.`);
            }
        }

        return lines.join(' ');
    }
}
