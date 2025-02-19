from typing import Dict, Any

# TODO: add back in last month impact score later
async def langchain_pre_process_street_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplifies street manager data by removing redundancies and consolidating information.
    
    Args:
        data: Raw street manager data dictionary
    
    Returns:
        Dict containing simplified street and statistics data
    """
    
    # Extract common street information from first feature
    if not data.get('features'):
        return data
        
    base_street = {
        'usrn': data['features'][0]['properties']['usrn'],
        'street_name': data['features'][0]['properties']['designatedname1_text'],
        'town': data['features'][0]['properties']['townname1_text'],
        'authority': {
            'name': data['features'][0]['properties']['responsibleauthority_name'],
            'area': data['features'][0]['properties']['administrativearea1_text']
        },
        'geometry': {
            'length': data['features'][0]['properties']['geometry_length']
        },
        'operational_state': data['features'][0]['properties']['operationalstate'],
        'operational_state_date': data['features'][0]['properties']['operationalstatedate']
    }

    # Simplify features
    simplified_features = []
    for feature in data['features']:
        props = feature['properties']
        
        # Skip the base street feature
        if props.get('description') == 'Designated Street Name':
            continue
            
        simplified_feature = {
            'type': props.get('description'),
            'designation': props.get('designation'),
            'timeframe': props.get('timeinterval'),
            'location': props.get('locationdescription'),
            'details': props.get('designationdescription'),
            'effective_date': props.get('effectivestartdate')
        }
        
        # Only include non-None values
        simplified_feature = {k: v for k, v in simplified_feature.items() if v is not None}
        simplified_features.append(simplified_feature)

    # Process statistics if present
    stats = {}
    if 'street_manager_stats' in data:
        raw_stats = data['street_manager_stats']
        stats = {
            # 'last_month_impact_levels': raw_stats.get('last_month_impact_levels', ['NO DATA']),
            'last_month_work_summary': raw_stats.get('last_month_work_summary', ['NO DATA']),
            '2024_work_summary': raw_stats.get('2024_work_summary', ['NO DATA'])
        }

    return {
        'street': base_street,
        'designations': simplified_features,
        'stats': stats,
        'metadata': {
            'timestamp': data.get('timeStamp'),
            'number_returned': data.get('numberReturned')
        }
    }

async def langchain_pre_process_land_use_info(data: dict) -> dict:
    """
    Simplifies land use data by extracting key information and consolidating features.
    
    Args:
        data: Raw land use data dictionary
    
    Returns:
        Dict containing simplified properties and summary stats
    """
    if not data.get('features'):
        return data

    simplified_features = []
    total_area = 0
    residential_count = 0
    commercial_count = 0
    
    for feature in data['features']:
        props = feature['properties']
        
        # Extract core property information
        property_info = {
            'property': {
                'name': props.get('name1_text'),
                'secondary_name': props.get('name2_text'),
                'description': props.get('description'),
                'area': props.get('geometry_area')
            },
            'classification': {
                'type': props.get('oslandusetiera'),
                'subtypes': props.get('oslandusetierb', []),
                'status': props.get('changetype')
            }
        }
        
        # Update statistics
        if property_info['property']['area']:
            total_area += property_info['property']['area']
            
        if 'Residential' in property_info['classification']['type']:
            residential_count += 1
        elif 'Commercial' in property_info['classification']['type']:
            commercial_count += 1
            
        simplified_features.append(property_info)

    # Calculate summary statistics
    stats = {
        'total_properties': len(simplified_features),
        'total_area': round(total_area, 2),
        'residential_count': residential_count,
        'commercial_count': commercial_count,
        'average_property_size': round(total_area / len(simplified_features), 2) if simplified_features else 0
    }

    return {
        'features': simplified_features,
        'statistics': stats,
        'metadata': {
            'count': data.get('numberReturned'),
            'timestamp': data.get('timeStamp')
        }
    }

