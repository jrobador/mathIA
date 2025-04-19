"""
Define las rutas de aprendizaje (roadmaps) para diferentes temas matemáticos.
Cada roadmap contiene la secuencia de temas y los requisitos para avanzar.
"""

from typing import Dict, List, Any, Optional

class RoadmapTopic:
    """
    Representa un tema dentro de una ruta de aprendizaje.
    """
    def __init__(
        self, 
        id: str, 
        title: str, 
        description: str,
        cpa_phases: List[str] = ["Concrete", "Pictorial", "Abstract"],
        prerequisites: List[str] = None,
        required_mastery: float = 0.8,
        practice_problems_min: int = 3,
        subtopics: Optional[List[str]] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.cpa_phases = cpa_phases
        self.prerequisites = prerequisites or []
        self.required_mastery = required_mastery
        self.practice_problems_min = practice_problems_min
        self.subtopics = subtopics or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el tema a un diccionario."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cpa_phases": self.cpa_phases,
            "prerequisites": self.prerequisites,
            "required_mastery": self.required_mastery,
            "practice_problems_min": self.practice_problems_min,
            "subtopics": self.subtopics
        }

class LearningRoadmap:
    """
    Define una ruta de aprendizaje completa con una secuencia de temas.
    """
    def __init__(self, id: str, title: str, description: str, topics: List[RoadmapTopic]):
        self.id = id
        self.title = title
        self.description = description
        self.topics = topics
    
    def get_topic_ids(self) -> List[str]:
        """Retorna la lista de IDs de temas en la ruta."""
        return [topic.id for topic in self.topics]
    
    def get_topic_by_id(self, topic_id: str) -> Optional[RoadmapTopic]:
        """Busca un tema por su ID."""
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None
    
    def get_next_topic(self, current_topic_id: str) -> Optional[RoadmapTopic]:
        """Obtiene el siguiente tema en la secuencia."""
        topic_ids = self.get_topic_ids()
        try:
            current_index = topic_ids.index(current_topic_id)
            if current_index < len(topic_ids) - 1:
                next_id = topic_ids[current_index + 1]
                return self.get_topic_by_id(next_id)
        except ValueError:
            pass
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la ruta a un diccionario."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "topics": [topic.to_dict() for topic in self.topics]
        }

# ----- Definición de Roadmaps -----

# Roadmap de Fracciones
fractions_roadmap = LearningRoadmap(
    id="fractions",
    title="Fracciones",
    description="Aprende sobre fracciones, desde los conceptos básicos hasta operaciones avanzadas.",
    topics=[
        RoadmapTopic(
            id="fractions_introduction",
            title="Introducción a las Fracciones",
            description="Qué son las fracciones y cómo representan partes de un todo.",
            subtopics=["Concepto de fracción", "Numerador y denominador", "Representación visual"]
        ),
        RoadmapTopic(
            id="fractions_equivalent",
            title="Fracciones Equivalentes",
            description="Cómo identificar y crear fracciones equivalentes.",
            prerequisites=["fractions_introduction"],
            subtopics=["Simplificación", "Amplificación", "Comparación de fracciones"]
        ),
        RoadmapTopic(
            id="fractions_comparison",
            title="Comparación de Fracciones",
            description="Cómo comparar fracciones y ordenarlas.",
            prerequisites=["fractions_equivalent"],
            subtopics=["Común denominador", "Método de cruz", "Comparación con referentes"]
        ),
        RoadmapTopic(
            id="fractions_addition",
            title="Suma de Fracciones",
            description="Cómo sumar fracciones con igual y distinto denominador.",
            prerequisites=["fractions_equivalent", "fractions_comparison"],
            subtopics=["Mismo denominador", "Distinto denominador", "Fracciones mixtas"]
        ),
        RoadmapTopic(
            id="fractions_subtraction",
            title="Resta de Fracciones",
            description="Cómo restar fracciones con igual y distinto denominador.",
            prerequisites=["fractions_addition"],
            subtopics=["Mismo denominador", "Distinto denominador", "Fracciones mixtas"]
        ),
        RoadmapTopic(
            id="fractions_multiplication",
            title="Multiplicación de Fracciones",
            description="Cómo multiplicar fracciones y números mixtos.",
            prerequisites=["fractions_subtraction"],
            subtopics=["Multiplicación directa", "Con números enteros", "Con números mixtos"]
        ),
        RoadmapTopic(
            id="fractions_division",
            title="División de Fracciones",
            description="Cómo dividir fracciones y números mixtos.",
            prerequisites=["fractions_multiplication"],
            subtopics=["Recíproco o inverso", "División por enteros", "División de números mixtos"]
        )
    ]
)

# Roadmap de Suma
addition_roadmap = LearningRoadmap(
    id="addition",
    title="Suma",
    description="Aprende a sumar, desde conceptos básicos hasta sumas con llevadas y múltiples dígitos.",
    topics=[
        RoadmapTopic(
            id="addition_introduction",
            title="Introducción a la Suma",
            description="Qué significa sumar y cómo combinar cantidades.",
            subtopics=["Concepto de adición", "Signos y símbolos", "Propiedades básicas"]
        ),
        RoadmapTopic(
            id="addition_single_digit",
            title="Suma de Un Dígito",
            description="Cómo sumar números de un solo dígito de manera fluida.",
            prerequisites=["addition_introduction"],
            subtopics=["Combinaciones básicas", "Estrategias mentales", "Hechos numéricos"]
        ),
        RoadmapTopic(
            id="addition_double_digit",
            title="Suma de Dos Dígitos",
            description="Cómo sumar números de dos dígitos sin llevada.",
            prerequisites=["addition_single_digit"],
            subtopics=["Valor posicional", "Método vertical", "Estimación"]
        ),
        RoadmapTopic(
            id="addition_carrying",
            title="Suma con Llevada",
            description="Cómo sumar números cuando la suma de una columna es mayor a 9.",
            prerequisites=["addition_double_digit"],
            subtopics=["Concepto de llevada", "Método paso a paso", "Aplicaciones prácticas"]
        ),
        RoadmapTopic(
            id="addition_multiple_digit",
            title="Suma de Múltiples Dígitos",
            description="Cómo sumar números grandes de manera eficiente.",
            prerequisites=["addition_carrying"],
            subtopics=["Alineación de columnas", "Llevadas múltiples", "Estimación de resultados"]
        ),
        RoadmapTopic(
            id="addition_mental",
            title="Suma Mental",
            description="Estrategias para sumar mentalmente con rapidez.",
            prerequisites=["addition_multiple_digit"],
            subtopics=["Descomposición", "Redondeo", "Compensación"]
        ),
        RoadmapTopic(
            id="addition_word_problems",
            title="Problemas Verbales de Suma",
            description="Cómo aplicar la suma para resolver problemas prácticos.",
            prerequisites=["addition_mental"],
            subtopics=["Identificación de operaciones", "Estrategias de solución", "Verificación de resultados"]
        )
    ]
)

# Roadmap de Resta
subtraction_roadmap = LearningRoadmap(
    id="subtraction",
    title="Resta",
    description="Aprende a restar, desde conceptos básicos hasta restas con llevadas y múltiples dígitos.",
    topics=[
        RoadmapTopic(
            id="subtraction_introduction",
            title="Introducción a la Resta",
            description="Qué significa restar y cómo quitar cantidades.",
            subtopics=["Concepto de sustracción", "Signos y símbolos", "Relación con la suma"]
        ),
        RoadmapTopic(
            id="subtraction_single_digit",
            title="Resta de Un Dígito",
            description="Cómo restar números de un solo dígito con fluidez.",
            prerequisites=["subtraction_introduction"],
            subtopics=["Combinaciones básicas", "Estrategias mentales", "Hechos numéricos"]
        ),
        RoadmapTopic(
            id="subtraction_double_digit",
            title="Resta de Dos Dígitos",
            description="Cómo restar números de dos dígitos sin préstamo.",
            prerequisites=["subtraction_single_digit"],
            subtopics=["Valor posicional", "Método vertical", "Estimación"]
        ),
        RoadmapTopic(
            id="subtraction_borrowing",
            title="Resta con Préstamo",
            description="Cómo restar cuando el número de arriba es menor que el de abajo.",
            prerequisites=["subtraction_double_digit"],
            subtopics=["Concepto de préstamo", "Método paso a paso", "Verificación"]
        ),
        RoadmapTopic(
            id="subtraction_multiple_digit",
            title="Resta de Múltiples Dígitos",
            description="Cómo restar números grandes de manera eficiente.",
            prerequisites=["subtraction_borrowing"],
            subtopics=["Alineación de columnas", "Préstamos múltiples", "Estimación de resultados"]
        ),
        RoadmapTopic(
            id="subtraction_mental",
            title="Resta Mental",
            description="Estrategias para restar mentalmente con rapidez.",
            prerequisites=["subtraction_multiple_digit"],
            subtopics=["Descomposición", "Redondeo", "Método de complemento"]
        ),
        RoadmapTopic(
            id="subtraction_word_problems",
            title="Problemas Verbales de Resta",
            description="Cómo aplicar la resta para resolver problemas prácticos.",
            prerequisites=["subtraction_mental"],
            subtopics=["Identificación de operaciones", "Estrategias de solución", "Verificación de resultados"]
        )
    ]
)

# Roadmap de Multiplicación
multiplication_roadmap = LearningRoadmap(
    id="multiplication",
    title="Multiplicación",
    description="Aprende a multiplicar, desde conceptos básicos hasta multiplicaciones con múltiples dígitos.",
    topics=[
        RoadmapTopic(
            id="multiplication_introduction",
            title="Introducción a la Multiplicación",
            description="Qué significa multiplicar y su relación con la suma repetida.",
            subtopics=["Concepto de multiplicación", "Signos y símbolos", "Suma repetida"]
        ),
        RoadmapTopic(
            id="multiplication_tables",
            title="Tablas de Multiplicar",
            description="Cómo aprender y recordar las tablas de multiplicar.",
            prerequisites=["multiplication_introduction"],
            subtopics=["Tablas del 1 al 5", "Tablas del 6 al 10", "Patrones y trucos"]
        ),
        RoadmapTopic(
            id="multiplication_single_digit",
            title="Multiplicación por Un Dígito",
            description="Cómo multiplicar un número de varios dígitos por uno de un dígito.",
            prerequisites=["multiplication_tables"],
            subtopics=["Método vertical", "Llevadas", "Estimación"]
        ),
        RoadmapTopic(
            id="multiplication_double_digit",
            title="Multiplicación por Dos Dígitos",
            description="Cómo multiplicar cuando ambos factores tienen dos o más dígitos.",
            prerequisites=["multiplication_single_digit"],
            subtopics=["Método vertical extendido", "Productos parciales", "Verificación"]
        ),
        RoadmapTopic(
            id="multiplication_mental",
            title="Multiplicación Mental",
            description="Estrategias para multiplicar mentalmente con rapidez.",
            prerequisites=["multiplication_double_digit"],
            subtopics=["Descomposición", "Uso de múltiplos de 10", "Propiedades"]
        ),
        RoadmapTopic(
            id="multiplication_word_problems",
            title="Problemas Verbales de Multiplicación",
            description="Cómo aplicar la multiplicación para resolver problemas prácticos.",
            prerequisites=["multiplication_mental"],
            subtopics=["Identificación de situaciones", "Estrategias de solución", "Verificación de resultados"]
        )
    ]
)

# Roadmap de División
division_roadmap = LearningRoadmap(
    id="division",
    title="División",
    description="Aprende a dividir, desde conceptos básicos hasta divisiones con múltiples dígitos.",
    topics=[
        RoadmapTopic(
            id="division_introduction",
            title="Introducción a la División",
            description="Qué significa dividir y su relación con la multiplicación.",
            subtopics=["Concepto de división", "Signos y símbolos", "Partes de la división"]
        ),
        RoadmapTopic(
            id="division_basic",
            title="División Básica",
            description="Cómo dividir usando las tablas de multiplicar.",
            prerequisites=["division_introduction"],
            subtopics=["Divisiones exactas", "Relación con multiplicación", "Verificación"]
        ),
        RoadmapTopic(
            id="division_single_digit",
            title="División por Un Dígito",
            description="Cómo dividir números por un divisor de un dígito.",
            prerequisites=["division_basic"],
            subtopics=["Algoritmo de división", "División con resto", "Estimación"]
        ),
        RoadmapTopic(
            id="division_double_digit",
            title="División por Dos Dígitos",
            description="Cómo dividir números por divisores de dos o más dígitos.",
            prerequisites=["division_single_digit"],
            subtopics=["Algoritmo extendido", "Estimación de cocientes", "Verificación"]
        ),
        RoadmapTopic(
            id="division_decimal",
            title="División con Decimales",
            description="Cómo dividir cuando hay decimales en el dividendo o divisor.",
            prerequisites=["division_double_digit"],
            subtopics=["Desplazamiento decimal", "División decimal", "Aproximaciones"]
        ),
        RoadmapTopic(
            id="division_word_problems",
            title="Problemas Verbales de División",
            description="Cómo aplicar la división para resolver problemas prácticos.",
            prerequisites=["division_decimal"],
            subtopics=["Identificación de situaciones", "Estrategias de solución", "Verificación de resultados"]
        )
    ]
)

# Diccionario de roadmaps disponibles
AVAILABLE_ROADMAPS = {
    "fractions": fractions_roadmap,
    "addition": addition_roadmap,
    "subtraction": subtraction_roadmap,
    "multiplication": multiplication_roadmap,
    "division": division_roadmap
}

def get_roadmap(roadmap_id: str) -> Optional[LearningRoadmap]:
    """
    Obtiene un roadmap por su ID.
    
    Args:
        roadmap_id: ID del roadmap a obtener
    
    Returns:
        LearningRoadmap o None si no existe
    """
    return AVAILABLE_ROADMAPS.get(roadmap_id)

def get_topic_sequence(roadmap_id: str) -> List[str]:
    """
    Obtiene la secuencia de temas para un roadmap específico.
    
    Args:
        roadmap_id: ID del roadmap
        
    Returns:
        Lista de IDs de temas en orden secuencial
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        return roadmap.get_topic_ids()
    return []

def get_next_topic_id(roadmap_id: str, current_topic_id: str) -> Optional[str]:
    """
    Obtiene el ID del siguiente tema en el roadmap.
    
    Args:
        roadmap_id: ID del roadmap
        current_topic_id: ID del tema actual
    
    Returns:
        ID del siguiente tema o None si es el último
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        next_topic = roadmap.get_next_topic(current_topic_id)
        if next_topic:
            return next_topic.id
    return None

def get_all_roadmaps_info() -> List[Dict[str, Any]]:
    """
    Retorna información básica de todos los roadmaps disponibles.
    
    Returns:
        Lista de diccionarios con información sobre cada roadmap
    """
    return [
        {
            "id": roadmap_id,
            "title": roadmap.title,
            "description": roadmap.description,
            "topic_count": len(roadmap.topics)
        }
        for roadmap_id, roadmap in AVAILABLE_ROADMAPS.items()
    ]

def get_roadmap_topic_info(roadmap_id: str, topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene información detallada sobre un tema específico.
    
    Args:
        roadmap_id: ID del roadmap
        topic_id: ID del tema
    
    Returns:
        Diccionario con información del tema o None si no existe
    """
    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return None
    
    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return None
    
    # Convertir el tema a diccionario
    topic_info = topic.to_dict()
    
    # Añadir información sobre los requisitos previos
    if topic.prerequisites:
        topic_info['prerequisite_topics'] = []
        for prereq_id in topic.prerequisites:
            prereq_topic = roadmap.get_topic_by_id(prereq_id)
            if prereq_topic:
                topic_info['prerequisite_topics'].append({
                    'id': prereq_id,
                    'title': prereq_topic.title
                })
    
    # Añadir información sobre el siguiente tema
    next_topic = roadmap.get_next_topic(topic_id)
    if next_topic:
        topic_info['next_topic'] = {
            'id': next_topic.id,
            'title': next_topic.title
        }
    
    return topic_info