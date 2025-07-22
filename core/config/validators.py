"""Data validation utilities."""

class DataValidators:
    @staticmethod
    def validate_weight(weight) -> bool:
        return isinstance(weight, (int, float)) and weight > 0 and weight < 10
    
    @staticmethod 
    def validate_age(age) -> bool:
        return isinstance(age, int) and 1 <= age <= 70
    
    @staticmethod
    def validate_coordinates(lat, lon) -> bool:
        return (-90 <= lat <= 90) and (-180 <= lon <= 180)
    
    @staticmethod
    def validate_barn_id(barn_id) -> bool:
        return isinstance(barn_id, str) and len(barn_id.strip()) > 0
    
    @staticmethod
    def validate_weight_consistency(today_weight, yesterday_weight) -> bool:
        if not (DataValidators.validate_weight(today_weight) and 
                DataValidators.validate_weight(yesterday_weight)):
            return False
        gain = today_weight - yesterday_weight
        return -0.2 <= gain <= 0.3  # Reasonable daily gain in kg
