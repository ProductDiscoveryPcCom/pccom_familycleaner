"""
Data Processor Module - CORREGIDO
Maneja el parseo correcto de cada tipo de archivo según su formato real
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from io import StringIO, BytesIO


class DataProcessor:
    """Procesa y normaliza las diferentes fuentes de datos"""
    
    def __init__(self, category_keyword: str = "televisores"):
        self.category_keyword = category_keyword.lower()
        self.category_path = f"/{category_keyword}"
        self.data = {}
        
    # ═══════════════════════════════════════════════════════════════════════════
    # PARSEO DE ARCHIVOS - FORMATO ESPECÍFICO DE CADA FUENTE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def load_filter_usage(self, file_content: str, source_name: str = 'all') -> pd.DataFrame:
        """
        Carga datos de uso de filtros desde Adobe Analytics
        Formato especial: headers con #, luego "faceta:valor,sesiones"
        """
        lines = file_content.split('\n')
        
        # Encontrar donde empiezan los datos reales
        data_start = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(','):
                continue
            # Buscar línea que tenga formato "texto,numero" o "Search Filters"
            if 'Search Filters' in line:
                data_start = i
                break
            parts = line.rsplit(',', 1)
            if len(parts) == 2 and parts[1].strip().replace(',', '').isdigit():
                data_start = i
                break
        
        # Parsear datos
        data = []
        for line in lines[data_start:]:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.rsplit(',', 1)
            if len(parts) == 2:
                filter_name = parts[0].strip()
                try:
                    sessions = int(parts[1].strip().replace(',', ''))
                except:
                    continue
                
                # Parsear tipo de faceta
                facet_type, facet_value = self._parse_filter_name(filter_name)
                
                data.append({
                    'filter_raw': filter_name,
                    'facet_type': facet_type,
                    'facet_value': facet_value,
                    'sessions': sessions
                })
        
        df = pd.DataFrame(data)
        self.data[f'filter_usage_{source_name}'] = df
        return df
    
    def _parse_filter_name(self, filter_name: str) -> Tuple[str, str]:
        """Parsea 'pulgadas:55 pulgadas' -> ('size', '55')"""
        
        if ':' in filter_name:
            parts = filter_name.split(':', 1)
            facet_type_raw = parts[0].strip().lower()
            facet_value = parts[1].strip()
        else:
            facet_type_raw = 'other'
            facet_value = filter_name
        
        # Mapear tipos de faceta al estándar
        type_mapping = {
            'pulgadas': 'size',
            'tamaño': 'size',
            'marcas': 'brand',
            'marca': 'brand',
            'tecnologia': 'technology',
            'tecnología': 'technology',
            'panel': 'technology',
            'conectividad': 'connectivity',
            'precio': 'price',
            'order': 'sorting',
            'ordenar': 'sorting',
            'resolucion': 'resolution',
            'resolución': 'resolution',
            'frecuencia': 'refresh_rate',
            'hz': 'refresh_rate',
            'uso': 'use_case',
            'hdr': 'feature',
            'hdmi': 'feature',
            'oferta': 'offer',
            'ofertas': 'offer',
            'reacondicionado': 'condition',
            'estado': 'condition',
            'search filters': 'total'
        }
        
        facet_type = type_mapping.get(facet_type_raw, facet_type_raw)
        
        # Extraer valor limpio para tamaños
        if facet_type == 'size':
            match = re.search(r'(\d+)', facet_value)
            if match:
                facet_value = match.group(1)
        
        return facet_type, facet_value
    
    def load_top_query(self, df: pd.DataFrame) -> pd.DataFrame:
        """Carga datos de Top Query por URL"""
        df = df.copy()
        df.columns = df.columns.str.strip()
        
        column_mapping = {
            'url': ['url', 'URL', 'page', 'Page', 'página', 'Página'],
            'clicks': ['url_total_clicks', 'Clics', 'clicks', 'Clicks'],
            'impressions': ['url_total_impressions', 'Impresiones', 'impressions'],
            'position': ['url_avg_position', 'Posición', 'position', 'Position'],
            'top_query': ['top_query', 'Top Query', 'top query', 'consulta'],
            'top_query_clicks': ['top_query_clicks', 'query_clicks'],
            'top_query_position': ['top_query_position', 'query_position']
        }
        
        for standard_name, possible_names in column_mapping.items():
            for col in possible_names:
                if col in df.columns and standard_name not in df.columns:
                    df = df.rename(columns={col: standard_name})
                    break
        
        self.data['top_query'] = df
        return df
    
    def load_gsc_queries(self, df: pd.DataFrame) -> pd.DataFrame:
        """Carga consultas de GSC (columnas en español)"""
        df = df.copy()
        
        column_mapping = {
            'Consultas principales': 'query',
            'Clics': 'clicks',
            'Impresiones': 'impressions',
            'CTR': 'ctr',
            'Posición': 'position'
        }
        
        df = df.rename(columns=column_mapping)
        
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        
        self.data['gsc_queries'] = df
        return df
    
    def load_gsc_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Carga páginas de GSC (columnas en español)"""
        df = df.copy()
        
        column_mapping = {
            'Páginas principales': 'url',
            'Clics': 'clicks',
            'Impresiones': 'impressions',
            'CTR': 'ctr',
            'Posición': 'position'
        }
        
        df = df.rename(columns=column_mapping)
        
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        
        self.data['gsc_pages'] = df
        return df
    
    def load_keyword_research(self, file_bytes: bytes) -> pd.DataFrame:
        """Carga Keyword Research (UTF-16 de Google Keyword Planner)"""
        
        # Intentar diferentes encodings
        encodings = ['utf-16', 'utf-16-le', 'utf-8', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                content = file_bytes.decode(encoding)
                # Intentar como TSV primero (formato típico de Keyword Planner)
                df = pd.read_csv(StringIO(content), sep='\t')
                if len(df.columns) > 1:
                    break
                # Si solo hay 1 columna, intentar como CSV
                df = pd.read_csv(StringIO(content))
                if len(df.columns) > 1:
                    break
            except:
                continue
        
        if df is None or len(df.columns) <= 1:
            raise ValueError("No se pudo parsear el archivo de keywords")
        
        # Mapear columnas
        column_mapping = {
            'Keyword': 'keyword',
            'keyword': 'keyword',
            'Palabra clave': 'keyword',
            'Avg. monthly searches': 'volume',
            'Volume': 'volume',
            'Volumen': 'volume',
            'Búsquedas mensuales': 'volume',
            'Competition': 'competition',
            'Competencia': 'competition'
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        if 'volume' in df.columns:
            df['volume'] = df['volume'].apply(self._parse_volume)
        
        self.data['keyword_research'] = df
        return df
    
    def _parse_volume(self, val) -> int:
        """Parsea volúmenes como '1K', '10K' a números"""
        if pd.isna(val):
            return 0
        
        val_str = str(val).upper().strip()
        
        try:
            if 'K' in val_str:
                return int(float(val_str.replace('K', '').replace(',', '.')) * 1000)
            elif 'M' in val_str:
                return int(float(val_str.replace('M', '').replace(',', '.')) * 1000000)
            else:
                return int(float(val_str.replace(',', '').replace(' ', '')))
        except:
            return 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CLASIFICACIÓN DE URLs Y QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def classify_url(self, url: str) -> Dict:
        """Clasifica URL y extrae metadatos"""
        if pd.isna(url):
            return {'type': 'OTHER', 'facets': {}, 'num_facets': 0, 
                    'has_sorting': False, 'has_pagination': False, 'has_price': False}
        
        url_lower = url.lower()
        keyword = self.category_keyword
        
        result = {
            'type': 'OTHER',
            'facets': {},
            'num_facets': 0,
            'has_sorting': '?order=' in url_lower or '&order=' in url_lower,
            'has_pagination': '?page=' in url_lower or '&page=' in url_lower,
            'has_price': 'precio=' in url_lower or 'price=' in url_lower
        }
        
        # URLs con parámetros problemáticos = FILTER_NOINDEX
        if result['has_sorting'] or result['has_pagination'] or result['has_price']:
            result['type'] = 'FILTER_NOINDEX'
            return result
        
        # Categoría principal
        if url_lower.endswith(f'/{keyword}') or url_lower.endswith(f'/{keyword}/'):
            result['type'] = 'CATEGORY'
            return result
        
        # Filtros
        if f'/{keyword}/' in url_lower:
            if re.search(r'/[a-z0-9-]+-\d{5,}', url_lower):
                result['type'] = 'PRODUCT'
                return result
            
            result['type'] = 'FILTER'
            result['facets'] = self._extract_facets_from_url(url)
            result['num_facets'] = sum(1 for v in result['facets'].values() if v is not None)
            return result
        
        # Artículos
        if keyword in url_lower or keyword[:-1] in url_lower:
            result['type'] = 'ARTICLE'
            return result
        
        return result
    
    def _extract_facets_from_url(self, url: str) -> Dict:
        """Extrae facetas de una URL de filtro"""
        facets = {k: None for k in ['size', 'brand', 'technology', 'feature', 
                                     'condition', 'use_case', 'connectivity']}
        
        url_lower = url.lower()
        
        # Tamaño
        size_match = re.search(r'/(\d{2,3})-pulgadas', url_lower)
        if size_match:
            facets['size'] = size_match.group(1)
        
        # Marca
        brands = ['samsung', 'lg', 'sony', 'philips', 'tcl', 'hisense', 
                  'xiaomi', 'nilait', 'tesla', 'panasonic', 'sharp', 'toshiba']
        for brand in brands:
            if f'/{brand}' in url_lower:
                facets['brand'] = brand
                break
        
        # Tecnología
        techs = {'oled': 'oled', 'qled': 'qled', 'qned': 'qned',
                 'mini-led': 'mini-led', 'miniled': 'mini-led',
                 'nanocell': 'nanocell', 'neo-qled': 'neo-qled', 'ambilight': 'ambilight'}
        for tech_url, tech_name in techs.items():
            if f'/{tech_url}' in url_lower:
                facets['technology'] = tech_name
                break
        
        # Conectividad
        for conn in ['smart-tv', 'android-tv', 'google-tv']:
            if f'/{conn}' in url_lower:
                facets['connectivity'] = conn
                break
        
        # Features
        if '/120-hz' in url_lower or '/120hz' in url_lower:
            facets['feature'] = '120hz'
        elif '/hdmi-2-1' in url_lower:
            facets['feature'] = 'hdmi-2.1'
        
        # Condición
        if '/reacondicionado' in url_lower:
            facets['condition'] = 'reacondicionado'
        elif '/ofertas' in url_lower:
            facets['condition'] = 'ofertas'
        
        # Uso
        if '/gaming' in url_lower:
            facets['use_case'] = 'gaming'
        
        return facets
    
    def classify_query_intent(self, query: str) -> str:
        """Clasifica intención: INFORMATIONAL, TRANSACTIONAL, NAVIGATIONAL"""
        if pd.isna(query):
            return 'OTHER'
        
        query_lower = query.lower().strip()
        
        # Navegacional
        for nav in ['pccomponentes', 'pcc', 'mediamarkt', 'amazon', 'el corte ingles']:
            if nav in query_lower:
                return 'NAVIGATIONAL'
        
        # Informacional
        info_markers = [
            'mejor', 'mejores', 'top', 'ranking', 'cual', 'cuál', 
            'que es', 'qué es', 'diferencia', 'vs', 'versus', 'comparativa',
            'guia', 'guía', 'como', 'cómo', 'elegir', 'recomend', 'opinion',
            'review', 'análisis', 'vale la pena', 'calidad precio',
            'medidas', 'dimensiones', 'pulgadas a cm', '2024', '2025', '2026'
        ]
        
        for marker in info_markers:
            if marker in query_lower:
                return 'INFORMATIONAL'
        
        return 'TRANSACTIONAL'
    
    def suggest_filter_url(self, query: str) -> str:
        """Sugiere URL de filtro para query transaccional"""
        if not query:
            return f"/{self.category_keyword}"
        
        query_lower = query.lower()
        parts = [f"/{self.category_keyword}"]
        
        # 1. Tamaño (prioridad 1)
        size_match = re.search(r'(\d{2,3})\s*(pulgadas|")?', query_lower)
        if size_match:
            parts.append(f"{size_match.group(1)}-pulgadas")
        
        # 2. Tecnología (prioridad 2)
        tech_map = [('oled', 'oled'), ('qled', 'qled'), ('mini led', 'mini-led'),
                    ('smart tv', 'smart-tv'), ('android tv', 'android-tv')]
        for pattern, url_part in tech_map:
            if pattern in query_lower:
                parts.append(url_part)
                break
        
        # 3. Marca (prioridad 3)
        for brand in ['samsung', 'lg', 'sony', 'philips', 'tcl', 'hisense', 'xiaomi', 'nilait']:
            if brand in query_lower:
                parts.append(brand)
                break
        
        # 4. Features
        if '120hz' in query_lower or '120 hz' in query_lower:
            parts.append('120-hz')
        
        # 5. Uso
        if any(x in query_lower for x in ['gaming', 'ps5', 'xbox', 'jugar']):
            if 'gaming' not in str(parts):
                parts.append('gaming')
        
        return '/'.join(parts)


class AnalysisResults:
    """Contenedor para resultados de análisis"""
    
    def __init__(self):
        self.url_classification = pd.DataFrame()
        self.cannibalization = pd.DataFrame()
        self.gaps = pd.DataFrame()
        self.facet_usage = pd.DataFrame()
        self.facet_performance = pd.DataFrame()
        self.ux_seo_matrix = pd.DataFrame()
        self.indexation_audit = pd.DataFrame()
        self.recommendations = []
        self.summary = {}
        self.facet_priority_order = []
