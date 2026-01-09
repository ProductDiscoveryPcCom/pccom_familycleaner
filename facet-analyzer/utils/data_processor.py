"""
Data Processor Module - GENÉRICO v2
Maneja el parseo correcto de cada tipo de archivo según su formato real
Funciona con CUALQUIER categoría sin mapeos hardcodeados
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
        
    def load_filter_usage(self, file_content: str, source_name: str = 'all') -> pd.DataFrame:
        """Carga datos de uso de filtros desde Adobe Analytics"""
        lines = file_content.split('\n')
        
        data_start = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(','):
                continue
            if 'Search Filters' in line:
                data_start = i
                break
            parts = line.rsplit(',', 1)
            if len(parts) == 2 and parts[1].strip().replace(',', '').isdigit():
                data_start = i
                break
        
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
        """Parsea 'tipo:valor' -> ('tipo_normalizado', 'valor')
        
        GENÉRICO: Usa el nombre original del CSV, solo normaliza tipos de sistema
        """
        
        if ':' in filter_name:
            parts = filter_name.split(':', 1)
            facet_type_raw = parts[0].strip().lower()
            facet_value = parts[1].strip()
        else:
            facet_type_raw = 'other'
            facet_value = filter_name
        
        # Solo normalizar tipos de SISTEMA (no de producto)
        system_types = {
            'order': 'sorting', 'ordenar': 'sorting', 'ordenar por': 'sorting',
            'search filters': 'total', 'page full url': 'total'
        }
        
        facet_type = system_types.get(facet_type_raw, facet_type_raw)
        
        # Normalizar: quitar acentos y espacios para consistencia interna
        facet_type = self._normalize_string(facet_type)
        
        return facet_type, facet_value
    
    def _normalize_string(self, text: str) -> str:
        """Normaliza string: quitar acentos, espacios por guiones bajos"""
        normalized = text.replace(' ', '_').replace('-', '_')
        accent_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
            'ã': 'a', 'õ': 'o', 'ñ': 'n', 'ç': 'c'
        }
        for accented, plain in accent_map.items():
            normalized = normalized.replace(accented, plain)
        return normalized.lower()
    
    def load_filter_usage_url(self, file_content: str, source_name: str = 'all') -> pd.DataFrame:
        """Carga datos de uso de filtros desde Adobe Analytics - Formato Page Full URL"""
        lines = file_content.split('\n')
        
        data_start = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if 'Page Full URL' in line and ',' in line:
                data_start = i
                break
        
        data = []
        for line in lines[data_start:]:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '(Low Traffic)' in line or 'Unspecified' in line:
                continue
            
            parts = line.rsplit(',', 1)
            if len(parts) == 2:
                url = parts[0].strip()
                try:
                    sessions = int(parts[1].strip().replace(',', ''))
                except:
                    continue
                
                if self.category_keyword not in url.lower():
                    continue
                
                url_info = self.classify_url(url)
                
                facet_type = 'category'
                facet_value = self.category_keyword
                
                if url_info['facets']:
                    for ft, fv in url_info['facets'].items():
                        if fv:
                            facet_type = ft
                            facet_value = fv
                            break
                
                data.append({
                    'url': url,
                    'facet_type': facet_type,
                    'facet_value': facet_value,
                    'sessions': sessions,
                    'num_facets': url_info['num_facets'],
                    'has_price': url_info['has_price']
                })
        
        df = pd.DataFrame(data)
        self.data[f'filter_usage_url_{source_name}'] = df
        return df
    
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
        """Carga consultas de GSC"""
        df = df.copy()
        column_mapping = {
            'Consultas principales': 'query', 'Clics': 'clicks',
            'Impresiones': 'impressions', 'CTR': 'ctr', 'Posición': 'position'
        }
        df = df.rename(columns=column_mapping)
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        self.data['gsc_queries'] = df
        return df
    
    def load_gsc_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Carga páginas de GSC"""
        df = df.copy()
        column_mapping = {
            'Páginas principales': 'url', 'Clics': 'clicks',
            'Impresiones': 'impressions', 'CTR': 'ctr', 'Posición': 'position'
        }
        df = df.rename(columns=column_mapping)
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        self.data['gsc_pages'] = df
        return df
    
    def load_keyword_research(self, file_bytes: bytes) -> pd.DataFrame:
        """Carga Keyword Research"""
        encodings = ['utf-16', 'utf-16-le', 'utf-8', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                content = file_bytes.decode(encoding)
                df = pd.read_csv(StringIO(content), sep='\t')
                if len(df.columns) > 1:
                    break
                df = pd.read_csv(StringIO(content))
                if len(df.columns) > 1:
                    break
            except:
                continue
        
        if df is None or len(df.columns) <= 1:
            raise ValueError("No se pudo parsear el archivo de keywords")
        
        column_mapping = {
            'Keyword': 'keyword', 'keyword': 'keyword', 'Palabra clave': 'keyword',
            'Avg. monthly searches': 'volume', 'Volume': 'volume', 'Volumen': 'volume',
            'Búsquedas mensuales': 'volume', 'Competition': 'competition', 'Competencia': 'competition'
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
    
    def load_screaming_frog(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Carga datos de Screaming Frog Internal HTML con integración GSC
        
        Columnas esperadas (Screaming Frog en español):
        - Dirección: URL
        - Indexabilidad: Estado de indexación
        - Clics, Impresiones, Posición: Datos GSC
        - Recuento de palabras: Contenido
        - Nivel de profundidad: Arquitectura
        - Enlaces internos únicos: Link juice
        - Productos (extracción personalizada, opcional)
        """
        df = df.copy()
        
        # Mapeo de columnas (español -> interno)
        column_mapping = {
            'Dirección': 'url',
            'Indexabilidad': 'indexability',
            'Estado de indexabilidad': 'indexability_status',
            'Clics': 'clicks',
            'Impresiones': 'impressions',
            'Posición': 'position',
            'Porcentaje de clics': 'ctr',
            'Recuento de palabras': 'word_count',
            'Nivel de profundidad': 'depth',
            'Profundidad de carpeta': 'folder_depth',
            'Enlaces internos únicos': 'internal_links',
            'Link Score': 'link_score',
            '% del total': 'pct_total_links',
            'Título 1': 'title',
            'Meta description 1': 'meta_description',
            'H1-1': 'h1',
            'Meta robots 1': 'meta_robots',
            'Elemento de enlace canónico 1': 'canonical',
            'Código de respuesta': 'status_code'
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Filtrar solo URLs de la categoría
        if 'url' in df.columns:
            df = df[df['url'].str.contains(self.category_keyword, case=False, na=False)].copy()
        
        # Convertir columnas numéricas
        numeric_cols = ['clicks', 'impressions', 'word_count', 'depth', 'internal_links', 'link_score']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Parsear posición (formato español: "2,7" -> 2.7)
        if 'position' in df.columns:
            df['position'] = df['position'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
        
        # Calcular nivel de facetas desde la URL
        def get_facet_level(url):
            if pd.isna(url):
                return -1
            url = str(url).lower()
            if self.category_keyword not in url:
                return -1
            parts = url.split(f'/{self.category_keyword}')
            if len(parts) < 2:
                return 0
            path = parts[1].split('?')[0].strip('/')
            if not path:
                return 0
            return len([s for s in path.split('/') if s])
        
        df['facet_level'] = df['url'].apply(get_facet_level)
        
        # Detectar si hay extracción personalizada de productos
        product_cols = ['Productos', 'productos', 'Products', 'product_count', 'Total productos']
        for col in product_cols:
            if col in df.columns:
                df['product_count'] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                break
        
        self.data['screaming_frog'] = df
        return df
    
    def classify_url(self, url: str) -> Dict:
        """Clasifica URL y extrae metadatos - GENÉRICO
        
        Lógica de clasificación:
        - TRANSACTIONAL (PLP): URLs que contienen /{categoria}/ o terminan en /{categoria}
        - INFORMATIONAL: Contenido del blog/editorial que NO está bajo /{categoria}/
        - PRODUCT: URLs de producto (detectadas por ID numérico)
        """
        if pd.isna(url):
            return {'type': 'OTHER', 'facets': {}, 'num_facets': 0, 
                    'has_sorting': False, 'has_pagination': False, 'has_price': False,
                    'content_type': 'OTHER', 'funnel_stage': 'OTHER'}
        
        url_lower = url.lower()
        keyword = self.category_keyword
        
        # Generar variaciones del keyword para detectar contenido informacional
        # Ej: "smartphone-moviles" -> ["smartphone", "moviles", "movil", "telefono"]
        keyword_variations = self._get_keyword_variations(keyword)
        
        result = {
            'type': 'OTHER',
            'facets': {},
            'num_facets': 0,
            'has_sorting': '?order=' in url_lower or '&order=' in url_lower,
            'has_pagination': '?page=' in url_lower or '&page=' in url_lower,
            'has_price': 'precio=' in url_lower or 'price=' in url_lower,
            'content_type': 'OTHER',  # TRANSACTIONAL, INFORMATIONAL, PRODUCT
            'funnel_stage': 'OTHER'   # TOFU, MOFU, BOFU
        }
        
        # Detectar parámetros que hacen la URL no indexable
        if result['has_sorting'] or result['has_pagination'] or result['has_price']:
            result['type'] = 'FILTER_NOINDEX'
            result['content_type'] = 'TRANSACTIONAL'
            return result
        
        # ═══════════════════════════════════════════════════════════════════════
        # CONTENIDO TRANSACCIONAL: bajo /{categoria}/
        # ═══════════════════════════════════════════════════════════════════════
        
        # Categoría raíz: termina en /{categoria} o /{categoria}/
        if url_lower.endswith(f'/{keyword}') or url_lower.endswith(f'/{keyword}/'):
            result['type'] = 'CATEGORY'
            result['content_type'] = 'TRANSACTIONAL'
            result['funnel_stage'] = 'BOFU'
            return result
        
        # URLs bajo /{categoria}/...
        if f'/{keyword}/' in url_lower:
            # Detectar producto por ID numérico largo (ej: samsung-galaxy-s24-123456)
            if re.search(r'/[a-z0-9-]+-\d{5,}', url_lower):
                result['type'] = 'PRODUCT'
                result['content_type'] = 'TRANSACTIONAL'
                result['funnel_stage'] = 'BOFU'
                return result
            
            # Es un filtro/PLP
            result['type'] = 'FILTER'
            result['content_type'] = 'TRANSACTIONAL'
            result['funnel_stage'] = 'BOFU'
            result['facets'] = self._extract_facets_from_url(url)
            result['num_facets'] = len([v for v in result['facets'].values() if v])
            return result
        
        # ═══════════════════════════════════════════════════════════════════════
        # CONTENIDO INFORMACIONAL: fuera de /{categoria}/ (blog, guías, etc.)
        # ═══════════════════════════════════════════════════════════════════════
        
        # Patrones de contenido informacional por etapa
        informational_patterns = {
            'tofu': ['que-es', 'que-son', 'tipos-de', 'como-funciona', 'diferencia-entre', 
                     'ventajas', 'desventajas', 'historia-de'],
            'mofu': ['mejor', 'mejores', 'comparativa', 'vs', 'versus', 'guia', 'guide',
                     'como-elegir', 'como-comprar', 'top-', 'ranking', 'recomend'],
            'bofu': ['review', 'analisis', 'opinion', 'experiencia', 'unboxing', 
                     'prueba', 'test']
        }
        
        # Verificar si la URL menciona alguna variación del keyword
        mentions_category = any(var in url_lower for var in keyword_variations)
        
        if mentions_category:
            result['type'] = 'ARTICLE'
            result['content_type'] = 'INFORMATIONAL'
            
            # Clasificar etapa del funnel
            for stage, patterns in informational_patterns.items():
                if any(p in url_lower for p in patterns):
                    result['funnel_stage'] = stage.upper()
                    break
            else:
                result['funnel_stage'] = 'MOFU'  # Default para artículos
            
            return result
        
        # Contenido editorial genérico (sin mención de categoría pero con patrón editorial)
        editorial_patterns = ['mejor', 'mejores', 'guia', 'como-', 'comparativa', 'review', 'analisis', 'top-', 'ranking']
        if any(pattern in url_lower for pattern in editorial_patterns):
            result['type'] = 'ARTICLE'
            result['content_type'] = 'INFORMATIONAL'
            
            # Clasificar etapa del funnel
            for stage, patterns in informational_patterns.items():
                if any(p in url_lower for p in patterns):
                    result['funnel_stage'] = stage.upper()
                    break
            else:
                result['funnel_stage'] = 'MOFU'
            
            return result
        
        return result
    
    def _get_keyword_variations(self, keyword: str) -> List[str]:
        """Genera variaciones del keyword para detectar contenido relacionado
        
        Ej: "smartphone-moviles" -> ["smartphone-moviles", "smartphone", "moviles", "movil", "telefono", "móvil"]
        """
        variations = [keyword]
        
        # Separar por guiones
        parts = keyword.replace('_', '-').split('-')
        variations.extend(parts)
        
        # Añadir singulares/plurales comunes
        for part in parts:
            if part.endswith('es'):
                variations.append(part[:-2])  # moviles -> movil
                variations.append(part[:-1])  # moviles -> movile (por si acaso)
            elif part.endswith('s'):
                variations.append(part[:-1])  # smartphones -> smartphone
        
        # Sinónimos comunes por categoría
        synonym_map = {
            'movil': ['telefono', 'celular', 'móvil', 'teléfono'],
            'moviles': ['telefonos', 'celulares', 'móviles', 'teléfonos'],
            'smartphone': ['movil', 'telefono', 'celular'],
            'smartphones': ['moviles', 'telefonos', 'celulares'],
            'televisor': ['tv', 'television', 'tele'],
            'televisores': ['tvs', 'televisiones', 'teles'],
            'portatil': ['laptop', 'notebook', 'portátil'],
            'portatiles': ['laptops', 'notebooks', 'portátiles'],
            'ordenador': ['computadora', 'computador', 'pc'],
            'ordenadores': ['computadoras', 'computadores', 'pcs'],
            'tablet': ['tableta'],
            'tablets': ['tabletas'],
            'auricular': ['cascos', 'headphones', 'audifonos'],
            'auriculares': ['cascos', 'headphones', 'audífonos'],
        }
        
        for part in parts:
            part_lower = part.lower()
            if part_lower in synonym_map:
                variations.extend(synonym_map[part_lower])
        
        # Eliminar duplicados y vacíos
        variations = list(set(v for v in variations if v and len(v) > 2))
        
        return variations
    
    def _extract_facets_from_url(self, url: str) -> Dict:
        """Extrae facetas de una URL - GENÉRICO
        
        Retorna los segmentos del path después de la categoría
        """
        url_lower = url.lower()
        facets = {}
        
        pattern = rf'/{self.category_keyword}/([^?]*)'
        match = re.search(pattern, url_lower)
        
        if match:
            path_after_category = match.group(1).strip('/')
            segments = [s for s in path_after_category.split('/') if s]
            
            for i, segment in enumerate(segments):
                facets[f'segment_{i+1}'] = segment
        
        return facets
    
    def classify_query_intent(self, query: str) -> str:
        """Clasifica intención: INFORMATIONAL, TRANSACTIONAL, NAVIGATIONAL"""
        if pd.isna(query):
            return 'OTHER'
        
        query_lower = query.lower().strip()
        
        for nav in ['pccomponentes', 'pcc', 'mediamarkt', 'amazon', 'el corte ingles']:
            if nav in query_lower:
                return 'NAVIGATIONAL'
        
        info_markers = [
            'mejor', 'mejores', 'top', 'ranking', 'cual', 'cuál', 
            'que es', 'qué es', 'diferencia', 'vs', 'versus', 'comparativa',
            'guia', 'guía', 'como', 'cómo', 'elegir', 'recomend', 'opinion',
            'review', 'análisis', 'vale la pena', 'calidad precio',
            'medidas', 'dimensiones', '2024', '2025', '2026'
        ]
        
        for marker in info_markers:
            if marker in query_lower:
                return 'INFORMATIONAL'
        
        return 'TRANSACTIONAL'
    
    def classify_query_funnel(self, query: str) -> Dict:
        """Clasifica query por etapa del funnel y detecta drivers de compra
        
        Returns:
            Dict con: intent, funnel_stage, drivers, content_opportunity
        """
        if pd.isna(query):
            return {'intent': 'OTHER', 'funnel_stage': 'OTHER', 'drivers': [], 'content_type': None}
        
        query_lower = query.lower().strip()
        result = {
            'intent': self.classify_query_intent(query),
            'funnel_stage': 'BOFU',
            'drivers': [],
            'content_type': None
        }
        
        # ═══════════════════════════════════════════════════════════════════════
        # TOFU (Awareness) - Preguntas genéricas, educación
        # ═══════════════════════════════════════════════════════════════════════
        tofu_patterns = [
            'que es', 'qué es', 'que son', 'qué son', 'para que sirve', 
            'como funciona', 'cómo funciona', 'tipos de', 'diferencia entre',
            'ventajas', 'desventajas', 'pros y contras', 'merece la pena',
            'historia de', 'evolución de', 'futuro de'
        ]
        if any(p in query_lower for p in tofu_patterns):
            result['funnel_stage'] = 'TOFU'
            result['content_type'] = 'educational'
        
        # ═══════════════════════════════════════════════════════════════════════
        # MOFU (Consideration) - Comparación, evaluación
        # ═══════════════════════════════════════════════════════════════════════
        mofu_patterns = [
            'mejor', 'mejores', 'top', 'ranking', 'comparativa', 'comparar',
            'vs', 'versus', 'o ', ' o ', 'cual elegir', 'cuál elegir',
            'cual comprar', 'cuál comprar', 'recomend', 'guia', 'guía',
            'como elegir', 'cómo elegir', 'calidad precio', 'relacion calidad',
            'gama alta', 'gama media', 'gama baja', 'barato', 'económico',
            'premium', 'profesional'
        ]
        if any(p in query_lower for p in mofu_patterns):
            result['funnel_stage'] = 'MOFU'
            result['content_type'] = 'comparison'
        
        # ═══════════════════════════════════════════════════════════════════════
        # BOFU (Decision) - Producto/modelo específico, compra
        # ═══════════════════════════════════════════════════════════════════════
        bofu_patterns = [
            'comprar', 'precio', 'oferta', 'descuento', 'donde comprar',
            'review', 'análisis', 'opinion', 'opiniones', 'experiencia',
            'unboxing', 'test', 'prueba'
        ]
        if any(p in query_lower for p in bofu_patterns):
            result['funnel_stage'] = 'BOFU'
            result['content_type'] = 'transactional' if 'comprar' in query_lower or 'precio' in query_lower else 'review'
        
        # ═══════════════════════════════════════════════════════════════════════
        # DETECTAR DRIVERS DE COMPRA (atributos mencionados)
        # ═══════════════════════════════════════════════════════════════════════
        
        # Normalizar query (quitar tildes para matching)
        query_normalized = query_lower
        accent_map = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n'}
        for accented, plain in accent_map.items():
            query_normalized = query_normalized.replace(accented, plain)
        
        driver_patterns = {
            'precio': ['barato', 'economico', 'precio', 'oferta', 'descuento', 'calidad precio', 'low cost', 'chollo'],
            'marca': ['samsung', 'apple', 'xiaomi', 'sony', 'lg', 'huawei', 'oppo', 'realme', 'google', 'oneplus', 
                      'iphone', 'pixel', 'motorola', 'nokia', 'honor', 'vivo', 'asus', 'tcl', 'hisense'],
            'rendimiento': ['potente', 'rapido', 'rendimiento', 'procesador', 'ram', 'velocidad', 'gaming', 'gamer', 'snapdragon', 'mediatek'],
            'tamaño': ['pulgadas', 'grande', 'pequeno', 'compacto', 'tamano', 'dimensiones', 'pantalla grande', 'mini'],
            'calidad_imagen': ['resolucion', '4k', '8k', 'full hd', 'hd', 'oled', 'qled', 'amoled', 'ips', 'retina'],
            'bateria': ['bateria', 'autonomia', 'duracion', 'carga rapida', 'mah', 'carga inalambrica'],
            'camara': ['camara', 'camaras', 'fotos', 'megapixeles', 'mpx', 'zoom', 'video', 'grabacion', 'selfie', 'fotografico'],
            'almacenamiento': ['gb', 'tb', 'almacenamiento', 'memoria', 'capacidad', 'espacio', '128', '256', '512', '1tb'],
            'conectividad': ['5g', 'wifi', 'bluetooth', 'nfc', 'usb', 'hdmi', 'wifi 6', 'dual sim', 'esim'],
            'diseno': ['diseno', 'color', 'elegante', 'premium', 'acabado', 'ligero', 'fino', 'cristal', 'titanio'],
            'durabilidad': ['resistente', 'duradero', 'ip68', 'ip67', 'agua', 'golpes', 'proteccion', 'rugerizado', 'militar'],
            'ecosistema': ['compatible', 'integracion', 'homekit', 'google home', 'alexa', 'app', 'sincronizar'],
        }
        
        for driver, keywords in driver_patterns.items():
            for kw in keywords:
                # Usar word boundaries para evitar falsos positivos como "smart" en "smartphone"
                if len(kw) <= 3:
                    # Keywords cortos: match exacto con espacios o inicio/fin
                    if f' {kw} ' in f' {query_normalized} ' or f' {kw}' in f' {query_normalized}' or f'{kw} ' in f'{query_normalized} ':
                        result['drivers'].append(driver)
                        break
                else:
                    # Keywords largos: substring match es seguro
                    if kw in query_normalized:
                        result['drivers'].append(driver)
                        break
        
        return result
    
    def suggest_filter_url(self, query: str) -> str:
        """Sugiere URL de filtro para query transaccional"""
        if not query:
            return f"/{self.category_keyword}"
        
        # URL base - los valores específicos se detectan de los datos
        return f"/{self.category_keyword}"


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
