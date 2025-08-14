# -*- coding: utf-8 -*-
"""
📊 Calculators Adapter - Orchestrateur pour calculs avicoles
🎯 P0.4 : Orchestrateur qui normalise → formulas.py → format sortie avec hypothèses/flags

Ce module sert d'interface unifiée entre le dialogue_manager et les formulas.py.
Il standardise les entrées, délègue les calculs, et formate les sorties avec métadonnées.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# Import des modules existants du projet
try:
    from . import units
    from . import entity_normalizer
    from ...formulas import (
        # Performance & Economics
        iep, cout_aliment_par_kg_vif, cout_total_aliment,
        # Environment
        setpoint_temp_C_broiler, setpoint_hr_pct, co2_max_ppm, nh3_max_ppm, lux_program_broiler,
        # Ventilation
        vent_min_m3h_par_kg, vent_min_total_m3h, debit_tunnel_m3h, chaleur_a_extraire_w,
        # Water & Equipment  
        conso_eau_j, debit_eau_l_min, dimension_mangeoires, dimension_abreuvoirs
    )
except ImportError as e:
    logging.warning(f"⚠️ Import formulas.py partiel: {e}")
    # Fallback pour développement
    from typing import Callable
    iep = cout_aliment_par_kg_vif = cout_total_aliment = lambda *args, **kwargs: None
    setpoint_temp_C_broiler = setpoint_hr_pct = lambda *args, **kwargs: 20.0
    co2_max_ppm = nh3_max_ppm = lambda: 1000
    lux_program_broiler = lambda *args, **kwargs: 10.0
    vent_min_m3h_par_kg = vent_min_total_m3h = lambda *args, **kwargs: 1.0
    debit_tunnel_m3h = chaleur_a_extraire_w = lambda *args, **kwargs: 100.0
    conso_eau_j = debit_eau_l_min = lambda *args, **kwargs: 50.0
    dimension_mangeoires = dimension_abreuvoirs = lambda *args, **kwargs: 100.0

logger = logging.getLogger(__name__)

# ================== TYPES & ENUMS ==================

class CalculationType(str, Enum):
    """Types de calculs supportés"""
    WATER = "water"
    FEED = "feed" 
    ENVIRONMENT = "environment"
    VENTILATION = "ventilation"
    EQUIPMENT = "equipment"
    ECONOMICS = "economics"
    PERFORMANCE = "performance"

class ConfidenceLevel(str, Enum):
    """Niveaux de confiance des résultats"""
    HIGH = "high"        # Paramètres complets, calcul précis
    MEDIUM = "medium"    # Quelques paramètres manquants, estimations
    LOW = "low"         # Nombreuses hypothèses, ordre de grandeur
    UNCERTAIN = "uncertain"  # Calcul impossible ou très imprécis

@dataclass
class CalculationResult:
    """Résultat standardisé d'un calcul"""
    value: Optional[Union[float, int, str]]
    unit: str
    confidence: ConfidenceLevel
    assumptions: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    source_formula: str

@dataclass 
class CalculationRequest:
    """Requête de calcul normalisée"""
    calc_type: CalculationType
    entities: Dict[str, Any]
    parameters: Dict[str, Any]
    target_unit: Optional[str] = None

# ================== CORE ADAPTER CLASS ==================

class CalculatorsAdapter:
    """
    Orchestrateur principal pour les calculs avicoles
    
    Flux: normalize_input → delegate_calculation → format_output
    """
    
    def __init__(self):
        self.normalizer = entity_normalizer.EntityNormalizer() if hasattr(entity_normalizer, 'EntityNormalizer') else None
        self._calculation_handlers = self._setup_handlers()
        
    def _setup_handlers(self) -> Dict[CalculationType, Callable]:
        """Configuration des handlers par type de calcul"""
        return {
            CalculationType.WATER: self._calculate_water,
            CalculationType.FEED: self._calculate_feed,
            CalculationType.ENVIRONMENT: self._calculate_environment,
            CalculationType.VENTILATION: self._calculate_ventilation,
            CalculationType.EQUIPMENT: self._calculate_equipment,
            CalculationType.ECONOMICS: self._calculate_economics,
            CalculationType.PERFORMANCE: self._calculate_performance,
        }
    
    # ================== PUBLIC API ==================
    
    def calculate(
        self, 
        calc_type: Union[str, CalculationType], 
        entities: Dict[str, Any],
        parameters: Dict[str, Any] = None,
        target_unit: str = None
    ) -> CalculationResult:
        """
        Point d'entrée principal pour tous les calculs
        
        Args:
            calc_type: Type de calcul (water, feed, environment, etc.)
            entities: Entités extraites (species, age, etc.)
            parameters: Paramètres spécifiques au calcul
            target_unit: Unité de sortie souhaitée
            
        Returns:
            CalculationResult avec valeur, confiance, hypothèses
        """
        try:
            # 1. Normalisation et validation
            calc_type_enum = CalculationType(calc_type) if isinstance(calc_type, str) else calc_type
            request = self._normalize_request(calc_type_enum, entities, parameters or {}, target_unit)
            
            # 2. Délégation du calcul
            handler = self._calculation_handlers.get(calc_type_enum)
            if not handler:
                return self._error_result(f"Type de calcul non supporté: {calc_type_enum}")
            
            result = handler(request)
            
            # 3. Post-traitement et validation
            return self._post_process_result(result, request)
            
        except Exception as e:
            logger.exception(f"❌ Erreur calcul {calc_type}: {e}")
            return self._error_result(f"Erreur lors du calcul: {str(e)}")
    
    def batch_calculate(
        self, 
        requests: List[Tuple[str, Dict[str, Any], Dict[str, Any]]]
    ) -> Dict[str, CalculationResult]:
        """Calculs multiples en batch"""
        results = {}
        
        for i, (calc_type, entities, params) in enumerate(requests):
            try:
                key = f"{calc_type}_{i}"
                results[key] = self.calculate(calc_type, entities, params)
            except Exception as e:
                logger.error(f"❌ Erreur batch calcul {i}: {e}")
                results[f"error_{i}"] = self._error_result(str(e))
        
        return results
    
    def get_supported_calculations(self) -> List[str]:
        """Liste des types de calculs supportés"""
        return [calc_type.value for calc_type in CalculationType]
    
    # ================== INTERNAL METHODS ==================
    
    def _normalize_request(
        self, 
        calc_type: CalculationType, 
        entities: Dict[str, Any],
        parameters: Dict[str, Any],
        target_unit: Optional[str]
    ) -> CalculationRequest:
        """Normalise et valide la requête"""
        
        # Normalisation des entités
        normalized_entities = entities.copy()
        if self.normalizer:
            try:
                normalized_entities = self.normalizer.normalize(entities)
            except Exception as e:
                logger.warning(f"⚠️ Normalisation entités échouée: {e}")
        
        # Nettoyage des paramètres
        clean_params = {}
        for key, value in parameters.items():
            if value is not None and value != "":
                clean_params[key] = value
        
        return CalculationRequest(
            calc_type=calc_type,
            entities=normalized_entities,
            parameters=clean_params,
            target_unit=target_unit
        )
    
    def _post_process_result(
        self, 
        result: CalculationResult, 
        request: CalculationRequest
    ) -> CalculationResult:
        """Post-traitement du résultat"""
        
        # Conversion d'unité si demandée
        if request.target_unit and request.target_unit != result.unit:
            converted_result = self._convert_unit(result, request.target_unit)
            if converted_result:
                result = converted_result
        
        # Ajout métadonnées de traçabilité
        result.metadata.update({
            "calculation_type": request.calc_type.value,
            "input_entities": list(request.entities.keys()),
            "input_parameters": list(request.parameters.keys()),
            "timestamp": logger.handlers[0].formatter.formatTime(logging.LogRecord(
                "", 0, "", 0, "", (), None)) if logger.handlers else "unknown"
        })
        
        return result
    
    def _convert_unit(self, result: CalculationResult, target_unit: str) -> Optional[CalculationResult]:
        """Conversion d'unité si possible"""
        try:
            # Conversions de température
            if result.unit == "°C" and target_unit == "°F":
                new_value = units.c_to_f(float(result.value))
                result.value = round(new_value, 1)
                result.unit = "°F"
                result.assumptions.append(f"Converti de °C vers °F")
                return result
            
            # Conversions de débit
            elif result.unit == "m³/h" and target_unit == "CFM":
                new_value = units.m3h_to_cfm(float(result.value))
                result.value = round(new_value, 1) 
                result.unit = "CFM"
                result.assumptions.append(f"Converti de m³/h vers CFM")
                return result
            
            # Autres conversions...
            logger.debug(f"🔄 Conversion {result.unit} → {target_unit} non implémentée")
            
        except Exception as e:
            logger.warning(f"⚠️ Conversion unité échouée: {e}")
        
        return None
    
    def _error_result(self, message: str) -> CalculationResult:
        """Génère un résultat d'erreur standardisé"""
        return CalculationResult(
            value=None,
            unit="",
            confidence=ConfidenceLevel.UNCERTAIN,
            assumptions=[],
            warnings=[message],
            metadata={"error": True},
            source_formula="error"
        )
    
    # ================== CALCULATION HANDLERS ==================
    
    def _calculate_water(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de consommation d'eau"""
        entities = request.entities
        params = request.parameters
        
        # Extraction paramètres
        effectif = self._get_int_param(entities, params, ["effectif", "flock_size"], 1000)
        age_jours = self._get_int_param(entities, params, ["age_jours", "age_days"], 28)
        temperature = self._get_float_param(params, ["temperature", "temp_C"], 20.0)
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.HIGH
        
        # Hypothèses par défaut
        if "effectif" not in entities and "flock_size" not in params:
            assumptions.append(f"Effectif estimé: {effectif} sujets")
            confidence = ConfidenceLevel.MEDIUM
            
        if "temperature" not in params:
            assumptions.append(f"Température ambiante: {temperature}°C")
            confidence = ConfidenceLevel.MEDIUM
        
        # Calcul via formulas.py
        try:
            water_consumption = conso_eau_j(effectif, age_jours, temperature)
            
            if water_consumption is None:
                raise ValueError("Calcul impossible avec ces paramètres")
            
            # Validation résultat
            if water_consumption < 0:
                warnings.append("Consommation négative détectée")
                confidence = ConfidenceLevel.LOW
            elif water_consumption > effectif * 0.5:  # > 500mL/sujet/jour
                warnings.append("Consommation très élevée, vérifier paramètres")
                confidence = ConfidenceLevel.MEDIUM
                
            return CalculationResult(
                value=round(water_consumption, 1),
                unit="L/jour",
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={"effectif": effectif, "age_jours": age_jours, "temperature": temperature},
                source_formula="conso_eau_j"
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul eau: {e}")
    
    def _calculate_feed(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de consommation d'aliment"""
        entities = request.entities
        params = request.parameters
        
        # Extraction paramètres
        effectif = self._get_int_param(entities, params, ["effectif", "flock_size"], 1000)
        poids_kg = self._get_float_param(entities, params, ["poids_moy_kg", "weight"], 2.0)
        fcr = self._get_float_param(params, ["fcr"], 1.7)
        prix_tonne = self._get_float_param(params, ["prix_aliment_tonne", "feed_price"], 450.0)
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.HIGH
        
        # Gestion des hypothèses
        if "fcr" not in params:
            assumptions.append(f"FCR estimé: {fcr}")
            confidence = ConfidenceLevel.MEDIUM
            
        if "feed_price" not in params:
            assumptions.append(f"Prix aliment: {prix_tonne}€/tonne")
            confidence = ConfidenceLevel.MEDIUM
        
        try:
            # Calcul coût via formulas.py
            cout_kg_vif = cout_aliment_par_kg_vif(prix_tonne, fcr)
            
            if cout_kg_vif is None:
                raise ValueError("Calcul coût impossible")
            
            # Calcul pour le lot
            kg_total = effectif * poids_kg
            cout_total = kg_total * cout_kg_vif
            
            return CalculationResult(
                value=round(cout_total, 2),
                unit="€",
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={
                    "cout_par_kg_vif": round(cout_kg_vif, 3),
                    "kg_total": kg_total,
                    "fcr": fcr,
                    "prix_tonne": prix_tonne
                },
                source_formula="cout_aliment_par_kg_vif"
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul aliment: {e}")
    
    def _calculate_environment(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de paramètres d'ambiance"""
        entities = request.entities
        params = request.parameters
        
        age_jours = self._get_int_param(entities, params, ["age_jours", "age_days"], 28)
        housing = entities.get("housing", "tunnel")
        param_type = params.get("param_type", "temperature")
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.HIGH
        
        try:
            if param_type == "temperature":
                temp = setpoint_temp_C_broiler(age_jours, housing)
                unit = "°C"
                formula = "setpoint_temp_C_broiler"
                
            elif param_type == "humidity":
                temp = setpoint_hr_pct(age_jours)
                unit = "%"
                formula = "setpoint_hr_pct"
                
            elif param_type == "co2":
                temp = co2_max_ppm()
                unit = "ppm"
                formula = "co2_max_ppm"
                
            elif param_type == "lux":
                temp = lux_program_broiler(age_jours)
                unit = "lux"
                formula = "lux_program_broiler"
                
            else:
                return self._error_result(f"Paramètre environnement non supporté: {param_type}")
            
            if housing != "tunnel":
                assumptions.append(f"Valeurs pour élevage {housing}")
                confidence = ConfidenceLevel.MEDIUM
            
            return CalculationResult(
                value=round(temp, 1),
                unit=unit,
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={"age_jours": age_jours, "housing": housing, "param_type": param_type},
                source_formula=formula
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul environnement: {e}")
    
    def _calculate_ventilation(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de ventilation"""
        entities = request.entities
        params = request.parameters
        
        effectif = self._get_int_param(entities, params, ["effectif", "flock_size"], 1000)
        poids_kg = self._get_float_param(entities, params, ["poids_moy_kg", "weight"], 2.0)
        age_jours = self._get_int_param(entities, params, ["age_jours", "age_days"], 28)
        saison = params.get("saison", "hiver")
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.HIGH
        
        try:
            # Calcul débit minimal via formulas.py
            debit_total = vent_min_total_m3h(poids_kg, effectif, age_jours, saison)
            
            if debit_total is None:
                raise ValueError("Calcul débit impossible")
            
            if saison not in ["hiver", "été"]:
                assumptions.append(f"Saison '{saison}' → valeurs hiver par défaut")
                confidence = ConfidenceLevel.MEDIUM
            
            # Conversion CFM si demandé
            debit_cfm = units.m3h_to_cfm(debit_total)
            
            return CalculationResult(
                value=round(debit_total, 0),
                unit="m³/h",
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={
                    "debit_cfm": round(debit_cfm, 0),
                    "debit_par_kg": round(debit_total/(poids_kg*effectif), 2),
                    "saison": saison
                },
                source_formula="vent_min_total_m3h"
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul ventilation: {e}")
    
    def _calculate_equipment(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de dimensionnement équipements"""
        entities = request.entities
        params = request.parameters
        
        effectif = self._get_int_param(entities, params, ["effectif", "flock_size"], 1000)
        age_jours = self._get_int_param(entities, params, ["age_jours", "age_days"], 28)
        equipment_type = params.get("equipment_type", "feeders")
        feeder_type = params.get("feeder_type", "chaîne")
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.HIGH
        
        try:
            if equipment_type == "feeders":
                dimension = dimension_mangeoires(effectif, age_jours, feeder_type)
                unit = "cm"
                formula = "dimension_mangeoires"
                
            elif equipment_type == "drinkers":
                drinker_type = params.get("drinker_type", "nipple")
                dimension = dimension_abreuvoirs(effectif, age_jours, drinker_type)
                unit = "unités" if drinker_type == "nipple" else "cm"
                formula = "dimension_abreuvoirs"
                
            else:
                return self._error_result(f"Type équipement non supporté: {equipment_type}")
            
            if dimension is None:
                raise ValueError("Calcul dimension impossible")
            
            return CalculationResult(
                value=round(dimension, 1),
                unit=unit,
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={
                    "equipment_type": equipment_type,
                    "effectif": effectif,
                    "age_jours": age_jours,
                    "per_bird": round(dimension/effectif, 2) if effectif > 0 else 0
                },
                source_formula=formula
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul équipement: {e}")
    
    def _calculate_economics(self, request: CalculationRequest) -> CalculationResult:
        """Calculs économiques"""
        entities = request.entities
        params = request.parameters
        
        # Paramètres pour IEP
        ep = self._get_float_param(params, ["ep", "production_efficiency"], 85.0)
        survie_pct = self._get_float_param(params, ["survie_pct", "viability"], 95.0)
        fcr = self._get_float_param(params, ["fcr"], 1.7)
        poids_kg = self._get_float_param(entities, params, ["poids_vif_kg", "weight"], 2.0)
        age_jours = self._get_int_param(entities, params, ["age_jours", "age_days"], 42)
        
        assumptions = []
        warnings = []
        confidence = ConfidenceLevel.MEDIUM  # Économie = plus d'hypothèses
        
        # Gestion hypothèses
        if "ep" not in params:
            assumptions.append(f"Efficacité production: {ep}%")
        if "survie_pct" not in params:
            assumptions.append(f"Viabilité: {survie_pct}%")
        if "fcr" not in params:
            assumptions.append(f"FCR: {fcr}")
            
        try:
            # Calcul IEP via formulas.py
            iep_value = iep(ep, survie_pct, fcr, poids_kg, age_jours)
            
            if iep_value is None:
                raise ValueError("Calcul IEP impossible")
            
            # Validation résultat
            if iep_value < 100:
                warnings.append("IEP faible (< 100)")
            elif iep_value > 500:
                warnings.append("IEP très élevé (> 500), vérifier paramètres")
                confidence = ConfidenceLevel.LOW
            
            return CalculationResult(
                value=round(iep_value, 1),
                unit="points",
                confidence=confidence,
                assumptions=assumptions,
                warnings=warnings,
                metadata={
                    "ep": ep,
                    "survie_pct": survie_pct, 
                    "fcr": fcr,
                    "poids_kg": poids_kg,
                    "age_jours": age_jours
                },
                source_formula="iep"
            )
            
        except Exception as e:
            return self._error_result(f"Erreur calcul économique: {e}")
    
    def _calculate_performance(self, request: CalculationRequest) -> CalculationResult:
        """Calculs de performance (alias pour economics)"""
        # La performance utilise les mêmes calculs que l'économie
        return self._calculate_economics(request)
    
    # ================== HELPER METHODS ==================
    
    def _get_int_param(
        self, 
        entities: Dict[str, Any], 
        params: Dict[str, Any], 
        keys: List[str], 
        default: int
    ) -> int:
        """Récupère un paramètre entier depuis entities ou params"""
        for key in keys:
            value = entities.get(key) or params.get(key)
            if value is not None:
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    continue
        return default
    
    def _get_float_param(
        self, 
        entities_or_params: Dict[str, Any], 
        keys: List[str], 
        default: float
    ) -> float:
        """Récupère un paramètre float depuis un dictionnaire"""
        for key in keys:
            value = entities_or_params.get(key)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return default

# ================== PUBLIC API FUNCTIONS ==================

# Instance globale pour utilisation simple
_adapter = CalculatorsAdapter()

def calculate_water(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs d'eau"""
    return _adapter.calculate(CalculationType.WATER, entities, params)

def calculate_feed(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs d'aliment"""
    return _adapter.calculate(CalculationType.FEED, entities, params)

def calculate_environment(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs d'environnement"""
    return _adapter.calculate(CalculationType.ENVIRONMENT, entities, params)

def calculate_ventilation(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs de ventilation"""
    return _adapter.calculate(CalculationType.VENTILATION, entities, params)

def calculate_equipment(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs d'équipement"""
    return _adapter.calculate(CalculationType.EQUIPMENT, entities, params)

def calculate_economics(entities: Dict[str, Any], **params) -> CalculationResult:
    """API simplifiée pour calculs économiques"""
    return _adapter.calculate(CalculationType.ECONOMICS, entities, params)

# Alias pour compatibilité
calculate_performance = calculate_economics

def get_adapter() -> CalculatorsAdapter:
    """Récupère l'instance de l'adaptateur"""
    return _adapter

# ================== EXAMPLE USAGE ==================

if __name__ == "__main__":
    # Test rapide de l'adaptateur
    entities = {"species": "broiler", "age_jours": 35, "effectif": 1000}
    
    # Test calcul eau
    result_water = calculate_water(entities, temperature=25.0)
    print(f"💧 Eau: {result_water.value} {result_water.unit} (confiance: {result_water.confidence.value})")
    
    # Test calcul économie
    result_econ = calculate_economics(entities, fcr=1.6, ep=88.0)
    print(f"💰 IEP: {result_econ.value} {result_econ.unit} (confiance: {result_econ.confidence.value})")
    
    print("\n✅ Calculators Adapter initialisé avec succès !")
