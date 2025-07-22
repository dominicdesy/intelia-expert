"""
Enhanced barn list parser with barn_type support for alert monitoring system.
Maintains backward compatibility while adding new functionality.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class BarnClient:
    """Client associated with a barn including type and coordinates."""
    barn_id: str
    language: str
    email: str
    barn_type: str = "broiler"  # New field for alert thresholds
    name: Optional[str] = None
    company: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @property
    def has_coordinates(self) -> bool:
        """Check if client has GPS coordinates."""
        return (self.coordinates is not None and 
                'lat' in self.coordinates and 
                'lon' in self.coordinates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "barn_id": self.barn_id,
            "language": self.language,
            "email": self.email,
            "barn_type": self.barn_type,
            "name": self.name,
            "company": self.company,
            "coordinates": self.coordinates,
            "preferences": self.preferences
        }
    
    @classmethod
    def from_txt_line(cls, line: str) -> Optional['BarnClient']:
        """
        Parse barn_list.txt line supporting multiple formats:
        - barn_id,language,email (legacy)
        - barn_id,language,lat,lon,email (legacy with GPS)
        - barn_id,language,lat,lon,barn_type,email (new format)
        """
        parts = [part.strip() for part in line.split(',')]
        
        if len(parts) == 3:
            # Legacy format: barn_id,language,email
            barn_id, language, email = parts
            return cls(
                barn_id=barn_id,
                language=language,
                email=email,
                barn_type="broiler"  # Default for backward compatibility
            )
        
        elif len(parts) == 5:
            # Legacy GPS format: barn_id,language,lat,lon,email
            barn_id, language, lat_str, lon_str, email = parts
            
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                coordinates = {"lat": lat, "lon": lon}
            except ValueError:
                logger.warning(f"Invalid coordinates in line: {line}")
                coordinates = None
            
            return cls(
                barn_id=barn_id,
                language=language,
                email=email,
                barn_type="broiler",  # Default for backward compatibility
                coordinates=coordinates
            )
        
        elif len(parts) >= 6:
            # New format: barn_id,language,lat,lon,barn_type,email1,email2,...
            barn_id, language, lat_str, lon_str, barn_type = parts[:5]
            emails = [email.strip() for email in parts[5:] if email.strip()]
            
            # Validate barn_type
            if barn_type not in ['broiler', 'layer']:
                logger.warning(f"Invalid barn_type '{barn_type}' in line: {line}")
                barn_type = "broiler"  # Default fallback
            
            # Parse coordinates
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                coordinates = {"lat": lat, "lon": lon}
            except ValueError:
                logger.warning(f"Invalid coordinates in line: {line}")
                coordinates = None
            
            # Use first email for single-email model compatibility
            primary_email = emails[0] if emails else "no-email@example.com"
            
            return cls(
                barn_id=barn_id,
                language=language,
                email=primary_email,
                barn_type=barn_type,
                coordinates=coordinates
            )
        
        else:
            logger.warning(f"Invalid format in line: {line}")
            return None


class BarnListManager:
    """Manages barn and client configurations with barn_type support."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize with configuration file path."""
        if config_file is None:
            # Try different possible locations
            possible_paths = [
                "Data/barn_list.txt",
                "barn_list.txt",
                "config/barn_list.txt",
                "data/barn_list.txt"
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.config_file = path
                    break
            else:
                self.config_file = "Data/barn_list.txt"
        else:
            self.config_file = config_file
            
        self.clients: List[BarnClient] = []
        self.barns: List[str] = []
        
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from barn_list.txt file."""
        config_path = Path(self.config_file)
        
        logger.info(f"Loading configuration from: {config_path.absolute()}")
        
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path.absolute()}")
            self._create_default_configuration()
            return
        
        try:
            self._load_txt_config(config_path)
            logger.info(f"Successfully loaded configuration from {config_path.absolute()}")
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._create_default_configuration()
    
    def _load_txt_config(self, config_path: Path):
        """Load TXT configuration from barn_list.txt."""
        clients = []
        
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                client = BarnClient.from_txt_line(line)
                if client:
                    clients.append(client)
                else:
                    logger.warning(f"Skipped invalid line {line_num}: {line}")
        
        self.clients = clients
        self.barns = sorted(list(set(client.barn_id for client in self.clients)))
        
        logger.info(f"Loaded {len(self.clients)} clients for {len(self.barns)} barns")
    
    def _create_default_configuration(self):
        """Create default configuration and save to barn_list.txt."""
        logger.info("Creating default barn_list.txt configuration")
        
        default_lines = [
            "# Barn list configuration with barn_type support",
            "# Format: barn_id,language,latitude,longitude,barn_type,email",
            "# barn_type: broiler or layer",
            "# Languages: en (English), fr (French), es (Spanish)",
            "",
            "712,en,45.508888,-73.561668,broiler,dominic.desy@intelia.com",
            "799,en,32.157435,-82.907123,broiler,test.en@farm799.com",
            "800,fr,32.157435,-82.907123,layer,test.fr@farm800.com",
            "801,es,35.20105,-91.83148,broiler,test.es@farm801.com"
        ]
        
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(default_lines))
        
        logger.info(f"Created default configuration at: {config_path}")
        self._load_txt_config(config_path)
    
    def get_clients_for_barn(self, barn_id: str) -> List[BarnClient]:
        """Get all clients for a specific barn."""
        return [client for client in self.clients if client.barn_id == barn_id]
    
    def get_all_barns(self) -> List[str]:
        """Get all barn IDs."""
        return self.barns.copy()
    
    def get_barn_type(self, barn_id: str) -> str:
        """Get barn type for specific barn ID."""
        clients = self.get_clients_for_barn(barn_id)
        if clients:
            return clients[0].barn_type
        return "broiler"  # Default fallback
    
    def get_barns_by_type(self, barn_type: str) -> List[str]:
        """Get all barns of specific type."""
        barn_types = {}
        for client in self.clients:
            barn_types[client.barn_id] = client.barn_type
        
        return [barn_id for barn_id, btype in barn_types.items() if btype == barn_type]
    
    def get_unique_barns_with_types(self) -> Dict[str, str]:
        """Get mapping of barn_id to barn_type."""
        barn_types = {}
        for client in self.clients:
            barn_types[client.barn_id] = client.barn_type
        return barn_types
    
    def get_languages_for_barn(self, barn_id: str) -> List[str]:
        """Get all languages for a barn."""
        clients = self.get_clients_for_barn(barn_id)
        return sorted(list(set(client.language for client in clients)))
    
    def add_client(self, barn_id: str, language: str, email: str, barn_type: str = "broiler",
                   lat: Optional[float] = None, lon: Optional[float] = None):
        """Add new client and update the file."""
        coordinates = None
        if lat is not None and lon is not None:
            coordinates = {"lat": lat, "lon": lon}
        
        client = BarnClient(
            barn_id=barn_id,
            language=language, 
            email=email,
            barn_type=barn_type,
            coordinates=coordinates
        )
        
        self.clients.append(client)
        
        if barn_id not in self.barns:
            self.barns.append(barn_id)
            self.barns.sort()
        
        self._save_configuration()
    
    def remove_client(self, email: str, barn_id: str = None):
        """Remove client by email and update the file."""
        self.clients = [
            c for c in self.clients 
            if not (c.email == email and (barn_id is None or c.barn_id == barn_id))
        ]
        
        # Update barn list
        self.barns = sorted(list(set(client.barn_id for client in self.clients)))
        self._save_configuration()
    
    def _save_configuration(self):
        """Save current configuration back to barn_list.txt."""
        config_path = Path(self.config_file)
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            lines = [
                "# Barn list configuration with barn_type support",
                "# Format: barn_id,language,latitude,longitude,barn_type,email",
                "# barn_type: broiler or layer",
                ""
            ]
            
            for client in self.clients:
                if client.has_coordinates:
                    line = f"{client.barn_id},{client.language},{client.coordinates['lat']},{client.coordinates['lon']},{client.barn_type},{client.email}"
                else:
                    line = f"{client.barn_id},{client.language},,{client.barn_type},{client.email}"
                lines.append(line)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            logger.info(f"Configuration saved to {config_path}")
        
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration including barn_type."""
        validation = {
            "valid": True,
            "total_clients": len(self.clients),
            "total_barns": len(self.barns),
            "languages": sorted(list(set(client.language for client in self.clients))),
            "barn_types": sorted(list(set(client.barn_type for client in self.clients))),
            "errors": [],
            "warnings": []
        }
        
        # Validate barn_type consistency per barn
        barn_types = {}
        for client in self.clients:
            barn_id = client.barn_id
            if barn_id not in barn_types:
                barn_types[barn_id] = client.barn_type
            elif barn_types[barn_id] != client.barn_type:
                validation["warnings"].append(
                    f"Inconsistent barn_type for {barn_id}: {barn_types[barn_id]} vs {client.barn_type}"
                )
        
        # Validate barn_type values
        for client in self.clients:
            if client.barn_type not in ['broiler', 'layer']:
                validation["errors"].append(
                    f"Invalid barn_type '{client.barn_type}' for barn {client.barn_id}"
                )
                validation["valid"] = False
        
        # Validate email formats
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for client in self.clients:
            if not email_pattern.match(client.email):
                validation["errors"].append(f"Invalid email format: {client.email}")
                validation["valid"] = False
        
        # Check supported languages
        supported_languages = {"en", "fr", "es"}
        for client in self.clients:
            if client.language not in supported_languages:
                validation["warnings"].append(f"Unsupported language: {client.language} for {client.email}")
        
        return validation
    
    def get_stats(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        clients_by_barn = {}
        languages_by_barn = {}
        barn_types = {}
        
        for client in self.clients:
            # Count clients per barn
            if client.barn_id not in clients_by_barn:
                clients_by_barn[client.barn_id] = 0
            clients_by_barn[client.barn_id] += 1
            
            # Count languages per barn
            if client.barn_id not in languages_by_barn:
                languages_by_barn[client.barn_id] = set()
            languages_by_barn[client.barn_id].add(client.language)
            
            # Track barn types
            barn_types[client.barn_id] = client.barn_type
        
        return {
            "total_clients": len(self.clients),
            "total_barns": len(self.barns),
            "clients_by_barn": clients_by_barn,
            "languages_by_barn": {k: list(v) for k, v in languages_by_barn.items()},
            "barn_types": barn_types,
            "clients_with_coordinates": len([c for c in self.clients if c.has_coordinates]),
            "broiler_barns": len([b for b, t in barn_types.items() if t == "broiler"]),
            "layer_barns": len([b for b, t in barn_types.items() if t == "layer"])
        }


# Global manager instance
_barn_manager = None

def get_barn_manager() -> BarnListManager:
    """Get the global barn manager instance."""
    global _barn_manager
    if _barn_manager is None:
        _barn_manager = BarnListManager()
    return _barn_manager


# Convenience functions for backward compatibility
def get_clients_for_barn(barn_id: str) -> List[BarnClient]:
    """Get all clients for a specific barn."""
    return get_barn_manager().get_clients_for_barn(barn_id)


def get_all_barns() -> List[str]:
    """Get all barn IDs."""
    return get_barn_manager().get_all_barns()


def get_languages_for_barn(barn_id: str) -> List[str]:
    """Get all languages for a barn."""
    return get_barn_manager().get_languages_for_barn(barn_id)


def get_barn_type(barn_id: str) -> str:
    """Get barn type for specific barn ID."""
    return get_barn_manager().get_barn_type(barn_id)


def get_barns_by_type(barn_type: str) -> List[str]:
    """Get all barns of specific type."""
    return get_barn_manager().get_barns_by_type(barn_type)


def get_unique_barns_with_types() -> Dict[str, str]:
    """Get mapping of barn_id to barn_type."""
    return get_barn_manager().get_unique_barns_with_types()


def validate_barn_list() -> Dict[str, Any]:
    """Validate the barn list configuration."""
    return get_barn_manager().validate_configuration()


def reload_configuration():
    """Reload configuration from file."""
    global _barn_manager
    _barn_manager = None
    return get_barn_manager()


def get_barn_stats() -> Dict[str, Any]:
    """Get barn configuration statistics."""
    return get_barn_manager().get_stats()


if __name__ == "__main__":
    # Test the enhanced barn manager
    manager = BarnListManager()
    
    stats = manager.get_stats()
    print(f"Loaded {stats['total_clients']} clients for {stats['total_barns']} barns")
    print(f"Broiler barns: {stats['broiler_barns']}, Layer barns: {stats['layer_barns']}")
    
    for barn_id, client_count in stats['clients_by_barn'].items():
        barn_type = stats['barn_types'].get(barn_id, 'unknown')
        languages = stats['languages_by_barn'].get(barn_id, [])
        print(f"Barn {barn_id} ({barn_type}): {client_count} clients, languages: {languages}")
    
    # Validation
    validation = manager.validate_configuration()
    print(f"Configuration valid: {validation['valid']}")
    if validation['errors']:
        print("Errors:", validation['errors'])
    if validation['warnings']:
        print("Warnings:", validation['warnings'])
