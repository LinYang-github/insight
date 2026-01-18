try:
    import patsy
    print("Patsy imported successfully.")
except ImportError:
    print("Patsy not found.")

try:
    from app.services.advanced_modeling_service import AdvancedModelingService
    print("AdvancedModelingService imported successfully.")
except Exception as e:
    print(f"Error importing service: {e}")
