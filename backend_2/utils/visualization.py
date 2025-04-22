from typing import Dict, Any, Optional
import uuid

def generate_visual(visual_type: str, topic_id: str, content: Dict[str, Any], 
                   user_answer: Optional[str] = None) -> Dict[str, Any]:
    """
    Genera datos para visualizaciones basadas en el tipo y contenido
    
    Esta función actúa como un punto de extensión para integrar con 
    herramientas de visualización más avanzadas.
    
    Args:
        visual_type: Tipo de visualización (concept, problem, feedback_conceptual)
        topic_id: ID del tema
        content: Datos del contenido relacionado
        user_answer: Respuesta del usuario (opcional, para feedback)
        
    Returns:
        Datos de visualización en formato adecuado para el frontend
    """
    visual_id = str(uuid.uuid4())
    
    # Estructura base para todos los tipos de visualización
    visual_data = {
        "id": visual_id,
        "type": visual_type,
        "topic_id": topic_id,
        "format": "svg"  # Por defecto usar SVG
    }
    
    # Generar datos específicos según el tipo de visualización
    if visual_type == "concept":
        # Visualización de conceptos teóricos
        visual_data.update({
            "title": content.get("title", "Concepto"),
            "description": content.get("visual_description", ""),
            "elements": content.get("visual_elements", []),
            # Aquí iría la generación o carga del SVG real
            "svg_data": _placeholder_svg(
                title=content.get("title", "Concepto"),
                width=480,
                height=320,
                color="#4A90E2"
            )
        })
        
    elif visual_type == "problem":
        # Visualización de problemas
        visual_data.update({
            "title": content.get("title", "Problema"),
            "description": content.get("visual_description", ""),
            "problem_id": content.get("id", ""),
            "difficulty": content.get("difficulty", 1),
            # Aquí iría la generación o carga del SVG real
            "svg_data": _placeholder_svg(
                title=content.get("title", "Problema"),
                width=480,
                height=320,
                color="#50C878"
            )
        })
        
    elif visual_type == "feedback_conceptual":
        # Visualización para retroalimentación conceptual
        visual_data.update({
            "title": "Retroalimentación conceptual",
            "description": content.get("conceptual_feedback", ""),
            "user_answer": user_answer,
            "correct_approach": content.get("correct_approach", ""),
            # Aquí iría la generación o carga del SVG real
            "svg_data": _placeholder_svg(
                title="Retroalimentación conceptual",
                width=480,
                height=320,
                color="#FF7E79"
            )
        })
    
    else:
        # Tipo desconocido, devolver visualización genérica
        visual_data.update({
            "title": "Visualización",
            "description": "Visualización genérica",
            "svg_data": _placeholder_svg(
                title="Visualización",
                width=400,
                height=300,
                color="#888888"
            )
        })
    
    return visual_data

def _placeholder_svg(title: str, width: int = 400, height: int = 300, 
                    color: str = "#4A90E2") -> str:
    """
    Genera un SVG de placeholder básico
    
    Args:
        title: Título para mostrar
        width: Ancho del SVG
        height: Alto del SVG
        color: Color principal
        
    Returns:
        Contenido SVG en formato string
    """
    # Texto a mostrar (limitar longitud)
    display_text = title if len(title) < 30 else title[:27] + "..."
    
    # Crear SVG básico
    svg = f'''
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#f8f9fa" stroke="{color}" stroke-width="2"/>
        <rect x="10" y="10" width="{width-20}" height="{height-20}" fill="{color}" fill-opacity="0.1" stroke="{color}" stroke-width="1" stroke-dasharray="5,5"/>
        <text x="{width/2}" y="{height/2}" font-family="Arial" font-size="16" fill="{color}" text-anchor="middle">{display_text}</text>
        <text x="{width/2}" y="{height/2 + 24}" font-family="Arial" font-size="12" fill="#666" text-anchor="middle">Visualización educativa</text>
    </svg>
    '''
    
    return svg.strip()

def generate_chart_data(chart_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera datos para gráficos interactivos (para implementación futura)
    
    Args:
        chart_type: Tipo de gráfico (bar, line, pie, etc.)
        data: Datos para el gráfico
        
    Returns:
        Configuración del gráfico para el frontend
    """
    # Esta función es un punto de extensión para integrar 
    # con bibliotecas de gráficos en el frontend (como Chart.js)
    
    return {
        "type": chart_type,
        "data": data,
        "options": {
            "responsive": True,
            "maintainAspectRatio": False
        }
    }