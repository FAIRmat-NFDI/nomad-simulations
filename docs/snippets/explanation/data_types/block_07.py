# Custom serialization preserving bounds
def serialize_bounded_type(bounded_type):
    return {
        'type_kind': 'custom',
        'type_data': f'{bounded_type.__class__.__module__}.{bounded_type.__class__.__name__}',
        'type_bound': str(bounded_type.bound),
    }

def deserialize_bounded_type(serialized):
    # Import the class and reconstruct with bounds
    module_path, class_name = serialized['type_data'].rsplit('.', 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    
    # Create instance and set bounds
    instance = cls()
    instance.bound = Bound(serialized['type_bound'])
    return instance
