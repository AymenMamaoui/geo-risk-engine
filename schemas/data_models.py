from pydantic import BaseModel, Field
from typing import List, Optional

# SCHÉMAS MÉTÉOROLOGIQUES (Extraction et Analyse)

class ZoneDetail(BaseModel):
    seuil_specifique: Optional[str] = None
    provinces: List[str]
    date_debut: str
    date_fin: str

class AlerteMeteo(BaseModel):
    niveau_vigilance: str = Field(..., description="Niveau de vigilance (ex: rouge, orange)")
    seuil_global: Optional[str] = Field(None, description="Seuil global associé à l'alerte")
    details_zones: List[ZoneDetail] = Field(..., description="Détails des provinces et dates associées à ce niveau de vigilance")

class Phenomene(BaseModel):
    type_phenomene: str
    alertes: List[AlerteMeteo]

class MeteoRawExtraction(BaseModel):
    id_bulletin: Optional[float] = None
    phenomenes: List[Phenomene]

# Schéma d'analyse de risque météo
class ZoneRisqueMeteo(BaseModel):
    province: str
    niveau_vigilance_dgm: str
    niveau_severite_agent: str = Field(..., enum=["CRITIQUE", "HAUT"])
    phenomene_declencheur: str
    date_debut: str
    date_fin: str
    justification: str

class MeteoAnalysisReport(BaseModel):
    id_bulletin: Optional[float] = Field(None, description="L'ID du bulletin DGM ayant généré cette analyse")
    zones_urgentes: List[ZoneRisqueMeteo]


# SCHÉMAS HYDRAULIQUES (Barrages et Oueds)

class Barrage(BaseModel):
    nom_barrage: str
    capacite_normale_mm3: Optional[float] = None
    reserve_actuelle_mm3: Optional[float] = None
    taux_remplissage_pourcentage: float

class Oued(BaseModel):
    nom_oued: str
    debit_m3s: Optional[float] = None
    niveau_vigilance: str

class HydrauliqueRawExtraction(BaseModel):
    date_situation: Optional[str] = None
    taux_remplissage_global: Optional[float] = None
    barrages: List[Barrage]
    oueds: List[Oued]


class OuedAlerte(BaseModel):
    nom_oued: str
    debit_actuel_m3_s: Optional[float] = None
    niveau_vigilance: Optional[str] = None

class HydrauliqueOuedsExtraction(BaseModel):
    date_alerte_oued: Optional[str] = None
    agence_bassin: Optional[str] = None
    alertes_oueds: List[OuedAlerte]

# Schéma d'analyse de risque hydraulique
class RisqueHydraulique(BaseModel):
    infrastructure_concernee: str
    type_infrastructure: str = Field(..., enum=["BARRAGE", "OUED"])
    indicateur_critique: str
    niveau_severite_agent: str = Field(..., enum=["CRITIQUE", "HAUT", "MODERE", "FAIBLE"])
    justification: str

class HydrauliqueAnalysisReport(BaseModel):
    risques_hydrauliques: List[RisqueHydraulique]


# SCHÉMA DE L'ORCHESTRATEUR (La Synthèse Finale)

class ConfluenceRisque(BaseModel):
    localisation_impactee: str
    niveau_alerte_combine: str = Field(..., enum=["URGENCE NOIRE", "ALERTE ROUGE", "VIGILANCE ORANGE"])
    synthese_decisionnelle: str
    recommandations_terrain: str

class GeoRiskReport(BaseModel):
    confluences_risques_majeurs: List[ConfluenceRisque]